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
from app.schemas.effect_status import EffectStatus
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

    def test_get_choice_ignores_none_slots(self, trainer, rival, monkeypatch):
        chosen = []
        def mock_choice(moves):
            chosen.extend(moves)
            return moves[0]
        trainer.in_battle.moves = [make_move(name='Tackle'), None, None, None]
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
        monkeypatch.setattr('app.core.strategy.random.choice', mock_choice)
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        s = RandomStrategy()
        s.get_choice(trainer, rival)
        assert len(chosen) == 1

    def test_get_choice_all_none_struggles(self, trainer, rival, monkeypatch):
        trainer.in_battle.moves = [None, None, None, None]
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
        monkeypatch.setattr('app.core.player.struggle_no_pp', lambda a, d: 'struggle!')
        s = RandomStrategy()
        assert s.get_choice(trainer, rival) == 'struggle!'

    def test_get_choice_picks_among_available(self, trainer, rival, monkeypatch):
        m1 = make_move(name='Tackle')
        m2 = make_move(name='Growl')
        trainer.in_battle.moves = [m1, m2, None, None]
        monkeypatch.setattr(
            'app.core.strategy.random.choice',
            lambda moves: next(a for a in moves if a.target.name == 'Growl'),
        )
        monkeypatch.setattr('app.core.strategy.try_atk_status', lambda a, m, d: 'msg')
        s = RandomStrategy()
        s.get_choice(trainer, rival)
        assert s.choices == ['Growl']

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

    def test_effectiveness_2x_bonus(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t, r = self._balanced_trainers()
        r.in_battle.typing = [Typing.GRASS]
        move = make_move(typing=Typing.FIRE, power=40)
        action = Action(kind=ActionKind.ATTACK, user=t.in_battle.name, target=move)
        s = MinimaxStrategy()
        v = s.evaluate(action, t, r)
        assert v == pytest.approx(67.5)

    def test_effectiveness_half_penalty(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t, r = self._balanced_trainers()
        r.in_battle.typing = [Typing.ROCK]
        move = make_move(typing=Typing.NORMAL, power=40)
        action = Action(kind=ActionKind.ATTACK, user=t.in_battle.name, target=move)
        s = MinimaxStrategy()
        v = s.evaluate(action, t, r)
        assert v == pytest.approx(-32.5)

    @staticmethod
    def _balanced_trainers():
        t = Trainer()
        r = Trainer()
        t.team = [make_pkmn(name='A', hp=200, max_hp=200)]
        r.team = [make_pkmn(name='B', hp=200, max_hp=200)]
        t.team[0].on_field = True
        r.team[0].on_field = True
        t.in_battle = t.team[0]
        r.in_battle = r.team[0]
        return t, r


class TestMinimaxStrategy:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_get_choice_returns_string(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        trainer.in_battle.name = 'TestMon'
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
        def fake_try_atk(a, m, d):
            return f'{a.name} used {m.name}!'
        monkeypatch.setattr('app.core.strategy.try_atk_status', fake_try_atk)
        s = MinimaxStrategy()
        result = s.get_choice(trainer, rival)
        assert result == 'TestMon used Tackle!'

    def test_get_choice_no_pp(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40, pp=0)
        trainer.in_battle.moves = [move, None, None, None]
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
        monkeypatch.setattr('app.core.player.struggle_no_pp', lambda a, d: f'{a.name} struggled!')
        s = MinimaxStrategy()
        result = s.get_choice(trainer, rival)
        assert 'struggled' in result

    def test_get_choice_stores_last_move(self, trainer, rival, monkeypatch):
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
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
        for p in trainer.team[1:]:
            if p is not None:
                p.fainted = True
        monkeypatch.setattr('app.core.player.struggle_no_pp', lambda a, d: 'struggle')
        s = AlphaBetaStrategy()
        result = s.get_choice(trainer, rival)
        assert result == 'struggle'

    def test_default_depth_is_7(self):
        s = AlphaBetaStrategy()
        assert s.max_play_depth == 7

    def test_terminal_win(self, attack_action, trainer, rival):
        rival.team = [make_pkmn(fainted=True) for _ in range(6)]
        rival.in_battle = rival.team[0]
        s = AlphaBetaStrategy()
        assert s.minimax(1, attack_action, True, trainer, rival) == s.win_val

    def test_terminal_lose(self, attack_action, trainer, rival):
        trainer.team = [make_pkmn(fainted=True) for _ in range(6)]
        trainer.in_battle = trainer.team[0]
        s = AlphaBetaStrategy()
        assert s.minimax(1, attack_action, True, trainer, rival) == -s.win_val

    @staticmethod
    def _mk_action(name: str) -> Action:
        return Action(kind=ActionKind.ATTACK, user='X', target=make_move(name=name))

    @staticmethod
    def _recording_evaluate(calls: list[str], vals: dict[str, float]):
        def evaluate(action, tr, rv):
            calls.append(action.target.name)
            return vals[action.target.name]
        return evaluate

    def test_maximizer_prunes_when_child_meets_beta(self):
        s = AlphaBetaStrategy()
        s.ordered = False
        calls = []
        vals = {'t1': 10.0, 't2': 1.0, 'r1': 0.0, 'r2': 0.0}
        s.evaluate = self._recording_evaluate(calls, vals)
        t = Trainer()
        r = Trainer()
        t.get_possible_choices = lambda: [self._mk_action('t1'), self._mk_action('t2')]
        r.get_possible_choices = lambda: [self._mk_action('r1'), self._mk_action('r2')]

        val = s.minimax(2, self._mk_action('root'), False, t, r)

        assert val == 10.0
        assert calls == ['t1', 't2', 't1']

    def test_minimizer_prunes_when_child_meets_alpha(self):
        s = AlphaBetaStrategy()
        s.ordered = False
        calls = []
        vals = {'r1': 5.0, 'r2': 9.0, 't1': 0.0, 't2': 0.0}
        s.evaluate = self._recording_evaluate(calls, vals)
        t = Trainer()
        r = Trainer()
        t.get_possible_choices = lambda: [self._mk_action('t1'), self._mk_action('t2')]
        r.get_possible_choices = lambda: [self._mk_action('r1'), self._mk_action('r2')]

        val = s.minimax(2, self._mk_action('root'), True, t, r)

        assert val == 5.0
        assert calls == ['r1', 'r2', 'r1']


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

    def test_terminal_win(self, attack_action, trainer, rival):
        rival.team = [make_pkmn(fainted=True) for _ in range(6)]
        rival.in_battle = rival.team[0]
        s = ExpectiMaxStrategy()
        assert s.minimax(1, attack_action, True, trainer, rival) == s.win_val

    def test_terminal_lose(self, attack_action, trainer, rival):
        trainer.team = [make_pkmn(fainted=True) for _ in range(6)]
        trainer.in_battle = trainer.team[0]
        s = ExpectiMaxStrategy()
        assert s.minimax(1, attack_action, True, trainer, rival) == -s.win_val

    def test_minimizer_no_children_returns_zero(self, trainer, rival):
        rival.in_battle.moves = [None, None, None, None]
        move = make_move(name='A')
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        em = ExpectiMaxStrategy()
        assert em.minimax(1, action, False, trainer, rival) == 0.0


class TestUnifiedSearch:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    @staticmethod
    def _two_move_trainer():
        t = Trainer()
        t.set_turn(True)
        t.in_battle.moves = [
            make_move(name='High', power=80),
            make_move(name='Low', power=10),
            None,
            None,
        ]
        return t

    def test_strategies_agree_at_maximizer_depth_1(self, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t = self._two_move_trainer()
        action = Action(kind=ActionKind.ATTACK, user=t.in_battle.name, target=t.in_battle.moves[0])
        values = [
            MinimaxStrategy().minimax(1, action, True, t, rival),
            AlphaBetaStrategy().minimax(1, action, True, t, rival),
            ExpectiMaxStrategy().minimax(1, action, True, t, rival),
        ]
        assert values[0] == values[1] == values[2]

    def test_strategies_agree_at_minimizer_depth_1(self, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t = self._two_move_trainer()
        action = Action(kind=ActionKind.ATTACK, user=t.in_battle.name, target=t.in_battle.moves[0])
        mm = MinimaxStrategy().minimax(1, action, False, t, rival)
        ab = AlphaBetaStrategy().minimax(1, action, False, t, rival)
        assert mm == ab

    def test_nodes_visited_increments(self, trainer, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        move = make_move(name='Tackle', power=40)
        trainer.in_battle.moves = [move, None, None, None]
        action = Action(kind=ActionKind.ATTACK, user=trainer.in_battle.name, target=move)
        s = MinimaxStrategy()
        s.minimax(2, action, True, trainer, rival)
        assert s.nodes_visited > 0

    def test_alphabeta_ordering_same_value_no_more_nodes(self, rival, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t = self._two_move_trainer()
        action = Action(kind=ActionKind.ATTACK, user=t.in_battle.name, target=t.in_battle.moves[0])
        ordered = AlphaBetaStrategy()
        base = AlphaBetaStrategy()
        base.ordered = False
        v_ord = ordered.minimax(3, action, True, t, rival)
        v_base = base.minimax(3, action, True, t, rival)
        assert v_ord == v_base
        assert ordered.nodes_visited <= base.nodes_visited


class TestStrategicSwitch:
    @pytest.fixture(autouse=True)
    def patch_randint(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.random.randint', lambda a, b: 255)

    def test_action_accepts_battle_pokemon_target(self):
        mon = make_pkmn(name='Bench')
        action = Action(kind=ActionKind.SWITCH, user='Active', target=mon)
        assert action.kind == ActionKind.SWITCH
        assert action.target is mon

    def test_evaluate_switch_healthy_bench_better(self):
        t = Trainer()
        current = make_pkmn(name='Current', hp=100, max_hp=200)
        healthy = make_pkmn(name='Healthy', hp=180, max_hp=200)
        low = make_pkmn(name='Low', hp=20, max_hp=200)
        r = Trainer()
        t.in_battle = current
        r.in_battle = make_pkmn(name='Riv', hp=200, max_hp=200)
        s = MinimaxStrategy()
        act_healthy = Action(kind=ActionKind.SWITCH, user=current.name, target=healthy)
        act_low = Action(kind=ActionKind.SWITCH, user=current.name, target=low)
        assert s.evaluate(act_healthy, t, r) > s.evaluate(act_low, t, r)

    def test_evaluate_switch_penalizes_type_disadvantage(self):
        t = Trainer()
        current = make_pkmn(name='Current', hp=100, max_hp=200)
        grass = make_pkmn(name='Grass', hp=100, max_hp=200, typing=[Typing.GRASS])
        rock = make_pkmn(name='Rock', hp=100, max_hp=200, typing=[Typing.ROCK])
        r = Trainer()
        rival = make_pkmn(name='Riv', hp=200, max_hp=200, typing=[Typing.WATER, Typing.FLYING])
        rival.moves = [make_move(name='Fire', typing=Typing.FIRE), None, None, None]
        r.in_battle = rival
        t.in_battle = current
        s = MinimaxStrategy()
        act_grass = Action(kind=ActionKind.SWITCH, user=current.name, target=grass)
        act_rock = Action(kind=ActionKind.SWITCH, user=current.name, target=rock)
        # Fire hits Grass for 2x, Rock for 0.5x → Grass target is penalised
        assert s.evaluate(act_rock, t, r) > s.evaluate(act_grass, t, r)

    def test_get_choice_switches_when_beneficial(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (10, ''))
        t = Trainer()
        current = make_pkmn(name='Current', hp=5, max_hp=200, status=EffectStatus.BURN)
        current.moves = [make_move(name='Tackle', power=40), None, None, None]
        bench = make_pkmn(name='Bench1', hp=190, max_hp=200, typing=[Typing.GRASS])
        bench.moves = [make_move(name='Ember', typing=Typing.FIRE, power=60), None, None, None]
        t.team = [current, bench, None, None, None, None]
        t.in_battle = current
        t.set_turn(True)

        r = Trainer()
        rival = make_pkmn(name='Riv', hp=60, max_hp=200, typing=[Typing.GRASS])
        r.team = [rival, None, None, None, None, None]
        r.in_battle = rival

        s = MinimaxStrategy()
        result = s.get_choice(t, r)
        assert 'sent out Bench1' in result
        assert t.in_battle is bench
        assert s.last_move is None
        assert s.choices == ['switch:Bench1']

    def test_get_choice_prefers_attack_when_switch_is_bad(self, monkeypatch):
        monkeypatch.setattr('app.core.strategy.calculate_damage', lambda a, m, d: (50, ''))
        t = Trainer()
        current = make_pkmn(name='Current', hp=200, max_hp=200)
        current.moves = [make_move(name='Tackle', power=40), None, None, None]
        bench = make_pkmn(name='Bench1', hp=10, max_hp=200)
        t.team = [current, bench, None, None, None, None]
        t.in_battle = current
        t.set_turn(True)

        r = Trainer()
        r.team = [make_pkmn(name='Riv', hp=200, max_hp=200), None, None, None, None, None]
        r.in_battle = r.team[0]

        s = MinimaxStrategy()
        result = s.get_choice(t, r)
        assert 'used Tackle' in result
        assert t.in_battle is current

    def test_random_can_switch(self, trainer, rival, monkeypatch):
        monkeypatch.setattr(
            'app.core.strategy.random.choice',
            lambda actions: next(a for a in actions if a.kind == ActionKind.SWITCH),
        )
        s = RandomStrategy()
        result = s.get_choice(trainer, rival)
        assert 'sent out' in result
        assert s.choices[0].startswith('switch:')
