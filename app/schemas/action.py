from enum import Enum

from pydantic import BaseModel
from app.schemas.pokemon import Pokemon
from app.schemas.move import Move

class ActionKind(str, Enum):
    ATTACK = "Attack"
    SWITCH = "Switch"

class Action(BaseModel):
    kind: ActionKind
    user: str
    target: Pokemon | Move
