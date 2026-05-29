from app.data.pokedex import pokedex
from app.schemas.pokemon import BattlePokemon
from app.schemas.action import Action, ActionKind
from app.core.combat import calculate_damage, try_atk_status, struggle_no_pp, reset_stats_mult, reset_battle_stats, inc_dec_stat_mult, update_battle_stat
import app.data.pkmn_types as pkmn_types
from app.data.pkmn_types import get_effectiveness
import random

class Trainer:
    """
    Represents a Pokémon Trainer, either human or AI, with a team of six Pokémon.

    Attributes:
        team (list[BattlePokemon | None]): The trainer's team of up to six Pokémon.
        token (bool | None): Turn token indicating whether it is this trainer's turn.
        is_ai (bool): Whether this trainer is controlled by an AI (False for human players).
        in_battle (BattlePokemon): The currently active Pokémon on the field.
    """

    def __init__(self):
        self.team = [None, None, None, None, None, None]    # Trainer Pokemon team

        self.token = None                                   # token used to assingnate actual turn

        self.is_ai = False

        for i in range(len(self.team)):
            tmp = random.choice(pokedex)
            self.team[i] = BattlePokemon.from_template(tmp)

        self.in_battle = self.team[0]
        self.team[0].on_field = True
        
    def get_team_with_stats(self):
        for pkmn in self.team:
            pkmn.get_stats()
            pkmn.get_moves()

    def get_team(self):
        if not self.is_ai:
            print('Player Team:')
        else: print('AI Team:')
        for pkmn in self.team:
            print('- {mon} \t{types}'.format(mon = pkmn.name, types = [t.value for t in pkmn.typing]))

    def get_possible_choices(self):
        possible_choices = [ ]

        for move in self.in_battle.moves:
            if move != None:
                if move.pp > 0:
                    possible_choices.append(Action(kind=ActionKind.ATTACK, user=self.in_battle.name, target=move))

        return possible_choices

    def print_choices(self, choices):
        print('\n{pkmn}\'s possible choices:'.format(pkmn = self.in_battle.name))
        for i in range(len(choices)):
            print('- {index}) name: {move_name},\
                \tpower: {move_power},\
                \ttype: {move_type},\
                \tkind: {move_kind}'.format(index = i+1,\
                move_name = choices[i].target.name,\
                move_power = choices[i].target.power,\
                move_type = choices[i].target.typing.value,\
                move_kind = choices[i].target.category.value))
            
    def game_over_lose(self):
        faint_cnt = 0

        for pkmn in self.team:
            if pkmn.fainted:
                faint_cnt += 1
        
        if faint_cnt == 6:
            return True
        else:
            return False

    def is_turn(self):
        return self.token

    def set_turn(self, _token):
        self.token = _token

class TrainerAI(Trainer):
    """
    Base class for AI-controlled trainers. Provides common utilities such as
    automatically switching in the next non-fainted Pokémon when the current one faints.

    Attributes:
        is_ai (bool): Always True for AI trainers.
    """

    def __init__(self):
        super(TrainerAI, self).__init__()
        self.is_ai = True

    def verify_fainted_switch(self):
        if self.game_over_lose() == False:
            if self.in_battle.fainted == True:
                self.in_battle.on_field = False
                i = 0
                while True:
                    if self.team[i].fainted == True:
                        i += 1
                    else:
                        self.in_battle = self.team[i]
                        self.team[i].on_field = True
                        break

class RandomAI(TrainerAI):
    """
    AI that selects a random move from the current Pokémon's moveset.
    Primarily used for testing and baseline comparison.

    Attributes:
        choices (list[str]): History of chosen move names.
    """

    def __init__(self):
        super(RandomAI, self).__init__()
        self.choices = [ ]

    def get_choice(self, rival):
        target = rival

        if self.is_turn():
            self.verify_fainted_switch()
            move = None
            while move == None: 
                move = random.choice(self.in_battle.moves)
            
            print(move.name)
            self.choices.append(move.name)
            try_atk_status(self.in_battle, move, target)


class MinimaxAI(TrainerAI):
    """
    AI that uses the Minimax algorithm to select the best move by simulating
    the game tree up to a given depth. The AI maximises its evaluation function
    while the opponent tries to minimise it.

    Attributes:
        choices (list[str]): History of chosen actions.
        win_val (int): The value assigned to a winning terminal state.
        max_play_depth (int): Maximum depth of the game tree to explore.
        last_move (Move | None): The last move used; penalised to discourage repetition.
        rival (Trainer): The opposing trainer.
    """

    def __init__(self, rival, max_play_depth = 7):
        super(MinimaxAI, self).__init__()
        self.choices = [ ]
        self.win_val = 1000000
        self.max_play_depth = max_play_depth

        self.last_move = None

        self.rival = rival

    def evaluate(self, action):        
        # self vars
        s_hp = 0
        s_hp_full = 0
        s_stats = 0
        s_status = 0
        s_fainted = 0

        for pkmn in self.team:
            s_hp += pkmn.hp
            s_hp_full += pkmn.max_hp
            s_stats += pkmn.atk_mult + pkmn.def_mult + pkmn.sp_atk_mult + pkmn.sp_def_mult + pkmn.speed_mult + pkmn.acc_mult + pkmn.ev_mult

            if pkmn.status != None and pkmn.fainted == False:
                s_status += 1

            if pkmn.fainted != False:
                s_fainted += 1

        # target vars
        t_hp = 0
        t_hp_full = 0
        t_stats = 0
        t_status = 0
        t_fainted = 0

        for pkmn in self.rival.team:
            t_hp += pkmn.hp
            t_hp_full += pkmn.max_hp
            t_stats += pkmn.atk_mult + pkmn.def_mult + pkmn.sp_atk_mult + pkmn.sp_def_mult + pkmn.speed_mult + pkmn.acc_mult + pkmn.ev_mult

            if pkmn.status != None and pkmn.fainted == False:
                t_status += 1

            if pkmn.fainted != False:
                t_fainted += 1
        
        hp_diff = (s_hp_full - t_hp_full) - (s_hp - t_hp)
        status_diff = t_status - s_status
        stats_diff = s_stats - t_stats
        fainted_diff = t_fainted - s_fainted
        move = action.target
        user = action.user
        move_damage = calculate_damage(self.in_battle, move, self.rival.in_battle)

        print('hp_diff:', hp_diff)
        print('status_diff:', status_diff)
        print('stats_diff:', stats_diff)
        print('fainted_diff:', fainted_diff)
        print('user:', user)
        print('possible move:', move.name)
        print('possible damage:', move_damage)

        value = hp_diff * .35 + move_damage * .35 + status_diff * 100 * .25 + stats_diff * 100 * .05 + fainted_diff * 100

        # malus if move was used last turn
        if move == self.last_move:
            value -= 100

        type1 = pkmn_types.get_effectiveness(move.typing, self.rival.in_battle.typing[0])                  # effectiveness vs enemy's type1
        type2 = 1

        if len(self.rival.in_battle.typing) == 2:
            type2 = pkmn_types.get_effectiveness(move.typing, self.rival.in_battle.typing[1])                  # effectiveness vs enemy's type1

        # effectiveness bonus/malus
        if type1 * type2 == 4:
            value += 100
        elif type1 * type2 == 2:
            value += 50
        elif type1 * type2 == 0.5:
            value -= 50
        elif type1 * type2 == 0:
            value -= 100

        print('value: {value}\n'.format(value = value))

        return value

    def get_choice(self, target):
        if self.is_turn():
            self.verify_fainted_switch()
            choosen_action = None
            while choosen_action == None:
                possible_choices = self.get_possible_choices()
                self.print_choices(possible_choices)
                
                if len(possible_choices) >= 1:
                    best_action = possible_choices[0]
                    best_val = -float('inf')
                    for action in possible_choices:
                        val = self.minimax(self.max_play_depth, action, True)
                        if val >= best_val:
                            best_action = action
                            best_val = val
                
                    choosen_action = best_action
                    self.last_move = choosen_action
                else:
                    choosen_action = 'no_pp'

            if choosen_action != 'no_pp':
                if choosen_action.kind == ActionKind.ATTACK:        
                    move = choosen_action.target    
                    print('Choosen move:', move.name)
                    self.choices.append(move.name)
                    try_atk_status(self.in_battle, move, target)
            else:
                # simply trigger struggle
                struggle_no_pp(self.in_battle, target)

    def minimax(self, depth, action, is_maximizing):
        print('\n--- NODE DEPTH: {depth} ---'.format(depth = depth))
        if self.game_over_lose() or self.rival.game_over_lose():
            if self.game_over_lose():
                return -self.win_val
            else:
                return self.win_val
        elif depth == 0:
            return self.evaluate(action)

        if is_maximizing:
            best_val = -float('inf')
            for move in self.get_possible_choices():
                val = self.minimax(depth - 1, move, False)
                best_val = max(best_val, val)
            return best_val
        else:
            best_val = float('inf')
            for move in self.rival.get_possible_choices():
                val = self.minimax(depth - 1, move, True)
                best_val = min(best_val, val)
            return best_val


class MMAlphaBetaAI(MinimaxAI):
    """
    Minimax AI enhanced with Alpha-Beta pruning, which cuts off branches of the
    game tree that cannot influence the final decision, allowing deeper search
    than plain Minimax.

    Attributes:
        alpha (float): The best value currently achievable by the maximising player.
        beta (float): The best value currently achievable by the minimising player.
    """

    def __init__(self, rival, max_play_depth = 20):
        super(MMAlphaBetaAI, self).__init__(rival)
        self.alpha = -float('inf')
        self.beta = -self.alpha

    def minimax(self, depth, action, is_maximizing):
        print('\n--- NODE DEPTH: {depth} ---'.format(depth = depth))
        if self.game_over_lose() or self.rival.game_over_lose():
            if self.game_over_lose():
                return -self.win_val
            else:
                return self.win_val
        elif depth == 0:
            return self.evaluate(action)

        if is_maximizing:
            best_val = -float('inf')
            for move in self.get_possible_choices():
                val = self.minimax(depth - 1, move, False)
                best_val = max(best_val, val)
                self.alpha = max(self.alpha, best_val)
                if self.beta <= self.alpha:
                    break
            return best_val
        else:
            best_val = float('inf')
            for move in self.rival.get_possible_choices():
                val = self.minimax(depth - 1, move, True)
                best_val = min(best_val, val)
                self.beta = min(self.beta, best_val)
                if self.beta <= self.alpha:
                    break
            return best_val


class ExpectiMaxAI(MinimaxAI):
    """
    Expectimax AI that computes a weighted average of the opponent's possible
    moves instead of assuming they will always choose the minimal value.
    This is suitable when the opponent's behaviour is unknown or stochastic.

    Attributes:
        max_play_depth (int): Maximum depth of the game tree to explore.
    """

    def __init__(self, rival, max_play_depth = 7):
        super(ExpectiMaxAI, self).__init__(rival)

    def minimax(self, depth, action, is_maximizing):
        print('\n--- NODE DEPTH: {depth} ---'.format(depth = depth))
        if self.game_over_lose() or self.rival.game_over_lose():
            if self.game_over_lose():
                return -self.win_val
            else:
                return self.win_val
        elif depth == 0:
            return self.evaluate(action)

        if is_maximizing:
            best_val = -float('inf')
            for move in self.get_possible_choices():
                val = self.minimax(depth - 1, move, False)
                best_val = max(best_val, val)
            return best_val
        else:
            avg_val = 0
            n_moves = len(self.rival.get_possible_choices())
            for move in self.rival.get_possible_choices():
                val = self.minimax(depth - 1, move, True)
                avg_val += val/n_moves
            return avg_val