from __future__ import annotations

import logging
import math
import random
from typing import Any, cast

from pydantic import BaseModel, Field

from app.data import moves
from app.schemas.effect_status import EffectStatus
from app.schemas.move import Move
from app.schemas.pokemon import Pokemon, calculate_max_stat
from app.schemas.typing import Typing

logger = logging.getLogger(__name__)


class BattlePokemon(BaseModel):
    """Runtime battle state for a single Pokémon instance.

    Tracks current HP, stat stages, status conditions, and battle flags
    (substitute, reflect, light screen, etc.). Created from a static
    Pokemon template via from_template().

    Attributes:
        id (int): National Pokédex number.
        name (str): The species name.
        typing (list[Typing]): Current type(s) — may change via Conversion/Transform.
        level (int): Current level (1-100).
        moves (list[Move | None]): Up to 4 moves with current PP.
        status (EffectStatus | None): Primary status condition.
        temp_status (EffectStatus | None): Temporary status (confusion).
        on_field (bool): Whether this Pokémon is currently active.
        fainted (bool): Whether this Pokémon has fainted.
        base_hp (int): Base HP stat.
        base_attack (int): Base Attack stat.
        base_defense (int): Base Defense stat.
        base_sp_atk (int): Base Special Attack stat.
        base_sp_def (int): Base Special Defense stat.
        base_speed (int): Base Speed stat.
        max_hp (int): Maximum HP after stat calculation.
        max_attack (int): Maximum Attack after stat calculation.
        max_defense (int): Maximum Defense after stat calculation.
        max_sp_atk (int): Maximum Special Attack after stat calculation.
        max_sp_def (int): Maximum Special Defense after stat calculation.
        max_speed (int): Maximum Speed after stat calculation.
        hp (float): Current HP.
        attack (float): Current Attack (affected by stat stages).
        defense (float): Current Defense (affected by stat stages).
        sp_atk (float): Current Special Attack (affected by stat stages).
        sp_def (float): Current Special Defense (affected by stat stages).
        speed (float): Current Speed (affected by stat stages).
        accuracy (float): Current accuracy multiplier.
        evasion (float): Current evasion multiplier.
        atk_mult (int): Attack stat stage (-6 to +6).
        def_mult (int): Defense stat stage (-6 to +6).
        sp_atk_mult (int): Special Attack stat stage (-6 to +6).
        sp_def_mult (int): Special Defense stat stage (-6 to +6).
        speed_mult (int): Speed stat stage (-6 to +6).
        acc_mult (int): Accuracy stat stage (-6 to +6).
        ev_mult (int): Evasion stat stage (-6 to +6).
        substitute (bool): Whether a Substitute doll is active.
        sub_damage (int): Damage absorbed by Substitute.
        sub_max (int): Max HP of the Substitute doll (25% of max HP).
        transformed (bool): Whether this Pokémon has used Transform.
        seeded (bool): Whether this Pokémon is seeded by Leech Seed.
        sleeping_turns (int): Turns of sleep remaining (decrements to 0).
        confused_turns (int): Turns of confusion remaining (decrements to 0).
        toxic_turns (int): Turns of Toxic accumulation.
        reflect (bool): Whether Reflect is active on this side.
        reflect_turns (int): Turns remaining for Reflect.
        light_screen (bool): Whether Light Screen is active on this side.
        light_screen_turns (int): Turns remaining for Light Screen.
        mist (bool): Whether Mist is active on this side.
        mist_turns (int): Turns remaining for Mist.
        disabled_move (int): Index of disabled move, or -1.
        disabled_turns (int): Turns remaining for disable.
        focus_energy (bool): Whether Focus Energy is active.
        recharging (bool): Whether the Pokémon must recharge (Hyper Beam).
        biding (bool): Whether the Pokémon is using Bide.
        bide_damage (int): Accumulated damage during Bide.
        bide_turns (int): Turns spent charging Bide.
        bide_duration (int): Total turns Bide charges (2-3).
        last_damage_taken (int): Most recent damage received.
        last_move_was_physical (bool): Whether the last move used against this was physical.
        trapped (bool): Whether the Pokémon is trapped (Wrap, Bind, etc.).
        trapped_turns (int): Turns remaining for trap.
    """
    id: int
    name: str
    typing: list[Typing] = []
    level: int = 100
    moves: list[Move | None] = Field(
        default_factory=lambda: cast(list[Move | None], [None] * 4),
    )

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
    sub_max: int = 0
    transformed: bool = False
    seeded: bool = False
    sleeping_turns: int = 0
    confused_turns: int = 0
    toxic_turns: int = 0
    reflect: bool = False
    reflect_turns: int = 0
    light_screen: bool = False
    light_screen_turns: int = 0
    mist: bool = False
    mist_turns: int = 0
    disabled_move: int = -1
    disabled_turns: int = 0
    focus_energy: bool = False
    recharging: bool = False

    biding: bool = False
    bide_damage: int = 0
    bide_turns: int = 0
    bide_duration: int = 0

    last_damage_taken: int = 0
    last_move_was_physical: bool = False
    last_move_used: str = ''

    trapped: bool = False
    trapped_turns: int = 0

    rampaging: bool = False
    rampage_turns: int = 0
    rampage_move: str = ''

    charging: bool = False
    charge_move: str = ''

    raging: bool = False
    rage_move: str = ''
    rage_hit: bool = False

    def model_post_init(self, __context: Any) -> None:
        """Select random moves if no moves are set."""
        if all(m is None for m in self.moves):
            self._select_random_moves()

    @staticmethod
    def _normalize_level(level: int) -> int:
        """Clamp level to the valid range 1-100.

        Args:
            level (int): The level to normalize.

        Returns:
            int: A level between 1 and 100 inclusive.
        """
        if level < 1:
            return 1
        if level > 100:
            return 100
        return level

    def _select_random_moves(self) -> None:
        """Fill empty move slots with random compatible moves from the learnset."""
        available = list(moves.COMPAT_MOVES.get(self.name, []))
        random.shuffle(available)

        chosen: list[Move] = []
        for move in available:
            if len(chosen) >= 4:
                break
            if move.name not in [m.name for m in chosen]:
                chosen.append(move)

        for index, move in enumerate(chosen):
            self.moves[index] = move.model_copy(deep=True)

    def forced_move(self) -> Move | None:
        """Return the move this Pokémon is locked into (charge, rampage, or Rage)."""
        name = ''
        if self.charging:
            name = self.charge_move
        elif self.rampaging:
            name = self.rampage_move
        elif self.raging:
            name = self.rage_move
        if not name:
            return None
        return next((m for m in self.moves if m is not None and m.name == name), None)

    @classmethod
    def from_template(cls, template: Pokemon, level: int = 100) -> BattlePokemon:
        """Create a BattlePokemon from a static Pokemon template.

        Calculates stats at the given level using Gen 1 formulas.

        Args:
            template (Pokemon): The species template from the Pokédex.
            level (int): The level for the new instance (1-100).

        Returns:
            BattlePokemon: A fully initialized battle Pokémon.
        """
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

    def get_stats(self) -> None:
        """Log current stats for debugging."""
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

    def get_stats_mult(self) -> None:
        """Log current stat stage multipliers for debugging."""
        logger.debug('Atk: %s', self.atk_mult)
        logger.debug('Def: %s', self.def_mult)
        logger.debug('Sp Atk: %s', self.sp_atk_mult)
        logger.debug('Sp Def: %s', self.sp_def_mult)
        logger.debug('Spe: %s', self.speed_mult)
        logger.debug('Ev: %s', self.ev_mult)
        logger.debug('Acc: %s\n', self.acc_mult)

    def get_moves(self) -> None:
        """Log current moves and their details for debugging."""
        for move in self.moves:
            if move is not None:
                move.get_info()
                logger.debug('\n')
            else:
                logger.debug('None\n')
