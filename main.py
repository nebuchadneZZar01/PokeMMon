import logging
import time

from rich.prompt import Prompt

from app.core import battle_system
from app.core.combat import reset_battle_stats, reset_stats_mult, struggle_no_pp, try_atk_status
from app.core.player import Trainer
from app.core.strategy import (
    AlphaBetaStrategy,
    ExpectiMaxStrategy,
    MinimaxStrategy,
    RandomStrategy,
)
from app.ui.menu import AIType, LogLevel, run_setup_menu
from app.ui.renderer import Panel, console, render_core, render_team

AI_THINKING_PANEL = Panel(
    '[bold yellow]AI is thinking...[/]',
    border_style='yellow',
)


def switch_valid(bs, idx: int) -> str | None:
    target = bs.player.team[idx]
    if target is None:
        return 'Invalid slot.'
    if target.fainted:
        return f'{target.name} is fainted!'
    if target is bs.player.in_battle:
        return f'{target.name} is already on the field!'
    if bs.player.in_battle.trapped:
        return f'{bs.player.in_battle.name} is trapped and can\'t switch!'
    return None


def exec_switch(bs, idx: int):
    player = bs.player
    target = player.team[idx]
    old = player.in_battle
    old.substitute = False
    reset_stats_mult(old)
    reset_battle_stats(old)
    old.temp_status = None
    old.on_field = False
    old.biding = False
    old.bide_damage = 0
    old.bide_turns = 0
    old.trapped = False
    old.trapped_turns = 0
    old.last_damage_taken = 0
    old.last_move_was_physical = False
    player.in_battle = target
    target.on_field = True
    bs.switch_turn()
    bs.player_msg = f'Go, {target.name}!'


def exec_move(bs, idx: int) -> bool:
    p = bs.player.in_battle
    e = bs.ai.in_battle
    move = p.moves[idx]
    if move is None:
        bs.player_msg = 'No move in that slot.'
        return False
    if p.fainted:
        bs.player_msg = "Can't attack — Pokémon fainted! Switch or forfeit."
        return False
    if move.pp <= 0:
        cnt_moves = sum(1 for m in p.moves if m is not None)
        cnt_no_pp = sum(1 for m in p.moves if m is not None and m.pp <= 0)
        if cnt_no_pp == cnt_moves:
            bs.player_msg = struggle_no_pp(p, e)
            bs.switch_turn()
            return True
        bs.player_msg = 'No PP left for this move!'
        return False
    bs.player_msg = try_atk_status(p, move, e)
    bs.switch_turn()
    return True


def do_ai_turn(bs):
    if not bs.player.is_turn():
        bs.handle_turns()


def main():
    config = run_setup_menu()
    if config is None:
        return

    match config.log_level:
        case LogLevel.SILENT:
            level = logging.CRITICAL + 1
        case LogLevel.INFO:
            level = logging.INFO
        case LogLevel.DEBUG:
            level = logging.DEBUG
    logging.basicConfig(level=level, format='%(message)s')

    player = Trainer()

    match config.ai_type:
        case AIType.RANDOM:
            ai = Trainer(RandomStrategy(), name='AI Random Trainer')
        case AIType.ALPHABETA:
            ai = Trainer(AlphaBetaStrategy(config.depth), name='AI Alpha-Beta Trainer')
        case AIType.EXPECTIMAX:
            ai = Trainer(ExpectiMaxStrategy(config.depth), name='AI ExpectiMax Trainer')
        case AIType.LLM:
            from app.core.llm_strategy import LLMAgentStrategy
            _provider_names = {
                'openai': 'OpenAI', 'anthropic': 'Anthropic',
                'gemini': 'Gemini', 'ollama': 'Ollama',
            }
            pn = _provider_names.get(config.llm_provider.value, config.llm_provider.value)
            ai = Trainer(LLMAgentStrategy(
                provider=config.llm_provider.value if config.llm_provider else 'openai',
                model=config.llm_model,
                api_key=config.llm_api_key,
            ), name=f'AI {pn} Trainer')
        case _:
            ai = Trainer(MinimaxStrategy(config.depth), name='AI Minimax Trainer')

    ai.get_team()
    bs = battle_system.TurnBattleSystem(player, ai)

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
            console.print(AI_THINKING_PANEL)
            do_ai_turn(bs)
            console.clear()
            render_core(bs)
            time.sleep(1.2)
            continue

        if p.fainted:
            console.clear()
            render_core(bs)
            console.print()
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
                exec_switch(bs, idx)
                break
            console.clear()
            render_core(bs)
            time.sleep(1.2)
            continue

        if p.recharging:
            p.recharging = False
            bs.player_msg = f'{p.name} must recharge!'
            bs.switch_turn()
            render_core(bs)
            time.sleep(1.2)
            continue

        if p.biding:
            bide_idx = next(
                (i for i, m in enumerate(p.moves)
                 if m is not None and m.name == 'Bide'), None
            )
            if bide_idx is not None:
                exec_move(bs, bide_idx)
            render_core(bs)
            time.sleep(1.2)
            continue

        render_core(bs)

        choice = Prompt.ask('Action', choices=['1', '2', '3', '4', '5', '6'])
        if choice in ('1', '2', '3', '4'):
            idx = int(choice) - 1
            if exec_move(bs, idx):
                console.clear()
                render_core(bs)
                time.sleep(1.2)
        elif choice == '5':
            console.clear()
            render_team(bs)
            while True:
                sub = Prompt.ask('Switch to', choices=['0', '1', '2', '3', '4', '5', '6'])
                if sub == '0':
                    break
                idx = int(sub) - 1
                err = switch_valid(bs, idx)
                if err:
                    console.clear()
                    render_team(bs)
                    console.print(f'[red]{err}[/]')
                    continue
                exec_switch(bs, idx)
                console.clear()
                render_core(bs)
                time.sleep(1.2)
                break
        elif choice == '6':
            confirm = Prompt.ask('Forfeit? (y/n)', choices=['y', 'n'], default='n')
            if confirm == 'y':
                bs.player.team = [None] * 6


if __name__ == '__main__':
    main()
