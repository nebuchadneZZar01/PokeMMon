from __future__ import annotations

import logging
import math
import random

from pydantic import BaseModel, Field

from app.data import moves
from app.schemas.effect_status import EffectStatus
from app.schemas.move import Move
from app.schemas.pokemon import Pokemon, calculate_max_stat
from app.schemas.typing import Typing

logger = logging.getLogger(__name__)


class BattlePokemon(BaseModel):
    id: int
    name: str
    typing: list[Typing] = []
    level: int = 100
    moves: list[Move | None] = Field(default_factory=lambda: [None] * 4)

    status: EffectStatus | None = None
    temp_status: EffectStatus | None = None
    on_field: bool = False
    fainted: bool = False

    base_hp: int = 0
    base_attack: int = 0
    base_defense: int = 0
    base_sp_atk: int = 0
    base_sp_def: int = 0
    base_speed: int = 0

    max_hp: int = 0
    max_attack: int = 0
    max_defense: int = 0
    max_sp_atk: int = 0
    max_sp_def: int = 0
    max_speed: int = 0

    hp: float = 0
    attack: float = 0
    defense: float = 0
    sp_atk: float = 0
    sp_def: float = 0
    speed: float = 0
    accuracy: float = 1.0
    evasion: float = 1.0

    atk_mult: int = 0
    def_mult: int = 0
    sp_atk_mult: int = 0
    sp_def_mult: int = 0
    speed_mult: int = 0
    acc_mult: int = 0
    ev_mult: int = 0

    substitute: bool = False
    sub_damage: int = 0
    transformed: bool = False
    seeded: bool = False
    sleeping_turns: int = 0
    confused_turns: int = 0
    toxic_turns: int = 0
    reflect: bool = False
    light_screen: bool = False
    mist: bool = False

    def model_post_init(self, __context):
        if all(m is None for m in self.moves):
            self._select_random_moves()

    @staticmethod
    def _normalize_level(level):
        if level < 1:
            return 1
        if level > 100:
            return 100
        return level

    def _select_random_moves(self):
        available = [m for m in moves.attacks if moves.is_compatible(m.name, self.name)]
        random.shuffle(available)

        chosen = []
        for move in available:
            if len(chosen) >= 4:
                break
            if move.name not in [m.name for m in chosen]:
                chosen.append(move)

        for index, move in enumerate(chosen):
            self.moves[index] = move.model_copy(deep=True)

    @classmethod
    def from_template(cls, template: Pokemon, level: int = 100):
        level = cls._normalize_level(level)
        typing = template.typing[:]
        bs = template.base_stats

        max_hp = math.floor((bs.hp * 2 * level) / 100) + level + 10
        max_attack = calculate_max_stat(bs.attack, level)
        max_defense = calculate_max_stat(bs.defense, level)
        max_sp_atk = calculate_max_stat(bs.sp_attack, level)
        max_sp_def = calculate_max_stat(bs.sp_defense, level)
        max_speed = calculate_max_stat(bs.speed, level)

        return cls(
            id=template.id,
            name=template.name,
            typing=typing,
            level=level,
            base_hp=bs.hp,
            base_attack=bs.attack,
            base_defense=bs.defense,
            base_sp_atk=bs.sp_attack,
            base_sp_def=bs.sp_defense,
            base_speed=bs.speed,
            max_hp=max_hp,
            max_attack=max_attack,
            max_defense=max_defense,
            max_sp_atk=max_sp_atk,
            max_sp_def=max_sp_def,
            max_speed=max_speed,
            hp=max_hp,
            attack=max_attack,
            defense=max_defense,
            sp_atk=max_sp_atk,
            sp_def=max_sp_def,
            speed=max_speed,
        )

    def get_stats(self):
        logger.debug(
            'Name: %s Type: %s Level: %s',
            self.name, [t.value for t in self.typing], self.level,
        )
        logger.debug('Hp: %s', self.hp)
        logger.debug('Atk: %s', self.attack)
        logger.debug('Def: %s', self.defense)
        logger.debug('Sp Atk: %s', self.sp_atk)
        logger.debug('Sp Def: %s', self.sp_def)
        logger.debug('Spe: %s\n', self.speed)

    def get_stats_mult(self):
        logger.debug('Atk: %s', self.atk_mult)
        logger.debug('Def: %s', self.def_mult)
        logger.debug('Sp Atk: %s', self.sp_atk_mult)
        logger.debug('Sp Def: %s', self.sp_def_mult)
        logger.debug('Spe: %s', self.speed_mult)
        logger.debug('Ev: %s', self.ev_mult)
        logger.debug('Acc: %s\n', self.acc_mult)

    def get_moves(self):
        for move in self.moves:
            if move is not None:
                move.get_info()
                logger.debug('\n')
            else:
                logger.debug('None\n')
