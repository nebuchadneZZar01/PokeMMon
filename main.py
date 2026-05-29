import argparse
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from app.core import battle_system
from app.core.player import *
from app.core.combat import try_atk_status, struggle_no_pp, reset_stats_mult, reset_battle_stats

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
    'PSN': 'magenta', 'TOX': 'purple', 'BRN': 'red', 'PAR': 'yellow',
    'SLP': 'cyan', 'FRZ': 'blue',
}


def make_hp_bar(current: float, max_hp: int, width: int = 18) -> str:
    ratio = current / max_hp if max_hp > 0 else 0
    filled = max(0, min(int(ratio * width), width))
    empty = width - filled
    color = 'green' if ratio > 0.5 else ('yellow' if ratio > 0.2 else 'red')
    return f'[{color}]{"█" * filled}[/]{ "░" * empty}'


def status_tag(pkmn) -> str:
    if pkmn.fainted:
        return '[red]FAINTED[/]'
    if pkmn.status is None:
        return '[green]OK[/]'
    c = STATUS_COLORS.get(pkmn.status, 'white')
    return f'[{c}]{pkmn.status}[/]'


def team_dots(team) -> str:
    return ''.join('○' if (p is None or p.fainted) else '●' for p in team)


def get_message(p, e) -> str:
    for mon in (e, p):
        if mon.msg and mon.msg != 'You are challenged by AI Trainer!':
            return mon.msg
    return p.msg or ''


def render_core(bs):
    p = bs.player.in_battle
    e = bs.ai.in_battle

    hp_e = make_hp_bar(e.hp, e.max_hp)
    e_content = (
        f'  [bold]{e.name}[/bold]    Lv{e.level}\n'
        f'  HP {hp_e}  [bold]{int(e.hp)}/{int(e.max_hp)}[/]\n'
        f'  {status_tag(e)}               Team {team_dots(bs.ai.team)}'
    )
    console.print(Panel(e_content, title=' AI ', border_style='bold'))

    hp_p = make_hp_bar(p.hp, p.max_hp)
    p_content = (
        f'  [bold]{p.name}[/bold]    Lv{p.level}\n'
        f'  HP {hp_p}  [bold]{int(p.hp)}/{int(p.max_hp)}[/]\n'
        f'  {status_tag(p)}               Team {team_dots(bs.player.team)}'
    )
    console.print(Panel(p_content, title=' Player ', border_style='bold'))

    console.print(Panel(get_message(p, e), title=' Message ', border_style='bold'))

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


def render_team(bs):
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


def switch_valid(bs, idx: int) -> Optional[str]:
    target = bs.player.team[idx]
    if target is None:
        return 'Invalid slot.'
    if target.fainted:
        return f'{target.name} is fainted!'
    if target is bs.player.in_battle:
        return f'{target.name} is already on the field!'
    return None


def exec_switch(bs, idx: int) -> str:
    player = bs.player
    target = player.team[idx]
    old = player.in_battle
    old.substitute = False
    reset_stats_mult(old)
    reset_battle_stats(old)
    old.temp_status = None
    old.on_field = False
    player.in_battle = target
    target.on_field = True
    bs.switch_turn()
    return f'Go, {target.name}!'


def exec_move(bs, idx: int) -> str:
    p = bs.player.in_battle
    e = bs.ai.in_battle
    move = p.moves[idx]
    if move is None:
        return 'No move in that slot.'
    if move.pp <= 0:
        cnt_moves = sum(1 for m in p.moves if m is not None)
        cnt_no_pp = sum(1 for m in p.moves if m is not None and m.pp <= 0)
        if cnt_no_pp == cnt_moves:
            struggle_no_pp(p, e)
            bs.switch_turn()
            return p.msg or 'Struggle!'
        return 'No PP left for this move!'
    if p.fainted:
        return "Can't attack — Pokémon fainted! Switch or forfeit."
    try_atk_status(p, move, e)
    bs.switch_turn()
    return p.msg or ''


def do_ai_turn(bs):
    if not bs.player.is_turn():
        bs.handle_turns()


def main():
    parser = argparse.ArgumentParser(
        description='Pokémon battle simulator — terminal edition.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--ai', type=str, default='minimax',
                        choices=['random', 'minimax', 'alphabeta', 'expectimax'],
                        help='AI algorithm (default: minimax)')
    parser.add_argument('--depth', type=int, default=7,
                        help='max search depth for AI tree (default: 7)')
    args = parser.parse_args()

    player = Trainer()

    if args.ai == 'random':
        ai = RandomAI()
    elif args.ai == 'alphabeta':
        ai = MMAlphaBetaAI(player, args.depth)
    elif args.ai == 'expectimax':
        ai = ExpectiMaxAI(player, args.depth)
    else:
        ai = MinimaxAI(player, args.depth)

    ai.get_team()
    bs = battle_system.TurnBattleSystem(player, ai)

    msg = ''
    while True:
        console.clear()
        p = bs.player.in_battle
        e = bs.ai.in_battle
        bs.player_mon = p
        bs.enemy_mon = e

        if bs.player.game_over_lose():
            console.print(Panel(
                '[bold red]DEFEAT![/]\n\nYour last Pokémon fainted!',
                title=' Game Over ', border_style='red',
            ))
            console.print('\nPress Enter to quit...')
            input()
            return

        if bs.ai.game_over_lose():
            console.print(Panel(
                '[bold green]VICTORY![/]\n\nAI\'s last Pokémon fainted!',
                title=' Game Over ', border_style='green',
            ))
            console.print('\nPress Enter to quit...')
            input()
            return

        if not bs.player.is_turn():
            do_ai_turn(bs)
            continue

        if p.fainted:
            render_team(bs)
            console.print('[red]Your Pokémon fainted! Choose a replacement.[/]')
            while True:
                sub = Prompt.ask('Switch to', choices=['0', '1', '2', '3', '4', '5', '6'])
                if sub == '0':
                    break
                idx = int(sub) - 1
                err = switch_valid(bs, idx)
                if err:
                    console.print(f'[red]{err}[/]')
                    continue
                msg = exec_switch(bs, idx)
                break
            continue

        render_core(bs)
        if msg:
            console.print(f'\n[italic]{msg}[/]')
            msg = ''

        choice = Prompt.ask('Action', choices=['1', '2', '3', '4', '5', '6'])
        if choice in ('1', '2', '3', '4'):
            idx = int(choice) - 1
            if p.moves[idx] is None:
                msg = 'No move in that slot.'
                continue
            msg = exec_move(bs, idx)
        elif choice == '5':
            render_team(bs)
            while True:
                sub = Prompt.ask('Switch to', choices=['0', '1', '2', '3', '4', '5', '6'])
                if sub == '0':
                    break
                idx = int(sub) - 1
                err = switch_valid(bs, idx)
                if err:
                    render_team(bs)
                    console.print(f'[red]{err}[/]')
                    continue
                msg = exec_switch(bs, idx)
                break
        elif choice == '6':
            confirm = Prompt.ask('Forfeit? (y/n)', choices=['y', 'n'], default='n')
            if confirm == 'y':
                bs.player.team = [None] * 6


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()
