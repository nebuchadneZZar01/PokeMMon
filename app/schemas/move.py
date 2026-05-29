from enum import Enum

from pydantic import BaseModel

from app.schemas.effect_status import EffectStatus
from app.schemas.typing import Typing


class SecondaryEffect(BaseModel):
    """
    Represents a secondary effect that a move can have, such as inflicting a status condition.

    Attributes:
        chance (int): The percentage chance that the secondary effect will occur when the move is used.
        effect (EffectStatus): The status effect that can be inflicted on the target.
    """

    chance: int
    effect: EffectStatus

class MoveCategory(str, Enum):
    SPECIAL = 'Special'
    PHYSICAL = 'Physical'
    NON_DAMAGING = 'Non-Damaging'

class Move(BaseModel):
    """
    Represents a move that a Pokemon can use in battle.
    
    Attributes:
        name (str): The name of the move.
        category (MoveCategory): The category of the move (Special, Physical, or Non-Damaging).
        typing (Typing): The elemental type of the move.
        power (int): The base power of the move, which is used in damage calculations (0 for non-damaging moves).
        accuracy (int): The percentage chance that the move will hit the target.
        pp (int): The number of times the move can be used before it runs out.
        secondary_effect (SecondaryEffect | None): An optional secondary effect that the move can
    """

    name: str
    category: MoveCategory
    typing: Typing
    power: int
    accuracy: int
    pp: int
    max_pp: int = 0
    secondary_effect: SecondaryEffect | None = None

    def model_post_init(self, __context):
        if self.max_pp == 0:
            self.max_pp = self.pp

    def get_info(self):
        print(self.name)
        print('Typing:', self.typing.value)
        print('Power:', self.power)
        print('PP:', self.pp)
        print('Category:', self.category.value)
        print('Accuracy:', self.accuracy)
