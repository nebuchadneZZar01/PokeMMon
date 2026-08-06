from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import app.data.pkmn_types as pkmn_types
from app.core.combat import calculate_damage, struggle_no_pp, try_atk_status
from app.schemas.action import Action
from app.schemas.move import Move

if TYPE_CHECKING:
    from app.core.player import Trainer

logger = logging.getLogger(__name__)


class RandomStrategy:
    """Strategy that picks a random move for the AI."""

    def __init__(self) -> None:
        self.choices: list[str] = []

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        """Pick and execute a random move.

        Returns:
            str | None: Battle message from the executed move.
        """
        if trainer.is_turn():
            trainer.verify_fainted_switch()
            available = [m for m in trainer.in_battle.moves if m is not None]
            if not available:
                return struggle_no_pp(trainer.in_battle, rival.in_battle)
            move = random.choice(available)
            logger.info(move.name)
            self.choices.append(move.name)
            return try_atk_status(trainer.in_battle, move, rival.in_battle)
        return None


class _BaseMinimaxStrategy:
    """Base class for minimax-based AI strategies with state evaluation."""

    def __init__(self, max_play_depth: int = 7) -> None:
        """Initialize the minimax strategy.

        Args:
            max_play_depth (int): Maximum search depth (default 7).
        """
        self.choices: list[str] = []
        self.max_play_depth = max_play_depth
        self.win_val = 1000000
        self.last_move: Move | None = None

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        """Pick the best move using minimax search.

        Returns:
            str | None: Battle message from the chosen move.
        """
        if not trainer.is_turn():
            return None
        trainer.verify_fainted_switch()
        choices = trainer.get_possible_choices()
        trainer.print_choices(choices)
        if not choices:
            return struggle_no_pp(trainer.in_battle, rival.in_battle)
        best = choices[0]
        best_val = -float('inf')
        for action in choices:
            val = self.minimax(self.max_play_depth, action, True, trainer, rival)
            if val >= best_val:
                best = action
                best_val = val
        best_move = best.target
        assert isinstance(best_move, Move)
        self.last_move = best_move
        logger.info('Chosen move: %s', best_move.name)
        self.choices.append(best_move.name)
        return try_atk_status(trainer.in_battle, best_move, rival.in_battle)

    def evaluate(self, action: Action, trainer: Trainer, rival: Trainer) -> float:
        """Evaluate the board state after a hypothetical action.

        Considers HP difference, damage potential, stat stages, status effects,
        fainted count, type effectiveness, and move repetition penalty.

        Returns:
            float: Heuristic value (higher = better for the evaluating player).
        """
        s_hp = sum(p.hp for p in trainer.team if p is not None)
        s_hp_full = sum(p.max_hp for p in trainer.team if p is not None)
        s_stats = sum(
            p.atk_mult + p.def_mult + p.sp_atk_mult + p.sp_def_mult
            + p.speed_mult + p.acc_mult + p.ev_mult
            for p in trainer.team if p is not None
        )
        s_status = sum(
            1 for p in trainer.team
            if p is not None and p.status is not None and not p.fainted
        )
        s_fainted = sum(1 for p in trainer.team if p is not None and p.fainted)

        t_hp = sum(p.hp for p in rival.team if p is not None)
        t_hp_full = sum(p.max_hp for p in rival.team if p is not None)
        t_stats = sum(
            p.atk_mult + p.def_mult + p.sp_atk_mult + p.sp_def_mult
            + p.speed_mult + p.acc_mult + p.ev_mult
            for p in rival.team if p is not None
        )
        t_status = sum(
            1 for p in rival.team
            if p is not None and p.status is not None and not p.fainted
        )
        t_fainted = sum(1 for p in rival.team if p is not None and p.fainted)

        hp_diff = (s_hp_full - t_hp_full) - (s_hp - t_hp)
        status_diff = t_status - s_status
        stats_diff = s_stats - t_stats
        fainted_diff = t_fainted - s_fainted
        move = action.target
        assert isinstance(move, Move)
        move_damage, _ = calculate_damage(trainer.in_battle, move, rival.in_battle)

        logger.debug('hp_diff: %s', hp_diff)
        logger.debug('status_diff: %s', status_diff)
        logger.debug('stats_diff: %s', stats_diff)
        logger.debug('fainted_diff: %s', fainted_diff)
        logger.debug('possible move: %s', move.name)
        logger.debug('possible damage: %s', move_damage)

        value = (hp_diff * .35 + move_damage * .35 + status_diff * 100 * .25
                 + stats_diff * 100 * .05 + fainted_diff * 100)

        if action.target == self.last_move:
            value -= 100

        eff = pkmn_types.get_effectiveness(move.typing, rival.in_battle.typing[0])
        if len(rival.in_battle.typing) == 2:
            eff *= pkmn_types.get_effectiveness(move.typing, rival.in_battle.typing[1])

        if eff == 4:
            value += 100
        elif eff == 2:
            value += 50
        elif eff == 0.5:
            value -= 50
        elif eff == 0:
            value -= 100

        logger.debug('value: %s\n', value)
        return value


    def minimax(self, depth: int, action: Action, is_maximizing: bool,
                trainer: Trainer, rival: Trainer) -> float:
        """Recursive minimax search for the best action.

        Args:
            depth (int): Remaining search depth.
            action: The current action being evaluated.
            is_maximizing (bool): True if this is a maximizing node.
            trainer (Trainer): The current player.
            rival (Trainer): The opponent.

        Returns:
            float: The evaluated value of this node.
        """
        if trainer.game_over_lose() or rival.game_over_lose():
            return -self.win_val if trainer.game_over_lose() else self.win_val
        if depth == 0:
            return self.evaluate(action, trainer, rival)

        if is_maximizing:
            best_val = -float('inf')
            for move in trainer.get_possible_choices():
                val = self.minimax(depth - 1, move, False, trainer, rival)
                best_val = max(best_val, val)
            return best_val
        best_val = float('inf')
        for move in rival.get_possible_choices():
            val = self.minimax(depth - 1, move, True, trainer, rival)
            best_val = min(best_val, val)
        return best_val


class MinimaxStrategy(_BaseMinimaxStrategy):
    """Standard minimax strategy — no alpha-beta pruning."""
    pass


class AlphaBetaStrategy(_BaseMinimaxStrategy):
    """Minimax strategy with alpha-beta pruning for efficiency."""

    def __init__(self, max_play_depth: int = 7) -> None:
        """Initialize the alpha-beta strategy.

        Args:
            max_play_depth (int): Maximum search depth (default 7).
        """
        super().__init__(max_play_depth)

    def minimax(self, depth: int, action: Action, is_maximizing: bool,
                trainer: Trainer, rival: Trainer,
                alpha: float = -float('inf'), beta: float = float('inf')) -> float:
        """Recursive minimax with alpha-beta pruning.

        Args:
            depth (int): Remaining search depth.
            action: The current action being evaluated.
            is_maximizing (bool): True if this is a maximizing node.
            trainer (Trainer): The current player.
            rival (Trainer): The opponent.
            alpha (float): Best value the maximizing player can force so far.
            beta (float): Best value the minimizing player can force so far.

        Returns:
            float: The evaluated value of this node.
        """
        logger.debug('\n--- NODE DEPTH: %s ---', depth)
        if trainer.game_over_lose() or rival.game_over_lose():
            return -self.win_val if trainer.game_over_lose() else self.win_val
        if depth == 0:
            return self.evaluate(action, trainer, rival)

        if is_maximizing:
            best_val = -float('inf')
            for move in trainer.get_possible_choices():
                val = self.minimax(depth - 1, move, False, trainer, rival, alpha, beta)
                best_val = max(best_val, val)
                alpha = max(alpha, best_val)
                if beta <= alpha:
                    break
            return best_val
        best_val = float('inf')
        for move in rival.get_possible_choices():
            val = self.minimax(depth - 1, move, True, trainer, rival, alpha, beta)
            best_val = min(best_val, val)
            beta = min(beta, best_val)
            if beta <= alpha:
                break
        return best_val


class ExpectiMaxStrategy(_BaseMinimaxStrategy):
    """Expectimax strategy — averages opponent moves instead of minimizing."""

    def minimax(self, depth: int, action: Action, is_maximizing: bool,
                trainer: Trainer, rival: Trainer) -> float:
        """Recursive expectimax search (averages over stochastic opponent choices).

        Args:
            depth (int): Remaining search depth.
            action: The current action being evaluated.
            is_maximizing (bool): True if this is a maximizing node.
            trainer (Trainer): The current player.
            rival (Trainer): The opponent.

        Returns:
            float: The evaluated value of this node.
        """
        logger.debug('\n--- NODE DEPTH: %s ---', depth)
        if trainer.game_over_lose() or rival.game_over_lose():
            return -self.win_val if trainer.game_over_lose() else self.win_val
        if depth == 0:
            return self.evaluate(action, trainer, rival)

        if is_maximizing:
            best_val = -float('inf')
            for move in trainer.get_possible_choices():
                val = self.minimax(depth - 1, move, False, trainer, rival)
                best_val = max(best_val, val)
            return best_val
        total = 0.0
        n = len(rival.get_possible_choices())
        for move in rival.get_possible_choices():
            val = self.minimax(depth - 1, move, True, trainer, rival)
            total += val / n
        return total
