from __future__ import annotations

import math
import random
from unittest.mock import patch

from app.core.combat import (
    MOVE_HANDLERS,
    atk,
    calculate_crit_multiplier,
    calculate_damage,
    handle_burn_poison,
    handle_leech_seed,
    handle_special_physical_move,
    handle_status_move,
    handle_toxicity,
    has_type,
    struggle_no_pp,
)
from app.data import pkmn_types
from app.schemas.effect_status import EffectStatus
from app.schemas.move import MoveCategory, SecondaryEffect
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

    def test_disable_disables_move(self):
        atk_pkmn = make_pkmn(name='A')
        m1 = make_move(name='Tackle', pp=35)
        m2 = make_move(name='Growl', pp=40)
        df_pkmn = make_pkmn(name='B', moves=[m1, m2, None, None])
        msg = MOVE_HANDLERS['Disable'](atk_pkmn, df_pkmn)
        assert df_pkmn.disabled_move != -1
        assert df_pkmn.disabled_turns == 4
        assert 'disabled' in msg

    def test_disable_substitute_blocks(self):
        atk_pkmn = make_pkmn(name='A')
        df_pkmn = make_pkmn(
            name='B', substitute=True,
            moves=[make_move(name='Tackle'), None, None, None],
        )
        msg = MOVE_HANDLERS['Disable'](atk_pkmn, df_pkmn)
        assert df_pkmn.disabled_move == -1
        assert 'Substitute' in msg

    def test_disable_no_available_move(self):
        atk_pkmn = make_pkmn(name='A')
        df_pkmn = make_pkmn(name='B', moves=[None, None, None, None])
        msg = MOVE_HANDLERS['Disable'](atk_pkmn, df_pkmn)
        assert 'nothing' in msg

    def test_focus_energy_sets_flag(self):
        atk_pkmn = make_pkmn(name='A')
        df_pkmn = make_pkmn(name='B')
        assert not atk_pkmn.focus_energy
        msg = MOVE_HANDLERS['Focus Energy'](atk_pkmn, df_pkmn)
        assert atk_pkmn.focus_energy
        assert 'getting pumped' in msg

    def test_focus_energy_already_active(self):
        atk_pkmn = make_pkmn(name='A', focus_energy=True)
        df_pkmn = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Focus Energy'](atk_pkmn, df_pkmn)
        assert 'nothing' in msg

    def test_mirror_move_copies_enemy_move(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', attack=50)
        enemy_move = make_move(name='Tackle', power=40)
        df_pkmn = make_pkmn(
            name='Defender', hp=200, defense=50,
            moves=[enemy_move, None, None, None],
        )
        msg = MOVE_HANDLERS['Mirror Move'](atk_pkmn, df_pkmn)
        assert df_pkmn.hp < 200
        assert 'used' in msg

    def test_mirror_move_no_enemy_moves(self):
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', moves=[None, None, None, None])
        msg = MOVE_HANDLERS['Mirror Move'](atk_pkmn, df_pkmn)
        assert 'nothing' in msg

    def test_smokescreen_reduces_accuracy(self):
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', accuracy=1.0, acc_mult=0)
        msg = MOVE_HANDLERS['Smokescreen'](atk_pkmn, df_pkmn)
        assert df_pkmn.acc_mult == -1
        assert df_pkmn.accuracy < 1.0
        assert 'Accuracy' in msg

    def test_smokescreen_mist_blocks(self):
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', accuracy=1.0, acc_mult=0, mist=True)
        msg = MOVE_HANDLERS['Smokescreen'](atk_pkmn, df_pkmn)
        assert df_pkmn.acc_mult == 0
        assert 'Mist' in msg

    def test_meditate_raises_attack(self):
        atk_pkmn = make_pkmn(name='Attacker', atk_mult=0, attack=100)
        df_pkmn = make_pkmn(name='Defender')
        MOVE_HANDLERS['Meditate'](atk_pkmn, df_pkmn)
        assert atk_pkmn.atk_mult == 1
        assert atk_pkmn.attack > 100

    def test_screech_sharply_lowers_defense(self):
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', def_mult=0, defense=100)
        msg = MOVE_HANDLERS['Screech'](atk_pkmn, df_pkmn)
        assert df_pkmn.def_mult == -2
        assert df_pkmn.defense < 100
        assert 'went way down' in msg

    def test_sharpen_raises_attack(self):
        atk_pkmn = make_pkmn(name='Attacker', atk_mult=0, attack=100)
        df_pkmn = make_pkmn(name='Defender')
        MOVE_HANDLERS['Sharpen'](atk_pkmn, df_pkmn)
        assert atk_pkmn.atk_mult == 1
        assert atk_pkmn.attack > 100

    def test_metronome_calls_random_move(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        chosen = make_move(name='Tackle', power=40)
        monkeypatch.setattr(random, 'choice', lambda _: chosen)
        atk_pkmn = make_pkmn(name='Attacker', attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        msg = MOVE_HANDLERS['Metronome'](atk_pkmn, df_pkmn)
        expected_dmg = damage_no_var(100, 40, 50, 50, stab=2)
        assert df_pkmn.hp == 200 - expected_dmg
        assert 'Tackle' in msg


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


class TestAtkFixedDamage:
    def test_dragon_rage_fixed_40_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', level=100)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Dragon Rage', power=0, typing=Typing.DRAGON)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 160

    def test_sonic_boom_fixed_20_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', level=100)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Sonic Boom', power=0, typing=Typing.NORMAL)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 180

    def test_seismic_toss_fixed_level_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(level=50)
        df_pkmn = make_pkmn(hp=200)
        move = make_move(name='Seismic Toss', power=0, typing=Typing.FIGHTING)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 150

    def test_night_shade_fixed_level_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(level=75)
        df_pkmn = make_pkmn(hp=200)
        move = make_move(name='Night Shade', power=0, typing=Typing.GHOST)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 125

    def test_super_fang_halves_current_hp(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=179)
        move = make_move(name='Super Fang', power=0, typing=Typing.NORMAL)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 90  # 179 // 2 = 89, 179 - 89 = 90


class TestAtkRecoil:
    def test_double_edge_recoil_quarter_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(name='Double-Edge', power=100)
        expected_dmg = damage_no_var(100, 100, 50, 50, stab=2)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - expected_dmg
        assert atk_pkmn.hp == 200 - expected_dmg // 4

    def test_take_down_recoil_quarter_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(name='Take Down', power=90)
        expected_dmg = damage_no_var(100, 90, 50, 50, stab=2)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - expected_dmg
        assert atk_pkmn.hp == 200 - expected_dmg // 4

    def test_submission_recoil_quarter_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(name='Submission', power=80)
        expected_dmg = damage_no_var(100, 80, 50, 50, stab=2)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - expected_dmg
        assert atk_pkmn.hp == 200 - expected_dmg // 4

    def test_no_recoil_on_normal_move(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        hp_before = atk_pkmn.hp
        move = make_move(name='Tackle', power=40)
        atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.hp == hp_before


class TestAtkDraining:
    def test_absorb_drains_and_heals(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=100, max_hp=200, attack=5)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=100)
        move = make_move(
            name='Absorb', power=20, typing=Typing.GRASS, category=MoveCategory.SPECIAL,
        )
        hp_before = atk_pkmn.hp
        df_hp_before = df_pkmn.hp
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp < df_hp_before
        assert atk_pkmn.hp > hp_before

    def test_dream_eater_only_on_sleeping(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=100, max_hp=200, attack=5)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=100, status=EffectStatus.SLEEP)
        move = make_move(name='Dream Eater', power=100, typing=Typing.PSYCHIC)
        df_hp_before = df_pkmn.hp
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp < df_hp_before

    def test_dream_eater_no_effect_awake(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', hp=200, status=None)
        move = make_move(name='Dream Eater', power=100, typing=Typing.PSYCHIC)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200


class TestAtkOHKO:
    def test_explosion_faints_both(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, max_hp=200)
        df_pkmn = make_pkmn(name='Defender', hp=200)
        move = make_move(name='Explosion', power=170)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.fainted
        assert atk_pkmn.fainted
        assert df_pkmn.hp == 0
        assert atk_pkmn.hp == 0

    def test_self_destruct_faints_both(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, max_hp=200)
        df_pkmn = make_pkmn(name='Defender', hp=200)
        move = make_move(name='Self-Destruct', power=130)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.fainted
        assert atk_pkmn.fainted

    def test_fissure_faints_defender(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=1)
        move = make_move(name='Fissure', power=0, accuracy=30, typing=Typing.GROUND)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.fainted
        assert not atk_pkmn.fainted


class TestAtkBurnAndConfusion:
    def test_burn_halves_physical_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(attack=50, status=EffectStatus.BURN)
        df_pkmn = make_pkmn(hp=200, defense=50)
        move = make_move(power=40)
        expected = damage_no_var(100, 40, 50, 50, stab=2) // 2
        hp_before = df_pkmn.hp
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == hp_before - expected

    def test_confusion_self_hit(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        monkeypatch.setattr(random, 'random', lambda: 0.25)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50, temp_status=EffectStatus.CONFUSION)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(power=40)
        expected_self_dmg = damage_no_var(100, 40, 50, 50, stab=2)
        atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.hp == 200 - expected_self_dmg
        assert df_pkmn.hp == 200

    def test_confusion_no_self_hit(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        monkeypatch.setattr(random, 'random', lambda: 0.75)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50, temp_status=EffectStatus.CONFUSION)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(power=40, category=MoveCategory.SPECIAL)
        atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.hp == 200


class TestMultiHitMoves:
    def test_variable_multi_hit_min_hits(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200)
        move = make_move(name='Fury Swipes', power=18)
        with patch('app.core.combat.random.randint', return_value=50):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 18)
        assert df_pkmn.hp == 182
        assert 'Hit 1 time(s)' in msg

    def test_variable_multi_hit_max_hits(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=500)
        move = make_move(name='Fury Swipes', power=18)
        with patch('app.core.combat.random.randint', side_effect=[30, 10, 10, 10]):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 18)
        assert df_pkmn.hp == 500 - 18 * 5
        assert 'Hit 5 time(s)' in msg

    def test_variable_multi_hit_three_hits(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=500)
        move = make_move(name='Fury Swipes', power=18)
        with patch('app.core.combat.random.randint', side_effect=[30, 10, 50]):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 18)
        assert df_pkmn.hp == 500 - 18 * 3
        assert 'Hit 3 time(s)' in msg

    def test_fixed_two_hit_moves(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200)
        move = make_move(name='Double Kick', power=30)
        msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 30)
        assert df_pkmn.hp == 140
        assert 'Hit 2 time(s)' in msg

    def test_multi_hit_secondary_effect(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, typing=[Typing.NORMAL], status=None)
        move = make_move(
            name='Fury Swipes', power=18,
            secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.POISON),
        )
        with patch('app.core.combat.random.randint', side_effect=[50, 5]):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 18)
        assert df_pkmn.hp == 182
        assert df_pkmn.status == EffectStatus.POISON
        assert 'poisoned' in msg


class TestSecondaryEffects:
    def test_burn_secondary_effect(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.BURN),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status == EffectStatus.BURN
        assert 'burned' in msg

    def test_paralyze_ghost_immune(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, typing=[Typing.GHOST], status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.PARALYZE),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status is None

    def test_freeze_secondary_effect(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.FREEZE),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status == EffectStatus.FREEZE
        assert 'frozen' in msg

    def test_poison_immune_poison_type(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, typing=[Typing.POISON], status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.POISON),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status is None

    def test_confuse_secondary_effect(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, temp_status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.CONFUSION),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.temp_status == EffectStatus.CONFUSION
        assert 'confused' in msg


class TestCriticalHitFocusEnergy:
    def test_focus_energy_increases_crit_threshold(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
        atk_pkmn = make_pkmn(base_speed=10, focus_energy=True)
        mult, msg = calculate_crit_multiplier(atk_pkmn)
        assert mult == 2
        assert msg == '\nCritical hit!'

    def test_focus_energy_no_crit_above_threshold(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(base_speed=10, focus_energy=True)
        mult, msg = calculate_crit_multiplier(atk_pkmn)
        assert mult == 1
        assert msg == ''

    def test_focus_energy_crit_still_caps(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 254)
        atk_pkmn = make_pkmn(base_speed=600, focus_energy=True)
        mult, msg = calculate_crit_multiplier(atk_pkmn)
        assert mult == 2
        assert msg == '\nCritical hit!'
