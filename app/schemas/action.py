from enum import StrEnum

from pydantic import BaseModel

from app.schemas.move import Move
from app.schemas.pokemon import Pokemon


class ActionKind(StrEnum):
    """The kind of action a trainer can take in battle."""

    ATTACK = "Attack"
    SWITCH = "Switch"

class Action(BaseModel):
    """Represents a single action choice (attack or switch) during a turn.

    Attributes:
        kind (ActionKind): Whether this is an attack or switch action.
        user (str): The name of the Pokémon performing the action.
        target (Pokemon | Move): The move to use (if attacking) or the Pokémon to switch to.
    """

    kind: ActionKind
    user: str
    target: Pokemon | Move
