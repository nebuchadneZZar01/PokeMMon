from app.schemas.battle_pokemon import BattlePokemon
from app.schemas.effect_status import EffectStatus
from app.schemas.move import Move, MoveCategory, SecondaryEffect
from app.schemas.pokemon import Pokemon, Stats
from app.schemas.typing import Typing

test_pokemon = Pokemon(
    id=1, 
    name="Bulbasaur", 
    typing=[Typing.GRASS, Typing.POISON], 
    base_stats=Stats(hp=45, attack=49, defense=49, sp_attack=65, sp_defense=65, speed=45)
)

test_in_battle_pokemon = BattlePokemon(
    id=1, 
    name="Bulbasaur", 
    typing=[Typing.GRASS, Typing.POISON],
    base_hp=45, base_attack=49, base_defense=49, base_sp_atk=65, base_sp_def=65, base_speed=45,
    max_hp=100, max_attack=50, max_defense=50, max_sp_atk=65, max_sp_def=65, max_speed=45,
    hp=100, attack=50, defense=50, sp_atk=65, sp_def=65, speed=45,
    moves=[
        Move(
            name="Tackle", 
            typing=Typing.NORMAL, 
            power=40, accuracy=100, pp=35, 
            category=MoveCategory.PHYSICAL,
            secondary_effect=None
        ),
        Move(
            name="Toxic",
            typing=Typing.POISON,
            power=0,
            accuracy=90,
            pp=10,
            category=MoveCategory.NON_DAMAGING,
            secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.POISON)
        ),
        None,
        None,
    ]
)

print(test_in_battle_pokemon.model_dump_json(indent=4))
