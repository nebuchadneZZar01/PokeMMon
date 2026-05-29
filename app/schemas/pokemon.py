from pydantic import BaseModel

from app.schemas.typing import Typing
from app.schemas.move import Move

class Stats(BaseModel):
    """
    Represents the base stats of a Pokemon.

    Attributes:
        hp (int): The base HP stat of the Pokemon.
        attack (int): The base Attack stat of the Pokemon.
        defense (int): The base Defense stat of the Pokemon.
        sp_attack (int): The base Special Attack stat of the Pokemon.
        sp_defense (int): The base Special Defense stat of the Pokemon.
        speed (int): The base Speed stat of the Pokemon.
    """

    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int

class Pokemon(BaseModel):
    """
    Represents a Pokemon with its basic information and stats.

    Attributes:
        id (int): The unique identifier of the Pokemon.
        name (str): The name of the Pokemon.
        types (list[Typing]): The elemental types of the Pokemon.
        base_stats (Stats): The base stats of the Pokemon.
    """

    id: int
    name: str
    types: list[Typing]
    base_stats: Stats

class InBattlePokemon(Pokemon):
    """
    Represents a Pokemon in battle.

    Attributes:
        moves (list[Move]): The list of moves that the Pokemon can use in battle.
    """

    moves: list[Move]