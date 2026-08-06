from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import app.data.pkmn_types as pkmn_types
from app.core.combat import calculate_damage, struggle_no_pp, try_atk_status
from app.schemas.action import Action, ActionKind
from app.schemas.battle_pokemon import BattlePokemon
from app.schemas.move import Move

if TYPE_CHECKING:
    from app.core.player import Trainer

logger = logging.getLogger(__name__)

_HP_WEIGHT = 0.35
_DAMAGE_WEIGHT = 0.35
_STATUS_WEIGHT = 0.25
_STAT_WEIGHT = 0.05
_FAINT_WEIGHT = 100
_SWITCH_COST = 100


class RandomStrategy:
    """Strategy that picks a random move for the AI."""

    def __init__(self) -> None:
        self.choices: list[str] = []

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        """Pick and execute a random action (move or switch).

        Returns:
            str | None: Battle message from the executed action.
        """
        if trainer.is_turn():
            trainer.verify_fainted_switch()
            moves = [m for m in trainer.in_battle.moves if m is not None]
            attacks = [
                Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=m)
                for m in moves
            ]
            choices = attacks + trainer.get_possible_switch_choices()
            if not choices:
                return struggle_no_pp(trainer.in_battle, rival.in_battle)
            chosen = random.choice(choices)
            return self._execute(trainer, rival, chosen)
        return None

    def _execute(self, trainer: Trainer, rival: Trainer, action: Action) -> str:
        """Execute a chosen action (attack or switch) and return its message.

        Returns:
            str: Battle message from the executed action.
        """
        if action.kind == ActionKind.SWITCH:
            target = action.target
            assert isinstance(target, BattlePokemon)
            self.choices.append(f'switch:{target.name}')
            return trainer.strategic_switch(target)
        move = action.target
        assert isinstance(move, Move)
        logger.info(move.name)
        self.choices.append(move.name)
        return try_atk_status(trainer.in_battle, move, rival.in_battle)


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
        self.prune = False
        self.average_opponent = False
        self.ordered = False
        self.nodes_visited = 0

    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None:
        """Pick the best action (move or switch) for the active Pokémon.

        Root actions are scored directly via ``evaluate``; the chosen action
        is then executed.

        Returns:
            str | None: Battle message from the chosen action.
        """
        if not trainer.is_turn():
            return None
        trainer.verify_fainted_switch()
        self.nodes_visited = 0
        choices = trainer.get_possible_choices() + trainer.get_possible_switch_choices()
        trainer.print_choices(choices)
        if not choices:
            return struggle_no_pp(trainer.in_battle, rival.in_battle)
        best = choices[0]
        best_val = -float('inf')
        for action in choices:
            val = self.evaluate(action, trainer, rival)
            if val >= best_val:
                best = action
                best_val = val
        return self._execute(trainer, rival, best)

    def _execute(self, trainer: Trainer, rival: Trainer, action: Action) -> str:
        """Execute a chosen action (attack or switch) and return its message.

        Returns:
            str: Battle message from the executed action.
        """
        if action.kind == ActionKind.SWITCH:
            target = action.target
            assert isinstance(target, BattlePokemon)
            self.last_move = None
            self.choices.append(f'switch:{target.name}')
            return trainer.strategic_switch(target)
        move = action.target
        assert isinstance(move, Move)
        self.last_move = move
        logger.info('Chosen move: %s', move.name)
        self.choices.append(move.name)
        return try_atk_status(trainer.in_battle, move, rival.in_battle)

    def evaluate(self, action: Action, trainer: Trainer, rival: Trainer) -> float:
        """Evaluate the board state after a hypothetical action.

        Attack actions consider HP difference, damage potential, stat stages,
        status effects, fainted count, type effectiveness, and move repetition
        penalty. Switch actions are scored on HP gain, status escape, lost stat
        stages, and type matchups.

        Returns:
            float: Heuristic value (higher = better for the evaluating player).
        """
        if action.kind == ActionKind.SWITCH:
            return self._evaluate_switch(action, trainer, rival)

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

        value = (hp_diff * _HP_WEIGHT + move_damage * _DAMAGE_WEIGHT
                 + status_diff * 100 * _STATUS_WEIGHT
                 + stats_diff * 100 * _STAT_WEIGHT
                 + fainted_diff * _FAINT_WEIGHT)

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

    def _evaluate_switch(
        self, action: Action, trainer: Trainer, rival: Trainer,
    ) -> float:
        """Score a hypothetical switch to a bench Pokémon.

        Rewards switching to a healthier bench member, escaping status, and a
        favourable type matchup; penalises losing raised stat stages, being
        vulnerable to the opponent, and the wasted turn.

        Returns:
            float: Heuristic value of the switch.
        """
        target = action.target
        assert isinstance(target, BattlePokemon)
        current = trainer.in_battle
        hp_gain = (target.hp / target.max_hp) - (current.hp / current.max_hp)
        status_escape = 100.0 if current.status is not None else 0.0
        stage_loss = (current.atk_mult + current.def_mult + current.sp_atk_mult
                      + current.sp_def_mult + current.speed_mult) * 100

        def_eff = 1.0
        for m in rival.in_battle.moves:
            if m is None:
                continue
            eff = pkmn_types.get_effectiveness(m.typing, target.typing[0])
            if len(target.typing) == 2:
                eff *= pkmn_types.get_effectiveness(m.typing, target.typing[1])
            def_eff = min(def_eff, eff)

        atk_eff = 0.0
        for m in target.moves:
            if m is None:
                continue
            eff = pkmn_types.get_effectiveness(m.typing, rival.in_battle.typing[0])
            if len(rival.in_battle.typing) == 2:
                eff *= pkmn_types.get_effectiveness(m.typing, rival.in_battle.typing[1])
            atk_eff = max(atk_eff, eff)

        return (hp_gain * 100 * _HP_WEIGHT
                + status_escape * _STATUS_WEIGHT
                - stage_loss * _STAT_WEIGHT
                + (atk_eff - 1.0) * 100
                + (1.0 - def_eff) * 100
                - _SWITCH_COST)


    def minimax(self, depth: int, action: Action, is_maximizing: bool,
                trainer: Trainer, rival: Trainer,
                alpha: float = -float('inf'), beta: float = float('inf')) -> float:
        """Recursive game-tree search.

        Single implementation shared by minimax, alpha-beta, and expectimax;
        the subclass chooses its behaviour through the ``prune``,
        ``average_opponent`` and ``ordered`` flags.

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
        self.nodes_visited += 1
        if trainer.game_over_lose() or rival.game_over_lose():
            return -self.win_val if trainer.game_over_lose() else self.win_val
        if depth == 0:
            return self.evaluate(action, trainer, rival)

        if is_maximizing:
            best_val = -float('inf')
            children = trainer.get_possible_choices()
            if self.ordered:
                children = sorted(
                    children,
                    key=lambda a: self.evaluate(a, trainer, rival),
                    reverse=True,
                )
            for move in children:
                val = self.minimax(depth - 1, move, False, trainer, rival, alpha, beta)
                best_val = max(best_val, val)
                alpha = max(alpha, best_val)
                if self.prune and beta <= alpha:
                    break
            return best_val

        children = rival.get_possible_choices()
        if self.average_opponent:
            n = len(children)
            if n == 0:
                return 0.0
            total = 0.0
            for move in children:
                val = self.minimax(depth - 1, move, True, trainer, rival, alpha, beta)
                total += val / n
            return total
        best_val = float('inf')
        for move in children:
            val = self.minimax(depth - 1, move, True, trainer, rival, alpha, beta)
            best_val = min(best_val, val)
            beta = min(beta, best_val)
            if self.prune and beta <= alpha:
                break
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
        self.prune = True
        self.ordered = True


class ExpectiMaxStrategy(_BaseMinimaxStrategy):
    """Expectimax strategy — averages opponent moves instead of minimizing."""

    def __init__(self, max_play_depth: int = 7) -> None:
        """Initialize the expectimax strategy.

        Args:
            max_play_depth (int): Maximum search depth (default 7).
        """
        super().__init__(max_play_depth)
        self.average_opponent = True
