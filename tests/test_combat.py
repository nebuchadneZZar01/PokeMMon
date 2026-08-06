from __future__ import annotations

import math
import random
from unittest.mock import patch

from app.core.combat import (
    CONST_THAW,
    MOVE_HANDLERS,
    _apply_secondary_effect,
    atk,
    calculate_crit_multiplier,
    calculate_damage,
    handle_burn_poison,
    handle_leech_seed,
    handle_special_physical_move,
    handle_status_move,
    handle_toxicity,
    handle_trapped,
    has_type,
    hit,
    inc_dec_stat_mult,
    struggle_no_pp,
    try_atk_status,
    update_battle_stat,
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
        dmg, _ = calculate_damage(atk, move, df)
        expected = damage_no_var(100, 40, 100, 50)
        assert dmg == expected

    def test_special_move_uses_sp_atk(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk = make_pkmn(attack=10, sp_atk=100)
        df = make_pkmn(sp_def=50)
        move = make_move(typing=Typing.WATER, power=40, category=MoveCategory.SPECIAL)
        dmg, _ = calculate_damage(atk, move, df)
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
    def test_double_edge_recoil_third_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Attacker', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(name='Double-Edge', power=100)
        expected_dmg = damage_no_var(100, 100, 50, 50, stab=2)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - expected_dmg
        assert atk_pkmn.hp == 200 - expected_dmg // 3

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
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
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
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
        monkeypatch.setattr(random, 'random', lambda: 0.25)
        atk_pkmn = make_pkmn(
            name='Attacker', hp=200, attack=50, defense=50,
            temp_status=EffectStatus.CONFUSION,
        )
        df_pkmn = make_pkmn(name='Defender', hp=200, defense=50)
        move = make_move(power=40)
        expected_self_dmg = 35
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


class TestFreezeThaw:
    def test_freeze_thaws_at_20_percent(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        monkeypatch.setattr(random, 'random', lambda: CONST_THAW - 0.01)
        atk_pkmn = make_pkmn(name='Atk', hp=200, status=EffectStatus.FREEZE)
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(power=40)
        msg = try_atk_status(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.status is None
        assert 'thawed out' in msg
        assert df_pkmn.hp < 200

    def test_freeze_stays_frozen(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        monkeypatch.setattr(random, 'random', lambda: CONST_THAW + 0.01)
        atk_pkmn = make_pkmn(name='Atk', status=EffectStatus.FREEZE)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(power=40)
        msg = try_atk_status(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.status == EffectStatus.FREEZE
        assert 'frozen solid' in msg
        assert df_pkmn.hp == 200


class TestPsywave:
    def test_psywave_damage_formula(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 100)
        atk_pkmn = make_pkmn(name='Atk', level=100)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Psywave', power=0, accuracy=80, typing=Typing.PSYCHIC)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp < 200

    def test_psywave_damage_at_level_100(self, monkeypatch):
        atk_pkmn = make_pkmn(name='Atk', level=100)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Psywave', power=0, accuracy=80, typing=Typing.PSYCHIC)
        with patch('app.core.combat.random.randint', side_effect=[0, 0, 217, 100]):
            atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - 100


class TestHighCritRatio:
    def test_slash_crits_more_often(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
        atk_pkmn = make_pkmn(base_speed=10)
        # high_crit threshold = floor(10/2)*8 = 40, rate=0 < 40 → crit
        mult, msg = calculate_crit_multiplier(atk_pkmn, high_crit=True)
        assert mult == 2
        assert msg == '\nCritical hit!'

    def test_normal_move_no_high_crit_at_same_speed(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 0)
        atk_pkmn = make_pkmn(base_speed=10)
        # normal threshold = floor(10/2) = 5, rate=0 < 5 → crit
        mult, msg = calculate_crit_multiplier(atk_pkmn, high_crit=False)
        assert mult == 2
        assert msg == '\nCritical hit!'

    def test_high_crit_vs_normal_threshold(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 20)
        atk_pkmn = make_pkmn(base_speed=10)
        # high_crit threshold = 40, rate=20 < 40 → crit
        mult_hc, _ = calculate_crit_multiplier(atk_pkmn, high_crit=True)
        # normal threshold = 5, rate=20 >= 5 → no crit
        mult_norm, _ = calculate_crit_multiplier(atk_pkmn, high_crit=False)
        assert mult_hc == 2
        assert mult_norm == 1


class TestHyperBeam:
    def test_hyper_beam_damages(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(name='Hyper Beam', power=150, category=MoveCategory.PHYSICAL)
        atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp < 200
        assert atk_pkmn.recharging

    def test_hyper_beam_recharge_forced(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200, attack=50, recharging=True)
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(name='Tackle', power=40)
        msg = try_atk_status(atk_pkmn, move, df_pkmn)
        assert 'must recharge' in msg
        assert not atk_pkmn.recharging
        assert df_pkmn.hp == 200  # no damage dealt

    def test_hyper_beam_no_extra_recharge(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200, attack=50)
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(name='Hyper Beam', power=150, category=MoveCategory.PHYSICAL)
        atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.recharging
        # Second call with a normal move should also recharge
        move2 = make_move(name='Tackle', power=40)
        msg = try_atk_status(atk_pkmn, move2, df_pkmn)
        assert 'must recharge' in msg
        assert not atk_pkmn.recharging


class TestBide:
    def test_bide_first_turn_sets_state(self):
        atk_pkmn = make_pkmn(name='Atk')
        df_pkmn = make_pkmn(name='Df')
        move = make_move(name='Bide', power=0, category=MoveCategory.PHYSICAL)
        msg = atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.biding
        assert atk_pkmn.bide_turns == 0
        assert atk_pkmn.bide_damage == 0
        assert df_pkmn.hp == 200  # no damage on first turn
        assert 'used Bide' in msg

    def test_bide_accumulates_then_releases_twice(self):
        atk_pkmn = make_pkmn(name='Atk', hp=200)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Bide', power=0, category=MoveCategory.PHYSICAL)

        atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.biding

        hit(atk_pkmn, 30, df_pkmn)
        assert atk_pkmn.bide_damage == 30

        any_move = make_move()
        msg = try_atk_status(atk_pkmn, any_move, df_pkmn)
        assert 'storing energy' in msg
        assert atk_pkmn.biding
        assert atk_pkmn.bide_turns == 1

        hit(atk_pkmn, 20, df_pkmn)
        assert atk_pkmn.bide_damage == 50

        msg = try_atk_status(atk_pkmn, any_move, df_pkmn)
        assert 'unleashed energy' in msg
        assert not atk_pkmn.biding
        assert df_pkmn.hp == 200 - 100  # 2 * 50

    def test_bide_faints_defender_on_release(self):
        atk_pkmn = make_pkmn(name='Atk', hp=200)
        df_pkmn = make_pkmn(name='Df', hp=10)
        move = make_move(name='Bide', power=0, category=MoveCategory.PHYSICAL)

        atk(atk_pkmn, move, df_pkmn)

        hit(atk_pkmn, 30, df_pkmn)

        any_move = make_move()
        try_atk_status(atk_pkmn, any_move, df_pkmn)

        hit(atk_pkmn, 30, df_pkmn)

        msg = try_atk_status(atk_pkmn, any_move, df_pkmn)
        assert 'unleashed energy' in msg
        assert 'fainted' in msg
        assert df_pkmn.fainted


class TestCounter:
    def test_counter_deals_double_physical_damage(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(
            name='Atk', hp=200, last_damage_taken=40, last_move_was_physical=True,
        )
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(
            name='Counter', power=0, accuracy=100,
            typing=Typing.FIGHTING, category=MoveCategory.PHYSICAL,
        )
        msg = atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.hp == 200 - 80
        assert atk_pkmn.last_damage_taken == 0
        assert 'countered' in msg

    def test_counter_fails_no_physical_hit(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(
            name='Counter', power=0, accuracy=100,
            typing=Typing.FIGHTING, category=MoveCategory.PHYSICAL,
        )
        msg = atk(atk_pkmn, move, df_pkmn)
        assert 'failed' in msg
        assert df_pkmn.hp == 200


class TestTrapping:
    def test_wrap_traps_target(self):
        atk_pkmn = make_pkmn(name='Atk', attack=50)
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(name='Wrap', power=15)
        # randint calls: accuracy(0,255), crit(0,255), damage(217,255), trap(2,5)
        with patch('app.core.combat.random.randint', side_effect=[255, 0, 255, 3]):
            atk(atk_pkmn, move, df_pkmn)
        assert df_pkmn.trapped
        assert df_pkmn.trapped_turns == 3
        assert df_pkmn.hp < 200

    def test_trapped_blocks_move_half_the_time(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200, trapped=True, trapped_turns=3)
        df_pkmn = make_pkmn(name='Df')
        move = make_move(name='Tackle')

        with patch('app.core.combat.random.random', return_value=0.25):
            msg = try_atk_status(atk_pkmn, move, df_pkmn)
            assert "can't move" in msg
            assert df_pkmn.hp == 200

    def test_trapped_move_goes_through_half_the_time(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        atk_pkmn = make_pkmn(name='Atk', hp=200, trapped=True, trapped_turns=3)
        df_pkmn = make_pkmn(name='Df')
        move = make_move(name='Tackle')

        with patch('app.core.combat.random.random', return_value=0.75):
            try_atk_status(atk_pkmn, move, df_pkmn)
            assert df_pkmn.hp < 200

    def test_trapped_tick_damage(self):
        p = make_pkmn(name='A', hp=160, max_hp=160, trapped=True, trapped_turns=3)
        e = make_pkmn(name='B')
        msg = handle_trapped(p, e)
        expected = max(1, 160 // 16)
        assert p.hp == 160 - expected
        assert p.trapped_turns == 2
        assert 'hurt by the trap' in msg
        assert 'B' not in msg

    def test_trapped_expires_after_last_tick(self):
        p = make_pkmn(name='A', hp=160, max_hp=160, trapped=True, trapped_turns=1)
        e = make_pkmn(name='B')
        handle_trapped(p, e)
        assert p.trapped_turns == 0
        assert not p.trapped

    def test_bind_clamp_fire_spin_also_trap(self):
        for name in ('Bind', 'Clamp', 'Fire Spin'):
            atk_pkmn = make_pkmn(name='Atk', attack=50)
            df_pkmn = make_pkmn(name=f'Df_{name}', hp=200, defense=50)
            move = make_move(name=name, power=15)
            # randint calls: accuracy(0,255), crit(0,255), damage(217,255), trap(2,5)
            with patch('app.core.combat.random.randint', side_effect=[255, 0, 255, 3]):
                atk(atk_pkmn, move, df_pkmn)
            assert df_pkmn.trapped, f'{name} should trap'
            assert df_pkmn.hp < 200


class TestHitOnFainted:
    def test_skips_damage_if_already_fainted(self):
        atk_pkmn = make_pkmn(name='Atk')
        df_pkmn = make_pkmn(name='Df', hp=200, fainted=True)
        hit(df_pkmn, 50, atk_pkmn)
        assert df_pkmn.hp == 200
        assert df_pkmn.fainted

    def test_skips_status_damage_if_already_fainted(self):
        df_pkmn = make_pkmn(name='Df', hp=200, fainted=True)
        hit(df_pkmn, 50, status=True)
        assert df_pkmn.hp == 200

    def test_skips_substitute_status_damage_if_fainted(self):
        df_pkmn = make_pkmn(name='Df', hp=200, fainted=True, substitute=True)
        hit(df_pkmn, 50, status=True)
        assert df_pkmn.hp == 200


class TestSwitchValid:
    def test_blocks_switch_when_trapped(self):
        from unittest.mock import MagicMock

        from main import switch_valid

        target = MagicMock()
        target.name = 'Target'
        target.fainted = False

        current = MagicMock()
        current.name = 'Current'
        current.fainted = False
        current.trapped = True

        bs = MagicMock()
        bs.player.team = [target, current, None, None, None, None]
        bs.player.in_battle = current

        result = switch_valid(bs, 0)
        assert result is not None
        assert 'trapped' in result.lower()
        assert "can't switch" in result.lower()

    def test_does_not_block_if_not_trapped(self):
        from unittest.mock import MagicMock

        from main import switch_valid

        target = MagicMock()
        target.name = 'Target'
        target.fainted = False

        current = MagicMock()
        current.name = 'Current'
        current.fainted = False
        current.trapped = False

        bs = MagicMock()
        bs.player.team = [target, current, None, None, None, None]
        bs.player.in_battle = current

        assert switch_valid(bs, 0) is None


class TestAccuracy:
    def test_move_can_miss_with_high_rand_t(self):
        atk_pkmn = make_pkmn(name='Atk')
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Tackle', accuracy=50)
        with patch('app.core.combat.random.randint', return_value=255):
            msg = atk(atk_pkmn, move, df_pkmn)
        assert 'failed' in msg
        assert df_pkmn.hp == 200

    def test_accuracy_scales_correctly(self):
        atk_pkmn = make_pkmn(name='Atk')
        df_pkmn = make_pkmn(name='Df', hp=200, defense=1)
        move = make_move(name='Tackle', accuracy=100)
        with patch('app.core.combat.random.randint', side_effect=[0, 0, 217]):
            msg = atk(atk_pkmn, move, df_pkmn)
        assert 'failed' not in msg
        assert df_pkmn.hp < 200


class TestConfusionSnapOut:
    def test_auto_snap_after_5_turns(self):
        atk_pkmn = make_pkmn(
            name='Atk', hp=200, attack=50, defense=50,
            temp_status=EffectStatus.CONFUSION, confused_turns=5,
        )
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(power=40)
        with patch('app.core.combat.random.randint', side_effect=[0, 0, 217]):
            msg = atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.temp_status is None
        assert 'not confused' in msg

    def test_snap_out_after_hit(self):
        atk_pkmn = make_pkmn(
            name='Atk', hp=200, attack=50, defense=50,
            temp_status=EffectStatus.CONFUSION, confused_turns=5,
        )
        df_pkmn = make_pkmn(name='Df', hp=200, defense=50)
        move = make_move(power=40)
        with patch('app.core.combat.random.randint', side_effect=[0, 0, 217]):
            msg = atk(atk_pkmn, move, df_pkmn)
        assert atk_pkmn.temp_status is None
        assert 'not confused' in msg
        assert df_pkmn.hp < 200


class TestSecondaryEffectExistingStatus:
    def test_does_not_overwrite_existing_status(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, status=EffectStatus.PARALYZE)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.BURN),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status == EffectStatus.PARALYZE
        assert 'burned' not in msg

    def test_confusion_bypasses_existing_status_guard(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, status=EffectStatus.BURN, temp_status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.CONFUSION),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.temp_status == EffectStatus.CONFUSION
        assert 'confused' in msg


class TestSecondaryEffectTypeImmunity:
    def test_fire_immune_to_burn_secondary(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, typing=[Typing.FIRE], status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.BURN),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status is None
        assert 'burned' not in msg

    def test_ice_immune_to_freeze_secondary(self):
        atk_pkmn = make_pkmn()
        df_pkmn = make_pkmn(hp=200, typing=[Typing.ICE], status=None)
        move = make_move(
            power=40, secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.FREEZE),
        )
        with patch('app.core.combat.random.randint', return_value=5):
            msg = handle_special_physical_move(atk_pkmn, move, df_pkmn, 40)
        assert df_pkmn.status is None
        assert 'frozen' not in msg


class TestExplosionSelfDestructMessage:
    def test_explosion_returns_message(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 217)
        atk_pkmn = make_pkmn(name='Atk', hp=200, max_hp=200)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Explosion', power=170)
        msg = atk(atk_pkmn, move, df_pkmn)
        assert 'used Explosion' in msg
        assert atk_pkmn.fainted
        assert df_pkmn.fainted

    def test_self_destruct_returns_message(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 217)
        atk_pkmn = make_pkmn(name='Atk', hp=200, max_hp=200)
        df_pkmn = make_pkmn(name='Df', hp=200)
        move = make_move(name='Self-Destruct', power=130)
        msg = atk(atk_pkmn, move, df_pkmn)
        assert 'used Self-Destruct' in msg
        assert atk_pkmn.fainted
        assert df_pkmn.fainted


class TestHit:
    def test_reduces_hp(self):
        df = make_pkmn(name='Df', hp=200)
        assert hit(df, 50) == ''
        assert df.hp == 150
        assert not df.fainted

    def test_faints_at_zero(self):
        df = make_pkmn(name='Df', hp=200)
        hit(df, 200)
        assert df.hp == 0
        assert df.fainted

    def test_does_not_drop_below_zero(self):
        df = make_pkmn(name='Df', hp=200)
        hit(df, 300)
        assert df.hp == 0
        assert df.fainted

    def test_records_last_damage_taken(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200)
        hit(df, 40, atk)
        assert df.last_damage_taken == 40

    def test_no_last_damage_for_status_damage(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200)
        hit(df, 40, atk, status=True)
        assert df.last_damage_taken == 0

    def test_no_last_damage_without_attacker(self):
        df = make_pkmn(name='Df', hp=200)
        hit(df, 40)
        assert df.last_damage_taken == 0

    def test_bide_accumulates_normal_damage(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200, biding=True)
        hit(df, 30, atk)
        assert df.bide_damage == 30

    def test_bide_ignores_status_damage(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200, biding=True)
        hit(df, 30, atk, status=True)
        assert df.bide_damage == 0

    def test_substitute_absorbs_damage(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200, substitute=True)
        msg = hit(df, 100, atk)
        assert df.hp == 200
        assert df.sub_damage == 100
        assert 'substitute was hit' in msg

    def test_substitute_vanishes_at_threshold(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200, substitute=True, sub_damage=200)
        msg = hit(df, 100, atk)
        assert not df.substitute
        assert df.sub_damage == 0
        assert 'vanished' in msg

    def test_substitute_status_damage_bypasses_doll(self):
        atk = make_pkmn(name='Atk')
        df = make_pkmn(name='Df', hp=200, substitute=True)
        hit(df, 50, atk, status=True)
        assert df.hp == 150
        assert df.sub_damage == 0


class TestTryAtkStatus:
    def test_recharging_blocks_and_resets(self):
        atk = make_pkmn(name='Atk', recharging=True)
        df = make_pkmn(name='Df')
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk must recharge!'
        assert not atk.recharging

    def test_bide_stores_energy(self):
        atk = make_pkmn(name='Atk', biding=True)
        df = make_pkmn(name='Df', hp=200)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk is storing energy!'
        assert atk.bide_turns == 1

    def test_bide_releases_double_damage(self):
        atk = make_pkmn(name='Atk', biding=True, bide_turns=1, bide_damage=50)
        df = make_pkmn(name='Df', hp=200)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk unleashed energy!'
        assert df.hp == 100
        assert not atk.biding

    def test_bide_release_faints_defender(self):
        atk = make_pkmn(name='Atk', biding=True, bide_turns=1, bide_damage=60)
        df = make_pkmn(name='Df', hp=100)
        msg = try_atk_status(atk, make_move(), df)
        assert 'fainted' in msg
        assert df.fainted

    def test_trapped_random_block(self, monkeypatch):
        atk = make_pkmn(name='Atk', trapped=True)
        df = make_pkmn(name='Df')
        monkeypatch.setattr(random, 'random', lambda: 0.2)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk is trapped and can\'t move!'

    def test_trapped_random_acts(self, monkeypatch):
        atk = make_pkmn(name='Atk', trapped=True)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'random', lambda: 0.9)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        try_atk_status(atk, make_move(), df)
        assert df.hp < 200

    def test_paralyzed_can_still_act(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.PARALYZE)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'random', lambda: 0.1)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        try_atk_status(atk, make_move(), df)
        assert df.hp < 200

    def test_paralyzed_full_paralysis(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.PARALYZE)
        df = make_pkmn(name='Df')
        monkeypatch.setattr(random, 'random', lambda: 0.9)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk is paralyzed and can\'t move!'

    def test_sleep_still_sleeping(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.SLEEP, sleeping_turns=0)
        df = make_pkmn(name='Df')
        monkeypatch.setattr(random, 'random', lambda: 0.9)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk is sleeping...'
        assert atk.sleeping_turns == 1

    def test_sleep_wakes_and_attacks(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.SLEEP, sleeping_turns=0)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'random', lambda: 0.1)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = try_atk_status(atk, make_move(), df)
        assert atk.status is None
        assert 'woke up' in msg
        assert df.hp < 200

    def test_sleep_forced_wake_after_seven_turns(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.SLEEP, sleeping_turns=7)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = try_atk_status(atk, make_move(), df)
        assert atk.status is None
        assert 'woke up' in msg

    def test_freeze_thaws(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.FREEZE)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'random', lambda: 0.0)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = try_atk_status(atk, make_move(), df)
        assert atk.status is None
        assert 'thawed' in msg

    def test_freeze_stays_frozen(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.FREEZE)
        df = make_pkmn(name='Df')
        monkeypatch.setattr(random, 'random', lambda: 0.9)
        msg = try_atk_status(atk, make_move(), df)
        assert msg == 'Atk is frozen solid!'

    def test_burn_acts(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=EffectStatus.BURN)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        try_atk_status(atk, make_move(), df)
        assert df.hp < 200

    def test_clean_attack(self, monkeypatch):
        atk = make_pkmn(name='Atk', status=None)
        df = make_pkmn(name='Df', hp=200)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        try_atk_status(atk, make_move(), df)
        assert df.hp < 200


class TestMoveHandlersExtended:
    def test_transform_copies_target(self):
        atk = make_pkmn(name='A', typing=[Typing.NORMAL])
        df = make_pkmn(
            name='B', typing=[Typing.FIRE],
            attack=100, defense=80, sp_atk=70, sp_def=60, speed=90,
            moves=[make_move(name='Ember', pp=25), None, None, None],
        )
        msg = MOVE_HANDLERS['Transform'](atk, df)
        assert atk.transformed
        assert atk.typing == [Typing.FIRE]
        assert atk.attack == 100
        assert atk.moves[0].name == 'Ember'
        assert atk.moves[0].pp == 12
        assert 'transforms into B' in msg

    def test_conversion_acquires_target_typing(self):
        atk = make_pkmn(name='A', typing=[Typing.NORMAL])
        df = make_pkmn(name='B', typing=[Typing.WATER, Typing.ICE])
        msg = MOVE_HANDLERS['Conversion'](atk, df)
        assert atk.typing == [Typing.WATER, Typing.ICE]
        assert 'assumes' in msg

    def test_mist_sets_flag(self):
        atk = make_pkmn(name='A')
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Mist'](atk, df)
        assert atk.mist
        assert 'shrouded in Mist' in msg

    def test_mist_twice(self):
        atk = make_pkmn(name='A', mist=True)
        df = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Mist'](atk, df)
        assert 'already a Mist' in msg

    def test_growth_raises_spatk_spdef(self):
        atk = make_pkmn(name='A', sp_atk_mult=0, sp_def_mult=0)
        df = make_pkmn(name='B')
        MOVE_HANDLERS['Growth'](atk, df)
        assert atk.sp_atk_mult == 1
        assert atk.sp_def_mult == 1

    def test_mimic_copies_enemy_move(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        enemy_move = make_move(name='Tackle', power=40)
        atk_pkmn = make_pkmn(name='Attacker', attack=50)
        df_pkmn = make_pkmn(
            name='Defender', hp=200, defense=50,
            moves=[enemy_move, None, None, None],
        )
        monkeypatch.setattr(random, 'choice', lambda seq: enemy_move)
        msg = MOVE_HANDLERS['Mimic'](atk_pkmn, df_pkmn)
        assert df_pkmn.hp < 200
        assert 'copies one of Defender' in msg

    def test_mimic_cannot_copy_itself(self, monkeypatch):
        enemy_move = make_move(name='Mimic')
        atk_pkmn = make_pkmn(name='Attacker')
        df_pkmn = make_pkmn(name='Defender', moves=[enemy_move, None, None, None])
        monkeypatch.setattr(random, 'choice', lambda seq: enemy_move)
        msg = MOVE_HANDLERS['Mimic'](atk_pkmn, df_pkmn)
        assert 'failed' in msg


class TestUpdateBattleStatNeg:
    def test_minus_three(self):
        assert math.isclose(update_battle_stat(100, -3), 40.0)

    def test_minus_four(self):
        assert math.isclose(update_battle_stat(100, -4), 33.0)

    def test_minus_five(self):
        assert math.isclose(update_battle_stat(100, -5), 28.0)

    def test_minus_six(self):
        assert math.isclose(update_battle_stat(100, -6), 25.0)


class TestIncDecStatMultCaps:
    def test_wont_rise_at_max(self):
        a = make_pkmn(name='A')
        a.atk_mult = 6
        val, msg = inc_dec_stat_mult(a, a, 'atk_mult', increase=True)
        assert val == 6
        assert "won't rise anymore" in msg

    def test_wont_drop_at_min(self):
        a = make_pkmn(name='A')
        a.def_mult = -6
        val, msg = inc_dec_stat_mult(a, a, 'def_mult', increase=False)
        assert val == -6
        assert "won't drop anymore" in msg


class TestHitSubstituteStatus:
    def test_status_damage_faints_through_substitute(self):
        df = make_pkmn(name='Df', hp=50, substitute=True)
        hit(df, 60, None, status=True)
        assert df.hp == 0
        assert df.fainted

    def test_status_damage_tracks_bide_and_last_damage(self):
        df = make_pkmn(name='Df', hp=200, substitute=True, biding=True)
        atk_p = make_pkmn(name='A')
        hit(df, 50, atk_p, status=True)
        assert df.hp == 150
        assert df.last_damage_taken == 50
        assert df.bide_damage == 50


class TestApplySecondaryEffect:
    def test_blocked_by_substitute(self):
        df = make_pkmn(name='Df', substitute=True)
        assert _apply_secondary_effect(df, EffectStatus.BURN) == ''

    def test_paralyze_reduces_speed(self):
        df = make_pkmn(name='Df', speed=100)
        msg = _apply_secondary_effect(df, EffectStatus.PARALYZE)
        assert df.status == EffectStatus.PARALYZE
        assert math.isclose(df.speed, 25.0)
        assert 'paralyzed' in msg

    def test_unknown_effect_returns_empty(self):
        df = make_pkmn(name='Df')
        assert _apply_secondary_effect(df, EffectStatus.TOXIC) == ''


class TestCounterFaint:
    def test_counter_faints_defender(self, monkeypatch):
        atk_p = make_pkmn(name='A', last_damage_taken=60, last_move_was_physical=True)
        df = make_pkmn(name='B', hp=100, defense=100)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        move = make_move(name='Counter', power=0)
        msg = handle_special_physical_move(atk_p, move, df, 0)
        assert "countered B" in msg
        assert 'fainted' in msg
        assert df.fainted


class TestFixedTwoHitSecondary:
    def test_secondary_effect_applied(self, monkeypatch):
        atk_p = make_pkmn(name='A')
        df = make_pkmn(name='B', hp=200)
        move = make_move(
            name='Bonemerang', power=50,
            secondary_effect=SecondaryEffect(chance=100, effect=EffectStatus.PARALYZE),
        )
        monkeypatch.setattr(random, 'randint', lambda a, b: 5)
        msg = handle_special_physical_move(atk_p, move, df, 20)
        assert 'Hit 2 time(s)' in msg
        assert df.status == EffectStatus.PARALYZE


class TestBoostMoveHandlers:
    def test_barrier_raises_defense_2(self):
        a = make_pkmn(name='A', defense=100)
        b = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Barrier'](a, b)
        assert a.def_mult == 2
        assert math.isclose(a.defense, 200)
        assert 'way up' in msg

    def test_agility_raises_speed_2(self):
        a = make_pkmn(name='A', speed=100)
        MOVE_HANDLERS['Agility'](a, make_pkmn(name='B'))
        assert a.speed_mult == 2
        assert math.isclose(a.speed, 200)

    def test_amnesia_raises_both_2(self):
        a = make_pkmn(name='A', sp_atk=100, sp_def=100)
        MOVE_HANDLERS['Amnesia'](a, make_pkmn(name='B'))
        assert a.sp_atk_mult == 2
        assert a.sp_def_mult == 2

    def test_harden_raises_defense_1(self):
        a = make_pkmn(name='A', defense=100)
        MOVE_HANDLERS['Harden'](a, make_pkmn(name='B'))
        assert a.def_mult == 1
        assert math.isclose(a.defense, 150)

    def test_double_team_raises_evasion_1(self):
        a = make_pkmn(name='A', speed=50)
        MOVE_HANDLERS['Double Team'](a, make_pkmn(name='B'))
        assert a.ev_mult == 1


class TestReduceMoveHandlers:
    def test_leer_lowers_defense(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', defense=100)
        msg = MOVE_HANDLERS['Leer'](a, d)
        assert d.def_mult == -1
        assert math.isclose(d.defense, 66)
        assert 'went down' in msg

    def test_screech_blocked_by_mist(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', mist=True)
        msg = MOVE_HANDLERS['Screech'](a, d)
        assert 'Mist prevents' in msg

    def test_string_shot_lowers_speed(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', speed=100)
        MOVE_HANDLERS['String Shot'](a, d)
        assert d.speed_mult == -1
        assert math.isclose(d.speed, 66)

    def test_leer_blocked_by_mist(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', mist=True)
        msg = MOVE_HANDLERS['Leer'](a, d)
        assert 'Mist prevents' in msg

    def test_string_shot_blocked_by_mist(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', mist=True)
        msg = MOVE_HANDLERS['String Shot'](a, d)
        assert 'Mist prevents' in msg


class TestStatusMoveBranches:
    def test_glare_already_status(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', status=EffectStatus.POISON)
        msg = MOVE_HANDLERS['Glare'](a, d)
        assert 'nothing happened' in msg

    def test_glare_substitute(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', substitute=True)
        msg = MOVE_HANDLERS['Glare'](a, d)
        assert 'Substitute prevents' in msg

    def test_hypnosis_substitute(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', substitute=True)
        msg = MOVE_HANDLERS['Hypnosis'](a, d)
        assert 'Substitute prevents' in msg

    def test_hypnosis_already_status(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', status=EffectStatus.BURN)
        msg = MOVE_HANDLERS['Hypnosis'](a, d)
        assert 'nothing happened' in msg

    def test_poison_gas_already_status(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', status=EffectStatus.BURN)
        msg = MOVE_HANDLERS['Poison Gas'](a, d)
        assert 'nothing happened' in msg

    def test_poison_gas_substitute(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', substitute=True)
        msg = MOVE_HANDLERS['Poison Gas'](a, d)
        assert 'Substitute prevents' in msg

    def test_toxic_already_status(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', status=EffectStatus.POISON)
        msg = MOVE_HANDLERS['Toxic'](a, d)
        assert 'nothing happened' in msg

    def test_toxic_substitute(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', substitute=True)
        msg = MOVE_HANDLERS['Toxic'](a, d)
        assert 'Substitute prevents' in msg


class TestLeechSeedBranches:
    def test_seeds_target(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B')
        msg = MOVE_HANDLERS['Leech Seed'](a, d)
        assert d.seeded
        assert 'was seeded' in msg

    def test_already_seeded(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', seeded=True)
        msg = MOVE_HANDLERS['Leech Seed'](a, d)
        assert 'already seeded' in msg

    def test_substitute(self):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', substitute=True)
        msg = MOVE_HANDLERS['Leech Seed'](a, d)
        assert 'Substitute prevents Leech Seed' in msg


class TestLightScreenReflectCaps:
    def test_light_screen_caps_at_1024(self):
        a = make_pkmn(name='A', sp_def=600)
        msg = MOVE_HANDLERS['Light Screen'](a, make_pkmn(name='B'))
        assert a.sp_def == 1024
        assert 'protected' in msg

    def test_light_screen_twice(self):
        a = make_pkmn(name='A', sp_def=100)
        b = make_pkmn(name='B')
        MOVE_HANDLERS['Light Screen'](a, b)
        msg = MOVE_HANDLERS['Light Screen'](a, b)
        assert 'already covering' in msg

    def test_reflect_twice(self):
        a = make_pkmn(name='A', defense=100)
        b = make_pkmn(name='B')
        MOVE_HANDLERS['Reflect'](a, b)
        msg = MOVE_HANDLERS['Reflect'](a, b)
        assert 'already covering' in msg

    def test_reflect_caps_at_1024(self):
        a = make_pkmn(name='A', defense=600)
        msg = MOVE_HANDLERS['Reflect'](a, make_pkmn(name='B'))
        assert a.defense == 1024
        assert 'gained armor' in msg


class TestMimicBranches:
    def test_copies_enemy_move(self, monkeypatch):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', moves=[make_move(name='Ember', power=40), None, None, None])
        monkeypatch.setattr(random, 'choice', lambda seq: seq[0])
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = MOVE_HANDLERS['Mimic'](a, d)
        assert 'copies one of B' in msg

    def test_no_moves_fails(self, monkeypatch):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', moves=[make_move(), None, None, None])
        d.moves = [None, None, None, None]
        monkeypatch.setattr(random, 'choice', lambda seq: seq[0])
        msg = MOVE_HANDLERS['Mimic'](a, d)
        assert 'failed' in msg


class TestRecoverRestBranches:
    def test_recover_caps_at_max_hp(self):
        a = make_pkmn(name='A', hp=180, max_hp=200)
        msg = MOVE_HANDLERS['Recover'](a, make_pkmn(name='B'))
        assert a.hp == 200
        assert 'restores half' in msg

    def test_rest_clears_status_and_temp(self):
        a = make_pkmn(
            name='A', hp=100, max_hp=200,
            status=EffectStatus.BURN, temp_status=EffectStatus.CONFUSION,
        )
        msg = MOVE_HANDLERS['Rest'](a, make_pkmn(name='B'))
        assert a.status == EffectStatus.SLEEP
        assert a.temp_status is None
        assert a.hp == 200
        assert 'regained health' in msg


class TestSubstituteBranches:
    def test_already_protected(self):
        a = make_pkmn(name='A', substitute=True)
        msg = MOVE_HANDLERS['Substitute'](a, make_pkmn(name='B'))
        assert 'already protected' in msg


class TestAtkEffectivenessMessages:
    def test_not_very_effective(self, monkeypatch):
        a = make_pkmn(name='A', typing=[Typing.NORMAL], attack=50)
        d = make_pkmn(name='B', typing=[Typing.ROCK], defense=50)
        move = make_move(name='Tackle', typing=Typing.NORMAL, power=40)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = atk(a, move, d)
        assert "It's not very effective" in msg


class TestDrainHealCap:
    def test_absorb_heal_capped(self, monkeypatch):
        a = make_pkmn(name='A', hp=199, max_hp=200, sp_atk=50)
        d = make_pkmn(name='B', hp=200, defense=50, sp_def=50, typing=[Typing.GRASS])
        move = make_move(
            name='Absorb', typing=Typing.GRASS, power=40,
            category=MoveCategory.SPECIAL,
        )
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = atk(a, move, d)
        assert a.hp == 200
        assert 'Sucked health' in msg

    def test_dream_eater_heal_capped(self, monkeypatch):
        a = make_pkmn(name='A', hp=199, max_hp=200, sp_atk=50)
        d = make_pkmn(name='B', hp=200, defense=50, sp_def=50, status=EffectStatus.SLEEP)
        move = make_move(
            name='Dream Eater', typing=Typing.PSYCHIC, power=100,
            category=MoveCategory.SPECIAL,
        )
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = atk(a, move, d)
        assert a.hp == 200
        assert 'dream was eaten' in msg


class TestConfusionSelfHitFaint:
    def test_self_hit_faints(self, monkeypatch):
        a = make_pkmn(
            name='A', hp=1, max_hp=200, attack=50, defense=50,
            temp_status=EffectStatus.CONFUSION, confused_turns=3,
        )
        d = make_pkmn(name='B', hp=200, defense=50)
        move = make_move(name='Tackle', power=40)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        monkeypatch.setattr(random, 'random', lambda: 0.1)
        msg = atk(a, move, d)
        assert 'fainted' in msg
        assert a.fainted


class TestStatusMoveDispatch:
    def test_atk_dispatches_status_move(self, monkeypatch):
        a = make_pkmn(name='A')
        d = make_pkmn(name='B', defense=100)
        move = make_move(name='Growl', power=0, category=MoveCategory.NON_DAMAGING)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = atk(a, move, d)
        assert 'went down' in msg
        assert d.atk_mult == -1


class TestJumpKickMiss:
    def test_jump_kick_misses_self_damage(self, monkeypatch):
        a = make_pkmn(name='A', hp=200)
        d = make_pkmn(name='B', defense=100)
        move = make_move(name='Jump Kick', power=70, accuracy=95)
        monkeypatch.setattr(random, 'randint', lambda a, b: 255)
        msg = atk(a, move, d)
        assert 'lost its poise' in msg
        assert a.hp == 199


class TestBurnPoisonPoisonBranch:
    def test_player_poison_message(self):
        p = make_pkmn(name='P', hp=200, status=EffectStatus.POISON)
        e = make_pkmn(name='E', hp=200)
        msg = handle_burn_poison(p, e)
        assert 'hurt by poison' in msg
        assert 'hurt by its burn' not in msg

    def test_enemy_poison_message(self):
        p = make_pkmn(name='P', hp=200)
        e = make_pkmn(name='E', hp=200, status=EffectStatus.POISON)
        msg = handle_burn_poison(p, e)
        assert 'E is hurt by poison' in msg

    def test_enemy_burn_message(self):
        p = make_pkmn(name='P', hp=200)
        e = make_pkmn(name='E', hp=200, status=EffectStatus.BURN)
        msg = handle_burn_poison(p, e)
        assert 'E is hurt by its burn' in msg


class TestToxicityEnemy:
    def test_enemy_toxic_damage(self):
        p = make_pkmn(name='P', hp=200)
        e = make_pkmn(name='E', hp=200, status=EffectStatus.TOXIC)
        msg = handle_toxicity(p, e)
        assert 'hurt by toxine' in msg
        assert e.hp < 200

    def test_enemy_toxic_caps(self):
        p = make_pkmn(name='P', hp=200)
        e = make_pkmn(name='E', hp=200, status=EffectStatus.TOXIC, toxic_turns=50)
        msg = handle_toxicity(p, e)
        assert 'hurt by toxine' in msg
        assert e.hp == 188


class TestLeechSeedEnemyCap:
    def test_player_heal_capped_when_enemy_seeded(self):
        p = make_pkmn(name='P', hp=199, max_hp=200)
        e = make_pkmn(name='E', hp=200, seeded=True)
        msg = handle_leech_seed(p, e)
        assert p.hp == 200
        assert 'saps E' in msg
