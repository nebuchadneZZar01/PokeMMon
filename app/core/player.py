from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from app.data.pokedex import pokedex
from app.schemas.action import Action, ActionKind
from app.schemas.battle_pokemon import BattlePokemon

if TYPE_CHECKING:
    from app.schemas.strategy import AIStrategy

logger = logging.getLogger(__name__)


class Trainer:
    def __init__(self, strategy: AIStrategy | None = None, name: str | None = None):
        self.team = [None] * 6
        self.token = None
        self.is_ai = strategy is not None
        self._strategy = strategy
        self._name = name

        for i in range(len(self.team)):
            tmp = random.choice(pokedex)
            self.team[i] = BattlePokemon.from_template(tmp)

        self.in_battle = self.team[0]
        self.team[0].on_field = True

    @property
    def name(self) -> str:
        if self._name:
            return self._name
        if not self._strategy:
            return 'Player'
        return type(self._strategy).__name__.removesuffix('Strategy')

    def get_team_with_stats(self):
        for pkmn in self.team:
            pkmn.get_stats()
            pkmn.get_moves()

    def get_team(self):
        if not self.is_ai:
            logger.info('Player Team:')
        else:
            logger.info('AI Team:')
        for pkmn in self.team:
            logger.info('- %s \t%s', pkmn.name, [t.value for t in pkmn.typing])

    def get_possible_choices(self):
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

    def print_choices(self, choices):
        logger.debug('\n%s\'s possible choices:', self.in_battle.name)
        for i, c in enumerate(choices):
            logger.debug('- %d) name: %s, power: %s, type: %s, kind: %s',
                         i + 1, c.target.name, c.target.power,
                         c.target.typing.value, c.target.category.value)

    def game_over_lose(self):
        faint_cnt = 0

        for pkmn in self.team:
            if pkmn is None or pkmn.fainted:
                faint_cnt += 1

        return faint_cnt == 6

    def is_turn(self):
        return self.token

    def set_turn(self, _token):
        self.token = _token

    def verify_fainted_switch(self):
        if not self.game_over_lose() and self.in_battle.fainted:
            self.in_battle.on_field = False
            for pkmn in self.team:
                if pkmn is not None and not pkmn.fainted:
                    self.in_battle = pkmn
                    pkmn.on_field = True
                    break

    def get_choice(self, rival: Trainer) -> str | None:
        if self._strategy:
            return self._strategy.get_choice(self, rival)
        return None
