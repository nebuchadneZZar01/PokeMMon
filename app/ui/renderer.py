from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel

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
    visible = len(re.sub(r'\[/?\w+\]', '', tag))
    return tag + ' ' * max(0, width - visible)


def team_dots(team) -> str:
    """Create a visual team health indicator using dots.

    Returns:
        str: String of '○' (fainted/empty) and '●' (alive) dots.
    """
    return ''.join('○' if (p is None or p.fainted) else '●' for p in team)


def battle_messages(player_msg: str, enemy_msg: str) -> str:
    """Combine player and enemy battle messages into a single display string.

    Returns:
        str: Combined message string.
    """
    parts = []
    for msg in (enemy_msg, player_msg):
        if msg and not msg.startswith('You are challenged by'):
            parts.append(msg)
    if parts:
        return '\n'.join(parts)
    return player_msg or ' '


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

    msg_content = battle_messages(bs.player_msg, bs.enemy_msg)
    console.print(Panel(msg_content, title=' Message ', border_style='bold'))

    for i, move in enumerate(p.moves):
        if move is None:
            continue
        t = move.typing.value.upper()
        c = TYPE_COLORS.get(t, 'white')
        suffix = ' [red](no PP)[/]' if move.pp <= 0 else ''
        console.print(
            f'  [{c}][{i + 1}][/] {move.name:<16} - [{c}]{t:<6}[/{c}]'
            f' {move.pp:>2}/{move.max_pp}{suffix}'
        )

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
