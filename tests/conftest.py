from __future__ import annotations

from app.schemas.battle_pokemon import BattlePokemon
from app.schemas.move import Move, MoveCategory, SecondaryEffect
from app.schemas.typing import Typing


def make_move(
    name: str = "Tackle",
    typing: Typing = Typing.NORMAL,
    power: int = 40,
    accuracy: int = 100,
    pp: int = 35,
    category: MoveCategory = MoveCategory.PHYSICAL,
    secondary_effect: SecondaryEffect | None = None,
) -> Move:
    return Move(
        name=name, typing=typing, power=power, accuracy=accuracy,
        pp=pp, max_pp=pp, category=category, secondary_effect=secondary_effect,
    )


def make_pkmn(
    id: int = 1,
    name: str = "TestMon",
    typing: list[Typing] | None = None,
    level: int = 100,
    hp: int = 200,
    attack: int = 50,
    defense: int = 50,
    sp_atk: int = 50,
    sp_def: int = 50,
    speed: int = 50,
    base_speed: int = 50,
    **kwargs,
) -> BattlePokemon:
    if typing is None:
        typing = [Typing.NORMAL]
    move = make_move()
    max_hp = kwargs.pop('max_hp', hp)
    moves = kwargs.pop('moves', [move.model_copy(deep=True), None, None, None])
    return BattlePokemon(
        id=id, name=name, typing=typing, level=level,
        base_hp=hp, base_attack=attack, base_defense=defense,
        base_sp_atk=sp_atk, base_sp_def=sp_def, base_speed=base_speed,
        max_hp=max_hp, max_attack=attack, max_defense=defense,
        max_sp_atk=sp_atk, max_sp_def=sp_def, max_speed=speed,
        hp=hp, attack=attack, defense=defense,
        sp_atk=sp_atk, sp_def=sp_def, speed=speed,
        moves=moves,
        **kwargs,
    )


def damage_no_var(level: int, power: int, a: float, d: float, crit: int = 1,
                  stab: int = 1, effectiveness: float = 1.0) -> int:
    return int(((2 * level * crit / 5 + 2) * power * (a / d) / 50 + 2)
               * stab * effectiveness * 1.0)
