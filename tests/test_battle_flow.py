from __future__ import annotations

from unittest.mock import MagicMock

from app.core.battle_flow import do_ai_turn, exec_move, exec_switch, forfeit, switch_valid
from app.core.battle_system import TurnBattleSystem
from app.core.player import Trainer
from tests.conftest import make_move, make_pkmn


def _make_bs() -> TurnBattleSystem:
    player = Trainer()
    ai = Trainer()
    bs = TurnBattleSystem(player, ai)
    bs.player.team = [make_pkmn(name='Mon0'), make_pkmn(name='Mon1')] + [None] * 4
    bs.ai.team = [make_pkmn(name='Rival')] + [None] * 5
    player.in_battle = bs.player.team[0]
    ai.in_battle = bs.ai.team[0]
    bs.player_mon = player.in_battle
    bs.enemy_mon = ai.in_battle
    return bs


class TestSwitchValid:
    def test_none_slot_invalid(self):
        bs = _make_bs()
        assert switch_valid(bs, 2) == 'Invalid slot.'

    def test_fainted_invalid(self):
        bs = _make_bs()
        bs.player.team[1].fainted = True
        assert switch_valid(bs, 1) == 'Mon1 is fainted!'

    def test_already_on_field_invalid(self):
        bs = _make_bs()
        assert switch_valid(bs, 0) == 'Mon0 is already on the field!'

    def test_trapped_invalid(self):
        bs = _make_bs()
        bs.player.in_battle.trapped = True
        assert switch_valid(bs, 1) == "Mon0 is trapped and can't switch!"

    def test_valid_returns_none(self):
        bs = _make_bs()
        assert switch_valid(bs, 1) is None


class TestExecSwitch:
    def test_swaps_active_and_message(self):
        bs = _make_bs()
        old = bs.player.in_battle
        target = bs.player.team[1]
        old.on_field = True

        exec_switch(bs, 1)

        assert bs.player.in_battle is target
        assert target.on_field is True
        assert old.on_field is False
        assert bs.player_msg == 'Go, Mon1!'

    def test_resets_battle_state(self):
        bs = _make_bs()
        old = bs.player.in_battle
        old.substitute = True
        old.temp_status = 'confused'
        old.biding = True
        old.bide_damage = 30
        old.bide_turns = 2
        old.trapped = True
        old.trapped_turns = 1
        old.last_damage_taken = 25
        old.last_move_was_physical = True
        old.atk_mult = 3
        old.def_mult = 2

        exec_switch(bs, 1)

        assert old.substitute is False
        assert old.temp_status is None
        assert old.biding is False
        assert old.bide_damage == 0
        assert old.bide_turns == 0
        assert old.trapped is False
        assert old.trapped_turns == 0
        assert old.last_damage_taken == 0
        assert old.last_move_was_physical is False
        assert old.atk_mult == 0
        assert old.def_mult == 0


class TestExecMove:
    def test_none_slot(self):
        bs = _make_bs()
        bs.player.in_battle.moves = [None, None, None, None]
        assert exec_move(bs, 0) is False
        assert bs.player_msg == 'No move in that slot.'

    def test_fainted(self):
        bs = _make_bs()
        bs.player.in_battle.fainted = True
        move = make_move(name='Tackle')
        bs.player.in_battle.moves = [move, None, None, None]
        assert exec_move(bs, 0) is False
        assert 'fainted' in bs.player_msg

    def test_struggle_when_all_no_pp(self):
        bs = _make_bs()
        move = make_move(name='Tackle', pp=0)
        bs.player.in_battle.moves = [move, None, None, None]
        assert exec_move(bs, 0) is True
        assert 'Struggle' in bs.player_msg

    def test_no_pp_partial_returns_false(self):
        bs = _make_bs()
        m1 = make_move(name='Tackle', pp=0)
        m2 = make_move(name='Growl', pp=10)
        bs.player.in_battle.moves = [m1, m2, None, None]
        assert exec_move(bs, 0) is False
        assert bs.player_msg == 'No PP left for this move!'

    def test_valid_executes_and_switches(self):
        bs = _make_bs()
        move = make_move(name='Tackle', pp=35)
        bs.player.in_battle.moves = [move, None, None, None]
        bs.player.token = True

        assert exec_move(bs, 0) is True
        assert bs.player.token is False
        assert bs.turn_count == 2


class TestDoAiTurn:
    def test_ai_turn_handles(self):
        bs = _make_bs()
        bs.player.token = False
        bs.ai.token = True
        bs.handle_turns = MagicMock()

        do_ai_turn(bs)

        bs.handle_turns.assert_called_once_with()

    def test_player_turn_does_nothing(self):
        bs = _make_bs()
        bs.player.token = True
        bs.ai.token = False
        bs.handle_turns = MagicMock()

        do_ai_turn(bs)

        bs.handle_turns.assert_not_called()


class TestForfeit:
    def test_wipes_player_team(self):
        bs = _make_bs()
        forfeit(bs)
        assert bs.player.team == [None] * 6
        assert bs.player.game_over_lose() is True
