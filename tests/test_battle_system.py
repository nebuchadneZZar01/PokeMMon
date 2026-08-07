from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.battle_system import TurnBattleSystem
from app.core.player import Trainer
from app.schemas.effect_status import EffectStatus
from tests.conftest import make_pkmn


@pytest.fixture
def trainers():
    p = Trainer()
    ai = Trainer()
    return p, ai


@pytest.fixture
def bs(trainers):
    p, ai = trainers
    return TurnBattleSystem(p, ai)


class TestInit:
    def test_sets_player_token(self, bs, trainers):
        p, ai = trainers
        assert p.token is True
        assert ai.token is False

    def test_links_mon(self, bs, trainers):
        p, ai = trainers
        assert bs.player_mon is p.in_battle
        assert bs.enemy_mon is ai.in_battle

    def test_turn_count_one(self, bs):
        assert bs.turn_count == 1

    def test_initial_messages(self, bs):
        assert 'challenged' in bs.player_msg
        assert bs.enemy_msg == ''

    def test_stores_references(self, bs, trainers):
        p, ai = trainers
        assert bs.player is p
        assert bs.ai is ai


class TestSwitchTurn:
    def test_player_to_ai(self, bs):
        bs.switch_turn()
        assert bs.player.token is False
        assert bs.ai.token is True

    def test_ai_to_player(self, bs):
        bs.switch_turn()
        bs.switch_turn()
        assert bs.player.token is True
        assert bs.ai.token is False

    def test_increments_count(self, bs):
        bs.switch_turn()
        assert bs.turn_count == 2
        bs.switch_turn()
        assert bs.turn_count == 3


class TestGetTurn:
    def test_player_turn(self, bs):
        assert bs.get_turn() == 'PL'

    def test_ai_turn(self, bs):
        bs.switch_turn()
        assert bs.get_turn() == 'AI'


class TestGetPlayerGetAi:
    def test_get_player(self, bs, trainers):
        assert bs.get_player() is trainers[0]

    def test_get_ai(self, bs, trainers):
        assert bs.get_ai() is trainers[1]


class TestLogMessage:
    def test_starts_empty(self, bs):
        assert bs.message_log == []

    def test_appends_with_round(self, bs):
        bs.log_message('player', 'Pikachu used Thunderbolt!')
        assert bs.message_log == [(1, 'player', 'Pikachu used Thunderbolt!')]

    def test_round_advances_with_turns(self, bs):
        bs.switch_turn()
        bs.log_message('ai', 'Gyarados used Hydro Pump!')
        assert bs.message_log == [(1, 'ai', 'Gyarados used Hydro Pump!')]
        bs.switch_turn()
        bs.log_message('player', 'Pikachu used Thunderbolt!')
        assert bs.message_log[0][0] == 1
        assert bs.message_log[1][0] == 2

    def test_skips_empty(self, bs):
        bs.log_message('player', '')
        bs.log_message('player', '   ')
        assert bs.message_log == []

    def test_skips_duplicate_adjacent(self, bs):
        bs.log_message('player', 'Go, Pikachu!')
        bs.log_message('player', 'Go, Pikachu!')
        assert len(bs.message_log) == 1

    def test_same_text_different_side_logged(self, bs):
        bs.log_message('player', 'It is confused!')
        bs.log_message('ai', 'It is confused!')
        assert len(bs.message_log) == 2

    def test_stale_other_side_does_not_rededup(self, bs):
        bs.log_message('ai', 'Gyarados used Hydro Pump!')
        bs.log_message('player', 'Pikachu used Thunderbolt!')
        bs.log_message('ai', 'Gyarados used Hydro Pump!')
        assert len(bs.message_log) == 2

    def test_repeat_after_new_same_side_message_logged(self, bs):
        bs.log_message('player', 'Go, Pikachu!')
        bs.log_message('player', 'Pikachu used Thunderbolt!')
        bs.log_message('player', 'Go, Pikachu!')
        assert len(bs.message_log) == 3

    def test_caps_at_thirty(self, bs):
        for i in range(40):
            bs.log_message('player', f'msg {i}')
        assert len(bs.message_log) == 30
        assert bs.message_log[0][2] == 'msg 10'
        assert bs.message_log[-1][2] == 'msg 39'


class TestHandleTurns:
    def test_player_game_over_sets_lose_msg(self, bs):
        bs.player.team = [make_pkmn(fainted=True) for _ in range(6)]
        bs.player.in_battle = bs.player.team[0]
        bs.handle_turns()
        assert 'won' in bs.player_msg
        assert 'Player' in bs.player_msg

    def test_ai_game_over_sets_win_msg(self, bs):
        bs.ai.team = [make_pkmn(fainted=True) for _ in range(6)]
        bs.ai.in_battle = bs.ai.team[0]
        bs.handle_turns()
        assert 'lost' in bs.player_msg
        assert 'Player' in bs.player_msg

    def test_ai_turn_calls_get_choice(self, bs):
        mock_strategy = MagicMock()
        mock_strategy.get_choice.return_value = 'AI used move!'
        bs.ai._strategy = mock_strategy
        bs.switch_turn()
        bs.handle_turns()
        assert bs.enemy_msg == 'AI used move!'

    def test_player_turn_does_nothing(self, bs):
        bs.player.token = True
        bs.ai.token = False
        old_msg = bs.enemy_msg
        bs.handle_turns()
        assert bs.enemy_msg == old_msg

    def test_ai_turn_sets_enemy_msg(self, bs):
        mock_strategy = MagicMock()
        mock_strategy.get_choice.return_value = 'AI used move!'
        bs.ai._strategy = mock_strategy
        bs.switch_turn()
        bs.handle_turns()
        assert bs.enemy_msg == 'AI used move!'

    def test_ai_turn_switches_back(self, bs):
        bs.switch_turn()
        bs.handle_turns()
        assert bs.player.token is True

    def test_game_over_does_not_switch(self, bs):
        bs.player.team = [make_pkmn(fainted=True) for _ in range(6)]
        bs.player.in_battle = bs.player.team[0]
        old_turn = bs.turn_count
        bs.handle_turns()
        assert bs.turn_count == old_turn

    def test_game_over_messages_on_both_sides(self, bs):
        bs.player.team = [make_pkmn(fainted=True) for _ in range(6)]
        bs.player.in_battle = bs.player.team[0]
        bs.handle_turns()
        assert bs.enemy_msg != ''


class TestHandleStatusByTurn:
    def test_updates_mon_from_in_battle(self, bs):
        bs.player.in_battle = make_pkmn(name='New')
        bs.handle_status_by_turn()
        assert bs.player_mon is bs.player.in_battle

    def test_no_status_clears_msg(self, bs):
        bs.player_msg = 'old'
        bs.handle_status_by_turn()
        assert bs.player_msg == 'old'

    def test_burn_sets_msg(self, bs):
        pkmn = make_pkmn(hp=200, status=EffectStatus.BURN)
        bs.player.team[0] = pkmn
        bs.player.in_battle = pkmn
        bs.enemy_mon = make_pkmn(hp=200)
        bs.handle_status_by_turn()
        assert 'hurt' in bs.player_msg.lower()

    def test_appends_to_existing_msg(self, bs):
        pkmn = make_pkmn(hp=200, status=EffectStatus.BURN)
        bs.player.team[0] = pkmn
        bs.player.in_battle = pkmn
        bs.enemy_mon = make_pkmn(hp=200)
        bs.player_msg = 'Go, Pikachu!'
        bs.handle_status_by_turn()
        assert 'Go, Pikachu!' in bs.player_msg
        assert 'hurt' in bs.player_msg.lower()

    def test_disable_countdown_expires(self, bs):
        pkmn = make_pkmn(disabled_move=0, disabled_turns=1)
        bs.player.team[0] = pkmn
        bs.player.in_battle = pkmn
        bs.enemy_mon = make_pkmn()
        bs.handle_status_by_turn()
        assert pkmn.disabled_move == -1
        assert pkmn.disabled_turns == 0

    def test_disable_countdown_decrements(self, bs):
        pkmn = make_pkmn(disabled_move=0, disabled_turns=3)
        bs.player.team[0] = pkmn
        bs.player.in_battle = pkmn
        bs.enemy_mon = make_pkmn()
        bs.handle_status_by_turn()
        assert pkmn.disabled_move == 0
        assert pkmn.disabled_turns == 2
