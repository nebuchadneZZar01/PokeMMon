from pokedex import *
from pokemon import *
import random

class Trainer:
    def __init__(self):
        self.team = [None, None, None, None, None, None]    # Trainer Pokemon team

        self.choices = [ ]

        self.token = None                                   # token used to assingnate actual turn

        for i in range(len(self.team)):
            tmp = random.choice(list(pokedex_list.items()))[1]

            self.team[i] = Pokemon(tmp.num, tmp.species, tmp.elements, 100, tmp.base_stats)

        self.in_battle = self.team[0]
        
    def get_team(self):
        print('Player Team')
        for pkmn in self.team:
            pkmn.get_stats()
            pkmn.get_moves()

    def is_turn(self):
        return self.token

    def set_turn(self, _token):
        self.token = _token

class RandomAI(Trainer):
    def get_choice(self, target):
        if self.is_turn():
            if self.in_battle.fainted == True:
                i = 0
                while True:
                    if self.team[i].fainted == True:
                        i += 1
                    else:
                        self.in_battle = self.team[i]
                        break

            move = None
            while move == None:
                move = random.choice(self.in_battle.moves)
            self.choices.append(move.name)
            self.in_battle.try_atk_status(move, target)
        