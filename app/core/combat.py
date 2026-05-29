import math
import random
from copy import deepcopy

from app.data import moves
from app.data import pkmn_types
from app.schemas.move import Move, MoveCategory
from app.schemas.typing import Typing


def calculate_max_stat(base_stat, level):
    return math.floor((base_stat * 2 * level) / 100) + 5


def update_battle_stat(stat, multiplier):
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


def handle_recoil(target, damage, perc_scaler):
    scaler = perc_scaler / 100
    if target.hp - damage < 0:
        damage_caused = damage - (target.hp - damage)
    else:
        damage_caused = damage
    return int(damage_caused * scaler)


def inc_dec_stat_mult(attacker, stat_owner, stat_attr, increase, highly=False):
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
            attacker.msg += f"\n{stat_owner.name}'s {name} won't rise anymore!\n"
        else:
            if highly:
                multiplier += 2
                attacker.msg += f"\n{stat_owner.name}'s {name} went way up!\n"
            else:
                multiplier += 1
                attacker.msg += f"\n{stat_owner.name}'s {name} went up!\n"
    else:
        if multiplier <= -6:
            attacker.msg += f"\n{stat_owner.name}'s {name} won't drop anymore!\n"
        else:
            if highly:
                multiplier -= 2
                attacker.msg += f"\n{stat_owner.name}'s {name} went way down!\n"
            else:
                multiplier -= 1
                attacker.msg += f"\n{stat_owner.name}'s {name} went down!\n"

    setattr(stat_owner, stat_attr, multiplier)
    return multiplier


def reset_stats_mult(pokemon):
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


def reset_battle_stats(pokemon):
    pokemon.attack = pokemon.max_attack
    pokemon.defense = pokemon.max_defense
    pokemon.sp_atk = pokemon.max_sp_atk
    pokemon.sp_def = pokemon.max_sp_def
    pokemon.speed = pokemon.max_speed
    pokemon.accuracy = 1
    pokemon.evasion = 1


def calculate_crit_multiplier(attacker):
    treshold = math.floor(attacker.base_speed / 2)
    if treshold > 255:
        treshold = 255
    rate = random.randint(0, 255)
    if rate < treshold:
        attacker.msg += '\nCritical hit!'
        return 2
    return 1


def calculate_damage(attacker, move, defender):
    power = move.power
    if len(attacker.typing) == 2:
        if move.typing == attacker.typing[0] or move.typing == attacker.typing[1]:
            stab = 2
        else:
            stab = 1
    else:
        if len(attacker.typing) >= 1 and move.typing == attacker.typing[0]:
            stab = 2
        else:
            stab = 1

    a = attacker.attack if move.category == MoveCategory.PHYSICAL else attacker.sp_atk
    d = defender.defense if move.category == MoveCategory.PHYSICAL else defender.sp_def

    type2 = 1
    type1 = pkmn_types.get_effectiveness(move.typing, defender.typing[0])
    if len(defender.typing) == 2:
        type2 = pkmn_types.get_effectiveness(move.typing, defender.typing[1])

    if type1 == 0 or type2 == 0:
        crit = 0
    else:
        crit = calculate_crit_multiplier(attacker)

    rand_list = [random.randint(217, 255) for _ in range(9)]
    rand = 1
    for r in rand_list:
        rand *= r
    rand = r / 255

    damage = int(((((2 * attacker.level * crit) / 5 + 2) * power * (a / d)) / 50 + 2) * stab * type1 * type2 * rand)
    return damage


def hit(defender, damage, attacker=None, status=False):
    if not defender.substitute:
        defender.hp -= damage
        if defender.hp <= 0:
            defender.hp = 0
            defender.fainted = True
    else:
        if not status:
            defender.sub_damage += damage
            attacker.msg += f'\n{defender.name}\'s substitute was hit!'
            if defender.sub_damage >= 255:
                defender.substitute = False
                defender.sub_damage = 0
                attacker.msg += f'\n{defender.name}\'s substitute vanished!'
        else:
            defender.hp -= damage
            if defender.hp <= 0:
                defender.hp = 0
                defender.fainted = True


def struggle_no_pp(attacker, defender):
    power = 50
    a = attacker.level
    b = attacker.attack
    c = defender.defense
    damage = int((((2 * a / 5 + 2) * b * 40) / c) / 50) + 2
    recoil = handle_recoil(defender, damage, 50)
    attacker.msg = '{pkmn} has no moves left!\n{pkmn} uses Struggle!\n{pkmn} is hit with recoil!'.format(pkmn=attacker.name)
    hit(defender, damage, attacker)
    hit(attacker, recoil, attacker)


def handle_special_physical_move(attacker, move, defender, damage):
    if move.typing == Typing.FIRE:
        hit(defender, damage, attacker)
        if not defender.substitute:
            prob = random.randint(0, 100)
            if prob <= 10:
                defender.status = 'BRN'
                attacker.msg += f'\n{defender.name} is burned!'
    if move.name == 'Body Slam':
        hit(defender, damage, attacker)
        if not defender.substitute:
            if len(defender.typing) == 2:
                if defender.typing[0] != Typing.GHOST and defender.typing[1] != Typing.GHOST:
                    prob = random.randint(0, 100)
                    if prob <= 30:
                        defender.status = 'PAR'
                        defender.speed -= 0.75 * defender.speed
                        attacker.msg += f'\n{defender.name} is paralyzed! Maybe it can\'t attack!'
            elif defender.typing[0] != Typing.GHOST:
                prob = random.randint(0, 100)
                if prob <= 30:
                    defender.status = 'PAR'
                    defender.speed -= 0.75 * defender.speed
                    attacker.msg += f'\n{defender.name} is paralyzed! Maybe it can\'t attack!'
    if move.name == 'Confusion':
        hit(defender, damage, attacker)
        prob = random.randint(0, 100)
        if prob <= 10:
            defender.temp_status = 'CONF'
            attacker.msg += f'\n{defender.name} is now confused!'
    if move.name == 'Explosion':
        hit(defender, damage, attacker)
        hit(attacker, attacker.max_hp)
    elif move.name == 'Fissure' or move.name == 'Guillotine':
        hit(defender, defender.max_hp, attacker)
    elif move.name in ('Fury Swipes', 'Fury Attack', 'Double Slap', 'Wrap'):
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
        attacker.msg += f'\nHit {cnt} time(s)!'
    elif move.name == 'Poison Sting':
        hit(defender, damage, attacker)
        if not defender.substitute:
            if len(defender.typing) == 2:
                if defender.typing[0] != Typing.POISON and defender.typing[1] != Typing.POISON:
                    prob = random.randint(0, 100)
                    if prob <= 20:
                        defender.status = 'PSN'
                        attacker.msg += f'\n{defender.name} is poisoned!'
            elif defender.typing[0] != Typing.POISON:
                prob = random.randint(0, 100)
                if prob <= 20:
                    defender.status = 'PSN'
                    attacker.msg += f'\n{defender.name} is poisoned!'
    else:
        hit(defender, damage, attacker)


def handle_status_move(attacker, move, defender):
    if move.name == 'Acid Armor':
        inc_dec_stat_mult(attacker, attacker, 'def_mult', increase=True, highly=True)
        attacker.defense = update_battle_stat(attacker.defense, attacker.def_mult)
    elif move.name == 'Agility':
        inc_dec_stat_mult(attacker, attacker, 'speed_mult', increase=True, highly=True)
        attacker.speed = update_battle_stat(attacker.speed, attacker.speed_mult)
    elif move.name == 'Amnesia':
        inc_dec_stat_mult(attacker, attacker, 'sp_atk_mult', increase=True, highly=True)
        attacker.sp_atk = update_battle_stat(attacker.sp_atk, attacker.sp_atk_mult)
        inc_dec_stat_mult(attacker, attacker, 'sp_def_mult', increase=True, highly=True)
        attacker.sp_def = update_battle_stat(attacker.sp_def, attacker.sp_def_mult)
    elif move.name == 'Barrier':
        inc_dec_stat_mult(attacker, attacker, 'def_mult', increase=True, highly=True)
        attacker.defense = update_battle_stat(attacker.defense, attacker.def_mult)
    elif move.name in ('Confuse Ray', 'Supersonic'):
        defender.temp_status = 'CONF'
        attacker.msg += f'\n{defender.name} is now confused!'
    elif move.name == 'Conversion':
        attacker.typing = defender.typing
        attacker.msg += f'\n{attacker.name} assumes {defender.name} types!'
    elif move.name in ('Defense Curl', 'Harden', 'Withdraw'):
        inc_dec_stat_mult(attacker, attacker, 'def_mult', increase=True)
        attacker.defense = update_battle_stat(attacker.defense, attacker.def_mult)
    elif move.name == 'Double Team':
        inc_dec_stat_mult(attacker, attacker, 'ev_mult', increase=True)
        attacker.evasion = update_battle_stat(attacker.evasion, attacker.ev_mult)
    elif move.name in ('Flash', 'Kinesis', 'Sand Attack'):
        if not defender.mist:
            inc_dec_stat_mult(attacker, defender, 'acc_mult', increase=False)
            defender.accuracy = update_battle_stat(defender.accuracy, defender.acc_mult)
        else:
            attacker.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
    elif move.name in ('Glare', 'Stun Spore', 'Thunder Wave'):
        if not defender.substitute:
            if defender.status is None:
                defender.status = 'PAR'
                defender.speed -= 0.75 * defender.speed
                attacker.msg += f'\n{defender.name} is paralyzed! Maybe it can\'t attack!'
            else:
                attacker.msg += '\nBut nothing happened...'
        else:
            attacker.msg += f'\n{defender.name}\'s Substitute prevents its status change!'
    elif move.name == 'Growl':
        if not defender.mist:
            inc_dec_stat_mult(attacker, defender, 'atk_mult', increase=False)
            defender.attack = update_battle_stat(defender.attack, defender.atk_mult)
        else:
            attacker.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
    elif move.name == 'Growth':
        inc_dec_stat_mult(attacker, attacker, 'sp_atk_mult', increase=True)
        attacker.sp_atk = update_battle_stat(attacker.sp_atk, attacker.sp_atk_mult)
        inc_dec_stat_mult(attacker, attacker, 'sp_def_mult', increase=True)
        attacker.sp_def = update_battle_stat(attacker.sp_def, attacker.sp_def_mult)
    elif move.name == 'Haze':
        reset_stats_mult(attacker)
        reset_battle_stats(attacker)
        reset_stats_mult(defender)
        reset_battle_stats(defender)
        attacker.msg += '\nAll stats changes have been reset!'
    elif move.name in ('Hypnosis', 'Lovely Kiss', 'Sing', 'Spore', 'Sleep Powder'):
        if not defender.substitute:
            if defender.status is None:
                defender.status = 'SLP'
                attacker.msg += f'\n{defender.name} is now sleeping!'
            else:
                attacker.msg += '\nBut nothing happened...'
        else:
            attacker.msg += f'\n{defender.name}\'s Substitute prevents its status change!'
    elif move.name == 'Leech Seed':
        if not defender.substitute:
            if not defender.seeded:
                if len(defender.typing) == 2:
                    if defender.typing[0] != Typing.GRASS and defender.typing[1] != Typing.GRASS:
                        defender.seeded = True
                        attacker.msg += f'\n{defender.name} was seeded!'
                    else:
                        attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
                elif defender.typing[0] != Typing.GRASS:
                    defender.seeded = True
                    attacker.msg += f'\n{defender.name} was seeded!'
                else:
                    attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
            else:
                attacker.msg += '\nBut {pkmn}\'s is already seeded...'.format(pkmn=defender.name)
        else:
            attacker.msg += f'\n{defender.name}\'s Substitute prevents Leech Seed!'
    elif move.name == 'Light Screen':
        if not attacker.light_screen:
            attacker.light_screen = True
            if attacker.sp_def * 2 > 1024:
                attacker.sp_def = 1024
            else:
                attacker.sp_def *= 2
            attacker.msg += f'\n{attacker.name} protected against special attacks!'
        else:
            attacker.msg += '\nBut Light Screen is already covering {pkmn}...'.format(pkmn=attacker.name)
    elif move.name in ('Meditate', 'Minimize'):
        inc_dec_stat_mult(attacker, attacker, 'ev_mult', increase=True)
        attacker.evasion = update_battle_stat(attacker.evasion, attacker.ev_mult)
    elif move.name == 'Metronome':
        rand_move_tmp = random.choice(moves.attacks)
        rand_move = Move(
            name=rand_move_tmp['name'],
            typing=Typing(rand_move_tmp['type']),
            power=rand_move_tmp['power'],
            pp=rand_move_tmp['pp'],
            category=MoveCategory(rand_move_tmp['category']),
            accuracy=rand_move_tmp['accuracy'],
        )
        atk(attacker, rand_move, defender)
    elif move.name == 'Mimic':
        m = random.choice(defender.moves)
        if m is not None:
            if m.name == 'Mimic':
                attacker.msg += '\nBut it failed...'
            else:
                atk(attacker, m, defender)
                attacker.msg += f'\n{attacker.name} copies one of {defender.name}\'s moves!'
        else:
            attacker.msg += '\nBut it failed...'
    elif move.name == 'Mist':
        if not attacker.mist:
            attacker.mist = True
            attacker.msg += f'\n{attacker.name} is shrouded in Mist!'
        else:
            attacker.msg += '\nBut there is already a Mist covering {pkmn}...'.format(pkmn=attacker.name)
    elif move.name in ('Poison Gas', 'Poison Powder'):
        if not defender.substitute:
            if defender.status is None:
                if len(defender.typing) == 2:
                    if defender.typing[0] != Typing.POISON and defender.typing[1] != Typing.POISON:
                        defender.status = 'PSN'
                        attacker.msg += f'\n{defender.name} is poisoned!'
                    else:
                        attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
                elif defender.typing[0] != Typing.POISON:
                    defender.status = 'PSN'
                    attacker.msg += f'\n{defender.name} is poisoned!'
                else:
                    attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
            else:
                attacker.msg += '\nBut nothing happened...'
        else:
            attacker.msg += f'\n{defender.name}\'s Substitute prevents its status change!'
    elif move.name in ('Recover', 'Soft-Boiled'):
        if attacker.hp < attacker.max_hp:
            attacker.hp += 0.5 * attacker.max_hp
            if attacker.hp > attacker.max_hp:
                attacker.hp = attacker.max_hp
            attacker.msg += f'\n{attacker.name} restores half of its hp!'
        else:
            attacker.msg += '\nBut {pkmn} already has all its hp!'.format(pkmn=attacker.name)
    elif move.name == 'Reflect':
        if not attacker.reflect:
            attacker.reflect = True
            if attacker.defense * 2 > 1024:
                attacker.defense = 1024
            else:
                attacker.defense *= 2
            attacker.msg += f'\n{attacker.name} gained armor!'
        else:
            attacker.msg += '\nBut Reflect is already covering {pkmn}...'.format(pkmn=attacker.name)
    elif move.name == 'Rest':
        if attacker.hp < attacker.max_hp or attacker.status is not None:
            if attacker.status is not None:
                attacker.status = None
            if attacker.temp_status is not None:
                attacker.temp_status = None
            attacker.hp = attacker.max_hp
            attacker.status = 'SLP'
            attacker.msg += f'\n{attacker.name} went to sleep and regained health!'
        else:
            attacker.msg += '\nBut {pkmn} already has all its hp!'.format(pkmn=attacker.name)
    elif move.name in ('Roar', 'Splash', 'Teleport', 'Whirlwind'):
        attacker.msg += '\nBut nothing happened...'
    elif move.name == 'Screech':
        if not defender.mist:
            inc_dec_stat_mult(attacker, defender, 'def_mult', increase=False)
            defender.defense = update_battle_stat(defender.defense, defender.def_mult)
        else:
            attacker.msg += '\nBut {pkmn}\'s Mist prevents its stats decrease...'.format(pkmn=defender.name)
    elif move.name == 'String Shot':
        if not defender.mist:
            inc_dec_stat_mult(attacker, defender, 'speed_mult', increase=False)
            defender.speed = update_battle_stat(defender.speed, defender.speed_mult)
        else:
            attacker.msg += '\nBut {pkmn}\'s Mist prevents its stats decrease...'.format(pkmn=defender.name)
    elif move.name == 'Substitute':
        if not attacker.substitute:
            if attacker.hp >= 0.3 * attacker.max_hp:
                attacker.hp -= math.floor(0.25 * attacker.max_hp)
                attacker.substitute = True
                attacker.msg += f'\n{attacker.name} is replaced by a substitute doll!'
        else:
            attacker.msg += '\nBut {pkmn} is already protected by a substitute doll...'.format(pkmn=attacker.name)
    elif move.name == 'Sharpen':
        inc_dec_stat_mult(attacker, attacker, 'atk_mult', increase=True)
        attacker.attack = update_battle_stat(attacker.attack, attacker.atk_mult)
    elif move.name == 'Swords Dance':
        inc_dec_stat_mult(attacker, attacker, 'atk_mult', increase=True, highly=True)
        attacker.attack = update_battle_stat(attacker.attack, attacker.atk_mult)
    elif move.name in ('Tail Whip', 'Leer'):
        if not defender.mist:
            inc_dec_stat_mult(attacker, defender, 'def_mult', increase=False)
            defender.defense = update_battle_stat(defender.defense, defender.def_mult)
        else:
            attacker.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
    elif move.name == 'Toxic':
        if not defender.substitute:
            if defender.status is None:
                if len(defender.typing) == 2:
                    if defender.typing[0] != Typing.POISON and defender.typing[1] != Typing.POISON:
                        defender.status = 'TOX'
                        attacker.msg += f'\n{defender.name} is intoxicated!'
                    else:
                        attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
                elif defender.typing[0] != Typing.POISON:
                    defender.status = 'TOX'
                    attacker.msg += f'\n{defender.name} is intoxicated!'
                else:
                    attacker.msg += '\nIt has no effect on {pkmn}...'.format(pkmn=defender.name)
            else:
                attacker.msg += '\nBut nothing happened...'
        else:
            attacker.msg += f'\n{defender.name}\'s Substitute prevents its status change!'
    elif move.name == 'Transform':
        attacker.msg += f'\n{attacker.name} transforms into {defender.name}!'
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


def atk(attacker, move, defender):
    T = move.accuracy * attacker.accuracy * defender.evasion
    rand_t = random.randint(0, 255)
    attacker.msg = '{pkmn} used {mv}!'.format(pkmn=attacker.name, mv=move.name)

    if T == 255 or T < rand_t or move.accuracy == 100:
        if move.category in (MoveCategory.PHYSICAL, MoveCategory.SPECIAL):
            type2 = 1
            type1 = pkmn_types.get_effectiveness(move.typing, defender.typing[0])
            tmp = ''
            if move.name != 'Dream Eater' and defender.status != 'SLP':
                if len(defender.typing) == 2:
                    type2 = pkmn_types.get_effectiveness(move.typing, defender.typing[1])
                    if ((type1 == 0.5 and type2 == 1) or (type1 == 1 and type2 == 0.5)) or (type1 == 0.5 and type2 == 0.5):
                        tmp += '\nIt\'s not very effective...'
                    elif ((type1 == 2 and type2 == 1) or (type1 == 1 and type2 == 2)) or (type1 == 2 and type2 == 2):
                        tmp += '\nIt\'s super effective!'
                    elif type1 == 0 or type2 == 0:
                        tmp += '\nIt has no effect...'
                else:
                    if type1 == 0.5:
                        tmp += '\nIt\'s not very effective...'
                    elif type1 == 2:
                        tmp += '\nIt\'s super effective!'
                    elif type1 == 0:
                        tmp += '\nIt has no effect...'

            attacker.msg += tmp
            damage = calculate_damage(attacker, move, defender)

            if attacker.status == 'BRN':
                damage //= 2

            if move.name in ('Absorb', 'Mega Drain', 'Leech Life'):
                regain = handle_recoil(defender, damage, 50)
                if attacker.hp + regain > attacker.max_hp:
                    attacker.hp = attacker.max_hp
                else:
                    attacker.hp += regain
                attacker.msg += '\nSucked health from {pkmn}!'.format(pkmn=defender.name)
            elif move.name == 'Dream Eater':
                if defender.status == 'SLP':
                    regain = handle_recoil(defender, damage, 50)
                    if attacker.hp + regain > attacker.max_hp:
                        attacker.hp = attacker.max_hp
                    else:
                        attacker.hp += regain
                    attacker.msg += '\n{pkmn} dream was eaten!'.format(pkmn=defender.name)
                else:
                    attacker.msg += '\nIt does nothing...'
                    return

            if attacker.temp_status != 'CONF':
                if defender != attacker:
                    handle_special_physical_move(attacker, move, defender, damage)
                    if defender.fainted:
                        attacker.msg += '\n{enemy} fainted!'.format(enemy=defender.name)
            else:
                prob = random.random()
                if prob <= 0.5:
                    attacker.msg = '{pkmn} is so confused to hit itself!'.format(pkmn=attacker.name)
                    hit(attacker, damage)
                    if attacker.fainted:
                        attacker.msg += '\n{pkmn} fainted!'.format(pkmn=attacker.name)
        else:
            handle_status_move(attacker, move, defender)
    else:
        if 'jump kick' in move.name.lower():
            attacker.msg += '\n{pkmn} lost its poise and damaged itself!'.format(pkmn=attacker.name)
            hit(attacker, 1)
        else:
            attacker.msg += '\nBut it failed...'

    move.pp -= 1


def try_atk_status(attacker, move, defender):
    if attacker.status is not None:
        if attacker.status == 'PAR':
            p = random.random()
            if p <= 0.25:
                atk(attacker, move, defender)
            else:
                attacker.msg = '{pkmn} is paralyzed and can\'t move!'.format(pkmn=attacker.name)
        elif attacker.status == 'SLP':
            if attacker.sleeping_turns < 7:
                p = random.random()
                if p <= 0.33:
                    attacker.status = None
                    atk(attacker, move, defender)
                    attacker.msg += '\n{pkmn} woke up!'.format(pkmn=attacker.name)
                else:
                    attacker.sleeping_turns += 1
                    attacker.msg = '{pkmn} is sleeping...'.format(pkmn=attacker.name)
            else:
                attacker.status = None
                attacker.msg = '{pkmn} woke up!'.format(pkmn=attacker.name)
                atk(attacker, move, defender)
        else:
            atk(attacker, move, defender)
    if attacker.temp_status is not None:
        if attacker.confused_turns < 5:
            p = random.random()
            if p <= 0.33:
                attacker.temp_status = None
                atk(attacker, move, defender)
                attacker.msg += '\n{pkmn} is not confused anymore!'.format(pkmn=attacker.name)
            else:
                attacker.confused_turns += 1
                attacker.msg = '{pkmn} is confused...'.format(pkmn=attacker.name)
                power = 40
                a = attacker.attack
                d = attacker.defense
                damage = int((((2 * attacker.level) / 5 + 2) * power * (a / d)) / 50 + 2)
                hit(attacker, damage)
                attacker.msg += '\nIt\'s so confused to hit itself!'
        else:
            attacker.temp_status = None
            atk(attacker, move, defender)
            attacker.msg += '\n{pkmn} is not confused anymore!'.format(pkmn=attacker.name)
    elif attacker.temp_status is None and attacker.status is None:
        atk(attacker, move, defender)


def handle_burn_poison(player_mon, enemy_mon):
    if player_mon.status in ('BRN', 'PSN'):
        player_mon_max_hp = player_mon.max_hp
        hit(player_mon, math.floor((1 / 16) * player_mon_max_hp), None, status=True)
        if player_mon.status == 'BRN':
            player_mon.msg += '\n{pkmn} is hurt by its burn!'.format(pkmn=player_mon.name)
        else:
            player_mon.msg += '\n{pkmn} is hurt by poison!'.format(pkmn=player_mon.name)
    if enemy_mon.status in ('BRN', 'PSN'):
        enemy_mon_max_hp = enemy_mon.max_hp
        hit(enemy_mon, math.floor((1 / 16) * enemy_mon_max_hp), None, status=True)
        if enemy_mon.status == 'BRN':
            enemy_mon.msg += '\n{pkmn} is hurt by its burn!'.format(pkmn=enemy_mon.name)
        else:
            enemy_mon.msg += '\n{pkmn} is hurt by poison!'.format(pkmn=enemy_mon.name)


def handle_toxicity(player_mon, enemy_mon):
    if player_mon.status == 'TOX':
        player_mon.toxic_turns += 1
        player_mon_max_hp = player_mon.max_hp
        damage = math.floor(1 / 16 * player_mon_max_hp) * player_mon.toxic_turns
        if damage >= 15 * math.floor(1 / 16 * player_mon_max_hp):
            damage = math.floor(1 / 16 * player_mon_max_hp)
        hit(player_mon, damage, None, status=True)
        player_mon.msg += '\n{pkmn} is hurt by toxine!'.format(pkmn=player_mon.name)
    if enemy_mon.status == 'TOX':
        enemy_mon.toxic_turns += 1
        enemy_mon_max_hp = enemy_mon.max_hp
        damage = math.floor(1 / 16 * enemy_mon_max_hp) * enemy_mon.toxic_turns
        if damage >= 15 * math.floor(1 / 16 * enemy_mon_max_hp):
            damage = math.floor(1 / 16 * enemy_mon_max_hp)
        hit(enemy_mon, damage, None, status=True)
        enemy_mon.msg += '\n{pkmn} is hurt by toxine!'.format(pkmn=enemy_mon.name)


def handle_leech_seed(player_mon, enemy_mon):
    if player_mon.seeded:
        player_mon_max_hp = player_mon.max_hp
        damage = math.floor((1 / 16) * player_mon_max_hp)
        hit(player_mon, damage, None, status=True)
        if enemy_mon.hp + damage > enemy_mon.max_hp:
            enemy_mon.hp = enemy_mon.max_hp
        else:
            enemy_mon.hp += damage
        player_mon.msg += '\nLeech Seed saps {pkmn}!'.format(pkmn=player_mon.name)
    if enemy_mon.seeded:
        enemy_mon_max_hp = enemy_mon.max_hp
        damage = math.floor(math.floor((1 / 16) * enemy_mon_max_hp))
        hit(enemy_mon, damage, None, status=True)
        if player_mon.hp + damage > player_mon.max_hp:
            player_mon.hp = player_mon.max_hp
        else:
            player_mon.hp += damage
        enemy_mon.msg += '\nLeech Seeds saps {pkmn}!'.format(pkmn=enemy_mon.name)
