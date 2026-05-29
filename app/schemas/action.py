from enum import StrEnum

from pydantic import BaseModel

from app.schemas.move import Move
from app.schemas.pokemon import Pokemon


class ActionKind(StrEnum):
    ATTACK = "Attack"
    SWITCH = "Switch"

class Action(BaseModel):
    kind: ActionKind
    user: str
    target: Pokemon | Move
