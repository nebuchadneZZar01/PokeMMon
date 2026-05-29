import enum

from pydantic import BaseModel
from app.schemas.pokemon import Pokemon
from app.schemas.move import Move

class ActionKind(enum, str):
    """Kind of action a player can take during their turn."""
    
    ATTACK = "Attack"
    SWITCH = "Switch"

class Action(BaseModel):
    """
    A single action that a player can take during their turn.
    
    Attributes:
        kind (ActionKind): The kind of action (attack or switch).
        user (str): The name of the player performing the action.
        target (Pokemon | Move): The target of the action, which can be either a Pokemon (for switching) or a Move (for attacking).
    """

    kind: ActionKind
    user: str
    target: Pokemon | Move