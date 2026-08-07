from enum import StrEnum

from pydantic import BaseModel

from app.schemas.battle_pokemon import BattlePokemon
from app.schemas.move import Move


class ActionKind(StrEnum):
    """The kind of action a trainer can take in battle."""

    ATTACK = "Attack"
    SWITCH = "Switch"

class Action(BaseModel):
    """Represents a single action choice (attack or switch) during a turn.

    Attributes:
        kind (ActionKind): Whether this is an attack or switch action.
        user (str): The name of the Pokémon performing the action.
        target (BattlePokemon | Move): The move to use (if attacking) or
            the Pokémon to switch to.
    """

    kind: ActionKind
    user: str
    target: BattlePokemon | Move

    @classmethod
    def attack(cls, user: str, move: Move) -> Action:
        """Create an attack action using ``move``."""
        return cls(kind=ActionKind.ATTACK, user=user, target=move)

    @classmethod
    def switch(cls, user: str, pkmn: BattlePokemon) -> Action:
        """Create a switch action to ``pkmn``."""
        return cls(kind=ActionKind.SWITCH, user=user, target=pkmn)
