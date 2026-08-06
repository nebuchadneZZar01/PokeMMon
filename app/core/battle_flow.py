"""Pure battle-flow helpers extracted from the interactive game loop.

These functions manipulate a TurnBattleSystem without touching the
terminal, so the full move/switch/forfeit logic is unit-testable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.combat import reset_battle_stats, reset_stats_mult, struggle_no_pp, try_atk_status

if TYPE_CHECKING:
    from app.core.battle_system import TurnBattleSystem


def switch_valid(bs: TurnBattleSystem, idx: int) -> str | None:
    """Validate a switch action.

    Args:
        bs (TurnBattleSystem): The battle system.
        idx (int): 0-based team slot index.

    Returns:
        str | None: Error message if invalid, None if valid.
    """
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


def exec_switch(bs: TurnBattleSystem, idx: int) -> None:
    """Execute a switch action: swap active Pokémon and reset state.

    Args:
        bs (TurnBattleSystem): The battle system.
        idx (int): 0-based team slot index of the incoming Pokémon.
    """
    player = bs.player
    target = player.team[idx]
    assert target is not None
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
    bs.player_msg = f'Go, {target.name}!'


def exec_move(bs: TurnBattleSystem, idx: int) -> bool:
    """Execute a move action for the player.

    Args:
        bs (TurnBattleSystem): The battle system.
        idx (int): 0-based move slot index.

    Returns:
        bool: True if the move was executed, False if invalid.
    """
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


def do_ai_turn(bs: TurnBattleSystem) -> None:
    """Execute the AI's turn if it's the AI's turn.

    Args:
        bs (TurnBattleSystem): The battle system.
    """
    if not bs.player.is_turn():
        bs.handle_turns()


def forfeit(bs: TurnBattleSystem) -> None:
    """Forfeit the battle by wiping the player's team.

    Args:
        bs (TurnBattleSystem): The battle system.
    """
    bs.player.team = [None] * 6
