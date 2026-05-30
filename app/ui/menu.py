from __future__ import annotations

import os
from enum import StrEnum

from pydantic import BaseModel, Field
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from app.ui.renderer import console

_LLM_VERIFY_TIMEOUT = 30


class AIType(StrEnum):
    RANDOM = 'random'
    MINIMAX = 'minimax'
    ALPHABETA = 'alphabeta'
    EXPECTIMAX = 'expectimax'
    LLM = 'llm'


class LLMProvider(StrEnum):
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    GEMINI = 'gemini'
    OLLAMA = 'ollama'


class LogLevel(StrEnum):
    SILENT = 'silent'
    INFO = 'info'
    DEBUG = 'debug'


class BattleConfig(BaseModel):
    ai_type: AIType = AIType.MINIMAX
    depth: int = Field(default=7, ge=1, le=20)
    llm_provider: LLMProvider | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    log_level: LogLevel = LogLevel.SILENT


_AI_NAMES: dict[AIType, str] = {
    AIType.RANDOM: 'Random',
    AIType.MINIMAX: 'Minimax',
    AIType.ALPHABETA: 'Alpha-Beta',
    AIType.EXPECTIMAX: 'ExpectiMax',
    AIType.LLM: 'LLM (LangGraph Agent)',
}

_LLM_NAMES: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: 'OpenAI',
    LLMProvider.ANTHROPIC: 'Anthropic',
    LLMProvider.GEMINI: 'Gemini',
    LLMProvider.OLLAMA: 'Ollama (local)',
}

_LLM_DEFAULTS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: 'gpt-4o',
    LLMProvider.ANTHROPIC: 'claude-sonnet-4-20250514',
    LLMProvider.GEMINI: 'gemini-2.0-flash',
    LLMProvider.OLLAMA: 'llama3.1',
}

_LOG_NAMES: dict[LogLevel, str] = {
    LogLevel.SILENT: 'Silent — no logs',
    LogLevel.INFO: 'Info — AI move names, team listing',
    LogLevel.DEBUG: 'Debug — full tree search details',
}


def _show_title():
    console.clear()
    title = Text('PokeMMon - Battle Setup', style='bold cyan')
    console.print(Panel(title, border_style='cyan', padding=(1, 2)))


def _step_ai_type() -> AIType:
    _show_title()
    lines = ['Select AI opponent:\n']
    for i, t in enumerate(AIType, 1):
        lines.append(f'  {i}) {_AI_NAMES[t]}')
    lines.append('')
    console.print(Panel('\n'.join(lines), border_style='blue', padding=(1, 2)))
    while True:
        raw = Prompt.ask('Choice', default='2')
        if raw in ('1', '2', '3', '4', '5'):
            return list(AIType)[int(raw) - 1]
        console.print('[red]Invalid choice. Enter 1-5.[/]')


def _step_depth() -> int:
    console.print()
    while True:
        raw = Prompt.ask('Search depth', default='7')
        try:
            val = int(raw)
            if 1 <= val <= 20:
                return val
        except ValueError:
            pass
        console.print('[red]Enter a number between 1 and 20.[/]')


def _step_llm_provider() -> LLMProvider:
    _show_title()
    lines = ['Select LLM provider:\n']
    for i, t in enumerate(LLMProvider, 1):
        lines.append(f'  {i}) {_LLM_NAMES[t]}')
    lines.append('')
    console.print(Panel('\n'.join(lines), border_style='blue', padding=(1, 2)))
    while True:
        raw = Prompt.ask('Choice', default='1')
        if raw in ('1', '2', '3', '4'):
            return list(LLMProvider)[int(raw) - 1]
        console.print('[red]Invalid choice. Enter 1-4.[/]')


def _step_llm_model(provider: LLMProvider) -> str | None:
    default = _LLM_DEFAULTS[provider]
    console.print()
    raw = Prompt.ask('Model (enter for default)', default=default)
    return raw.strip() or default


def _step_api_key(provider: LLMProvider) -> str | None:
    env_var_map = {
        LLMProvider.OPENAI: 'OPENAI_API_KEY',
        LLMProvider.ANTHROPIC: 'ANTHROPIC_API_KEY',
        LLMProvider.GEMINI: 'GEMINI_API_KEY',
    }
    env_key = env_var_map.get(provider, '')
    env_val = os.environ.get(env_key, '')
    console.print()
    if env_val:
        masked = env_val[:4] + '*' * (len(env_val) - 8) + env_val[-4:]
        console.print(f'[dim]Current {env_key}: {masked}[/]')
    raw = Prompt.ask(
        f'API key (empty = {env_key} env var)',
        password=True, default='',
    )
    return raw or env_val or None


def _step_llm_verify(
    provider_str: str, model: str | None, api_key: str | None,
) -> bool | None:
    """Test LLM connection. Returns True=ok, False=skip, None=reconfigure."""
    from app.core.llm_strategy import verify_llm_connection

    provider = LLMProvider(provider_str)
    label = f"{_LLM_NAMES[provider]} ({model})"

    with console.status(f"[yellow]Testing {label}...[/]"):
        success, msg = verify_llm_connection(
            provider=provider_str,
            model=model,
            api_key=api_key,
            timeout=_LLM_VERIFY_TIMEOUT,
        )

    if success:
        console.print(Panel(
            f"✓ {msg}",
            title=" Connection Test ", border_style="green",
        ))
        return True

    note = ""
    if "tool calling" in msg.lower():
        note = (
            "\n\nNote: some local models lack tool-calling support.\n"
            "LLM strategy requires tool-capable models."
        )

    console.print(Panel(
        f"✗ {msg}{note}\n\n"
        "1) Retry\n"
        "2) Reconfigure model\n"
        "3) Skip",
        title=" Connection Test ", border_style="red",
    ))

    while True:
        raw = Prompt.ask("Choice", default="1")
        if raw == "1":
            return _step_llm_verify(provider_str, model, api_key)
        if raw == "2":
            return None
        if raw == "3":
            return False


def _step_log_level() -> LogLevel:
    _show_title()
    lines = ['Select log level:\n']
    for i, t in enumerate(LogLevel, 1):
        lines.append(f'  {i}) {_LOG_NAMES[t]}')
    lines.append('')
    console.print(Panel('\n'.join(lines), border_style='blue', padding=(1, 2)))
    while True:
        raw = Prompt.ask('Choice', default='1')
        if raw in ('1', '2', '3'):
            return list(LogLevel)[int(raw) - 1]
        console.print('[red]Invalid choice. Enter 1-3.[/]')


def _show_summary(config: BattleConfig) -> bool:
    lines = []
    lines.append(f'AI Type    : {_AI_NAMES[config.ai_type]}')
    if config.ai_type in (AIType.MINIMAX, AIType.ALPHABETA, AIType.EXPECTIMAX):
        lines.append(f'Depth      : {config.depth}')
    if config.ai_type == AIType.LLM:
        prov = config.llm_provider or LLMProvider.OPENAI
        lines.append(f'Provider   : {_LLM_NAMES[prov]}')
        if config.llm_model:
            lines.append(f'Model      : {config.llm_model}')
        if config.llm_api_key:
            k = config.llm_api_key
            masked = k[:4] + '*' * (len(k) - 8) + k[-4:] if len(k) > 8 else '****'
            lines.append(f'API Key    : {masked}')
        else:
            lines.append('API Key    : (env var)')
    lines.append(f'Log Level  : {_LOG_NAMES[config.log_level]}')
    console.print()
    console.print(Panel(
        '\n'.join(lines),
        title=' Configuration Summary ',
        border_style='green', padding=(1, 2),
    ))
    confirm = Prompt.ask('Start battle?', choices=['y', 'n'], default='y')
    return confirm == 'y'


def run_setup_menu() -> BattleConfig | None:
    try:
        while True:
            ai = _step_ai_type()
            depth = _step_depth() if ai in (
                AIType.MINIMAX, AIType.ALPHABETA, AIType.EXPECTIMAX,
            ) else 7

            llm_provider: LLMProvider | None = None
            llm_model: str | None = None
            llm_api_key: str | None = None

            if ai == AIType.LLM:
                llm_provider = _step_llm_provider()
                llm_model = _step_llm_model(llm_provider)
                if llm_provider != LLMProvider.OLLAMA:
                    llm_api_key = _step_api_key(llm_provider)

                while True:
                    result = _step_llm_verify(
                        llm_provider.value, llm_model, llm_api_key,
                    )
                    if result is None:
                        llm_model = _step_llm_model(llm_provider)
                        if llm_provider != LLMProvider.OLLAMA:
                            llm_api_key = _step_api_key(llm_provider)
                        continue
                    break

            log_level = _step_log_level()

            config = BattleConfig(
                ai_type=ai,
                depth=depth,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_api_key=llm_api_key,
                log_level=log_level,
            )

            if _show_summary(config):
                return config
    except (KeyboardInterrupt, EOFError):
        console.print('\n[red]Setup cancelled.[/]')
        return None
