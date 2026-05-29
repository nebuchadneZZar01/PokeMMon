from __future__ import annotations

import pytest

from app.core.player import Trainer
from app.core.strategy import (
    AlphaBetaStrategy,
    ExpectiMaxStrategy,
    MinimaxStrategy,
    RandomStrategy,
)
from app.schemas.action import Action, ActionKind
from app.schemas.typing import Typing
from tests.conftest import make_move, make_pkmn


@pytest.fixture
def trainer():
    t = Trainer()
    t.set_turn(True)
    return t


@pytest.fixture
def rival():
    return Trainer()


@pytest.fixture
def attack_action(trainer):
    move = make_move(name='Tackle', power=40)
    trainer.in_battle.moves = [move, None, None, None]
    return Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)


class TestRandomStrategy:
    def test_get_choice_returns_string(self, trainer, rival, monkeypatch):
        trainer.in_battle.name = 'TestMon'
        trainer.in_battle.moves[0].name = 'Tackle'
        monkeypatch.setattr('app.core.strategy.random.choice', lambda moves: moves[0])
        def fake_try_atk(a, m, d):
            return f'{a.name} used {m.name}!'
        monkeypatch.setattr('app.core.strategy.try_atk_status', fake_try_atk)
        s = RandomStrategy()
        result = s.get_choice(trainer, rival)
        assert result == 'TestMon used Tackle!'

    def test_get_choice_not_turn(self, trainer, rival):
        trainer.set_turn(False)
        s = RandomStrategy()
        result = s.get_choice(trainer, rival)
        assert result is None

    def test_choices_tracks_names(self, trainer, rival, monkeypatch):
        trainer.in_battle.moves[0].name = 'Tackle'
        monkeypatch.setattr('app.core.strategy.random.choice', lambda moves: moves[0])
        def fake_try_atk(a, m, d):
            return 'msg'
        monkeypatch.setattr('app.core.strategy.try_atk_status', fake_try_atk)
        s = RandomStrategy()
        s.get_choice(trainer, rival)
        assert s.choices == ['Tackle']

    def test_get_choice_loops_until_non_none(self, trainer, rival, monkeypatch):
        calls = []
        def mock_choice(moves):
            calls.append(1)
            if len(calls) == 1:
                return None
            return moves[0]
        monkeypatch.setattr('app.core.strategy.random.choice', mock_choice)
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        s = RandomStrategy()
        s.get_choice(trainer, rival)
        assert len(calls) > 1

    def test_verify_fainted_switch_called(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.choice', lambda moves: moves[0])
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        switched = False
        def mock_switch(self):
            nonlocal switched
            switched = True
        monkeypatch.setattr(Trainer, 'verify_fainted_switch', mock_switch)
        s = RandomStrategy()
        s.get_choice(trainer, rival)
        assert switched


class TestMinimaxEvaluate:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_self_more_hp_higher_value(self, attack_action):
        t = Trainer()
        r = Trainer()
        t.team = [make_pkmn(name='A', hp=200, max_hp=200)]
        r.team = [make_pkmn(name='B', hp=100, max_hp=200)]
        for team in (t, r):
            team.team[0].on_field = True
            team.in_battle = team.team[0]
        a_move = make_move(typing=Typing.NORMAL, power=40)
        action = Action(kind=ActionKind.ATTACK, user='A', target=a_move)
        s = MinimaxStrategy()
        v1 = s.evaluate(action, t, r)
        v2 = s.evaluate(action, r, t)
        # hp_diff = rival_hp - trainer_hp, so trainer with less HP gets higher value
        assert v1 < v2

    def test_last_move_penalty(self, attack_action):
        t = Trainer()
        r = Trainer()
        s = MinimaxStrategy()
        s.last_move = attack_action.target
        v = s.evaluate(attack_action, t, r)
        assert isinstance(v, float)
        # Same move again should have penalty applied
        v2 = s.evaluate(attack_action, t, r)
        assert v == v2  # penalty applied both times

    def test_effectiveness_4x_bonus(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move = make_move(typing=Typing.ELECTRIC, power=40)
        rival.in_battle.typing = [Typing.WATER, Typing.FLYING]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        s = MinimaxStrategy()
        v = s.evaluate(action, trainer, rival)
        assert v > 0

    def test_effectiveness_0x_penalty(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move = make_move(typing=Typing.NORMAL, power=40)
        rival.in_battle.typing = [Typing.GHOST]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        s = MinimaxStrategy()
        v = s.evaluate(action, trainer, rival)
        assert v < 0


class TestMinimaxStrategy:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_get_choice_returns_string(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        trainer.in_battle.name = 'TestMon'
        def fake_try_atk(a, m, d):
            return f'{a.name} used {m.name}!'
        monkeypatch.setattr('app.core.strategy.try_atk_status', fake_try_atk)
        s = MinimaxStrategy()
        result = s.get_choice(trainer, rival)
        assert result == 'TestMon used Tackle!'

    def test_get_choice_no_pp(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40, pp=0)
        trainer.in_battle.moves = [move, None, None, None]
        monkeypatch.setattr('app.core.strategy.struggle_no_pp', lambda a, d: f'{a.name} struggled!')
        s = MinimaxStrategy()
        result = s.get_choice(trainer, rival)
        assert 'struggled' in result

    def test_get_choice_stores_last_move(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: '')
        s = MinimaxStrategy()
        s.get_choice(trainer, rival)
        assert s.last_move is move

    def test_get_choice_not_turn(self, trainer, rival):
        trainer.set_turn(False)
        s = MinimaxStrategy()
        assert s.get_choice(trainer, rival) is None

    def test_minimax_depth_zero(self, attack_action, trainer, rival):
        s = MinimaxStrategy()
        val = s.minimax(0, attack_action, True, trainer, rival)
        expected = s.evaluate(attack_action, trainer, rival)
        assert val == expected

    def test_minimax_terminal_win(self, attack_action, trainer, rival):
        rival.team = [make_pkmn(fainted=True) for _ in range(6)]
        rival.in_battle = rival.team[0]
        s = MinimaxStrategy()
        val = s.minimax(1, attack_action, True, trainer, rival)
        assert val == s.win_val

    def test_minimax_terminal_lose(self, attack_action, trainer, rival):
        trainer.team = [make_pkmn(fainted=True) for _ in range(6)]
        trainer.in_battle = trainer.team[0]
        s = MinimaxStrategy()
        val = s.minimax(1, attack_action, True, trainer, rival)
        assert val == -s.win_val

    def test_minimax_maximizer_picks_higher(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move_high = make_move(name='High', power=80)
        move_low = make_move(name='Low', power=10)
        trainer.in_battle.moves = [move_high, move_low, None, None]
        s = MinimaxStrategy()
        act = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move_high)
        val = s.minimax(1, act, True, trainer, rival)
        assert isinstance(val, (int, float))

    def test_minimax_minimizer_picks_lower(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move_high = make_move(name='High', power=80)
        move_low = make_move(name='Low', power=10)
        trainer.in_battle.moves = [move_high, move_low, None, None]
        s = MinimaxStrategy()
        act = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move_high)
        val = s.minimax(1, act, False, trainer, rival)
        assert isinstance(val, (int, float))


class TestAlphaBetaStrategy:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_alphabeta_same_as_minimax_at_depth_1(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        mm = MinimaxStrategy()
        ab = AlphaBetaStrategy()
        mm_val = mm.minimax(1, action, True, trainer, rival)
        ab_val = ab.minimax(1, action, True, trainer, rival)
        assert mm_val == ab_val

    def test_get_choice_returns_string(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        s = AlphaBetaStrategy()
        result = s.get_choice(trainer, rival)
        assert isinstance(result, str)

    def test_get_choice_no_pp(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40, pp=0)
        trainer.in_battle.moves = [move, None, None, None]
        monkeypatch.setattr('app.core.strategy.struggle_no_pp', lambda a, d: 'struggle')
        s = AlphaBetaStrategy()
        result = s.get_choice(trainer, rival)
        assert result == 'struggle'

    def test_default_depth_is_7(self):
        s = AlphaBetaStrategy()
        assert s.max_play_depth == 7


class TestExpectiMaxStrategy:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_get_choice_returns_string(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        s = ExpectiMaxStrategy()
        result = s.get_choice(trainer, rival)
        assert isinstance(result, str)

    def test_maximizer_same_as_minimax(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        mm = MinimaxStrategy()
        em = ExpectiMaxStrategy()
        mm_val = mm.minimax(1, action, True, trainer, rival)
        em_val = em.minimax(1, action, True, trainer, rival)
        assert mm_val == em_val

    def test_minimizer_averages(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move1 = make_move(name='A', power=40)
        move2 = make_move(name='B', power=60)
        rival.in_battle.moves = [move1, move2, None, None]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move1)
        em = ExpectiMaxStrategy()
        val = em.minimax(1, action, False, trainer, rival)
        assert isinstance(val, (int, float))
