from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Literal, TypedDict

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

import app.data.pkmn_types as pkmn_types
from app.core.combat import (
    calculate_damage,
    reset_battle_stats,
    reset_stats_mult,
    struggle_no_pp,
    try_atk_status,
)
from app.schemas.typing import Typing

if TYPE_CHECKING:
    from app.core.player import Trainer

logger = logging.getLogger(__name__)

_TYPE_MAP = {t.value: t for t in Typing}


class BattleDecision(BaseModel):
    action: Literal['attack', 'switch']
    move: str | None = None
    slot: int | None = Field(default=None, ge=0, le=5)
    reasoning: str


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


SYSTEM_PROMPT = '''You are an AI battle strategist for Pokémon Generation 1 (Red/Blue).

=== BATTLE RULES ===
STAB: 1.5x damage if move type matches attacker type.
Type chart: Normal→Ghost=0x, Electric→Ground=0x, Fighting→Ghost=0x, etc.
Critical hit: base_speed/2 threshold vs random 0-255 roll.
Burn: physical moves do 50% damage. 1/16 max HP per turn.
Paralyze: speed -75%, 25% chance can\'t move.
Sleep: 33% wake chance each turn.
Freeze: 20% thaw chance each turn.
Poison: 1/16 max HP per turn.
Toxic: +1/16 max HP each turn (caps at 15/16).
Confusion: 50% chance to self-hit (40 base power typeless).
Reflect: halves physical damage for 5 turns.
Light Screen: halves special damage for 5 turns.
No abilities, no hold items. SpDef = SpAtk.

=== BATTLE HISTORY (most recent first) ===
{history}

=== CURRENT STATE ===
{state}

=== INSTRUCTIONS ===
Analyze the situation. Use the tools to simulate damage or check type matchups.
Choose the best action.

Respond with a raw JSON object. No markdown, no code fences, no extra text.

For attack:
{{"action": "attack", "move": "ExactMoveName", "reasoning": "Brief strategic reasoning"}}

For switch (slot 0 = active Pokémon, bench slots are 1-5):
{{"action": "switch", "slot": N, "reasoning": "Brief strategic reasoning"}}
'''


def verify_llm_connection(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Test LLM connectivity and tool-calling capability.

    Checks:
    1. Model creation and basic text response.
    2. Tool calling via a minimal ReAct agent with a dummy tool.

    Returns (success, message). On failure message contains the raw error.
    """
    try:
        llm = _create_model(provider, model, api_key)

        response = llm.invoke(
            [HumanMessage(content="Reply with only the word: PONG")],
        )
        content = (response.content or "").strip()
        if "PONG" not in content.upper():
            return False, (
                f"Unexpected response: {content[:80]!r}. "
                "Expected 'PONG'."
            )

        @tool
        def _ping() -> str:
            """Return 'pong' to verify tool calling."""
            return "pong"

        agent = create_agent(llm, [_ping])
        result = agent.invoke({
            "messages": [
                HumanMessage(content="Call the ping tool and tell me the result."),
            ],
        })
        final = result["messages"][-1].content
        if "pong" not in str(final).lower():
            return False, (
                f"Tool calling failed — unexpected agent output: "
                f"{str(final)[:80]!r}"
            )

        return True, (
            f"LLM ready ({model or 'default'}) — responds + tool calling OK"
        )

    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _create_model(provider: str, model: str | None = None, api_key: str | None = None):
    kwargs = {}
    if api_key:
        kwargs['api_key'] = api_key
    match provider:
        case 'openai':
            return ChatOpenAI(model=model or 'gpt-4o', temperature=0.2, **kwargs)
        case 'anthropic':
            return ChatAnthropic(model=model or 'claude-sonnet-4-20250514', **kwargs)
        case 'gemini':
            return ChatGoogleGenerativeAI(model=model or 'gemini-2.0-flash', **kwargs)
        case 'ollama':
            return ChatOllama(model=model or 'llama3.1', temperature=0.2)
        case _:
            msg = f'Unknown LLM provider: {provider}'
            raise ValueError(msg)


def _make_tools(trainer: Trainer, rival: Trainer) -> list:
    @tool
    def simulate_damage(move_name: str) -> int:
        '''Calculate expected damage for a named move against the current opponent.'''
        move = next(
            (m for m in trainer.in_battle.moves if m is not None and m.name == move_name),
            None,
        )
        if move is None:
            return 0
        dmg, _ = calculate_damage(trainer.in_battle, move, rival.in_battle)
        return dmg

    @tool
    def get_type_effectiveness(move_type: str) -> str:
        '''Check type matchup of a move type against opponent\'s types.'''
        t = _TYPE_MAP.get(move_type)
        if t is None:
            return f'Unknown type: {move_type}'
        types_str = ', '.join(t.value for t in rival.in_battle.typing)
        eff = pkmn_types.get_effectiveness(t, rival.in_battle.typing[0])
        if len(rival.in_battle.typing) == 2:
            eff *= pkmn_types.get_effectiveness(t, rival.in_battle.typing[1])
        if eff == 0:
            return f'no effect (0x) against {types_str}'
        if eff < 1:
            return f'not very effective ({eff}x) against {types_str}'
        if eff == 1:
            return f'neutral (1x) against {types_str}'
        return f'super effective ({eff}x) against {types_str}'

    return [simulate_damage, get_type_effectiveness]


def _stat_stage_str(mult: float) -> str:
    return f'x{mult:g}'


def _build_state_str(trainer: Trainer, rival: Trainer) -> str:
    a = trainer.in_battle
    d = rival.in_battle

    def _status(p):
        return p.status.value if p.status else 'None'

    def _stages(p):
        return (
            f'Atk{_stat_stage_str(p.atk_mult)} '
            f'Def{_stat_stage_str(p.def_mult)} '
            f'SpA{_stat_stage_str(p.sp_atk_mult)} '
            f'SpD{_stat_stage_str(p.sp_def_mult)} '
            f'Spe{_stat_stage_str(p.speed_mult)} '
            f'Acc{_stat_stage_str(p.acc_mult)} '
            f'Eva{_stat_stage_str(p.ev_mult)}'
        )

    def _bench(team, exclude, label: str) -> str:
        lines = []
        for i, p in enumerate(team):
            if p is None or p is exclude:
                continue
            if p.fainted:
                lines.append(f'  [{i}] {p.name} - Fainted')
            else:
                s = p.status.value if p.status else 'None'
                lines.append(f'  [{i}] {p.name} ({p.hp}/{p.max_hp} HP) | Sts: {s}')
        return label + '\n' + ('\n'.join(lines) if lines else '  (none)')

    def _moves(p) -> str:
        lines = []
        for i, m in enumerate(p.moves):
            if m is None:
                continue
            power = str(m.power) if m.power else '-'
            lines.append(
                f'  [{i}] {m.name} - {m.typing.value} | {m.category.value}'
                f' | Pow {power} | Acc {m.accuracy} | PP {m.pp}'
            )
        return '\n'.join(lines)

    state = '=== YOUR TEAM ===\n'
    state += f'Active: {a.name} ({a.hp}/{a.max_hp} HP) | Status: {_status(a)}\n'
    state += f'  {_stages(a)}\n'
    state += 'Moves:\n' + _moves(a) + '\n'
    state += _bench(trainer.team, a, 'Bench:') + '\n\n'

    state += '=== OPPONENT TEAM ===\n'
    state += f'Active: {d.name} ({d.hp}/{d.max_hp} HP) | Status: {_status(d)}\n'
    state += _bench(rival.team, d, 'Bench:') + '\n\n'

    reflect_self = 'Yes' if a.reflect else 'No'
    ls_self = 'Yes' if a.light_screen else 'No'
    mist_self = 'Yes' if a.mist else 'No'
    reflect_opp = 'Yes' if d.reflect else 'No'
    ls_opp = 'Yes' if d.light_screen else 'No'
    mist_opp = 'Yes' if d.mist else 'No'

    sub_self = 'Yes' if a.substitute else 'No'
    sub_opp = 'Yes' if d.substitute else 'No'

    state += '=== FIELD ===\n'
    state += (
        f'Your side: Reflect={reflect_self}, LS={ls_self}, Mist={mist_self}'
        f' | Sub={sub_self}\n'
    )
    state += (
        f'Opponent side: Reflect={reflect_opp}, LS={ls_opp}, Mist={mist_opp}'
        f' | Sub={sub_opp}\n'
    )

    return state


class LLMAgentStrategy:
    def __init__(self, provider: str, model: str | None = None, api_key: str | None = None):
        self.choices: list[str] = []
        self._battle_log: list[str] = []
        self._turn_count: int = 0
        self._llm = _create_model(provider, model, api_key)

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        trainer.verify_fainted_switch()
        if trainer.game_over_lose():
            return None

        choices = trainer.get_possible_choices()
        if not choices:
            return struggle_no_pp(trainer.in_battle, rival.in_battle)

        prompt = SYSTEM_PROMPT.format(
            history=self._format_history(),
            state=_build_state_str(trainer, rival),
        )

        messages: list[BaseMessage] = [
            SystemMessage(content=prompt),
            HumanMessage(content='Choose the best action for this turn.'),
        ]

        tools = _make_tools(trainer, rival)
        agent = create_agent(self._llm, tools)
        result = agent.invoke({'messages': messages})
        final = result['messages'][-1]

        self._turn_count += 1

        try:
            decision = self._parse_decision(final.content)
        except Exception:
            logger.warning('Failed to parse LLM output, falling back to first valid move')
            first = choices[0]
            decision = BattleDecision(
                action='attack', move=first.target.name, reasoning='fallback',
            )

        match decision.action:
            case 'attack':
                return self._execute_attack(trainer, rival, decision)
            case 'switch':
                return self._execute_switch(trainer, rival, decision)
            case _:
                first = choices[0]
                decision = BattleDecision(
                    action='attack', move=first.target.name, reasoning='fallback',
                )
                return self._execute_attack(trainer, rival, decision)

    def _execute_attack(
        self, trainer: Trainer, rival: Trainer, decision: BattleDecision,
    ) -> str:
        move = next(
            (m for m in trainer.in_battle.moves if m is not None and m.name == decision.move),
            None,
        )
        if move is None:
            choices = trainer.get_possible_choices()
            if choices:
                move = choices[0].target
            else:
                return struggle_no_pp(trainer.in_battle, rival.in_battle)

        self.choices.append(move.name)
        result = try_atk_status(trainer.in_battle, move, rival.in_battle)

        self._battle_log.append(
            f'Turn {self._turn_count}: {trainer.in_battle.name} used {move.name}',
        )

        return result

    def _execute_switch(
        self, trainer: Trainer, rival: Trainer, decision: BattleDecision,
    ) -> str:
        slot = decision.slot if decision.slot is not None else 0
        target = trainer.team[slot]
        if target is None or target.fainted or target is trainer.in_battle:
            return self._fallback_attack(trainer, rival)

        old = trainer.in_battle
        old.substitute = False
        reset_stats_mult(old)
        reset_battle_stats(old)
        old.temp_status = None
        old.on_field = False

        trainer.in_battle = target
        target.on_field = True

        self.choices.append(f'switch:{target.name}')
        self._battle_log.append(
            f'Turn {self._turn_count}: Switched {old.name} -> {target.name}',
        )

        return f'{trainer.name} sent out {target.name}! Go, {target.name}!'

    def _fallback_attack(self, trainer: Trainer, rival: Trainer) -> str:
        choices = trainer.get_possible_choices()
        if choices:
            move = choices[0].target
            self.choices.append(move.name)
            result = try_atk_status(trainer.in_battle, move, rival.in_battle)
            self._battle_log.append(
                f'Turn {self._turn_count}: {trainer.in_battle.name} used {move.name}',
            )
            return result
        return struggle_no_pp(trainer.in_battle, rival.in_battle)

    def _format_history(self) -> str:
        if not self._battle_log:
            return '(no previous turns)'
        return '\n'.join(reversed(self._battle_log))

    @staticmethod
    def _parse_decision(content: str) -> BattleDecision:
        raw = content.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
            raw = raw.strip()
        return BattleDecision.model_validate_json(raw)
