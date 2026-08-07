from __future__ import annotations

from unittest.mock import MagicMock

import ollama
import pytest
from ollama import RequestError, ResponseError

from app.core.llm_strategy import (
    SYSTEM_PROMPT,
    BattleDecision,
    LLMAgentStrategy,
    _build_state_str,
    _create_model,
    _make_tools,
    _ping,
    _stat_stage_str,
    list_ollama_models,
    verify_llm_connection,
)
from app.core.player import Trainer
from app.schemas.effect_status import EffectStatus
from app.schemas.typing import Typing

from .conftest import make_move, make_pkmn


class _FakeModel:
    def __init__(self, name: str):
        self.model = name


class _FakeListResponse:
    def __init__(self, models: list[_FakeModel]):
        self.models = models


class _FakeClient:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def list(self):
        if self._error is not None:
            raise self._error
        return self._response


def test_returns_model_names(monkeypatch):
    resp = _FakeListResponse([_FakeModel('llama3.1:latest'), _FakeModel('mistral')])
    monkeypatch.setattr(ollama, 'Client', lambda **kw: _FakeClient(response=resp))

    ok, result = list_ollama_models('http://localhost:11434')

    assert ok is True
    assert result == ['llama3.1:latest', 'mistral']


def test_empty_models(monkeypatch):
    monkeypatch.setattr(ollama, 'Client', lambda **kw: _FakeClient(response=_FakeListResponse([])))

    ok, result = list_ollama_models('http://localhost:11434')

    assert ok is True
    assert result == []


def test_unreachable_server(monkeypatch):
    monkeypatch.setattr(
        ollama, 'Client', lambda **kw: _FakeClient(error=ConnectionError('refused')),
    )

    ok, result = list_ollama_models('http://localhost:11434')

    assert ok is False
    assert 'refused' in result


def test_api_error(monkeypatch):
    monkeypatch.setattr(
        ollama, 'Client', lambda **kw: _FakeClient(error=ResponseError('Server Error', 500)),
    )

    ok, result = list_ollama_models('http://localhost:11434')

    assert ok is False
    assert 'Server Error' in result


def test_request_error(monkeypatch):
    monkeypatch.setattr(
        ollama, 'Client', lambda **kw: _FakeClient(error=RequestError('connect timeout')),
    )

    ok, result = list_ollama_models('http://localhost:11434')

    assert ok is False
    assert 'connect timeout' in result


class _FakeLLM:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    def invoke(self, *args, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response


class _FakeMsg:
    def __init__(self, content):
        self.content = content


class _FakeAgent:
    def __init__(self, response):
        self._response = response

    def invoke(self, *args, **kwargs):
        return self._response


def _patch_llm(monkeypatch, llm, agent=None):
    monkeypatch.setattr('app.core.llm_strategy._create_model', lambda *a, **k: llm)
    if agent is not None:
        monkeypatch.setattr('app.core.llm_strategy.create_agent', lambda *a, **k: agent)


class TestVerifyLLMConnection:
    def test_success_ping_and_tool(self, monkeypatch):
        llm = _FakeLLM(response=MagicMock(content='PONG'))
        agent = _FakeAgent({'messages': [_FakeMsg('The result is: pong')]})
        _patch_llm(monkeypatch, llm, agent)

        ok, msg = verify_llm_connection('openai', model='gpt-4o')

        assert ok is True
        assert 'tool calling OK' in msg

    def test_wrong_pong_response(self, monkeypatch):
        llm = _FakeLLM(response=MagicMock(content='Hello there'))
        _patch_llm(monkeypatch, llm)

        ok, msg = verify_llm_connection('openai')

        assert ok is False
        assert 'Unexpected response' in msg

    def test_tool_call_fails(self, monkeypatch):
        llm = _FakeLLM(response=MagicMock(content='PONG'))
        agent = _FakeAgent({'messages': [_FakeMsg('I did not call the tool')]})
        _patch_llm(monkeypatch, llm, agent)

        ok, msg = verify_llm_connection('openai')

        assert ok is False
        assert 'Tool calling failed' in msg

    def test_exception_reported(self, monkeypatch):
        llm = _FakeLLM(error=RuntimeError('boom'))
        _patch_llm(monkeypatch, llm)

        ok, msg = verify_llm_connection('openai')

        assert ok is False
        assert 'RuntimeError: boom' in msg


class TestLLMAgentStrategy:
    def _make_strategy(self, monkeypatch, decision):
        llm = _FakeLLM(response=MagicMock(content='PONG'))
        agent = _FakeAgent({'structured_response': decision})
        _patch_llm(monkeypatch, llm, agent)
        return LLMAgentStrategy('openai')

    def _make_trainer(self, moves):
        trainer = Trainer()
        pkmn = make_pkmn(name='Atk', moves=moves)
        trainer.team = [pkmn, None, None, None, None, None]
        trainer.in_battle = pkmn
        return trainer

    def test_get_choice_attack(self, monkeypatch):
        strategy = self._make_strategy(
            monkeypatch, BattleDecision(action='attack', move='Tackle', reasoning='best'),
        )
        trainer = self._make_trainer([make_move(name='Tackle'), None, None, None])
        rival = Trainer()
        rival.in_battle = make_pkmn(name='Df', hp=200, defense=50)

        msg = strategy.get_choice(trainer, rival)

        assert strategy.choices == ['Tackle']
        assert 'used Tackle' in msg

    def test_get_choice_switch(self, monkeypatch):
        strategy = self._make_strategy(
            monkeypatch, BattleDecision(action='switch', slot=1, reasoning='swap'),
        )
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        bench = make_pkmn(name='Bench')
        trainer.team = [active, bench, None, None, None, None]
        trainer.in_battle = active
        active.on_field = True
        rival = Trainer()
        rival.in_battle = make_pkmn(name='Df')

        msg = strategy.get_choice(trainer, rival)

        assert trainer.in_battle is bench
        assert 'sent out Bench' in msg

    def test_get_choice_struggle_no_pp(self, monkeypatch):
        strategy = self._make_strategy(
            monkeypatch, BattleDecision(action='attack', move='Tackle', reasoning='x'),
        )
        trainer = self._make_trainer([make_move(name='Tackle', pp=0), None, None, None])
        rival = Trainer()
        rival.in_battle = make_pkmn(name='Df', hp=200, defense=50)

        msg = strategy.get_choice(trainer, rival)

        assert 'struggle' in msg.lower()

    def test_get_choice_invalid_move_fallback(self, monkeypatch):
        strategy = self._make_strategy(
            monkeypatch, BattleDecision(action='attack', move='NonExistent', reasoning='x'),
        )
        trainer = self._make_trainer([make_move(name='Tackle'), None, None, None])
        rival = Trainer()
        rival.in_battle = make_pkmn(name='Df', hp=200, defense=50)

        msg = strategy.get_choice(trainer, rival)

        assert strategy.choices == ['Tackle']
        assert 'used Tackle' in msg

    def test_get_choice_game_over_returns_none(self, monkeypatch):
        strategy = self._make_strategy(
            monkeypatch, BattleDecision(action='attack', move='Tackle', reasoning='x'),
        )
        trainer = Trainer()
        trainer.team = [None] * 6
        trainer.in_battle = make_pkmn(name='Atk')
        rival = Trainer()
        rival.in_battle = make_pkmn(name='Df')

        msg = strategy.get_choice(trainer, rival)

        assert msg is None


class _FakeChatModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class TestCreateModel:
    def test_openai_default(self, monkeypatch):
        monkeypatch.setattr('app.core.llm_strategy.ChatOpenAI', _FakeChatModel)
        m = _create_model('openai')
        assert m.kwargs['model'] == 'gpt-4o'
        assert m.kwargs['temperature'] == 0.2

    def test_openai_api_key(self, monkeypatch):
        monkeypatch.setattr('app.core.llm_strategy.ChatOpenAI', _FakeChatModel)
        m = _create_model('openai', model='gpt-4o-mini', api_key='secret')
        assert m.kwargs['model'] == 'gpt-4o-mini'
        assert m.kwargs['api_key'] == 'secret'

    def test_anthropic_default(self, monkeypatch):
        monkeypatch.setattr('app.core.llm_strategy.ChatAnthropic', _FakeChatModel)
        m = _create_model('anthropic')
        assert 'claude' in m.kwargs['model']

    def test_gemini_default(self, monkeypatch):
        monkeypatch.setattr('app.core.llm_strategy.ChatGoogleGenerativeAI', _FakeChatModel)
        m = _create_model('gemini')
        assert 'gemini' in m.kwargs['model']

    def test_ollama_base_uri(self, monkeypatch):
        monkeypatch.setattr('app.core.llm_strategy.ChatOllama', _FakeChatModel)
        m = _create_model('ollama', base_uri='http://ollama:11434')
        assert m.kwargs['base_url'] == 'http://ollama:11434'

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match='Unknown LLM provider'):
            _create_model('bogus')


def _attack_trainer(moves):
    trainer = Trainer()
    pkmn = make_pkmn(name='Atk', moves=moves)
    trainer.team = [pkmn, None, None, None, None, None]
    trainer.in_battle = pkmn
    return trainer, pkmn


def _rival(typing=None):
    rival = Trainer()
    rival.in_battle = make_pkmn(name='Df', hp=200, defense=50, typing=typing)
    return rival


class TestPingTool:
    def test_returns_pong(self):
        assert _ping.func() == 'pong'


class TestModuleMakeTools:
    def test_damage_found(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival())
        assert tools[0].func('Tackle') > 0

    def test_damage_move_not_found(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival())
        assert tools[0].func('Nope') == 0

    def test_effect_unknown_type(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival())
        assert 'Unknown type' in tools[1].func('psionic')

    def test_effect_no_effect(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival(typing=[Typing.GROUND]))
        assert 'no effect' in tools[1].func('Electric')

    def test_effect_not_very(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival(typing=[Typing.ROCK]))
        assert 'not very effective' in tools[1].func('Normal')

    def test_effect_neutral(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival())
        assert 'neutral' in tools[1].func('Normal')

    def test_effect_super(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival(typing=[Typing.GRASS]))
        assert 'super effective' in tools[1].func('Fire')

    def test_effect_dual_type(self):
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        tools = _make_tools(trainer, _rival(typing=[Typing.FIRE, Typing.GRASS]))
        assert 'neutral' in tools[1].func('Water')


def _battle_trainer(active, opponent=None):
    trainer = Trainer()
    trainer.team = [active, None, None, None, None, None]
    trainer.in_battle = active
    return _build_state_str(trainer, opponent or _rival())


class TestStatStageStr:
    def test_neutral(self):
        assert _stat_stage_str(0) == 'x1'

    def test_plus_one(self):
        assert _stat_stage_str(1) == 'x1.5'

    def test_minus_one(self):
        assert _stat_stage_str(-1) == 'x0.66'

    def test_max_boost(self):
        assert _stat_stage_str(6) == 'x4'


class TestBuildStateStr:
    def test_fainted_bench_listed(self):
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        bench = make_pkmn(name='Bench')
        bench.fainted = True
        trainer.team = [active, bench, None, None, None, None]
        trainer.in_battle = active
        state = _build_state_str(trainer, _rival())
        assert 'Bench' in state
        assert 'Fainted' in state

    def test_opponent_shows_level_stages_and_moves(self):
        rival = _rival()
        rival.in_battle.atk_mult = 2
        state = _battle_trainer(make_pkmn(name='Atk'), rival)
        assert 'OPPONENT TEAM' in state
        assert 'Lv100' in state
        assert 'Atkx2' in state
        assert 'Moves:' in state
        assert 'Tackle' in state

    def test_no_flags_line_without_special_state(self):
        state = _battle_trainer(make_pkmn(name='Atk'))
        assert 'Flags:' not in state

    def test_confusion_shown_on_active(self):
        active = make_pkmn(name='Atk', temp_status=EffectStatus.CONFUSION)
        active.confused_turns = 2
        state = _battle_trainer(active)
        assert 'Confusion (2 turns)' in state

    def test_sleep_turns_shown(self):
        active = make_pkmn(name='Atk', status=EffectStatus.SLEEP)
        active.sleeping_turns = 3
        state = _battle_trainer(active)
        assert 'Sleep (3 turns)' in state

    def test_sleep_and_confusion_combined(self):
        active = make_pkmn(
            name='Atk',
            status=EffectStatus.SLEEP,
            temp_status=EffectStatus.CONFUSION,
        )
        active.sleeping_turns = 1
        active.confused_turns = 1
        state = _battle_trainer(active)
        assert 'Sleep (1 turns)' in state
        assert '+ Confusion (1 turns)' in state

    def test_opponent_confusion_shown(self):
        rival = _rival()
        rival.in_battle.temp_status = EffectStatus.CONFUSION
        rival.in_battle.confused_turns = 4
        state = _battle_trainer(make_pkmn(name='Atk'), rival)
        assert 'Confusion (4 turns)' in state

    def test_recharging_flag(self):
        active = make_pkmn(name='Atk', recharging=True)
        state = _battle_trainer(active)
        assert 'Must recharge' in state

    def test_biding_flag(self):
        active = make_pkmn(name='Atk', biding=True)
        state = _battle_trainer(active)
        assert 'Biding' in state

    def test_charging_flag(self):
        active = make_pkmn(name='Atk', charging=True, charge_move='Dig')
        state = _battle_trainer(active)
        assert 'Charging Dig' in state

    def test_rampaging_flag(self):
        active = make_pkmn(name='Atk', rampaging=True, rampage_move='Thrash')
        state = _battle_trainer(active)
        assert 'Rampaging Thrash' in state

    def test_raging_flag(self):
        active = make_pkmn(name='Atk', raging=True)
        state = _battle_trainer(active)
        assert 'Raging' in state

    def test_trapped_flag(self):
        active = make_pkmn(name='Atk', trapped=True, trapped_turns=3)
        state = _battle_trainer(active)
        assert 'Trapped (3 turns)' in state

    def test_focus_energy_flag(self):
        active = make_pkmn(name='Atk', focus_energy=True)
        state = _battle_trainer(active)
        assert 'Focus Energy' in state

    def test_transformed_flag(self):
        active = make_pkmn(name='Atk', transformed=True)
        state = _battle_trainer(active)
        assert 'Transformed' in state

    def test_disabled_move_shown(self):
        active = make_pkmn(name='Atk', disabled_move=0)
        active.disabled_turns = 2
        state = _battle_trainer(active)
        assert 'Tackle disabled' in state

    def test_disabled_empty_slot_shown(self):
        active = make_pkmn(name='Atk', disabled_move=1)
        state = _battle_trainer(active)
        assert '? disabled' in state

    def test_substitute_hp_shown(self):
        active = make_pkmn(name='Atk', substitute=True)
        active.sub_damage = 55
        state = _battle_trainer(active)
        assert 'Substitute (absorbs 200 HP)' in state

    def test_opponent_trapped_flag(self):
        rival = _rival()
        rival.in_battle.trapped = True
        rival.in_battle.trapped_turns = 5
        state = _battle_trainer(make_pkmn(name='Atk'), rival)
        assert 'Trapped (5 turns)' in state


class TestSystemPrompt:
    def test_burn_one_eighth(self):
        assert 'Burn: physical moves do 50% damage. 1/8 max HP per turn.' in SYSTEM_PROMPT

    def test_no_stale_burn_one_sixteenth(self):
        assert 'Burn: physical moves do 50% damage. 1/16 max HP per turn' not in SYSTEM_PROMPT

    def test_no_stale_reflect_turn_limit(self):
        assert 'for 5 turns' not in SYSTEM_PROMPT

    def test_side_effects_persist_until_switch_or_haze(self):
        assert 'until the user switches out or Haze.' in SYSTEM_PROMPT

    def test_status_immunities_documented(self):
        assert 'Electric types immune' in SYSTEM_PROMPT
        assert 'Poison types immune' in SYSTEM_PROMPT

    def test_mechanics_documented(self):
        for clause in ('Disable', 'Trapping', 'Rampage', 'Hyper Beam', 'OHKO moves'):
            assert clause in SYSTEM_PROMPT


def _new_strategy(monkeypatch, decision=None):
    llm = _FakeLLM(response=MagicMock(content='PONG'))
    agent = _FakeAgent(
        {'structured_response': decision} if decision is not None else {},
    )
    _patch_llm(monkeypatch, llm, agent)
    return LLMAgentStrategy('openai')


class TestLLMToolsInstance:
    def test_simulate_damage_no_context(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        tools = strategy._make_tools()
        assert tools[0].func('Tackle') == 0

    def test_simulate_damage_move_not_found(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        strategy._trainer = trainer
        strategy._rival = _rival()
        tools = strategy._make_tools()
        assert tools[0].func('Nope') == 0

    def test_simulate_damage_found(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        strategy._trainer = trainer
        strategy._rival = _rival()
        tools = strategy._make_tools()
        assert tools[0].func('Tackle') > 0

    def test_effect_no_opponent(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        tools = strategy._make_tools()
        assert tools[1].func('Fire') == 'No opponent'

    def test_effect_unknown_type(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        strategy._rival = _rival()
        tools = strategy._make_tools()
        assert 'Unknown type' in tools[1].func('psionic')

    def test_effect_super(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        strategy._rival = _rival(typing=[Typing.GRASS])
        tools = strategy._make_tools()
        assert 'super effective' in tools[1].func('Fire')

    def test_effect_no_effect(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        strategy._rival = _rival(typing=[Typing.GROUND])
        tools = strategy._make_tools()
        assert 'no effect' in tools[1].func('Electric')

    def test_effect_not_very(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        strategy._rival = _rival(typing=[Typing.ROCK])
        tools = strategy._make_tools()
        assert 'not very effective' in tools[1].func('Normal')

    def test_effect_neutral(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        strategy._rival = _rival(typing=[Typing.FIRE, Typing.GRASS])
        tools = strategy._make_tools()
        assert 'neutral' in tools[1].func('Water')


class TestLLMChoiceFallbacks:
    def test_get_choice_no_structured_response(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        msg = strategy.get_choice(trainer, _rival())
        assert strategy.choices == ['Tackle']
        assert 'used Tackle' in msg

    def test_get_choice_unknown_action(self, monkeypatch):
        decision = BattleDecision.model_construct(
            action='bogus', move='Tackle', reasoning='x',
        )
        strategy = _new_strategy(monkeypatch, decision)
        trainer, _ = _attack_trainer([make_move(name='Tackle'), None, None, None])
        msg = strategy.get_choice(trainer, _rival())
        assert strategy.choices == ['Tackle']
        assert 'used Tackle' in msg

    def test_execute_attack_no_choices_struggles(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer, _ = _attack_trainer([make_move(name='Tackle', pp=0), None, None, None])
        decision = BattleDecision(action='attack', move='NonExistent', reasoning='x')
        msg = strategy._execute_attack(trainer, _rival(), decision)
        assert 'struggle' in msg.lower()

    def test_execute_switch_none_slot_falls_back(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        trainer.team = [active, None, None, None, None, None]
        trainer.in_battle = active
        decision = BattleDecision(action='switch', slot=3, reasoning='x')
        msg = strategy._execute_switch(trainer, _rival(), decision)
        assert 'used Tackle' in msg

    def test_execute_switch_fainted_slot_falls_back(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        bench = make_pkmn(name='Bench')
        bench.fainted = True
        trainer.team = [active, bench, None, None, None, None]
        trainer.in_battle = active
        decision = BattleDecision(action='switch', slot=1, reasoning='x')
        msg = strategy._execute_switch(trainer, _rival(), decision)
        assert 'used Tackle' in msg

    def test_execute_switch_same_active_falls_back(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        trainer.team = [active, None, None, None, None, None]
        trainer.in_battle = active
        decision = BattleDecision(action='switch', slot=0, reasoning='x')
        msg = strategy._execute_switch(trainer, _rival(), decision)
        assert 'used Tackle' in msg

    def test_execute_switch_resets_outgoing_state(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer = Trainer()
        active = make_pkmn(name='Atk', atk_mult=2, substitute=True, on_field=True)
        active.biding = True
        active.bide_damage = 40
        active.bide_turns = 2
        active.trapped_turns = 1
        bench = make_pkmn(name='Bench')
        trainer.team = [active, bench, None, None, None, None]
        trainer.in_battle = active
        decision = BattleDecision(action='switch', slot=1, reasoning='x')
        msg = strategy._execute_switch(trainer, _rival(), decision)
        assert 'sent out Bench' in msg
        assert active.on_field is False
        assert active.biding is False
        assert active.bide_damage == 0
        assert active.bide_turns == 0
        assert active.trapped is False
        assert active.trapped_turns == 0
        assert active.substitute is False
        assert active.atk_mult == 0
        assert trainer.in_battle is bench
        assert bench.on_field is True

    def test_execute_switch_trapped_falls_back(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer = Trainer()
        active = make_pkmn(name='Atk')
        active.trapped = True
        bench = make_pkmn(name='Bench')
        trainer.team = [active, bench, None, None, None, None]
        trainer.in_battle = active
        decision = BattleDecision(action='switch', slot=1, reasoning='x')
        msg = strategy._execute_switch(trainer, _rival(), decision)
        assert isinstance(msg, str)
        assert trainer.in_battle is active
        assert trainer.in_battle.trapped is True

    def test_fallback_attack_no_choices_struggles(self, monkeypatch):
        strategy = _new_strategy(monkeypatch)
        trainer, _ = _attack_trainer([make_move(name='Tackle', pp=0), None, None, None])
        msg = strategy._fallback_attack(trainer, _rival())
        assert 'struggle' in msg.lower()
