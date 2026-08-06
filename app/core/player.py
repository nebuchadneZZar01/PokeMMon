from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from app.core.combat import reset_on_switch_out
from app.data.pokedex import pokedex
from app.schemas.action import Action, ActionKind
from app.schemas.battle_pokemon import BattlePokemon
from app.schemas.move import Move

if TYPE_CHECKING:
    from app.schemas.strategy import AIStrategy

logger = logging.getLogger(__name__)


class Trainer:
    """Represents a Pokémon trainer (human or AI) with a team of 6 Pokémon.

    Attributes:
        team (list[BattlePokemon | None]): Up to 6 Pokémon, None for empty slots.
        token (bool): Turn ownership flag.
        is_ai (bool): Whether this trainer uses an AI strategy.
        _strategy (AIStrategy | None): The AI strategy instance (None for human).
        _name (str | None): Custom display name.
        in_battle (BattlePokemon): The currently active Pokémon.
    """

    team: list[BattlePokemon | None]
    token: bool | None
    is_ai: bool
    _strategy: AIStrategy | None
    _name: str | None
    in_battle: BattlePokemon

    def __init__(self, strategy: AIStrategy | None = None, name: str | None = None):
        """Initialize a trainer with a random team of 6 Pokémon.

        Args:
            strategy (AIStrategy | None): AI strategy to use (None for human player).
            name (str | None): Custom name for the trainer.
        """
        self.team = [None] * 6
        self.token = None
        self.is_ai = strategy is not None
        self._strategy = strategy
        self._name = name

        for i in range(len(self.team)):
            tmp = random.choice(pokedex)
            self.team[i] = BattlePokemon.from_template(tmp)

        first = self.team[0]
        assert first is not None
        self.in_battle = first
        first.on_field = True

    @property
    def name(self) -> str:
        """Get the trainer's display name.

        Returns:
            str: The custom name, 'Player' for humans, or the strategy class name for AI.
        """
        if self._name:
            return self._name
        if not self._strategy:
            return 'Player'
        return type(self._strategy).__name__.removesuffix('Strategy')

    def get_team_with_stats(self) -> None:
        """Log stats and moves for all team members."""
        for pkmn in self.team:
            assert pkmn is not None
            pkmn.get_stats()
            pkmn.get_moves()

    def get_team(self) -> None:
        """Log team roster with names and types."""
        if not self.is_ai:
            logger.info('Player Team:')
        else:
            logger.info('AI Team:')
        for pkmn in self.team:
            assert pkmn is not None
            logger.info('- %s \t%s', pkmn.name, [t.value for t in pkmn.typing])

    def get_possible_choices(self) -> list[Action]:
        """Get all valid move actions for the active Pokémon.

        Excludes moves with 0 PP and disabled moves. Forces Bide if active.

        Returns:
            list[Action]: List of valid attack actions.
        """
        possible_choices = []

        if self.in_battle.biding:
            bide_move = next(
                (m for m in self.in_battle.moves if m is not None and m.name == 'Bide'), None
            )
            if bide_move:
                return [Action(
                    kind=ActionKind.ATTACK, user=self.in_battle.name, target=bide_move,
                )]
            return []

        for i, move in enumerate(self.in_battle.moves):
            if move is not None and move.pp > 0 and i != self.in_battle.disabled_move:
                possible_choices.append(Action(
                    kind=ActionKind.ATTACK, user=self.in_battle.name, target=move,
                ))

        return possible_choices

    def get_possible_switch_choices(self) -> list[Action]:
        """Get all valid switch actions for the active Pokémon.

        Switches are unavailable while Biding or trapped. The active Pokémon
        and fainted/none bench slots are excluded.

        Returns:
            list[Action]: List of valid switch actions.
        """
        if self.in_battle.biding or self.in_battle.trapped:
            return []
        return [
            Action(kind=ActionKind.SWITCH, user=self.in_battle.name, target=p)
            for p in self.team
            if p is not None and p is not self.in_battle and not p.fainted
        ]

    def strategic_switch(self, target: BattlePokemon) -> str:
        """Switch the active Pokémon to ``target`` as a strategic action.

        Resets the outgoing Pokémon's battle state and returns the
        announcement message.

        Args:
            target (BattlePokemon): The Pokémon to send out.

        Returns:
            str: The switch announcement message.
        """
        old = self.in_battle
        reset_on_switch_out(old)
        self.in_battle = target
        target.on_field = True
        return f'{self.name} sent out {target.name}! Go, {target.name}!'

    def print_choices(self, choices: list[Action]) -> None:
        """Log possible choice details for debugging.

        Args:
            choices (list[Action]): The list of valid actions.
        """
        logger.debug('\n%s\'s possible choices:', self.in_battle.name)
        for i, c in enumerate(choices):
            if c.kind == ActionKind.SWITCH:
                target = c.target
                assert isinstance(target, BattlePokemon)
                logger.debug('- %d) SWITCH to: %s', i + 1, target.name)
                continue
            target = c.target
            assert isinstance(target, Move)
            logger.debug('- %d) name: %s, power: %s, type: %s, kind: %s',
                         i + 1, target.name, target.power,
                         target.typing.value, target.category.value)

    def game_over_lose(self) -> bool:
        """Check if all team members have fainted.

        Returns:
            bool: True if the entire team is fainted or empty.
        """
        faint_cnt = 0

        for pkmn in self.team:
            if pkmn is None or pkmn.fainted:
                faint_cnt += 1

        return faint_cnt == len(self.team)

    def is_turn(self) -> bool:
        """Check if it's this trainer's turn.

        Returns:
            bool: True if this trainer has the turn token.
        """
        return bool(self.token)

    def set_turn(self, _token: bool) -> None:
        """Set the turn token for this trainer.

        Args:
            _token (bool): The turn token value.
        """
        self.token = _token

    def verify_fainted_switch(self) -> None:
        """Auto-switch to the next available Pokémon if the current one has fainted."""
        if not self.game_over_lose() and self.in_battle.fainted:
            self.in_battle.on_field = False
            for pkmn in self.team:
                if pkmn is not None and not pkmn.fainted:
                    self.in_battle = pkmn
                    pkmn.on_field = True
                    break

    def get_choice(self, rival: Trainer) -> str | None:
        """Delegate move selection to the AI strategy, if set.

        Args:
            rival (Trainer): The opposing trainer.

        Returns:
            str | None: The battle message from the chosen action, or None if no strategy.
        """
        if self._strategy:
            return self._strategy.get_choice(self, rival)
        return None
