from enum import StrEnum


class EffectStatus(StrEnum):
    """Status effects that can be inflicted on a Pokemon."""

    BURN = 'Burn'
    FREEZE = 'Freeze'
    PARALYZE = 'Paralyze'
    POISON = 'Poison'
    TOXIC = 'Toxic'
    SLEEP = 'Sleep'
    CONFUSION = 'Confusion'