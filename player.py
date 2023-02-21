from pokedex import *
from pokemon import *
import random

ATTACK = 0
SWITCH = 1

class Action:
    def __init__(self, action, user, target = None):
        self.action = action
        self.user = user
        self.target = target

class Trainer:
    def __init__(self):
        self.team = [None, None, None, None, None, None]    # Trainer Pokemon team

        self.token = None                                   # token used to assingnate actual turn

        for i in range(len(self.team)):
            tmp = random.choice(list(pokedex_list.items()))[1]
            self.team[i] = Pokemon(tmp.num, tmp.species, tmp.elements, 100, tmp.base_stats)

        # self.team[2] = Pokemon(1, 'Bulbasaur', ['GRASS', 'POISON'], 100, [3,5,520,3,4,6])
        # self.team[3] = Pokemon(1, 'Oddish', ['GRASS', 'POISON'], 100, [3,5,520,3,4,6])
        # self.team[4] = Pokemon(1, 'Gloom', ['GRASS', 'POISON'], 100, [3,5,520,3,4,6])
        # self.team[5] = Pokemon(1, 'Vileplume', ['GRASS', 'POISON'], 100, [3,5,520,3,4,6])

        # FOR TESTING PURPOSES
        # for i in range(len(self.team)):
        #     self.team[i] = Pokemon(1, 'Blastoise', ['WATER'], 100, [3,5,4,3,4,6])

        self.in_battle = self.team[0]
        self.team[0].on_field = True
        
    def get_team(self):
        print('Player Team')
        for pkmn in self.team:
            pkmn.get_stats()
            pkmn.get_moves()

    def get_possible_choices(self):
        possible_choices = [ ]

        for pkmn in self.team:
            if (pkmn.fainted == False or pkmn.on_field == False):
                possible_choices.append(Action(SWITCH, self, pkmn))
        
        for move in self.in_battle.moves:
            if move != None:
                if move.pp > 0:
                    possible_choices.append(Action(ATTACK, self, move))

        return possible_choices

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
    def __init__(self):
        super(RandomAI, self).__init__()
        self.choices = [ ]

    def get_choice(self, rival):
        target = rival.in_battle
        possible_choices = self.get_possible_choices()
        print(possible_choices)

        if self.is_turn():
            self.verify_fainted_switch()
            move = None
            while move == None:
                move = random.choice(self.in_battle.moves)
            
            print(move.name)
            self.choices.append(move.name)
            self.in_battle.try_atk_status(move, target)

class MinimaxAI(TrainerAI):
    # depth to edit
    def __init__(self, rival, max_play_depth = 5):
        super(MinimaxAI, self).__init__()
        self.choices = [ ]
        self.win_val = 1000000
        self.max_play_depth = max_play_depth

        self.rival = rival

    # computes evaluation function; it's based on:
    # - total actual hp;
    # - total max hp;
    # - total stats;
    # - number of pkmn with status;
    # - number of fainted pkmn
    def evaluate(self):        
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

        print('hp_diff:', hp_diff)
        print('status_diff:', status_diff)
        print('stats_diff:', stats_diff)
        print('fainted_diff:', fainted_diff)

        value = hp_diff * .7 + status_diff * 100 * .25 + stats_diff * 100 * .5 + fainted_diff * 100
        print('value:', value)
        return value

    def get_choice(self, target):
        if self.is_turn():
            self.verify_fainted_switch()
            move = None
            while move == None:
                move = random.choice(self.in_battle.moves)
                possible_choices = self.get_possible_choices()
                print(possible_choices)

                best_action = possible_choices[0]
                best_val = -float('inf')
                for action in possible_choices:
                    val = self.rival_minimax(5, action)
                    if val > best_val and action is Move:
                        best_action = action
                        best_val = val
            
            print(move.name)
            self.choices.append(move.name)
            self.in_battle.try_atk_status(move, target)

    def self_minimax(self, depth):
        if self.game_over_lose() == False and self.rival.game_over_lose() == False:
            game_over = False
        else:
            game_over = True

        if depth >= self.max_play_depth:
            return self.evaluate()
        elif game_over:
            # if winner is self
            if self.rival.game_over_lose():
                return self.win_val
            # if winner is rival
            else:
                return -self.win_val

        best_move_val = self.win_val * (-1)
        possible_choices = self.rival.get_possible_choices()
        for action in possible_choices:
            val = self.rival_minimax(depth, action)
            best_move_val = max(val, best_move_val)
        
        return best_move_val

    def rival_minimax(self, depth, action):
        if self.game_over_lose() == False and self.rival.game_over_lose() == False:
            game_over = False
        else:
            game_over = True

        if game_over:
            # if winner is rival
            if self.game_over_lose():
                return self.win_val
            # if winner is self
            else:
                return -self.win_val

        best_move_val = self.win_val
        rival_choices = self.rival.get_possible_choices()

        for rival_action in rival_choices:
            if rival_action == SWITCH:
                continue
                
            if self.rival.is_turn():
                continue

            val = self.self_minimax(depth + 1)
            best_move_val = min(val, best_move_val)
            
        return best_move_val

class MMAlphaBetaAI(MinimaxAI):
    def __init__(self, rival, max_play_depth = 5):
        super(MMAlphaBetaAI, self).__init__(rival)
        self.alpha = -100000000
        self.beta = -self.alpha

    def self_minimax(self, depth):
        if self.game_over_lose() == False and self.rival.game_over_lose() == False:
            game_over = False
        else:
            game_over = True

        if depth >= self.max_play_depth:
            return self.evaluate()
        elif game_over:
            # if winner is self
            if self.rival.game_over_lose():
                return self.win_val
            # if winner is rival
            else:
                return -self.win_val

        best_move_val = self.win_val * (-1)
        possible_choices = self.rival.get_possible_choices()
        for action in possible_choices:
            val = self.rival_minimax(depth, action)
            best_move_val = max(val, best_move_val)
            if best_move_val >= self.beta:
                return best_move_val
            self.alpha = max(best_move_val, self.alpha)
        
        return best_move_val

    def rival_minimax(self, depth, action):
        if self.game_over_lose() == False and self.rival.game_over_lose() == False:
            game_over = False
        else:
            game_over = True

        if game_over:
            # if winner is rival
            if self.game_over_lose():
                return self.win_val
            # if winner is self
            else:
                return -self.win_val

        best_move_val = self.win_val
        rival_choices = self.rival.get_possible_choices()

        for rival_action in rival_choices:
            if rival_action == SWITCH:
                continue
                
            if self.rival.is_turn():
                continue

            val = self.self_minimax(depth + 1)
            best_move_val = min(val, best_move_val)
            
            if best_move_val <= self.alpha:
                return best_move_val
            
            self.beta = min(best_move_val, self.beta)
        
        return best_move_val