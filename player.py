from pokedex import *
from pokemon import *
import random

ATTACK = 0
SWITCH = 1

class Action:
    def __init__(self, action, user, target = None):
        self.action = action
        self.user = user
        self.target = target                # Pokemon() if action is switch, Move() if action is Attack

class Trainer:
    def __init__(self):
        self.team = [None, None, None, None, None, None]    # Trainer Pokemon team

        self.token = None                                   # token used to assingnate actual turn

        for i in range(len(self.team)):
            tmp = random.choice(list(pokedex_list.items()))[1]
            self.team[i] = Pokemon(tmp.num, tmp.species, tmp.elements, 100, tmp.base_stats)

        # self.team[2] = Pokemon(1, 'Mew', ['PSYCHIC'], 100, [3,5,520,3,4,6])
        # self.team[3] = Pokemon(1, 'Mewtwo', ['PSYCHIC'], 100, [3,5,520,3,4,6])
        # self.team[4] = Pokemon(1, 'Dragonite', ['DRAGON', 'FLYING'], 100, [3,5,520,3,4,6])
        # self.team[5] = Pokemon(1, 'Blastoise', ['WATER'], 100, [3,5,520,3,4,6])

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

        # for pkmn in self.team:
        #     if (pkmn.fainted == False or pkmn.on_field == False):
        #         possible_choices.append(Action(SWITCH, self, pkmn))
        
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
        target = rival

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
    def __init__(self, rival, max_play_depth = 7):
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
    def evaluate(self, damage):        
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

        print('\nhp_diff:', hp_diff)
        print('status_diff:', status_diff)
        print('stats_diff:', stats_diff)
        print('fainted_diff:', fainted_diff)

        value = hp_diff * .35 + damage * .35 + status_diff * 100 * .25 + stats_diff * 100 * .5 + fainted_diff * 100
        print('value:', value)
        return value

    def get_choice(self, target):
        if self.is_turn():
            self.verify_fainted_switch()
            choosen_action = None
            while choosen_action == None:
                possible_choices = self.get_possible_choices()
                print(possible_choices)
                
                if len(possible_choices) >= 1:
                    best_action = possible_choices[0]
                    best_val = -float('inf')
                    for action in possible_choices:
                        val = self.minimax(self.max_play_depth, action, False)
                        if val > best_val:
                            best_action = action
                            best_val = val
                
                    choosen_action = best_action
                else:
                    choosen_action = 'no_pp'

            if choosen_action != 'no_pp':
                if choosen_action.action == ATTACK:        
                    move = choosen_action.target    
                    print(move.name)
                    self.choices.append(move.name)
                    self.in_battle.try_atk_status(move, target)
                else:
                    pkmn = choosen_action.target
                    # remove substitute
                    self.in_battle.substitute = False
                    # reset all in-battle pkmn's temporary conditions and stats changements
                    self.in_battle.reset_stats_mult()
                    self.in_battle.reset_battle_stats()
                    self.in_battle.temp_status = None
                    self.in_battle.on_field = False
                    # then replace the pokemon with the selected one
                    self.in_battle = pkmn     
                    pkmn.on_field = True
            else:
                # simply trigger struggle using the first move
                self.in_battle.atk(self.in_battle.moves[0], target)

    def minimax(self, depth, action, is_maximizing):
        move_dmg = self.in_battle.calculate_damage(action.target, self.rival.in_battle)
        if self.game_over_lose() or self.rival.game_over_lose():
            if self.game_over_lose():
                return -self.win_val
            else:
                return self.win_val
        elif depth == 0:
            return self.evaluate(move_dmg)

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
    def __init__(self, rival, max_play_depth = 20):
        super(MMAlphaBetaAI, self).__init__(rival)
        self.alpha = -100000000
        self.beta = -self.alpha

    def minimax(self, depth, action, is_maximizing):
        move_dmg = self.in_battle.calculate_damage(action.target, self.rival.in_battle)
        if self.game_over_lose() or self.rival.game_over_lose():
            if self.game_over_lose():
                return -self.win_val
            else:
                return self.win_val
        elif depth == 0:
            return self.evaluate(move_dmg)

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