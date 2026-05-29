from __future__ import annotations

from unittest.mock import MagicMock

from app.core.player import Trainer
from app.schemas.action import ActionKind
from app.schemas.battle_pokemon import BattlePokemon
from tests.conftest import make_move, make_pkmn


class TestTrainerInit:
    def test_creates_six_pokemon(self, monkeypatch):
        monkeypatch.setattr('app.core.player.random.choice', lambda _: MagicMock(id=1, name='Test'))
        monkeypatch.setattr('app.core.player.BattlePokemon.from_template', lambda _: make_pkmn())
        t = Trainer()
        assert len([p for p in t.team if p is not None]) == 6
        assert all(isinstance(p, BattlePokemon) for p in t.team)

    def test_first_is_in_battle(self, monkeypatch):
        monkeypatch.setattr('app.core.player.random.choice', lambda _: MagicMock(id=1, name='Test'))
        monkeypatch.setattr('app.core.player.BattlePokemon.from_template', lambda _: make_pkmn())
        t = Trainer()
        assert t.in_battle is t.team[0]
        assert t.team[0].on_field is True

    def test_is_ai_with_strategy(self):
        strategy = MagicMock()
        t = Trainer(strategy)
        assert t.is_ai is True

    def test_is_ai_without_strategy(self):
        t = Trainer()
        assert t.is_ai is False

    def test_none_team_slots(self):
        t = Trainer()
        assert len(t.team) == 6
        assert all(p is not None for p in t.team)


class TestGameOverLose:
    def test_all_fainted(self):
        t = Trainer()
        t.team = [make_pkmn(fainted=True) for _ in range(6)]
        assert t.game_over_lose() is True

    def test_some_alive(self):
        t = Trainer()
        t.team = [make_pkmn(fainted=True) for _ in range(5)]
        t.team.append(make_pkmn(fainted=False))
        assert t.game_over_lose() is False

    def test_all_none(self):
        t = Trainer()
        t.team = [None] * 6
        assert t.game_over_lose() is True

    def test_mixed_none_and_alive(self):
        t = Trainer()
        t.team = [None, None, make_pkmn(fainted=False), None, None, None]
        assert t.game_over_lose() is False

    def test_mixed_none_and_fainted(self):
        t = Trainer()
        t.team = [make_pkmn(fainted=True), None, make_pkmn(fainted=False), None, None, None]
        assert t.game_over_lose() is False


class TestTurn:
    def test_set_turn_none(self):
        t = Trainer()
        assert t.is_turn() is None

    def test_set_turn_true(self):
        t = Trainer()
        t.set_turn(True)
        assert t.is_turn() is True

    def test_set_turn_false(self):
        t = Trainer()
        t.set_turn(False)
        assert t.is_turn() is False

    def test_set_turn_overwrites(self):
        t = Trainer()
        t.set_turn(True)
        t.set_turn(False)
        assert t.is_turn() is False


class TestGetPossibleChoices:
    def test_returns_actions_for_moves_with_pp(self):
        t = Trainer()
        move = make_move(name='Tackle', pp=35)
        t.in_battle.moves = [move, None, None, None]
        choices = t.get_possible_choices()
        assert len(choices) == 1
        assert choices[0].kind == ActionKind.ATTACK
        assert choices[0].target is move

    def test_skips_none_moves(self):
        t = Trainer()
        t.in_battle.moves = [None, None, None, None]
        assert t.get_possible_choices() == []

    def test_skips_zero_pp(self):
        t = Trainer()
        move = make_move(name='Tackle', pp=0)
        t.in_battle.moves = [move, None, None, None]
        assert t.get_possible_choices() == []

    def test_multiple_moves(self):
        t = Trainer()
        m1 = make_move(name='Tackle', pp=35)
        m2 = make_move(name='Growl', pp=40)
        t.in_battle.moves = [m1, m2, None, None]
        choices = t.get_possible_choices()
        assert len(choices) == 2


class TestVerifyFaintedSwitch:
    def test_switches_to_first_alive(self):
        t = Trainer()
        alive = make_pkmn(name='B', fainted=False)
        t.team = [
            make_pkmn(name='A', fainted=True), alive, make_pkmn(fainted=False),
            None, None, None,
        ]
        t.in_battle = t.team[0]
        t.in_battle.on_field = True
        t.verify_fainted_switch()
        assert t.in_battle is alive
        assert t.team[0].on_field is False
        assert alive.on_field is True

    def test_all_fainted_does_nothing(self):
        t = Trainer()
        t.team = [make_pkmn(fainted=True) for _ in range(6)]
        t.in_battle = t.team[0]
        t.verify_fainted_switch()
        assert t.in_battle is t.team[0]

    def test_not_fainted_does_nothing(self):
        t = Trainer()
        t.team = [make_pkmn(fainted=False) for _ in range(6)]
        t.in_battle = t.team[0]
        t.team[0].on_field = True
        t.verify_fainted_switch()
        assert t.in_battle is t.team[0]
        assert t.team[0].on_field is True

    def test_skips_none_slots(self):
        t = Trainer()
        alive = make_pkmn(name='B', fainted=False)
        t.team = [make_pkmn(name='A', fainted=True), None, alive, None, None, None]
        t.in_battle = t.team[0]
        t.in_battle.on_field = True
        t.verify_fainted_switch()
        assert t.in_battle is alive
        assert alive.on_field is True

    def test_skips_fainted_and_none(self):
        t = Trainer()
        alive = make_pkmn(name='C', fainted=False)
        t.team = [
            make_pkmn(name='A', fainted=True), make_pkmn(name='B', fainted=True),
            alive, None, None, None,
        ]
        t.in_battle = t.team[0]
        t.in_battle.on_field = True
        t.verify_fainted_switch()
        assert t.in_battle is alive


class TestGetChoice:
    def test_with_strategy_delegates(self):
        strategy = MagicMock()
        strategy.get_choice.return_value = 'Used Tackle!'
        t = Trainer(strategy)
        rival = Trainer()
        result = t.get_choice(rival)
        strategy.get_choice.assert_called_once_with(t, rival)
        assert result == 'Used Tackle!'

    def test_without_strategy_returns_none(self):
        t = Trainer()
        rival = Trainer()
        assert t.get_choice(rival) is None
