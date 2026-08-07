import logging
import time

from rich.prompt import Prompt

from app.core import battle_system
from app.core.battle_flow import do_ai_turn, exec_move, exec_switch, forfeit, switch_valid
from app.core.player import Trainer
from app.core.strategy import (
    AlphaBetaStrategy,
    ExpectiMaxStrategy,
    MinimaxStrategy,
    RandomStrategy,
)
from app.ui.menu import LLM_NAMES, AIType, LLMProvider, LogLevel, run_setup_menu
from app.ui.renderer import Panel, console, render_core, render_team

AI_THINKING_PANEL = Panel(
    '[bold yellow]AI is thinking...[/]',
    border_style='yellow',
)


def _prompt_switch(bs: battle_system.TurnBattleSystem) -> int | None:
    """Prompt the user for a replacement; return 0-based slot or None on cancel."""
    while True:
        sub = Prompt.ask('Switch to', choices=['0', '1', '2', '3', '4', '5', '6'])
        if sub == '0':
            return None
        idx = int(sub) - 1
        err = switch_valid(bs, idx)
        if err:
            console.clear()
            render_team(bs)
            console.print(f'[red]{err}[/]')
            continue
        return idx


def main() -> None:
    """Main entry point: run setup menu, create trainers, start battle loop."""
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
            provider = config.llm_provider or LLMProvider.OPENAI
            ai = Trainer(LLMAgentStrategy(
                provider=provider.value,
                model=config.llm_model,
                api_key=config.llm_api_key,
                base_uri=config.llm_base_uri,
            ), name=f'AI {LLM_NAMES[provider]} Trainer')
        case _:
            ai = Trainer(MinimaxStrategy(config.depth), name='AI Minimax Trainer')

    ai.get_team()
    bs = battle_system.TurnBattleSystem(player, ai)

    while True:
        try:
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
                idx = _prompt_switch(bs)
                if idx is not None:
                    exec_switch(bs, idx)
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
                idx = _prompt_switch(bs)
                if idx is not None:
                    exec_switch(bs, idx)
                    bs.switch_turn()
                    console.clear()
                    render_core(bs)
                    time.sleep(1.2)
            elif choice == '6':
                confirm = Prompt.ask('Forfeit? (y/n)', choices=['y', 'n'], default='n')
                if confirm == 'y':
                    forfeit(bs)
        except KeyboardInterrupt:
            console.print()
            try:
                confirm = Prompt.ask(
                    '[yellow]Are you really sure to exit? (y/n)[/]',
                    choices=['y', 'n'], default='n',
                )
            except KeyboardInterrupt:
                confirm = 'y'
            if confirm == 'y':
                console.print('[yellow]Exiting...[/]')
                return
            console.clear()
            render_core(bs)
            continue


if __name__ == '__main__':
    main()
