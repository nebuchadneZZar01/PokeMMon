from __future__ import annotations

import ollama
from ollama import RequestError, ResponseError

from app.core.llm_strategy import list_ollama_models


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
