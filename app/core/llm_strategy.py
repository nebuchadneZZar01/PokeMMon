from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Sequence
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
    try_atk_status,
    update_battle_stat,
)
from app.schemas.effect_status import EffectStatus
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
Critical hit: base_speed/2 threshold vs random 0-255 roll; Focus Energy x4.
  Crits ignore the attacker's negative stat stages and the target's positive stat
  stages, plus Reflect/Light Screen.
Burn: physical moves do 50% damage. 1/8 max HP per turn.
Paralyze: speed -75%, 25% chance can't move. (Electric types immune.)
Freeze: 20% thaw chance each turn (no type is immune).
Sleep: 1-3 turns (Rest exactly 2 turns).
Poison: 1/16 max HP per turn (Poison types immune).
Toxic: +1/16 max HP each turn (caps at 15/16).
Confusion: 50% chance to self-hit (40 base power typeless), lasts 2-5 turns.
Reflect: halves physical damage for 5 turns (persists across switches).
Light Screen: halves special damage for 5 turns (persists across switches).
Mist: blocks stat drops for 5 turns (persists across switches).
Substitute: costs 25% max HP and absorbs 25% max HP.
Grass types are immune to powder moves (Sleep Powder, Stun Spore, Poison
  Powder, Spore). Electric types are immune to paralysis.
Disable: blocks a target move for 4 turns.
Trapping (Wrap/Bind/Clamp/Fire Spin): 2-5 turns, 50% chance target can't move,
  and the target cannot switch.
Rampage (Thrash/Petal Dance): 2-3 turns, then the user becomes confused.
Hyper Beam: recharge only if it hits and the target survives.
Charge moves: Dig/Fly hide the user (unhittable that turn); Solar Beam, Razor
  Wind, Sky Attack, Skull Bash charge first, roll damage the following turn.
Bide: stores incoming damage for 2-3 turns, then deals double back.
OHKO moves (Fissure/Guillotine/Horn Drill): accuracy = 30 + (user level -
  target level)% (clamped 0-100); fail if the target's level is higher or
  the target has a Substitute.
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


def _make_tool_defs(
    get_state: Callable[[], tuple[Trainer | None, Trainer | None]],
) -> list:
    """Build the LLM agent's tool definitions against a state getter.

    Args:
        get_state (Callable[[], tuple[Trainer | None, Trainer | None]]): Callable
            returning the current trainer and rival.

    Returns:
        list: List of LangChain Tool objects.
    """
    @tool
    def simulate_damage(move_name: str) -> int:
        '''Calculate expected damage for a named move against the current opponent.'''
        t, r = get_state()
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
        _, r = get_state()
        if r is None:
            return 'No opponent'
        m = _TYPE_MAP.get(move_type)
        if m is None:
            return f'Unknown type: {move_type}'
        types_str = ', '.join(t.value for t in r.in_battle.typing)
        eff = pkmn_types.overall_effectiveness(m, r.in_battle.typing)
        if eff == 0:
            return f'no effect (0x) against {types_str}'
        if eff < 1:
            return f'not very effective ({eff}x) against {types_str}'
        if eff == 1:
            return f'neutral (1x) against {types_str}'
        return f'super effective ({eff}x) against {types_str}'

    return [simulate_damage, get_type_effectiveness]


def _make_tools(trainer: Trainer, rival: Trainer) -> list:
    """Create tool definitions for the LLM agent (module-level version).

    Args:
        trainer (Trainer): The AI trainer.
        rival (Trainer): The opposing trainer.

    Returns:
        list: List of LangChain Tool objects.
    """
    return _make_tool_defs(lambda: (trainer, rival))


def _stat_stage_str(mult: int) -> str:
    """Format a stat stage as its real Gen 1 damage multiplier.

    The stage integer is converted through ``update_battle_stat`` so the
    label matches the actual multiplier used in damage calculation: e.g.
    +1 renders as 'x1.5', -1 as 'x0.66', +6 as 'x4'.

    Args:
        mult (int): The stat stage (-6 to +6).

    Returns:
        str: Formatted multiplier string like 'x1.5' or 'x0.5'.
    """
    return f'x{update_battle_stat(1.0, mult):g}'


def _build_state_str(trainer: Trainer, rival: Trainer) -> str:
    """Build a string describing the current battle state for the LLM.

    Covers both active Pokémon: HP, level, primary and temporary status,
    stat stages, remaining substitutes, and every battle flag that affects
    decision making (charging, rampage, rage, bide, recharge, trap,
    focus energy, transform, disabled move).

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

    def _status_line(p: BattlePokemon) -> str:
        label = _status(p)
        if p.status == EffectStatus.SLEEP and p.sleeping_turns > 0:
            label = f'Sleep ({p.sleeping_turns} turns left)'
        if p.temp_status == EffectStatus.CONFUSION:
            label += f' + Confusion ({p.confused_turns} turns left)'
        return label

    def _flags(p: BattlePokemon) -> list[str]:
        flags: list[str] = []
        if p.recharging:
            flags.append('Must recharge')
        if p.biding:
            flags.append('Biding')
        if p.charging:
            flags.append(f'Charging {p.charge_move}')
        if p.rampaging:
            flags.append(f'Rampaging {p.rampage_move}')
        if p.raging:
            flags.append('Raging')
        if p.trapped:
            flags.append(f'Trapped ({p.trapped_turns} turns)')
        if p.focus_energy:
            flags.append('Focus Energy')
        if p.transformed:
            flags.append('Transformed')
        if p.disabled_move != -1:
            disabled = p.moves[p.disabled_move]
            name = disabled.name if disabled else '?'
            flags.append(f'{name} disabled')
        if p.substitute:
            remain = max(0, p.sub_max - p.sub_damage)
            flags.append(f'Substitute (absorbs {remain}/{p.sub_max} HP)')
        return flags

    def _active_line(p: BattlePokemon) -> str:
        lines = [
            f'Active: {p.name} ({p.hp}/{p.max_hp} HP) | Lv{p.level}',
            f'  Status: {_status_line(p)}',
            f'  {_stages(p)}',
        ]
        flags = _flags(p)
        if flags:
            lines.append('  Flags: ' + ', '.join(flags))
        return '\n'.join(lines)

    state = '=== YOUR TEAM ===\n'
    state += _active_line(a) + '\n'
    state += 'Moves:\n' + _moves(a) + '\n'
    state += _bench(trainer.team, a, 'Bench:') + '\n\n'

    state += '=== OPPONENT TEAM ===\n'
    state += _active_line(d) + '\n'
    state += 'Moves:\n' + _moves(d) + '\n'
    state += _bench(rival.team, d, 'Bench:') + '\n\n'

    reflect_self = 'Yes' if a.reflect else 'No'
    ls_self = 'Yes' if a.light_screen else 'No'
    mist_self = 'Yes' if a.mist else 'No'
    reflect_opp = 'Yes' if d.reflect else 'No'
    ls_opp = 'Yes' if d.light_screen else 'No'
    mist_opp = 'Yes' if d.mist else 'No'
    if a.reflect:
        reflect_self = f'Yes ({a.reflect_turns})'
    if a.light_screen:
        ls_self = f'Yes ({a.light_screen_turns})'
    if a.mist:
        mist_self = f'Yes ({a.mist_turns})'
    if d.reflect:
        reflect_opp = f'Yes ({d.reflect_turns})'
    if d.light_screen:
        ls_opp = f'Yes ({d.light_screen_turns})'
    if d.mist:
        mist_opp = f'Yes ({d.mist_turns})'

    state += '=== FIELD ===\n'
    state += (
        f'Your side: Reflect={reflect_self}, LS={ls_self}, Mist={mist_self}\n'
    )
    state += (
        f'Opponent side: Reflect={reflect_opp}, LS={ls_opp}, Mist={mist_opp}\n'
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
        return _make_tool_defs(lambda: (self._trainer, self._rival))

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
            return trainer.struggle(rival)

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
        choices = trainer.get_possible_choices()
        move = next(
            (m for m in trainer.in_battle.moves if m is not None and m.name == decision.move),
            None,
        )
        if move is None or all(c.target is not move for c in choices):
            if not choices:
                return trainer.struggle(rival)
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
        if (target is None or target.fainted or target is trainer.in_battle
                or trainer.in_battle.trapped
                or trainer.in_battle.charging
                or trainer.in_battle.rampaging
                or trainer.in_battle.raging):
            return self._fallback_attack(trainer, rival)

        self.choices.append(f'switch:{target.name}')
        return trainer.strategic_switch(target)

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
        return trainer.struggle(rival)
