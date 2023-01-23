import math
import random
import pkmn_types

def calculate_max_stat(base_stat, level):
    return math.floor((base_stat*2*level)/100) + 5

class Move:
    def __init__(self, name, typing, power, pp, physical):
        self.name = name
        self.typing = typing
        self.power = power
        self.pp = pp
        self.physical = physical

class Pokemon:
    def __init__(self, name, moves, typing, level, base_stats):
        # PKMN generals
        self.name = name
        
        if level < 1: 
            self.level = 1
        elif level > 100: 
            self.level = 100
        else:
             self.level = level

        self.typing = typing
        self.moves = moves

        self.status = None
        self.temp_status = None
        self.in_battle = True
        self.fainted = False

        # Base stats, given to instanciate
        self.base_hp = base_stats[0]
        self.base_attack = base_stats[1]
        self.base_defense = base_stats[2]
        self.base_sp_atk = base_stats[3]
        self.base_sp_def = base_stats[4]
        self.base_speed = base_stats[5]
        
        # Max stats, calculated from level
        self.max_hp = math.floor((self.base_hp*2*self.level)/100) + self.level + 10
        self.max_attack = calculate_max_stat(self.base_attack, self.level)
        self.max_defense = calculate_max_stat(self.base_defense, self.level)
        self.max_sp_atk = calculate_max_stat(self.base_sp_atk, self.level)
        self.max_sp_def = calculate_max_stat(self.base_sp_def, self.level)
        self.max_speed = calculate_max_stat(self.base_speed, self.level)

        # Actual stats, they variate in battle
        self.hp = self.max_hp
        self.attack = self.max_attack
        self.defense = self.max_defense
        self.sp_atk = self.max_sp_atk
        self.sp_def = self.max_sp_def
        self.speed = self.max_speed

        # stats multiplier
        self.atk_mult = 0
        self.def_mult = 0
        self.sp_atk_mult = 0
        self.sp_def_mult = 0
        self.speed_mult = 0

    def get_stats(self):
        print('Name:', self.name, '\tType:', self.typing, '\tLevel:', self.level)
        print('Hp:', self.hp)
        print('Atk:', self.attack)
        print('Def:', self.defense)
        print('Sp Atk:', self.sp_atk)
        print('Sp Def:', self.sp_def)
        print('Spe:', self.speed, '\n')

    # calculates the critical multiplier taking a random number
    # if the random number is higher than a treshold, then critical
    def calculate_crit_multiplier(self):
        treshold = math.floor(self.base_speed/2)
        if treshold > 255: treshold = 255

        rate = random.randint(0, 255)
        if (rate < treshold):
            print('Critical hit!')
            return 2
        else: 
            return 1

    def hit(self, damage):
        self.hp -= damage
        if self.hp <= 0: 
            self.hp = 0
            self.fainted = True
            print(self.name, 'fainted!')

    def atk(self, enemy):
        power = self.moves[0].power                                         # move base power
        stab = 2                                                            # same-type attack bonus
        a = self.attack                                                     # attacking pkmn atk stat if physical move, sp_atk stat otherwise
        d = enemy.defense                                                   # target pkmn def stat if physical move, sp_def stat otherwise
        type1 = pkmn_types.get_effectiveness('FIRE', enemy.typing[0])       # effectiveness vs enemy's type1
        type2 = pkmn_types.get_effectiveness('FIRE', enemy.typing[1])       # effectiveness vs enemy's type2
        
        if type1 == 0 or type2 == 0:
            crit = 0
        else:
            crit = self.calculate_crit_multiplier()                             # critical-hit multiplier
            
        rand_list = [random.randint(217, 255) for i in range(9)]
        rand = 1
        for r in rand_list:
            rand *= r
        rand = r/255

        damage = int(((((2*self.level*crit)/5 + 2) * power) /50 + 2) * stab * type1 * type2 * rand)
        print(damage)
        
        if self.temp_status != "CONF":
            if enemy != self: 
                enemy.hit(damage)
                self.moves[0].pp = self.moves[0].pp-1
        else:
            # if attacking pkmn is confused, it can hit hitself
            prob = random.random()
            if prob <= 0.5: 
                print(self.name, 'is so confused to hit itself!')
                self.hit(damage)


# char = Pokemon('Charmander', 'FIRE', 100, [39, 52, 43, 60, 50, 65])

# # char.get_stats()

# bulba = Pokemon('Bulbasaur', ['GRASS', 'POISON'], 100, [39, 52, 43, 60, 50, 65])
# # bulba.get_stats()

# # char.atk(bulba)

# # bulba.get_stats()
# # char.get_stats()