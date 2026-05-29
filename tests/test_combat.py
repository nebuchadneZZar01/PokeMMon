from __future__ import annotations

import math
import random

from app.core.combat import (
    MOVE_HANDLERS,
    calculate_crit_multiplier,
    calculate_damage,
    handle_burn_poison,
    handle_leech_seed,
    handle_status_move,
    handle_toxicity,
    has_type,
    struggle_no_pp,
)
from app.data import pkmn_types
from app.schemas.effect_status import EffectStatus
from app.schemas.move import MoveCategory
from app.schemas.typing import Typing

from .conftest import damage_no_var, make_move, make_pkmn


class TestHasType:
    def test_single_type_match(self):
        p = make_pkmn(typing=[Typing.FIRE])
        assert has_type(p, Typing.FIRE)

    def test_single_type_no_match(self):
        p = make_pkmn(typing=[Typing.WATER])
        assert not has_type(p, Typing.FIRE)

    def test_dual_type_match_first(self):
        p = make_pkmn(typing=[Typing.FIRE, Typing.FLYING])
        assert has_type(p, Typing.FIRE)

    def test_dual_type_match_second(self):
        p = make_pkmn(typing=[Typing.WATER, Typing.ICE])
        assert has_type(p, Typing.ICE)

    def test_dual_type_no_match(self):
        p = make_pkmn(typing=[Typing.GRASS, Typing.POISON])
        assert not has_type(p, Typing.GHOST)


class TestCalculateDamage:
    def test_base_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(typing=[Typing.FIGHTING], attack=50)
        df = make_pkmn(defense=50)
        move = make_move(typing=Typing.WATER, power=40)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 50, 50)
        assert dmg == expected
        assert msg == ''

    def test_stab_applies(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(typing=[Typing.NORMAL], attack=50)
        df = make_pkmn(defense=50)
        move = make_move(typing=Typing.NORMAL, power=40)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 50, 50, stab=2)
        assert dmg == expected
        assert msg == ''

    def test_super_effective_2x(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(attack=50)
        df = make_pkmn(typing=[Typing.ROCK], defense=50)
        move = make_move(typing=Typing.WATER, power=40)
        eff = pkmn_types.get_effectiveness(Typing.WATER, Typing.ROCK)
        assert eff == 2.0
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 50, 50, effectiveness=2.0)
        assert dmg == expected
        assert msg == ''

    def test_super_effective_4x(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(attack=50)
        df = make_pkmn(typing=[Typing.GRASS, Typing.GROUND], defense=50)
        move = make_move(typing=Typing.ICE, power=40)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 50, 50, effectiveness=4.0)
        assert dmg == expected
        assert msg == ''

    def test_no_effect(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(attack=50)
        df = make_pkmn(typing=[Typing.GHOST], defense=50)
        move = make_move(typing=Typing.NORMAL, power=40)
        dmg, msg = calculate_damage(atk, move, df)
        assert dmg == 0
        assert msg == ''

    def test_not_very_effective(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(typing=[Typing.WATER], attack=50)
        df = make_pkmn(typing=[Typing.ROCK], defense=50)
        move = make_move(typing=Typing.NORMAL, power=40)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 50, 50, effectiveness=0.5)
        assert dmg == expected
        assert msg == ''
        assert msg == ''

    def test_physical_move_uses_attack(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(typing=[Typing.FIGHTING], attack=100, sp_atk=10)
        df = make_pkmn(defense=50)
        move = make_move(typing=Typing.NORMAL, power=40, category=MoveCategory.PHYSICAL)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 100, 50)
        assert dmg == expected

    def test_special_move_uses_sp_atk(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(attack=10, sp_atk=100)
        df = make_pkmn(sp_def=50)
        move = make_move(typing=Typing.WATER, power=40, category=MoveCategory.SPECIAL)
        dmg, msg = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 100, 50)
        assert dmg == expected


class TestCriticalHit:
    def test_high_speed_crits(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
        atk = make_pkmn(base_speed=100)
        mult, msg = calculate_crit_multiplier(atk)
        assert mult == 2
        assert msg == '\nCritical hit!'

    def test_low_speed_no_crit(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(base_speed=10)
        mult, msg = calculate_crit_multiplier(atk)
        assert mult == 1
        assert msg == ''

    def test_crit_cap_at_255(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 254)
        atk = make_pkmn(base_speed=600)
        mult, msg = calculate_crit_multiplier(atk)
        assert mult == 2
        assert msg == '\nCritical hit!'


class TestStruggleNoPP:
    def test_damage_and_recoil(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(name='Attacker', attack=50)
        df = make_pkmn(name='Defender', hp=200, defense=50)
        hp_before = df.hp
        atk_hp = atk.hp

        msg = struggle_no_pp(atk, df)

        assert df.hp < hp_before
        assert atk.hp < atk_hp
        assert 'Struggle' in msg
        assert 'recoil' in msg

    def test_faints_defender(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(name='Attacker', attack=200)
        df = make_pkmn(name='Defender', hp=1, defense=1)
        struggle_no_pp(atk, df)
        assert df.fainted


class TestHandleBurnPoison:
    def test_burn_player(self):
        p = make_pkmn(name='A', hp=200, max_hp=200, status=EffectStatus.BURN)
        e = make_pkmn(name='B')
        msg = handle_burn_poison(p, e)
        assert p.hp < 200
        assert 'A is hurt by its burn' in msg
        assert 'B' not in msg

    def test_poison_enemy(self):
        p = make_pkmn(name='A')
        e = make_pkmn(name='B', hp=200, max_hp=200, status=EffectStatus.POISON)
        msg = handle_burn_poison(p, e)
        assert e.hp < 200
        assert 'B is hurt by poison' in msg
        assert 'A' not in msg

    def test_both_damaged(self):
        p = make_pkmn(name='A', hp=200, max_hp=200, status=EffectStatus.BURN)
        e = make_pkmn(name='B', hp=200, max_hp=200, status=EffectStatus.POISON)
        msg = handle_burn_poison(p, e)
        assert p.hp < 200
        assert e.hp < 200
        assert 'A is hurt by its burn' in msg
        assert 'B is hurt by poison' in msg

    def test_no_status_nothing(self):
        p = make_pkmn(name='A', hp=200)
        e = make_pkmn(name='B', hp=200)
        msg = handle_burn_poison(p, e)
        assert msg == ''
        assert p.hp == 200
        assert e.hp == 200

    def test_each_tick_damages_1_16(self):
        p = make_pkmn(name='A', hp=160, max_hp=160, status=EffectStatus.BURN)
        e = make_pkmn(name='B')
        handle_burn_poison(p, e)
        expected_loss = math.floor(1 / 16 * 160)
        assert p.hp == 160 - expected_loss


class TestHandleToxicity:
    def test_toxic_turns_increase_damage(self):
        p = make_pkmn(name='A', hp=500, max_hp=500, status=EffectStatus.TOXIC)
        e = make_pkmn(name='B')
        p.toxic_turns = 0
        handle_toxicity(p, e)
        assert p.toxic_turns == 1
        assert p.hp < 500

        handle_toxicity(p, e)
        assert p.toxic_turns == 2
        assert p.hp < 500

    def test_toxic_damage_scales_with_turns(self):
        p = make_pkmn(name='A', hp=500, max_hp=500, status=EffectStatus.TOXIC)
        e = make_pkmn(name='B')
        p.toxic_turns = 0
        handle_toxicity(p, e)
        loss_t1 = 500 - p.hp
        base = math.floor(1 / 16 * 500)
        assert loss_t1 == base

        handle_toxicity(p, e)
        expected_hp = 500 - base * 3
        assert p.hp == expected_hp

    def test_no_toxic_no_damage(self):
        p = make_pkmn(name='A', hp=200)
        e = make_pkmn(name='B', hp=200)
        msg = handle_toxicity(p, e)
        assert msg == ''
        assert p.hp == 200

    def test_damage_capped(self):
        p = make_pkmn(name='A', hp=300, max_hp=300, status=EffectStatus.TOXIC)
        e = make_pkmn(name='B')
        base = math.floor(1 / 16 * 300)
        p.toxic_turns = 14
        handle_toxicity(p, e)
        assert p.hp == 300 - base  # capped, not 300 - base*15


class TestHandleLeechSeed:
    def test_player_seeded_drains_to_enemy(self):
        p = make_pkmn(name='A', hp=200, max_hp=200, seeded=True)
        e = make_pkmn(name='B', hp=100, max_hp=200)
        msg = handle_leech_seed(p, e)
        assert p.hp < 200
        assert e.hp > 100
        assert 'A' in msg

    def test_enemy_seeded_drains_to_player(self):
        p = make_pkmn(name='A', hp=100, max_hp=200)
        e = make_pkmn(name='B', hp=200, max_hp=200, seeded=True)
        msg = handle_leech_seed(p, e)
        assert e.hp < 200
        assert p.hp > 100
        assert 'B' in msg

    def test_no_seed_no_effect(self):
        p = make_pkmn(name='A', hp=200)
        e = make_pkmn(name='B', hp=200)
        msg = handle_leech_seed(p, e)
        assert msg == ''
        assert p.hp == 200
        assert e.hp == 200

    def test_drain_does_not_overheal(self):
        p = make_pkmn(name='A', hp=190, max_hp=200, seeded=True)
        e = make_pkmn(name='B', hp=200, max_hp=200)
        handle_leech_seed(p, e)
        drain = math.floor(1 / 16 * 200)
        expected_e_hp = min(200 + drain, 200)
        assert e.hp == expected_e_hp


class TestMoveHandlers:
    def test_reflect(self):
        atk = make_pkmn(name='A', defense=100)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Reflect'](atk, df)
        assert atk.reflect
        assert atk.defense == 200
        assert 'gained armor' in msg

    def test_reflect_twice(self):
        atk = make_pkmn(name='A', defense=100, reflect=True)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Reflect'](atk, df)
        assert 'already' in msg

    def test_light_screen(self):
        atk = make_pkmn(name='A', sp_def=100)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Light Screen'](atk, df)
        assert atk.light_screen
        assert atk.sp_def == 200
        assert 'protected' in msg

    def test_substitute(self):
        atk = make_pkmn(name='A', hp=100, max_hp=100)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Substitute'](atk, df)
        assert atk.substitute
        assert atk.hp == 75
        assert 'substitute doll' in msg

    def test_substitute_no_hp(self):
        atk = make_pkmn(name='A', hp=20, max_hp=100)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Substitute'](atk, df)
        assert not atk.substitute
        assert msg == ''

    def test_rest_restores_hp(self):
        atk = make_pkmn(name='A', hp=50, max_hp=200)
        df = make_pkmn(name='B')
        MOVE_HANDLERS['Rest'](atk, df)
        assert atk.hp == 200
        assert atk.status == EffectStatus.SLEEP

    def test_rest_at_full_hp_no_effect(self):
        atk = make_pkmn(name='A', hp=200, max_hp=200, status=None)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Rest'](atk, df)
        assert 'already has all its hp' in msg
        assert atk.hp == 200
        assert atk.status is None

    def test_haze_resets_multipliers(self):
        atk = make_pkmn(name='A', atk_mult=4, def_mult=-3, sp_atk_mult=2)
        df = make_pkmn(name='B', atk_mult=1, def_mult=-2)
        atk.attack = 200
        atk.defense = 50
        df.attack = 150
        df.defense = 40
        MOVE_HANDLERS['Haze'](atk, df)
        assert atk.atk_mult == 0
        assert atk.def_mult == 0
        assert df.atk_mult == 0
        assert df.def_mult == 0

    def test_poison_applies(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', typing=[Typing.NORMAL], status=None)
        MOVE_HANDLERS['Poison Powder'](atk, df)
        assert df.status == EffectStatus.POISON

    def test_poison_immune_poison_type(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', typing=[Typing.POISON], status=None)
        msg = MOVE_HANDLERS['Poison Powder'](atk, df)
        assert df.status is None
        assert 'no effect' in msg

    def test_sleep_applies(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', status=None)
        MOVE_HANDLERS['Sing'](atk, df)
        assert df.status == EffectStatus.SLEEP

    def test_paralyze_reduces_speed(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', speed=100, status=None)
        MOVE_HANDLERS['Thunder Wave'](atk, df)
        assert df.status == EffectStatus.PARALYZE
        assert df.speed < 100

    def test_confuse_applies(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', temp_status=None)
        MOVE_HANDLERS['Confuse Ray'](atk, df)
        assert df.temp_status == EffectStatus.CONFUSION

    def test_toxic_applies(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', typing=[Typing.NORMAL], status=None)
        MOVE_HANDLERS['Toxic'](atk, df)
        assert df.status == EffectStatus.TOXIC

    def test_toxic_immune_poison(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', typing=[Typing.POISON], status=None)
        msg = MOVE_HANDLERS['Toxic'](atk, df)
        assert df.status is None
        assert 'no effect' in msg

    def test_leech_seed_grass_immune(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', typing=[Typing.GRASS], seeded=False)
        msg = MOVE_HANDLERS['Leech Seed'](atk, df)
        assert not df.seeded
        assert 'no effect' in msg

    def test_recover(self):
        atk = make_pkmn(name='A', hp=50, max_hp=200)
        df = make_pkmn(name='B')
        MOVE_HANDLERS['Recover'](atk, df)
        assert atk.hp == 150

    def test_recover_at_full_hp_no_effect(self):
        atk = make_pkmn(name='A', hp=200, max_hp=200)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Recover'](atk, df)
        assert 'already has all its hp' in msg
        assert atk.hp == 200

    def test_splash_does_nothing(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Splash'](atk, df)
        assert 'nothing happened' in msg

    def test_swords_dance_raises_atk(self):
        atk = make_pkmn(name='A', atk_mult=0, attack=100)
        df = make_pkmn(name='B')
        MOVE_HANDLERS['Swords Dance'](atk, df)
        assert atk.atk_mult == 2

    def test_growl_lowers_atk(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', atk_mult=0, attack=100)
        df.accuracy = 1.0
        MOVE_HANDLERS['Growl'](atk, df)
        assert df.atk_mult == -1
        assert df.attack < 100

    def test_mist_blocks_debuff(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B', atk_mult=0, mist=True)
        msg = MOVE_HANDLERS['Growl'](atk, df)
        assert df.atk_mult == 0
        assert 'Mist' in msg


class TestHandleStatusMove:
    def test_known_move_delegates(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B')
        move = make_move(name='Splash')
        msg = handle_status_move(atk, move, df)
        assert 'nothing happened' in msg

    def test_unknown_move_returns_empty(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B')
        move = make_move(name='Nonexistent')
        msg = handle_status_move(atk, move, df)
        assert msg == ''
