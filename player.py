from pokedex import *
from pokemon import *
import random

class Trainer:
    def __init__(self):
        self.team = [None, None, None, None, None, None]

        for i in range(len(self.team)):
            tmp = random.choice(list(pokedex_list.items()))[1]

            self.team[i] = Pokemon(tmp.num, tmp.species, tmp.elements, 100, tmp.base_stats)

        self.in_battle = self.team[0]

    def get_team(self):
        print('Player Team')
        for pkmn in self.team:
            print(pkmn.get_stats())

        