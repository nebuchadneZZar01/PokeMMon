from __future__ import annotations

from unittest.mock import MagicMock

import ollama
from ollama import RequestError, ResponseError

from app.core.llm_strategy import (
    BattleDecision,
    LLMAgentStrategy,
    list_ollama_models,
    verify_llm_connection,
)
from app.core.player import Trainer

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
