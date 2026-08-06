from __future__ import annotations

import io

import pytest
from rich.console import Console

from app.ui import menu
from app.ui.menu import (
    AIType,
    LLMProvider,
    LogLevel,
    _show_summary,
    _step_ai_type,
    _step_api_key,
    _step_depth,
    _step_llm_base_uri,
    _step_llm_model,
    _step_llm_provider,
    _step_llm_verify,
    _step_log_level,
    _step_ollama_models,
    run_setup_menu,
)


@pytest.fixture
def console_capture(monkeypatch):
    buf = io.StringIO()
    console = Console(file=buf, width=120, highlight=False)
    monkeypatch.setattr('app.ui.menu.console', console)
    return buf


@pytest.fixture
def fake_prompt(monkeypatch):
    def make(answers=None, exc=None):
        queue = list(answers or [])

        class FakePrompt:
            @staticmethod
            def ask(*args, **kwargs):
                if exc is not None:
                    raise exc
                if not queue:
                    raise EOFError
                return queue.pop(0)

        monkeypatch.setattr('app.ui.menu.Prompt', FakePrompt)
        return queue

    return make


class TestStepAiType:
    @pytest.mark.parametrize('idx,expected', [
        ('1', AIType.RANDOM),
        ('2', AIType.MINIMAX),
        ('3', AIType.ALPHABETA),
        ('4', AIType.EXPECTIMAX),
        ('5', AIType.LLM),
    ])
    def test_valid_choice(self, idx, expected, fake_prompt, console_capture):
        fake_prompt([idx])
        assert _step_ai_type() == expected

    def test_invalid_choice_loops(self, fake_prompt, console_capture):
        fake_prompt(['9', '3'])
        result = _step_ai_type()
        assert result == AIType.ALPHABETA
        assert 'Invalid choice. Enter 1-5.' in console_capture.getvalue()


class TestStepDepth:
    def test_valid_depth(self, fake_prompt, console_capture):
        fake_prompt(['15'])
        assert _step_depth() == 15

    def test_boundaries(self, fake_prompt, console_capture):
        fake_prompt(['1', '20'])
        assert _step_depth() == 1
        assert _step_depth() == 20

    def test_invalid_loops(self, fake_prompt, console_capture):
        fake_prompt(['abc', '0', '21', '7'])
        assert _step_depth() == 7
        assert 'Enter a number between 1 and 20.' in console_capture.getvalue()


class TestStepLLMProvider:
    @pytest.mark.parametrize('idx,expected', [
        ('1', LLMProvider.OPENAI),
        ('2', LLMProvider.ANTHROPIC),
        ('3', LLMProvider.GEMINI),
        ('4', LLMProvider.OLLAMA),
    ])
    def test_valid_choice(self, idx, expected, fake_prompt, console_capture):
        fake_prompt([idx])
        assert _step_llm_provider() == expected

    def test_invalid_choice_loops(self, fake_prompt, console_capture):
        fake_prompt(['7', '2'])
        assert _step_llm_provider() == LLMProvider.ANTHROPIC
        assert 'Invalid choice. Enter 1-4.' in console_capture.getvalue()


class TestStepLogLevel:
    @pytest.mark.parametrize('idx,expected', [
        ('1', LogLevel.SILENT),
        ('2', LogLevel.INFO),
        ('3', LogLevel.DEBUG),
    ])
    def test_valid_choice(self, idx, expected, fake_prompt, console_capture):
        fake_prompt([idx])
        assert _step_log_level() == expected

    def test_invalid_choice_loops(self, fake_prompt, console_capture):
        fake_prompt(['9', '1'])
        assert _step_log_level() == LogLevel.SILENT
        assert 'Invalid choice. Enter 1-3.' in console_capture.getvalue()


class TestStepLLMModel:
    def test_default_when_empty(self, fake_prompt, console_capture):
        fake_prompt([''])
        assert _step_llm_model(LLMProvider.OPENAI) == 'gpt-4o'

    def test_custom_stripped(self, fake_prompt, console_capture):
        fake_prompt(['  my-model  '])
        assert _step_llm_model(LLMProvider.OLLAMA) == 'my-model'


class TestStepLLMBaseUri:
    def test_default_when_empty(self, fake_prompt, console_capture):
        fake_prompt([''])
        assert _step_llm_base_uri() == 'http://localhost:11434'

    def test_custom(self, fake_prompt, console_capture):
        fake_prompt(['http://ollama:11434'])
        assert _step_llm_base_uri() == 'http://ollama:11434'


class TestStepOllamaModels:
    def test_pick_from_list(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['2'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, ['llama3.1', 'mistral']),
        )
        assert _step_ollama_models('http://localhost:11434') == 'mistral'

    def test_manual_entry_zero(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['0', 'llama3.2'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, ['llama3.1']),
        )
        assert _step_ollama_models('http://localhost:11434') == 'llama3.2'

    def test_no_models_manual_entry(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['my-model'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, []),
        )
        assert _step_ollama_models('http://localhost:11434') == 'my-model'
        assert 'No models found' in console_capture.getvalue()

    def test_unreachable_retry_then_pick(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['1', '1'])
        calls = {'n': 0}

        def fake_list(base_uri):
            calls['n'] += 1
            if calls['n'] == 1:
                return False, 'connection refused'
            return True, ['llama3.1']

        monkeypatch.setattr('app.core.llm_strategy.list_ollama_models', fake_list)
        assert _step_ollama_models('http://localhost:11434') == 'llama3.1'

    def test_unreachable_change_url(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['2', '', '1'])
        calls = {'n': 0}

        def fake_list(base_uri):
            calls['n'] += 1
            if calls['n'] == 1:
                return False, 'connection refused'
            return True, ['llama3.1']

        monkeypatch.setattr('app.core.llm_strategy.list_ollama_models', fake_list)
        assert _step_ollama_models('http://localhost:11434') == 'llama3.1'
        assert 'Ollama server unreachable' in console_capture.getvalue()

    def test_unreachable_manual_entry(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['3', 'custom-model'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (False, 'connection refused'),
        )
        assert _step_ollama_models('http://localhost:11434') == 'custom-model'

    def test_invalid_index_loops(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['9', 'x', '1'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, ['llama3.1']),
        )
        assert _step_ollama_models('http://localhost:11434') == 'llama3.1'
        assert 'Invalid choice. Enter a number or 0.' in console_capture.getvalue()


class TestStepApiKey:
    def test_env_var_fallback(self, fake_prompt, console_capture, monkeypatch):
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-1234567890abcd')
        fake_prompt([''])
        assert _step_api_key(LLMProvider.OPENAI) == 'sk-1234567890abcd'
        assert 'sk-1' in console_capture.getvalue()
        assert 'OPENAI_API_KEY' in console_capture.getvalue()

    def test_custom_key(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['sk-custom'])
        assert _step_api_key(LLMProvider.OPENAI) == 'sk-custom'

    def test_empty_no_env_returns_none(self, fake_prompt, console_capture, monkeypatch):
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        fake_prompt([''])
        assert _step_api_key(LLMProvider.ANTHROPIC) is None


class TestStepLLMVerify:
    def _patch_verify(self, monkeypatch, responses):
        calls = {'i': 0}

        def fake_verify(provider, model, api_key, base_uri, timeout):
            calls['i'] += 1
            return responses[min(calls['i'] - 1, len(responses) - 1)]

        monkeypatch.setattr('app.core.llm_strategy.verify_llm_connection', fake_verify)
        return calls

    def test_success(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(True, 'connected')])
        fake_prompt([])
        assert _step_llm_verify('openai', 'gpt-4o', 'k') is True
        assert 'connected' in console_capture.getvalue()

    def test_skip(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(False, 'bad key')])
        fake_prompt(['3'])
        assert _step_llm_verify('openai', 'gpt-4o', 'k') is False

    def test_reconfigure(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(False, 'bad key')])
        fake_prompt(['2'])
        assert _step_llm_verify('openai', 'gpt-4o', 'k') is None

    def test_retry_then_success(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(False, 'bad key'), (True, 'connected')])
        fake_prompt(['1'])
        assert _step_llm_verify('openai', 'gpt-4o', 'k') is True

    def test_tool_calling_note(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(False, 'model lacks tool calling support')])
        fake_prompt(['3'])
        _step_llm_verify('ollama', 'llama3.1', None)
        assert 'tool-calling support' in console_capture.getvalue()

    def test_ollama_pull_note(self, fake_prompt, console_capture, monkeypatch):
        self._patch_verify(monkeypatch, [(False, 'model not found')])
        fake_prompt(['3'])
        _step_llm_verify('ollama', 'llama3.1', None)
        assert 'ollama pull llama3.1' in console_capture.getvalue()


class TestShowSummary:
    def _capture(self, console_capture):
        return console_capture.getvalue()

    def test_minimax_shows_depth_confirm(self, fake_prompt, console_capture):
        config = menu.BattleConfig(ai_type=AIType.MINIMAX, depth=5, log_level=LogLevel.INFO)
        fake_prompt(['y'])
        assert _show_summary(config) is True
        out = self._capture(console_capture)
        assert 'Minimax' in out
        assert 'Depth' in out
        assert '5' in out
        assert 'Info' in out

    def test_decline(self, fake_prompt, console_capture):
        config = menu.BattleConfig(ai_type=AIType.RANDOM)
        fake_prompt(['n'])
        assert _show_summary(config) is False

    def test_llm_masked_api_key(self, fake_prompt, console_capture):
        config = menu.BattleConfig(
            ai_type=AIType.LLM,
            llm_provider=LLMProvider.OPENAI,
            llm_model='gpt-4o',
            llm_api_key='sk-1234567890abcd',
        )
        fake_prompt(['y'])
        _show_summary(config)
        out = self._capture(console_capture)
        assert 'OpenAI' in out
        assert 'gpt-4o' in out
        assert 'sk-1' in out
        assert 'abcd' in out

    def test_llm_short_key_masked_all(self, fake_prompt, console_capture):
        config = menu.BattleConfig(
            ai_type=AIType.LLM,
            llm_provider=LLMProvider.OPENAI,
            llm_model='gpt-4o',
            llm_api_key='short',
        )
        fake_prompt(['y'])
        _show_summary(config)
        assert '****' in self._capture(console_capture)

    def test_llm_env_var_fallback(self, fake_prompt, console_capture):
        config = menu.BattleConfig(
            ai_type=AIType.LLM,
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model='claude-sonnet-4-20250514',
        )
        fake_prompt(['y'])
        _show_summary(config)
        assert '(env var)' in self._capture(console_capture)

    def test_llm_ollama_shows_base_uri(self, fake_prompt, console_capture):
        config = menu.BattleConfig(
            ai_type=AIType.LLM,
            llm_provider=LLMProvider.OLLAMA,
            llm_model='llama3.1',
            llm_base_uri='http://ollama:11434',
        )
        fake_prompt(['y'])
        _show_summary(config)
        out = self._capture(console_capture)
        assert 'Ollama' in out
        assert 'http://ollama:11434' in out


class TestRunSetupMenu:
    def test_random_flow(self, fake_prompt, console_capture):
        fake_prompt(['1', '1', 'y'])
        config = run_setup_menu()
        assert config.ai_type == AIType.RANDOM
        assert config.depth == 7
        assert config.log_level == LogLevel.SILENT

    def test_minimax_flow(self, fake_prompt, console_capture):
        fake_prompt(['2', '5', '2', 'y'])
        config = run_setup_menu()
        assert config.ai_type == AIType.MINIMAX
        assert config.depth == 5
        assert config.log_level == LogLevel.INFO

    def test_llm_openai_flow(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['5', '1', '', 'sk-secret', '1', 'y'])
        monkeypatch.setattr(
            'app.core.llm_strategy.verify_llm_connection',
            lambda provider, model, api_key, base_uri, timeout: (True, 'connected'),
        )
        config = run_setup_menu()
        assert config.ai_type == AIType.LLM
        assert config.llm_provider == LLMProvider.OPENAI
        assert config.llm_model == 'gpt-4o'
        assert config.llm_api_key == 'sk-secret'

    def test_llm_ollama_flow(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['5', '4', '', '1', '1', 'y'])
        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, ['llama3.1']),
        )
        monkeypatch.setattr(
            'app.core.llm_strategy.verify_llm_connection',
            lambda provider, model, api_key, base_uri, timeout: (True, 'connected'),
        )
        config = run_setup_menu()
        assert config.llm_provider == LLMProvider.OLLAMA
        assert config.llm_model == 'llama3.1'
        assert config.llm_base_uri == 'http://localhost:11434'

    def test_verify_reconfigure_loop(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['5', '1', '', 'sk-secret', '2', '', 'new-key', '1', 'y'])
        responses = [(False, 'bad key'), (True, 'connected')]
        calls = {'i': 0}

        def fake_verify(provider, model, api_key, base_uri, timeout):
            calls['i'] += 1
            return responses[calls['i'] - 1]

        monkeypatch.setattr('app.core.llm_strategy.verify_llm_connection', fake_verify)
        config = run_setup_menu()
        assert config.llm_provider == LLMProvider.OPENAI
        assert config.llm_api_key == 'new-key'
        assert calls['i'] == 2

    def test_ollama_reconfigure_reasks_base_uri(self, fake_prompt, console_capture, monkeypatch):
        fake_prompt(['5', '4', '', '1', '2', 'http://ollama:11434', '1', '1', 'y'])
        responses = [(False, 'bad'), (True, 'connected')]
        calls = {'i': 0}

        def fake_verify(provider, model, api_key, base_uri, timeout):
            calls['i'] += 1
            return responses[calls['i'] - 1]

        monkeypatch.setattr(
            'app.core.llm_strategy.list_ollama_models',
            lambda base_uri: (True, ['llama3.1']),
        )
        monkeypatch.setattr('app.core.llm_strategy.verify_llm_connection', fake_verify)
        config = run_setup_menu()
        assert config.llm_provider == LLMProvider.OLLAMA
        assert config.llm_model == 'llama3.1'
        assert config.llm_base_uri == 'http://ollama:11434'
        assert calls['i'] == 2

    def test_summary_decline_loops(self, fake_prompt, console_capture):
        fake_prompt(['1', '1', 'n', '2', '7', '1', 'y'])
        config = run_setup_menu()
        assert config.ai_type == AIType.MINIMAX
        assert config.depth == 7

    def test_eof_cancels(self, fake_prompt, console_capture):
        fake_prompt([], exc=EOFError)
        assert run_setup_menu() is None
        assert 'Setup cancelled.' in console_capture.getvalue()

    def test_keyboard_interrupt_cancels(self, fake_prompt, console_capture):
        fake_prompt([], exc=KeyboardInterrupt)
        assert run_setup_menu() is None
        assert 'Setup cancelled.' in console_capture.getvalue()
