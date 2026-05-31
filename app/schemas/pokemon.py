import math

from pydantic import BaseModel

from app.schemas.typing import Typing


class Stats(BaseModel):
    """Base stats for a Pokémon species.

    Attributes:
        hp (int): Base HP stat.
        attack (int): Base Attack stat.
        defense (int): Base Defense stat.
        sp_attack (int): Base Special Attack stat.
        sp_defense (int): Base Special Defense stat.
        speed (int): Base Speed stat.
    """

    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int

class Pokemon(BaseModel):
    """A Pokémon species entry from the Pokédex.

    Attributes:
        id (int): National Pokédex number.
        name (str): The species name.
        typing (list[Typing]): The Pokémon's type(s), one or two.
        base_stats (Stats): The base stat values for the species.
    """

    id: int
    name: str
    typing: list[Typing]
    base_stats: Stats


def calculate_max_stat(base_stat: int, level: int) -> int:
    """Calculate the maximum value for a stat at a given level.

    Args:
        base_stat (int): The base stat value for the species.
        level (int): The Pokémon's level.

    Returns:
        int: The calculated maximum stat value.
    """
    return math.floor((base_stat * 2 * level) / 100) + 5
