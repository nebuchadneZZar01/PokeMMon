from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.data.moves import attacks
from app.data.pokedex import pokedex
from app.schemas.effect_status import EffectStatus

if TYPE_CHECKING:
    from app.core.battle_system import TurnBattleSystem

console = Console()

TYPE_COLORS = {
    'NORMAL': '#A8A878', 'FIGHTING': '#C03028', 'FLYING': '#A890F0',
    'POISON': '#A040A0', 'GROUND': '#E0C068', 'ROCK': '#B8A038',
    'BUG': '#A8B820', 'GHOST': '#705898', 'STEEL': '#B8B8D0',
    'FIRE': '#F08030', 'WATER': '#6890F0', 'GRASS': '#78C850',
    'ELECTRIC': '#F8D030', 'PSYCHIC': '#F85888', 'ICE': '#98D8D8',
    'DRAGON': '#7038F8', 'DARK': '#705848', 'FAIRY': '#EE99AC',
}

STATUS_COLORS = {
    EffectStatus.POISON: 'magenta',
    EffectStatus.TOXIC: 'purple',
    EffectStatus.BURN: 'red',
    EffectStatus.PARALYZE: 'yellow',
    EffectStatus.SLEEP: 'cyan',
    EffectStatus.FREEZE: 'blue',
    EffectStatus.CONFUSION: 'orange',
}


def _fmt_type(typing: list) -> str:
    """Format a list of types into colored rich text.

    Returns:
        str: Rich-formatted type string with colors.
    """
    return " ".join(
        f"[{TYPE_COLORS.get(t.value.upper(), 'white')}]{t.value.upper()}[/]"
        for t in typing
    )


def make_hp_bar(current: float, max_hp: int, width: int = 18) -> str:
    """Create a colored HP bar string.

    Returns:
        str: Rich-formatted HP bar (green/yellow/red filled blocks).
    """
    ratio = current / max_hp if max_hp > 0 else 0
    filled = max(0, min(int(ratio * width), width))
    empty = width - filled
    color = 'green' if ratio > 0.5 else ('yellow' if ratio > 0.2 else 'red')
    return f'[{color}]{"█" * filled}[/]{ "░" * empty}'


def status_tag(pkmn) -> str:
    """Generate a colored status tag for a Pokémon.

    Returns:
        str: Rich-formatted status string (e.g. '[red]FAINTED[/]').
    """
    if pkmn.fainted:
        return '[red]FAINTED[/]'
    if pkmn.status is None:
        return '[green]OK[/]'
    c = STATUS_COLORS.get(pkmn.status, 'white')
    return f'[{c}]{pkmn.status.value}[/]'


def _status_pad(pkmn, width: int = 18) -> str:
    """Get a status tag padded to a fixed width for alignment.

    Returns:
        str: Padded status tag string.
    """
    tag = status_tag(pkmn)
    visible = len(re.sub(r'\[/?[^\]]*\]', '', tag))
    return tag + ' ' * max(0, width - visible)


def team_dots(team) -> str:
    """Create a visual team health indicator using dots.

    Returns:
        str: String of '○' (fainted/empty) and '●' (alive) dots.
    """
    return ''.join('○' if (p is None or p.fainted) else '●' for p in team)


_SIDE_LABELS = {'player': 'Player', 'ai': 'AI', 'field': '·'}
_SIDE_COLORS = {'player': 'cyan', 'ai': 'red', 'field': 'dim'}

_LOG_MAX_LINES = 12

_MOVE_NAMES = {m.name.casefold() for m in attacks}
_POKE_NAMES = {p.name.casefold() for p in pokedex}
_LOG_WORD_RE = re.compile(
    r'\b(' + '|'.join(
        re.escape(w) for w in sorted(_MOVE_NAMES | _POKE_NAMES, key=len, reverse=True)
    ) + r')\b',
    re.IGNORECASE,
)


def _style_log_entry(message: Text, player_names: set[str], ai_names: set[str]) -> None:
    """Style move and pokemon names in a battle log message.

    Moves render in italic, pokemon names in italic colored by team
    ownership (cyan for player, red for AI), or italic dim when the
    owner is unknown.

    Args:
        message (Text): Rich text to style in place.
        player_names (set[str]): Lowercased player team pokemon names.
        ai_names (set[str]): Lowercased AI team pokemon names.
    """
    for match in _LOG_WORD_RE.finditer(message.plain):
        word = match.group(0).casefold()
        if word in _MOVE_NAMES:
            style = 'italic'
        elif word in player_names:
            style = 'italic cyan'
        elif word in ai_names:
            style = 'italic red'
        else:
            style = 'italic dim'
        message.stylize(style, match.start(), match.end())


def _render_log(bs: TurnBattleSystem) -> Table:
    """Build the battle log table (round, side, message).

    Recent entries are shown newest-first, keeping whole blocks only so a
    turn is never split across the visible boundary.

    Args:
        bs (TurnBattleSystem): The battle system with message history.

    Returns:
        Table: Rich table of recent battle log entries, newest highlighted.
    """
    keep = []
    lines_used = 0
    for entry in reversed(bs.message_log):
        lines = entry[2].count('\n') + 1
        if keep and lines_used + 1 + lines > _LOG_MAX_LINES:
            break
        lines_used += (1 if keep else 0) + lines
        keep.append(entry)
    keep.reverse()

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(justify='right', no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column(justify='left')

    player_names = {p.name.casefold() for p in bs.player.team if p}
    ai_names = {p.name.casefold() for p in bs.ai.team if p}

    for i, (round_n, side, msg) in enumerate(keep):
        if i != 0:
            table.add_row('', '', '')
        label = _SIDE_LABELS.get(side, side)
        color = _SIDE_COLORS.get(side, 'white')
        round_cell = '' if side == 'field' else f'[bold yellow]R{round_n}[/]'
        message = Text(msg)
        last = i == len(keep) - 1
        if last:
            message.stylize('bold white', 0, len(message))
            label_cell = f'[bold {color}]{label}[/]'
        else:
            label_cell = f'[{color}]{label}[/]'
        _style_log_entry(message, player_names, ai_names)
        table.add_row(round_cell, label_cell, message)
    return table


def _render_moves(p) -> Table:
    """Build the move selection menu as a rich table.

    Each move is a row: colored slot number, name, colored type, and PP.
    Moves with no PP left are dimmed and flagged in red.

    Args:
        p (BattlePokemon): The active Pokémon whose moves to show.

    Returns:
        Table: Rich table of selectable moves.
    """
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(width=3, justify='right')
    table.add_column()
    table.add_column(width=8)
    table.add_column(justify='right')
    for i, move in enumerate(p.moves):
        if move is None:
            continue
        t = move.typing.value.upper()
        c = TYPE_COLORS.get(t, 'white')
        out = move.pp <= 0
        slot = Text(f'[{i + 1}]', style=f'dim {c}' if out else c)
        name = Text(move.name, style='dim' if out else 'bold')
        type_cell = Text(t, style=c)
        pp_text = f'{move.pp:>2}/{move.max_pp}'
        pp = Text(pp_text, style='red' if out else '')
        if out:
            pp.append(' (no PP)', style='red')
        table.add_row(slot, name, type_cell, pp)
    return table


def render_core(bs: TurnBattleSystem) -> None:
    """Render the main battle screen: opponent, player, messages, and moves."""
    p = bs.player.in_battle
    e = bs.ai.in_battle

    hp_e = make_hp_bar(e.hp, e.max_hp)
    e_content = (
        f'  [bold]{e.name}[/bold]    Lv{e.level}\n'
        f'  {_fmt_type(e.typing)}\n'
        f'  HP {hp_e}  [bold]{int(e.hp)}/{int(e.max_hp)}[/]\n'
        f'  {_status_pad(e)} Team {team_dots(bs.ai.team)}'
    )
    console.print(Panel(e_content, title=f' {bs.ai.name} ', border_style='bold'))

    hp_p = make_hp_bar(p.hp, p.max_hp)
    p_content = (
        f'  [bold]{p.name}[/bold]    Lv{p.level}\n'
        f'  {_fmt_type(p.typing)}\n'
        f'  HP {hp_p}  [bold]{int(p.hp)}/{int(p.max_hp)}[/]\n'
        f'  {_status_pad(p)} Team {team_dots(bs.player.team)}'
    )
    console.print(Panel(p_content, title=' Player ', border_style='bold'))

    if bs.player_msg.startswith('You are challenged by'):
        bs.log_message('field', bs.player_msg)
    else:
        bs.log_message('player', bs.player_msg)
    bs.log_message('ai', bs.enemy_msg)

    console.print(Panel(_render_log(bs), title=' Battle Log ', border_style='bold'))

    console.print(_render_moves(p))

    console.print()
    console.print('  [5] Team     [6] Forfeit')


def render_team(bs: TurnBattleSystem) -> None:
    """Render the team overview screen showing all player Pokémon."""
    console.clear()
    body_lines = []
    for i, pkmn in enumerate(bs.player.team):
        if pkmn is None:
            continue
        mark = ' ←' if pkmn.on_field else ''
        if pkmn.fainted:
            body_lines.append(f'  [{i + 1}] [dim]{pkmn.name}[/dim]  [red]FAINTED[/]{mark}')
        else:
            hp_bar = make_hp_bar(pkmn.hp, pkmn.max_hp, width=14)
            body_lines.append(
                f'  [{i + 1}] {pkmn.name:<10} {hp_bar}'
                f'  [bold]{int(pkmn.hp)}/{int(pkmn.max_hp)}[/]'
                f'  {status_tag(pkmn)}{mark}'
            )
        tags = ' '.join(
            f'[{TYPE_COLORS.get(t.value.upper(), "white")}]{t.value.upper()}[/]'
            for t in pkmn.typing
        )
        body_lines.append(f'      {"":<10} {tags}')
        body_lines.append('')

    console.print(Panel('\n'.join(body_lines), title=' Your Team ', border_style='bold'))
    console.print()
    console.print('  Choose (1-6) to switch, [0] back to battle')
