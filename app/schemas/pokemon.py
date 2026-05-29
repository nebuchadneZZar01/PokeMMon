import math

from pydantic import BaseModel

from app.schemas.typing import Typing


class Stats(BaseModel):
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int

class Pokemon(BaseModel):
    id: int
    name: str
    typing: list[Typing]
    base_stats: Stats


def calculate_max_stat(base_stat: int, level: int) -> int:
    return math.floor((base_stat * 2 * level) / 100) + 5
