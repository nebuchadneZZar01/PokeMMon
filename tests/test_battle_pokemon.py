from __future__ import annotations

import logging

from app.data.moves import COMPAT_MOVES, is_compatible
from app.data.pokedex import pokedex
from app.schemas.battle_pokemon import BattlePokemon
from tests.conftest import make_move, make_pkmn


class TestFromTemplate:
    def test_default_level_calculates_stats(self):
        tpl = pokedex[0]
        bs = tpl.base_stats

        pkmn = BattlePokemon.from_template(tpl)

        assert pkmn.level == 100
        assert pkmn.max_hp == (bs.hp * 2 * 100 // 100) + 100 + 10
        assert pkmn.hp == pkmn.max_hp
        assert pkmn.typing == tpl.typing

    def test_level_below_one_clamped_to_one(self):
        assert BattlePokemon.from_template(pokedex[0], level=0).level == 1

    def test_level_above_100_clamped_to_100(self):
        assert BattlePokemon.from_template(pokedex[0], level=250).level == 100


class TestLoggingMethods:
    def _bp(self) -> BattlePokemon:
        return make_pkmn(name='Blastoise', hp=150, attack=80)

    def test_get_stats_logs_current_stats(self, caplog):
        with caplog.at_level(logging.DEBUG, logger='app.schemas.battle_pokemon'):
            self._bp().get_stats()
        text = caplog.text
        assert 'Blastoise' in text
        assert 'Type:' in text
        assert 'Hp: 150' in text
        assert 'Atk: 80' in text
        assert 'Spe: 50' in text

    def test_get_stats_mult_logs_multipliers(self, caplog):
        bp = self._bp()
        bp.atk_mult = 2.5
        bp.ev_mult = 0.5
        with caplog.at_level(logging.DEBUG, logger='app.schemas.battle_pokemon'):
            bp.get_stats_mult()
        text = caplog.text
        assert 'Atk: 2.5' in text
        assert 'Ev: 0.5' in text
        assert 'Acc: 0' in text

    def test_get_moves_logs_move_info_and_none_slots(self, caplog, capsys):
        bp = make_pkmn(
            name='Blastoise',
            moves=[make_move(name='Hydro Pump'), None, None, None],
        )
        with caplog.at_level(logging.DEBUG, logger='app.schemas.battle_pokemon'):
            bp.get_moves()
        out = capsys.readouterr().out
        assert 'Hydro Pump' in out
        assert 'Typing:' in out
        assert 'Power: 40' in out
        assert 'None' in caplog.text


class TestIsCompatible:
    def test_known_move_returns_true(self):
        name = pokedex[0].name
        move_name = COMPAT_MOVES[name][0].name
        assert is_compatible(move_name, name) is True

    def test_unknown_move_returns_false(self):
        assert is_compatible('NotAMove', pokedex[0].name) is False

    def test_unknown_pokemon_returns_false(self):
        assert is_compatible('Tackle', 'MissingNo') is False
