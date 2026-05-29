from enum import Enum


class EffectStatus(str, Enum):
    """Status effects that can be inflicted on a Pokemon."""
    
    BURN = 'Burn'
    FREEZE = 'Freeze'
    PARALYZE = 'Paralyze'
    POISON = 'Poison'
    SLEEP = 'Sleep'
    CONFUSION = 'Confusion'