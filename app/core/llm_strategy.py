from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

import ollama
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

import app.data.pkmn_types as pkmn_types
from app.core.combat import (
    calculate_damage,
    reset_on_switch_out,
    struggle_no_pp,
    try_atk_status,
)
from app.schemas.move import Move
from app.schemas.typing import Typing

if TYPE_CHECKING:
    from app.core.player import Trainer
    from app.schemas.battle_pokemon import BattlePokemon

logger = logging.getLogger(__name__)

_TYPE_MAP = {t.value: t for t in Typing}


@tool
def _ping() -> str:
    """Return 'pong' to verify tool calling."""
    return 'pong'


class BattleDecision(BaseModel):
    """Structured output from the LLM agent for a single turn decision."""

    action: Literal['attack', 'switch'] = Field(
        description='Choose attack to use a move, switch to change active Pokémon',
    )
    move: str | None = Field(
        default=None,
        description='Exact move name (required if action is attack)',
    )
    slot: int | None = Field(
        default=None, ge=0, le=5,
        description='Team slot to switch to, 0=active (required if action is switch)',
    )
    reasoning: str = Field(
        description='Brief strategic reasoning for this decision',
    )


class AgentState(TypedDict):
    """State type for the LangGraph agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


SYSTEM_PROMPT = '''You are an AI battle strategist for Pokémon Generation 1 (Red/Blue).

=== BATTLE RULES ===
STAB: 1.5x damage if move type matches attacker type.
Type chart: Normal→Ghost=0x, Electric→Ground=0x, Fighting→Ghost=0x, etc.
Critical hit: base_speed/2 threshold vs random 0-255 roll.
Burn: physical moves do 50% damage. 1/16 max HP per turn.
Paralyze: speed -75%, 25% chance can't move.
Sleep: 33% wake chance each turn.
Freeze: 20% thaw chance each turn.
Poison: 1/16 max HP per turn.
Toxic: +1/16 max HP each turn (caps at 15/16).
Confusion: 50% chance to self-hit (40 base power typeless).
Reflect: halves physical damage for 5 turns.
Light Screen: halves special damage for 5 turns.
No abilities, no hold items. SpDef = SpAtk.

=== INSTRUCTIONS ===
Analyze the situation. Use the tools to simulate damage or check type matchups.
Choose the best action. Output your decision using the provided structured response schema.
'''


def list_ollama_models(base_uri: str) -> tuple[bool, list[str] | str]:
    """List available models from an Ollama server via its API.

    Args:
        base_uri (str): Ollama server base URL (e.g. 'http://localhost:11434').

    Returns:
        tuple[bool, list[str] | str]: (True, model names) on success,
            (False, error message) if the server is unreachable or the
            request failed.
    """
    try:
        resp = ollama.Client(host=base_uri).list()
        models = [m.model for m in resp.models if m.model is not None]
        return True, models
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


def verify_llm_connection(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_uri: str | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Test LLM connectivity and tool-calling capability.

    Checks:
    1. Model creation and basic text response.
    2. Tool calling via a minimal ReAct agent with a dummy tool.

    Returns (success, message). On failure message contains the raw error.
    """
    try:
        llm = _create_model(provider, model, api_key, base_uri)

        response = llm.invoke(
            [HumanMessage(content="Reply with only the word: PONG")],
        )
        content = (response.content or "").strip()
        if "PONG" not in content.upper():
            return False, (
                f"Unexpected response: {content[:80]!r}. "
                "Expected 'PONG'."
            )

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


def _create_model(
    provider: str, model: str | None = None,
    api_key: str | None = None, base_uri: str | None = None,
) -> Any:
    """Create a LangChain chat model for the given provider.

    Args:
        provider (str): One of 'openai', 'anthropic', 'gemini', 'ollama'.
        model (str | None): Model name override.
        api_key (str | None): API key override.
        base_uri (str | None): Base URI override (Ollama only).

    Returns:
        ChatModel: A LangChain chat model instance.
    """
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
            return ChatOllama(model=model or 'llama3.1', temperature=0.2, base_url=base_uri or 'http://localhost:11434')
        case _:
            msg = f'Unknown LLM provider: {provider}'
            raise ValueError(msg)


def _make_tools(trainer: Trainer, rival: Trainer) -> list:
    """Create tool definitions for the LLM agent (module-level version).

    Returns:
        list: List of LangChain Tool objects.
    """
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
    """Format a stat stage multiplier as a short string.

    Returns:
        str: Formatted multiplier string like 'x1.5' or 'x0.5'.
    """
    return f'x{mult:g}'


def _build_state_str(trainer: Trainer, rival: Trainer) -> str:
    """Build a string describing the current battle state for the LLM.

    Returns:
        str: Formatted battle state description.
    """
    a = trainer.in_battle
    d = rival.in_battle

    def _status(p: BattlePokemon) -> str:
        return p.status.value if p.status else 'None'

    def _stages(p: BattlePokemon) -> str:
        return (
            f'Atk{_stat_stage_str(p.atk_mult)} '
            f'Def{_stat_stage_str(p.def_mult)} '
            f'SpA{_stat_stage_str(p.sp_atk_mult)} '
            f'SpD{_stat_stage_str(p.sp_def_mult)} '
            f'Spe{_stat_stage_str(p.speed_mult)} '
            f'Acc{_stat_stage_str(p.acc_mult)} '
            f'Eva{_stat_stage_str(p.ev_mult)}'
        )

    def _bench(team: list[BattlePokemon | None], exclude: BattlePokemon, label: str) -> str:
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

    def _moves(p: BattlePokemon) -> str:
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
    """AI strategy that uses a LangGraph agent with an LLM to make battle decisions."""

    def __init__(
        self, provider: str, model: str | None = None,
        api_key: str | None = None, base_uri: str | None = None,
    ):
        """Initialize the LLM agent strategy.

        Args:
            provider (str): LLM provider ('openai', 'anthropic', 'gemini', 'ollama').
            model (str | None): Model name override.
            api_key (str | None): API key override.
            base_uri (str | None): Base URI override (Ollama only).
        """
        self.choices: list[str] = []
        self._turn_count: int = 0
        self._llm = _create_model(provider, model, api_key, base_uri)
        self._trainer: Trainer | None = None
        self._rival: Trainer | None = None
        self._checkpointer = MemorySaver()
        self._thread_id = str(uuid.uuid4())
        self._agent = create_agent(
            self._llm,
            self._make_tools(),
            system_prompt=SYSTEM_PROMPT,
            response_format=BattleDecision,
            checkpointer=self._checkpointer,
        )

    def _make_tools(self) -> list:
        """Create tool definitions for this agent instance.

        Returns:
            list: List of LangChain Tool objects.
        """
        @tool
        def simulate_damage(move_name: str) -> int:
            '''Calculate expected damage for a named move against the current opponent.'''
            t = self._trainer
            r = self._rival
            if t is None or r is None:
                return 0
            move = next(
                (m for m in t.in_battle.moves if m is not None and m.name == move_name),
                None,
            )
            if move is None:
                return 0
            dmg, _ = calculate_damage(t.in_battle, move, r.in_battle)
            return dmg

        @tool
        def get_type_effectiveness(move_type: str) -> str:
            '''Check type matchup of a move type against opponent\'s types.'''
            r = self._rival
            if r is None:
                return 'No opponent'
            t = _TYPE_MAP.get(move_type)
            if t is None:
                return f'Unknown type: {move_type}'
            types_str = ', '.join(t.value for t in r.in_battle.typing)
            eff = pkmn_types.get_effectiveness(t, r.in_battle.typing[0])
            if len(r.in_battle.typing) == 2:
                eff *= pkmn_types.get_effectiveness(t, r.in_battle.typing[1])
            if eff == 0:
                return f'no effect (0x) against {types_str}'
            if eff < 1:
                return f'not very effective ({eff}x) against {types_str}'
            if eff == 1:
                return f'neutral (1x) against {types_str}'
            return f'super effective ({eff}x) against {types_str}'

        return [simulate_damage, get_type_effectiveness]

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        """Get the LLM's move choice for the current turn.

        Delegates to the LangGraph agent which returns a BattleDecision.

        Args:
            trainer (Trainer): The AI trainer.
            rival (Trainer): The opposing trainer.

        Returns:
            str | None: Battle message from the chosen action.
        """
        trainer.verify_fainted_switch()
        if trainer.game_over_lose():
            return None

        choices = trainer.get_possible_choices()
        if not choices:
            return struggle_no_pp(trainer.in_battle, rival.in_battle)

        self._trainer = trainer
        self._rival = rival
        self._turn_count += 1

        state_str = _build_state_str(trainer, rival)
        user_msg = (
            f'=== CURRENT BATTLE STATE (Turn {self._turn_count}) ===\n'
            f'{state_str}\n'
            'Choose the best action for this turn.'
        )

        result = self._agent.invoke(
            {'messages': [HumanMessage(content=user_msg)]},
            {'configurable': {'thread_id': self._thread_id}},
        )
        decision = result.get('structured_response')
        if not isinstance(decision, BattleDecision):
            logger.warning('No structured response, falling back to first valid move')
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
        """Execute an attack action chosen by the LLM.

        Returns:
            str: Battle message from the executed move.
        """
        move = next(
            (m for m in trainer.in_battle.moves if m is not None and m.name == decision.move),
            None,
        )
        if move is None:
            choices = trainer.get_possible_choices()
            if not choices:
                return struggle_no_pp(trainer.in_battle, rival.in_battle)
            chosen = choices[0].target
            assert isinstance(chosen, Move)
            move = chosen

        self.choices.append(move.name)
        return try_atk_status(trainer.in_battle, move, rival.in_battle)

    def _execute_switch(
        self, trainer: Trainer, rival: Trainer, decision: BattleDecision,
    ) -> str:
        """Execute a switch action chosen by the LLM.

        Returns:
            str: Battle message announcing the switch.
        """
        slot = decision.slot if decision.slot is not None else 0
        target = trainer.team[slot]
        if target is None or target.fainted or target is trainer.in_battle:
            return self._fallback_attack(trainer, rival)

        old = trainer.in_battle
        reset_on_switch_out(old)

        trainer.in_battle = target
        target.on_field = True

        self.choices.append(f'switch:{target.name}')

        return f'{trainer.name} sent out {target.name}! Go, {target.name}!'

    def _fallback_attack(self, trainer: Trainer, rival: Trainer) -> str:
        """Fallback to the first valid move if the LLM decision is invalid.

        Returns:
            str: Battle message from the chosen move.
        """
        choices = trainer.get_possible_choices()
        if choices:
            move = choices[0].target
            assert isinstance(move, Move)
            self.choices.append(move.name)
            return try_atk_status(trainer.in_battle, move, rival.in_battle)
        return struggle_no_pp(trainer.in_battle, rival.in_battle)
