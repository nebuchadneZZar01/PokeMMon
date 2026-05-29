from __future__ import annotations

import math
import random
from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING

from app.data import moves, pkmn_types
from app.schemas.effect_status import EffectStatus
from app.schemas.move import Move, MoveCategory
from app.schemas.typing import Typing

if TYPE_CHECKING:
    from app.schemas.battle_pokemon import BattlePokemon


def has_type(pkmn: BattlePokemon, t: Typing) -> bool:
    return any(ty == t for ty in pkmn.typing)


def update_battle_stat(stat: float, multiplier: int) -> float:
    if multiplier >= 0:
        stat *= ((multiplier * 50) + 100) / 100
    elif multiplier == -1:
        stat *= 0.66
    elif multiplier == -2:
        stat *= 0.5
    elif multiplier == -3:
        stat *= 0.4
    elif multiplier == -4:
        stat *= 0.33
    elif multiplier == -5:
        stat *= 0.28
    elif multiplier == -6:
        stat *= 0.25
    return stat


def handle_recoil(target: BattlePokemon, damage: int, perc_scaler: int) -> int:
    scaler = perc_scaler / 100
    damage_caused = damage - (target.hp - damage) if target.hp - damage < 0 else damage
    return int(damage_caused * scaler)


def inc_dec_stat_mult(
    attacker: BattlePokemon, stat_owner: BattlePokemon, stat_attr: str,
    increase: bool, highly: bool = False,
) -> tuple[int, str]:
    display_names = {
        'atk_mult': 'Attack',
        'def_mult': 'Defense',
        'sp_atk_mult': 'Special Attack',
        'sp_def_mult': 'Special Defense',
        'speed_mult': 'Speed',
        'ev_mult': 'Evasion',
        'acc_mult': 'Accuracy',
    }
    name = display_names[stat_attr]
    multiplier = getattr(stat_owner, stat_attr)

    if increase:
        if multiplier >= 6:
            msg = f"\n{stat_owner.name}'s {name} won't rise anymore!\n"
        else:
            if highly:
                multiplier += 2
                msg = f"\n{stat_owner.name}'s {name} went way up!\n"
            else:
                multiplier += 1
                msg = f"\n{stat_owner.name}'s {name} went up!\n"
    else:
        if multiplier <= -6:
            msg = f"\n{stat_owner.name}'s {name} won't drop anymore!\n"
        else:
            if highly:
                multiplier -= 2
                msg = f"\n{stat_owner.name}'s {name} went way down!\n"
            else:
                multiplier -= 1
                msg = f"\n{stat_owner.name}'s {name} went down!\n"

    setattr(stat_owner, stat_attr, multiplier)
    return multiplier, msg


def reset_stats_mult(pokemon: BattlePokemon) -> None:
    pokemon.atk_mult = 0
    pokemon.def_mult = 0
    pokemon.sp_atk_mult = 0
    pokemon.sp_def_mult = 0
    pokemon.speed_mult = 0
    pokemon.ev_mult = 0
    pokemon.acc_mult = 0
    pokemon.reflect = False
    pokemon.light_screen = False
    pokemon.mist = False


def reset_battle_stats(pokemon: BattlePokemon) -> None:
    pokemon.attack = pokemon.max_attack
    pokemon.defense = pokemon.max_defense
    pokemon.sp_atk = pokemon.max_sp_atk
    pokemon.sp_def = pokemon.max_sp_def
    pokemon.speed = pokemon.max_speed
    pokemon.accuracy = 1
    pokemon.evasion = 1


def calculate_crit_multiplier(attacker: BattlePokemon) -> tuple[int, str]:
    treshold = math.floor(attacker.base_speed / 2)
    if attacker.focus_energy:
        treshold *= 4
    if treshold > 255:
        treshold = 255
    rate = random.randint(0, 255)
    if rate < treshold:
        return 2, '\nCritical hit!'
    return 1, ''


def calculate_damage(
    attacker: BattlePokemon, move: Move, defender: BattlePokemon
) -> tuple[int, str]:
    power = move.power
    stab = 2 if has_type(attacker, move.typing) else 1

    a = attacker.attack if move.category == MoveCategory.PHYSICAL else attacker.sp_atk
    d = defender.defense if move.category == MoveCategory.PHYSICAL else defender.sp_def

    effectiveness = 1.0
    for t in defender.typing:
        effectiveness *= pkmn_types.get_effectiveness(move.typing, t)

    crit, crit_msg = calculate_crit_multiplier(attacker)

    rand = random.randint(217, 255) / 255

    damage = int(((2 * attacker.level * crit / 5 + 2) * power * (a / d) / 50 + 2)
                  * stab * effectiveness * rand)
    return damage, crit_msg


def hit(
    defender: BattlePokemon, damage: int,
    attacker: BattlePokemon | None = None, status: bool = False,
) -> str:
    if not defender.substitute:
        defender.hp -= damage
        if defender.hp <= 0:
            defender.hp = 0
            defender.fainted = True
        return ''
    else:
        if not status:
            defender.sub_damage += damage
            msg = f'\n{defender.name}\'s substitute was hit!'
            if defender.sub_damage >= 255:
                defender.substitute = False
                defender.sub_damage = 0
                msg += f'\n{defender.name}\'s substitute vanished!'
            return msg
        else:
            defender.hp -= damage
            if defender.hp <= 0:
                defender.hp = 0
                defender.fainted = True
            return ''


def struggle_no_pp(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    a = attacker.level
    b = attacker.attack
    c = defender.defense
    damage = int((((2 * a / 5 + 2) * b * 40) / c) / 50) + 2
    recoil = handle_recoil(defender, damage, 50)
    hit(defender, damage, attacker)
    hit(attacker, recoil, attacker)
    return (
        f'{attacker.name} has no moves left!\n'
        f'{attacker.name} uses Struggle!\n'
        f'{attacker.name} is hit with recoil!'
    )


def _apply_secondary_effect(
    defender: BattlePokemon, effect: EffectStatus,
) -> str:
    if defender.substitute:
        return ''
    if effect == EffectStatus.BURN:
        defender.status = EffectStatus.BURN
        return f'\n{defender.name} is burned!'
    if effect == EffectStatus.PARALYZE:
        if has_type(defender, Typing.GHOST):
            return ''
        defender.status = EffectStatus.PARALYZE
        defender.speed -= 0.75 * defender.speed
        return f'\n{defender.name} is paralyzed! Maybe it can\'t attack!'
    if effect == EffectStatus.FREEZE:
        defender.status = EffectStatus.FREEZE
        return f'\n{defender.name} is frozen solid!'
    if effect == EffectStatus.POISON:
        if has_type(defender, Typing.POISON):
            return ''
        defender.status = EffectStatus.POISON
        return f'\n{defender.name} is poisoned!'
    if effect == EffectStatus.CONFUSION:
        defender.temp_status = EffectStatus.CONFUSION
        return f'\n{defender.name} is now confused!'
    return ''


def handle_special_physical_move(
    attacker: BattlePokemon, move: Move, defender: BattlePokemon, damage: int,
) -> str:
    msg = ''

    if move.name in ('Explosion', 'Self-Destruct'):
        hit(defender, damage, attacker)
        hit(attacker, attacker.max_hp)
        return msg
    if move.name in ('Fissure', 'Guillotine', 'Horn Drill'):
        hit(defender, defender.max_hp, attacker)
        return msg
    if move.name in (
        'Fury Swipes', 'Fury Attack', 'Double Slap', 'Wrap',
        'Comet Punch', 'Barrage', 'Pin Missile', 'Spike Cannon',
    ):
        cnt = 1
        hit(defender, damage, attacker)
        while cnt < 5:
            prob = random.randint(0, 100)
            if cnt < 2:
                if prob <= 37:
                    hit(defender, damage, attacker)
                    cnt += 1
                else:
                    break
            elif 2 <= cnt < 5:
                if prob <= 12:
                    hit(defender, damage, attacker)
                    cnt += 1
                else:
                    break
        msg += f'\nHit {cnt} time(s)!'
        if move.secondary_effect and not defender.substitute:
            prob = random.randint(0, 100)
            if prob <= move.secondary_effect.chance:
                msg += _apply_secondary_effect(defender, move.secondary_effect.effect)
        return msg
    if move.name in ('Bonemerang', 'Double Kick', 'Twineedle'):
        hit(defender, damage, attacker)
        hit(defender, damage, attacker)
        msg += '\nHit 2 time(s)!'
        if move.secondary_effect and not defender.substitute:
            prob = random.randint(0, 100)
            if prob <= move.secondary_effect.chance:
                msg += _apply_secondary_effect(defender, move.secondary_effect.effect)
        return msg

    hit(defender, damage, attacker)

    if move.secondary_effect and not defender.substitute:
        prob = random.randint(0, 100)
        if prob <= move.secondary_effect.chance:
            msg += _apply_secondary_effect(defender, move.secondary_effect.effect)

    return msg


def _boost_def_high(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'def_mult', increase=True, highly=True)
    attacker.defense = update_battle_stat(attacker.defense, attacker.def_mult)
    return msg


def _boost_speed_high(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'speed_mult', increase=True, highly=True)
    attacker.speed = update_battle_stat(attacker.speed, attacker.speed_mult)
    return msg


def _boost_spatk_spdef_high(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, m1 = inc_dec_stat_mult(attacker, attacker, 'sp_atk_mult', increase=True, highly=True)
    attacker.sp_atk = update_battle_stat(attacker.sp_atk, attacker.sp_atk_mult)
    _, m2 = inc_dec_stat_mult(attacker, attacker, 'sp_def_mult', increase=True, highly=True)
    attacker.sp_def = update_battle_stat(attacker.sp_def, attacker.sp_def_mult)
    return m1 + m2


def _boost_def(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'def_mult', increase=True)
    attacker.defense = update_battle_stat(attacker.defense, attacker.def_mult)
    return msg


def _boost_ev(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'ev_mult', increase=True)
    attacker.evasion = update_battle_stat(attacker.evasion, attacker.ev_mult)
    return msg


def _boost_atk(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'atk_mult', increase=True)
    attacker.attack = update_battle_stat(attacker.attack, attacker.atk_mult)
    return msg


def _boost_atk_high(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, msg = inc_dec_stat_mult(attacker, attacker, 'atk_mult', increase=True, highly=True)
    attacker.attack = update_battle_stat(attacker.attack, attacker.atk_mult)
    return msg


def _boost_spatk_spdef(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    _, m1 = inc_dec_stat_mult(attacker, attacker, 'sp_atk_mult', increase=True)
    attacker.sp_atk = update_battle_stat(attacker.sp_atk, attacker.sp_atk_mult)
    _, m2 = inc_dec_stat_mult(attacker, attacker, 'sp_def_mult', increase=True)
    attacker.sp_def = update_battle_stat(attacker.sp_def, attacker.sp_def_mult)
    return m1 + m2


def _reduce_acc(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.mist:
        _, msg = inc_dec_stat_mult(attacker, defender, 'acc_mult', increase=False)
        defender.accuracy = update_battle_stat(defender.accuracy, defender.acc_mult)
        return msg
    return f'\nBut {defender.name}\'s Mist prevents its stats decrease...'


def _reduce_atk(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.mist:
        _, msg = inc_dec_stat_mult(attacker, defender, 'atk_mult', increase=False)
        defender.attack = update_battle_stat(defender.attack, defender.atk_mult)
        return msg
    return f'\nBut {defender.name}\'s Mist prevents its stats decrease...'


def _reduce_def(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.mist:
        _, msg = inc_dec_stat_mult(attacker, defender, 'def_mult', increase=False)
        defender.defense = update_battle_stat(defender.defense, defender.def_mult)
        return msg
    return f'\nBut {defender.name}\'s Mist prevents its stats decrease...'


def _reduce_def_high(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.mist:
        _, msg = inc_dec_stat_mult(attacker, defender, 'def_mult', increase=False, highly=True)
        defender.defense = update_battle_stat(defender.defense, defender.def_mult)
        return msg
    return f'\nBut {defender.name}\'s Mist prevents its stats decrease...'


def _reduce_speed(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.mist:
        _, msg = inc_dec_stat_mult(attacker, defender, 'speed_mult', increase=False)
        defender.speed = update_battle_stat(defender.speed, defender.speed_mult)
        return msg
    return f'\nBut {defender.name}\'s Mist prevents its stats decrease...'


def _paralyze(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        if defender.status is None:
            defender.status = EffectStatus.PARALYZE
            defender.speed -= 0.75 * defender.speed
            return f'\n{defender.name} is paralyzed! Maybe it can\'t attack!'
        return '\nBut nothing happened...'
    return f'\n{defender.name}\'s Substitute prevents its status change!'


def _confuse(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    defender.temp_status = EffectStatus.CONFUSION
    return f'\n{defender.name} is now confused!'


def _sleep(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        if defender.status is None:
            defender.status = EffectStatus.SLEEP
            return f'\n{defender.name} is now sleeping!'
        return '\nBut nothing happened...'
    return f'\n{defender.name}\'s Substitute prevents its status change!'


def _poison(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        if defender.status is None:
            if not has_type(defender, Typing.POISON):
                defender.status = EffectStatus.POISON
                return f'\n{defender.name} is poisoned!'
            return f'\nIt has no effect on {defender.name}...'
        return '\nBut nothing happened...'
    return f'\n{defender.name}\'s Substitute prevents its status change!'


def _toxic(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        if defender.status is None:
            if not has_type(defender, Typing.POISON):
                defender.status = EffectStatus.TOXIC
                return f'\n{defender.name} is intoxicated!'
            return f'\nIt has no effect on {defender.name}...'
        return '\nBut nothing happened...'
    return f'\n{defender.name}\'s Substitute prevents its status change!'


def _conversion(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    attacker.typing = defender.typing
    return f'\n{attacker.name} assumes {defender.name} types!'


def _haze(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    reset_stats_mult(attacker)
    reset_battle_stats(attacker)
    reset_stats_mult(defender)
    reset_battle_stats(defender)
    return '\nAll stats changes have been reset!'


def _leech_seed(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        if not defender.seeded:
            if not has_type(defender, Typing.GRASS):
                defender.seeded = True
                return f'\n{defender.name} was seeded!'
            return f'\nIt has no effect on {defender.name}...'
        return f'\nBut {defender.name}\'s is already seeded...'
    return f'\n{defender.name}\'s Substitute prevents Leech Seed!'


def _light_screen(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not attacker.light_screen:
        attacker.light_screen = True
        if attacker.sp_def * 2 > 1024:
            attacker.sp_def = 1024
        else:
            attacker.sp_def *= 2
        return f'\n{attacker.name} protected against special attacks!'
    return f'\nBut Light Screen is already covering {attacker.name}...'


def _reflect(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not attacker.reflect:
        attacker.reflect = True
        if attacker.defense * 2 > 1024:
            attacker.defense = 1024
        else:
            attacker.defense *= 2
        return f'\n{attacker.name} gained armor!'
    return f'\nBut Reflect is already covering {attacker.name}...'


def _mist(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not attacker.mist:
        attacker.mist = True
        return f'\n{attacker.name} is shrouded in Mist!'
    return f'\nBut there is already a Mist covering {attacker.name}...'


def _metronome(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    return atk(attacker, random.choice(moves.attacks), defender)


def _mimic(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    m = random.choice(defender.moves)
    if m is not None:
        if m.name == 'Mimic':
            return '\nBut it failed...'
        msg = atk(attacker, m, defender)
        return msg + f'\n{attacker.name} copies one of {defender.name}\'s moves!'
    return '\nBut it failed...'


def _recover(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if attacker.hp < attacker.max_hp:
        attacker.hp += 0.5 * attacker.max_hp
        if attacker.hp > attacker.max_hp:
            attacker.hp = attacker.max_hp
        return f'\n{attacker.name} restores half of its hp!'
    return f'\nBut {attacker.name} already has all its hp!'


def _rest(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if attacker.hp < attacker.max_hp or attacker.status is not None:
        if attacker.status is not None:
            attacker.status = None
        if attacker.temp_status is not None:
            attacker.temp_status = None
        attacker.hp = attacker.max_hp
        attacker.status = EffectStatus.SLEEP
        return f'\n{attacker.name} went to sleep and regained health!'
    return f'\nBut {attacker.name} already has all its hp!'


def _noop(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    return '\nBut nothing happened...'


def _substitute(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if attacker.substitute:
        return f'\nBut {attacker.name} is already protected by a substitute doll...'
    elif attacker.hp >= 0.3 * attacker.max_hp:
        attacker.hp -= math.floor(0.25 * attacker.max_hp)
        attacker.substitute = True
        return f'\n{attacker.name} is replaced by a substitute doll!'
    return ''


def _disable(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not defender.substitute:
        available = [
            (i, m) for i, m in enumerate(defender.moves)
            if m is not None and i != defender.disabled_move
        ]
        if available:
            idx, move = random.choice(available)
            defender.disabled_move = idx
            defender.disabled_turns = 4
            return f'\n{defender.name}\'s {move.name} was disabled!'
        return '\nBut nothing happened...'
    return f'\n{defender.name}\'s Substitute prevents status change!'


def _mirror_move(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    m = next((m for m in defender.moves if m is not None), None)
    if m is not None:
        return atk(attacker, m, defender)
    return '\nBut nothing happened...'


def _focus_energy(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    if not attacker.focus_energy:
        attacker.focus_energy = True
        return f'\n{attacker.name} is getting pumped!'
    return '\nBut nothing happened...'


def _transform(attacker: BattlePokemon, defender: BattlePokemon) -> str:
    attacker.transformed = True
    attacker.id = defender.id
    attacker.typing = defender.typing
    attacker.moves = deepcopy(defender.moves)
    attacker.max_attack = deepcopy(defender.max_attack)
    attacker.max_defense = deepcopy(defender.max_defense)
    attacker.max_sp_atk = deepcopy(defender.max_sp_atk)
    attacker.max_sp_def = deepcopy(defender.max_sp_def)
    attacker.max_speed = deepcopy(defender.max_speed)
    attacker.attack = deepcopy(defender.attack)
    attacker.defense = deepcopy(defender.defense)
    attacker.sp_atk = deepcopy(defender.sp_atk)
    attacker.sp_def = deepcopy(defender.sp_def)
    attacker.speed = deepcopy(defender.speed)
    for m in attacker.moves:
        if m is not None:
            m.pp = int(m.max_pp / 2)
    return f'\n{attacker.name} transforms into {defender.name}!'


MOVE_HANDLERS: dict[str, Callable[[BattlePokemon, BattlePokemon], str]] = {
    'Acid Armor': _boost_def_high,
    'Agility': _boost_speed_high,
    'Amnesia': _boost_spatk_spdef_high,
    'Barrier': _boost_def_high,
    'Confuse Ray': _confuse,
    'Conversion': _conversion,
    'Defense Curl': _boost_def,
    'Disable': _disable,
    'Double Team': _boost_ev,
    'Flash': _reduce_acc,
    'Focus Energy': _focus_energy,
    'Glare': _paralyze,
    'Growl': _reduce_atk,
    'Growth': _boost_spatk_spdef,
    'Harden': _boost_def,
    'Haze': _haze,
    'Hypnosis': _sleep,
    'Kinesis': _reduce_acc,
    'Leech Seed': _leech_seed,
    'Leer': _reduce_def,
    'Light Screen': _light_screen,
    'Lovely Kiss': _sleep,
    'Meditate': _boost_atk,
    'Metronome': _metronome,
    'Mimic': _mimic,
    'Minimize': _boost_ev,
    'Mirror Move': _mirror_move,
    'Mist': _mist,
    'Poison Gas': _poison,
    'Poison Powder': _poison,
    'Recover': _recover,
    'Reflect': _reflect,
    'Rest': _rest,
    'Roar': _noop,
    'Sand Attack': _reduce_acc,
    'Screech': _reduce_def_high,
    'Sharpen': _boost_atk,
    'Sing': _sleep,
    'Sleep Powder': _sleep,
    'Smokescreen': _reduce_acc,
    'Soft-Boiled': _recover,
    'Splash': _noop,
    'Spore': _sleep,
    'String Shot': _reduce_speed,
    'Stun Spore': _paralyze,
    'Substitute': _substitute,
    'Supersonic': _confuse,
    'Swords Dance': _boost_atk_high,
    'Tail Whip': _reduce_def,
    'Teleport': _noop,
    'Thunder Wave': _paralyze,
    'Toxic': _toxic,
    'Transform': _transform,
    'Whirlwind': _noop,
    'Withdraw': _boost_def,
}


def handle_status_move(attacker: BattlePokemon, move: Move, defender: BattlePokemon) -> str:
    handler = MOVE_HANDLERS.get(move.name)
    if handler:
        return handler(attacker, defender)
    return ''

def atk(attacker: BattlePokemon, move: Move, defender: BattlePokemon) -> str:
    t_ = move.accuracy * attacker.accuracy * defender.evasion
    rand_t = random.randint(0, 255)
    msg = f'{attacker.name} used {move.name}!'

    if t_ == 255 or rand_t > t_ or move.accuracy == 100:
        if move.category in (MoveCategory.PHYSICAL, MoveCategory.SPECIAL):
            tmp = ''
            if move.name != 'Dream Eater' and defender.status != EffectStatus.SLEEP:
                effectiveness = 1.0
                for t in defender.typing:
                    effectiveness *= pkmn_types.get_effectiveness(move.typing, t)

                if effectiveness == 0:
                    tmp += '\nIt has no effect...'
                elif effectiveness > 1:
                    tmp += '\nIt\'s super effective!'
                elif effectiveness < 1:
                    tmp += '\nIt\'s not very effective...'

            msg += tmp
            damage, crit_msg = calculate_damage(attacker, move, defender)
            msg += crit_msg

            if attacker.status == EffectStatus.BURN:
                damage //= 2

            if move.name == 'Dragon Rage':
                damage = 40
            elif move.name == 'Sonic Boom':
                damage = 20
            elif move.name in ('Seismic Toss', 'Night Shade'):
                damage = attacker.level
            elif move.name == 'Super Fang':
                damage = defender.hp // 2

            if move.name in ('Absorb', 'Mega Drain', 'Leech Life'):
                regain = handle_recoil(defender, damage, 50)
                if attacker.hp + regain > attacker.max_hp:
                    attacker.hp = attacker.max_hp
                else:
                    attacker.hp += regain
                msg += f'\nSucked health from {defender.name}!'
            elif move.name == 'Dream Eater':
                if defender.status == EffectStatus.SLEEP:
                    regain = handle_recoil(defender, damage, 50)
                    if attacker.hp + regain > attacker.max_hp:
                        attacker.hp = attacker.max_hp
                    else:
                        attacker.hp += regain
                    msg += f'\n{defender.name} dream was eaten!'
                else:
                    msg += '\nIt does nothing...'
                    move.pp -= 1
                    return msg

            if attacker.temp_status != EffectStatus.CONFUSION:
                if defender != attacker:
                    msg += handle_special_physical_move(attacker, move, defender, damage)
                    if move.name in ('Double-Edge', 'Take Down', 'Submission'):
                        recoil = damage // 4
                        msg += f'\n{attacker.name} is hit with recoil!'
                        hit(attacker, recoil)
                    if defender.fainted:
                        msg += f'\n{defender.name} fainted!'
            else:
                prob = random.random()
                if prob <= 0.5:
                    msg = f'{attacker.name} is so confused to hit itself!'
                    hit(attacker, damage)
                    if attacker.fainted:
                        msg += f'\n{attacker.name} fainted!'
        else:
            msg += handle_status_move(attacker, move, defender)
    else:
        if 'jump kick' in move.name.lower():
            msg += f'\n{attacker.name} lost its poise and damaged itself!'
            hit(attacker, 1)
        else:
            msg += '\nBut it failed...'

    move.pp -= 1
    return msg


def try_atk_status(attacker: BattlePokemon, move: Move, defender: BattlePokemon) -> str:
    if attacker.status is not None:
        if attacker.status == EffectStatus.PARALYZE:
            p = random.random()
            if p <= 0.25:
                return atk(attacker, move, defender)
            return f'{attacker.name} is paralyzed and can\'t move!'
        elif attacker.status == EffectStatus.SLEEP:
            if attacker.sleeping_turns < 7:
                p = random.random()
                if p <= 0.33:
                    attacker.status = None
                    msg = atk(attacker, move, defender)
                    return msg + f'\n{attacker.name} woke up!'
                else:
                    attacker.sleeping_turns += 1
                    return f'{attacker.name} is sleeping...'
            else:
                attacker.status = None
                msg = atk(attacker, move, defender)
                return f'{attacker.name} woke up!\n' + msg
        elif attacker.status in (
            EffectStatus.BURN, EffectStatus.POISON,
            EffectStatus.TOXIC, EffectStatus.FREEZE,
        ):
            return atk(attacker, move, defender)
    elif attacker.temp_status is not None:
        if attacker.confused_turns < 5:
            p = random.random()
            if p <= 0.33:
                attacker.temp_status = None
                msg = atk(attacker, move, defender)
                return msg + f'\n{attacker.name} is not confused anymore!'
            else:
                attacker.confused_turns += 1
                power = 40
                a = attacker.attack
                d = attacker.defense
                damage = int((((2 * attacker.level) / 5 + 2) * power * (a / d)) / 50 + 2)
                hit(attacker, damage)
                return f'{attacker.name} is confused...\nIt\'s so confused to hit itself!'
        else:
            attacker.temp_status = None
            msg = atk(attacker, move, defender)
            return msg + f'\n{attacker.name} is not confused anymore!'
    return atk(attacker, move, defender)


def handle_burn_poison(player_mon: BattlePokemon, enemy_mon: BattlePokemon) -> str:
    msg = ''
    if player_mon.status in (EffectStatus.BURN, EffectStatus.POISON):
        player_mon_max_hp = player_mon.max_hp
        hit(player_mon, math.floor((1 / 16) * player_mon_max_hp), None, status=True)
        if player_mon.status == EffectStatus.BURN:
            msg += f'\n{player_mon.name} is hurt by its burn!'
        else:
            msg += f'\n{player_mon.name} is hurt by poison!'
    if enemy_mon.status in (EffectStatus.BURN, EffectStatus.POISON):
        enemy_mon_max_hp = enemy_mon.max_hp
        hit(enemy_mon, math.floor((1 / 16) * enemy_mon_max_hp), None, status=True)
        if enemy_mon.status == EffectStatus.BURN:
            msg += f'\n{enemy_mon.name} is hurt by its burn!'
        else:
            msg += f'\n{enemy_mon.name} is hurt by poison!'
    return msg


def handle_toxicity(player_mon: BattlePokemon, enemy_mon: BattlePokemon) -> str:
    msg = ''
    if player_mon.status == EffectStatus.TOXIC:
        player_mon.toxic_turns += 1
        player_mon_max_hp = player_mon.max_hp
        damage = math.floor(1 / 16 * player_mon_max_hp) * player_mon.toxic_turns
        if damage >= 15 * math.floor(1 / 16 * player_mon_max_hp):
            damage = math.floor(1 / 16 * player_mon_max_hp)
        hit(player_mon, damage, None, status=True)
        msg += f'\n{player_mon.name} is hurt by toxine!'
    if enemy_mon.status == EffectStatus.TOXIC:
        enemy_mon.toxic_turns += 1
        enemy_mon_max_hp = enemy_mon.max_hp
        damage = math.floor(1 / 16 * enemy_mon_max_hp) * enemy_mon.toxic_turns
        if damage >= 15 * math.floor(1 / 16 * enemy_mon_max_hp):
            damage = math.floor(1 / 16 * enemy_mon_max_hp)
        hit(enemy_mon, damage, None, status=True)
        msg += f'\n{enemy_mon.name} is hurt by toxine!'
    return msg


def handle_leech_seed(player_mon: BattlePokemon, enemy_mon: BattlePokemon) -> str:
    msg = ''
    if player_mon.seeded:
        player_mon_max_hp = player_mon.max_hp
        damage = math.floor((1 / 16) * player_mon_max_hp)
        hit(player_mon, damage, None, status=True)
        if enemy_mon.hp + damage > enemy_mon.max_hp:
            enemy_mon.hp = enemy_mon.max_hp
        else:
            enemy_mon.hp += damage
        msg += f'\nLeech Seed saps {player_mon.name}!'
    if enemy_mon.seeded:
        enemy_mon_max_hp = enemy_mon.max_hp
        damage = math.floor(math.floor((1 / 16) * enemy_mon_max_hp))
        hit(enemy_mon, damage, None, status=True)
        if player_mon.hp + damage > player_mon.max_hp:
            player_mon.hp = player_mon.max_hp
        else:
            player_mon.hp += damage
        msg += f'\nLeech Seeds saps {enemy_mon.name}!'
    return msg
