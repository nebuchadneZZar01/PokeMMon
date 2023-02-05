import math
import random
import moves
import pkmn_types
from itertools import combinations

def calculate_max_stat(base_stat, level):
    return math.floor((base_stat*2*level)/100) + 5

class Move:
    def __init__(self, name, typing, power, pp, physical, accuracy):
        self.name = name
        self.typing = typing
        self.power = power
        self.pp = pp
        self.max_pp = pp
        self.physical = physical
        self.accuracy = accuracy

    def get_info(self):
        print(self.name)
        print('Typing:', self.typing)
        print('Power:', self.power)
        print('PP:', self.pp)
        print('Category:', self.physical)
        print('Accuracy:', self.accuracy)

class Pokemon:
    def __init__(self, pkmn_id, name, typing, level, base_stats):
        # PKMN generals
        self.id = pkmn_id
        self.name = name
        
        if level < 1: 
            self.level = 1
        elif level > 100: 
            self.level = 100
        else:
             self.level = level

        self.typing = typing
        self.moves = [None, None, None, None]

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
        self.atk_mult = 1
        self.def_mult = 1
        self.sp_atk_mult = 1
        self.sp_def_mult = 1
        self.speed_mult = 1
        self.accuracy = 1
        self.evasion = 1

        # random move injection
        while True:
            move = random.choice(moves.attacks)
            if moves.check_compatibility(move['name'], self.name): 
                self.moves[0] = Move(move['name'], move['type'], move['power'], move['pp'], move['category'], move['accuracy'])
                break

        while True:
            move = random.choice(moves.attacks)
            if moves.check_compatibility(move['name'], self.name): 
                if move['name'] != self.moves[0].name:
                    self.moves[1] = Move(move['name'], move['type'], move['power'], move['pp'], move['category'], move['accuracy'])
                    break
                else:
                    break

        while True:
            move = random.choice(moves.attacks)
            if self.moves[1] is not None:
                if moves.check_compatibility(move['name'], self.name): 
                    if move['name'] != self.moves[1].name and move['name'] != self.moves[0].name:
                        self.moves[2] = Move(move['name'], move['type'], move['power'], move['pp'], move['category'], move['accuracy'])
                        break
                    else:
                        break
            else:
                break

        while True:
            move = random.choice(moves.attacks)
            if self.moves[2] is not None:
                if moves.check_compatibility(move['name'], self.name): 
                    if move['name'] != self.moves[2].name and move['name'] != self.moves[1].name and move['name'] != self.moves[0].name:
                        self.moves[3] = Move(move['name'], move['type'], move['power'], move['pp'], move['category'], move['accuracy'])
                        break
                    else:
                        break
            else:
                break

    def get_stats(self):
        print('Name:', self.name, '\tType:', self.typing, '\tLevel:', self.level)
        print('Hp:', self.hp)
        print('Atk:', self.attack)
        print('Def:', self.defense)
        print('Sp Atk:', self.sp_atk)
        print('Sp Def:', self.sp_def)
        print('Spe:', self.speed, '\n')

    def get_moves(self):
        for move in self.moves:
            if move is not None:
                move.get_info()
                print('\n')
            else: print('None\n')


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

    def atk(self, move, enemy):
        if move.pp > 0:
            print(self.name, 'uses', move.name)

            if move.physical is 'Physical' or move.physical is 'Special':
                power = move.power                                                              # move base power
                # same-type attack bonus      
                if len(self.typing) == 2:     
                    # if attacker has two types                            
                    if move.typing == self.typing[0] or self.typing[1]:
                        stab = 2         
                    else:
                        stab = 1  
                else:
                    # if attacker has only one type
                    if move.typing == self.typing:
                        stab = 2   
                    else:
                        stab = 1

                a = self.attack                                                     # attacking pkmn atk stat if physical move, sp_atk stat otherwise
                d = enemy.defense                                                   # target pkmn def stat if physical move, sp_def stat otherwise
                type2 = 1
                if len(enemy.typing) == 2:
                    type2 = pkmn_types.get_effectiveness(move.typing, enemy.typing[1])       # effectiveness vs enemy's type2
                type1 = pkmn_types.get_effectiveness(move.typing, enemy.typing[0])             # effectiveness vs enemy's type1
                
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
                else:
                    # if attacking pkmn is confused, it can hit hitself
                    prob = random.random()
                    if prob <= 0.5: 
                        print(self.name, 'is so confused to hit itself!')
                        self.hit(damage)
            else:
                print("Non damaging move")
                self.handle_status_move(move, enemy)

            move.pp = move.pp - 1

        else:
            print('This move has any pp!\n')

    def handle_status_move(self, move, enemy):
        if move.name == 'Acid Armor':
            self.def_mult += 1
            print('{pkmn} defense higly increases!'.format(pkmn = self.name))
        elif move.name == 'Agility':
            self.speed_mult += 1
            print('{pkmn} speed higly increases!'.format(pkmn = self.name))
        elif move.name == 'Amnesia':
            self.sp_atk_mult += 1
            self.sp_def_mult += 1
            print('{pkmn} special attack higly increases!'.format(pkmn = self.name))
            print('{pkmn} special defense increases!'.format(pkmn = self.name))
        elif move.name == 'Confuse Ray':
            enemy.temp_status = 'CONF'
            print('{pkmn} is now confused!'.format(pkmn = enemy.name))
        elif move.name == 'Conversion':
            self.typing = enemy.typing
            print('{player_mon} assumes {enemy_mon} types!'.format(player_mon = self.name, enemy_mon = enemy.name))
        elif move.name == 'Defense Curl':
            self.def_mult += 0.5
            print('{pkmn} defense increases!'.format(pkmn = self.name))
        elif move.name == 'Disable':
            pass
        elif move.name == 'Double Team':
            enemy.evasion -= 0.5
            print('{pkmn} evasion decreases!'.format(pkmn = enemy.name))
        elif move.name == 'Focus Energy':
            pass
        elif move.name == 'Flash':
            enemy.accuracy -= 0.5
            print('{pkmn} evasion decreases!'.format(pkmn = enemy.name))
        elif move.name == 'Glare':
            enemy.status = 'PAR'
            print('{pkmn} is now paralized!'.format(pkmn = enemy.name))
        elif move.name == 'Growl':
            enemy.attack -= 0.5
            print('{pkmn} attack decreases!'.format(pkmn = enemy.name))
        elif move.name == 'Growth':
            self.sp_atk += 0.5
            self.sp_def += 0.5
            print('{pkmn} special attack increases!'.format(pkmn = self.name))
            print('{pkmn} special defense increases!'.format(pkmn = self.name))