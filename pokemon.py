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
        self.accuracy = 1
        self.evasion = 1

        # stats multiplier
        self.atk_mult = 0
        self.def_mult = 0
        self.sp_atk_mult = 0
        self.sp_def_mult = 0
        self.speed_mult = 0
        self.acc_mult = 0
        self.ev_mult = 0

        # defines if there is a substitute doll
        self.substitute = False

        # defines how many turn pkmn is sleeping
        self.sleeping_turns = 0
        
        # defines how many turns pkmn have been confused
        self.confused_turns = 0

        # defines how many turns pkmn have been intoxicated
        self.toxic_turns = 0
        
        # message to gui
        self.msg = 'What will {pkmn} do?'.format(pkmn = self.name)

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

    def get_stats_mult(self):
        print('Atk:', self.atk_mult)
        print('Def:', self.def_mult)
        print('Sp Atk:', self.sp_atk_mult)
        print('Sp Def:', self.sp_def_mult)
        print('Spe:', self.speed_mult)
        print('Ev:', self.ev_mult)
        print('Acc:', self.acc_mult, '\n')

    # increases or decreases (highly or normally) a generic stat multiplier
    # highly defines whether the multiplier is updated by one or two stages
    def inc_dec_stat_mult(self, multiplier, increase: bool, highly: bool = False, enemy = None):
        if enemy != None:
            if multiplier is enemy.atk_mult:
                name = 'Attack'
            elif multiplier is enemy.def_mult:
                name = 'Defense'
            elif multiplier is enemy.sp_atk_mult:
                name = 'Special Attack'
            elif multiplier is enemy.sp_def_mult:
                name = 'Special Defense'
            elif multiplier is enemy.speed_mult:
                name = 'Speed'
            elif multiplier is enemy.ev_mult:
                name = 'Evasion'
            elif multiplier is enemy.acc_mult:
                name = 'Accuracy'
        else:
            if multiplier is self.atk_mult:
                name = 'Attack'
            elif multiplier is self.def_mult:
                name = 'Defense'
            elif multiplier is self.sp_atk_mult:
                name = 'Special Attack'
            elif multiplier is self.sp_def_mult:
                name = 'Special Defense'
            elif multiplier is self.speed_mult:
                name = 'Speed'
            elif multiplier is self.ev_mult:
                name = 'Evasion'
            elif multiplier is self.acc_mult:
                name = 'Accuracy'
        
        if increase:
            if multiplier >= 6:
                self.msg += '\n{pkmn}\'s {stat_name} won\'t rise anymore!\n'.format(pkmn = self.name, stat_name = name)
            else:
                if highly:
                    multiplier += 2
                    self.msg += '\n{pkmn}\'s {stat_name} went way up!\n'.format(pkmn = self.name, stat_name = name)
                else:
                    multiplier += 1
                    self.msg += '\n{pkmn}\'s {stat_name} went up!\n'.format(pkmn = self.name, stat_name = name)
        else:
            if multiplier <= -6:
                self.msg += '\n{pkmn}\'s {stat_name} won\'t drop anumore!\n'.format(pkmn = enemy.name, stat_name = name)
            else: 
                if highly:
                    multiplier -= 2
                    self.msg += '\n{pkmn}\'s {stat_name} went way down!\n'.format(pkmn = enemy.name, stat_name = name)
                else:
                    multiplier -= 1
                    self.msg += '\n{pkmn}\'s {stat_name} went down!\n'.format(pkmn = enemy.name, stat_name = name)
        
        return multiplier

    # resets the multipliers
    def reset_stats_mult(self):
        self.atk_mult = 0
        self.def_mult = 0
        self.sp_atk_mult = 0
        self.sp_def_mult = 0
        self.speed_mult = 0
        self.ev_mult = 0
        self.acc_mult = 0

    # updates in-battle stats using the updated multipliers
    def update_battle_stat(self, stat, multiplier):
        if multiplier >= 0:
            stat *= ((multiplier*50)+100)/100
        elif multiplier == -1:
            stat *= 0.66
        elif multiplier == -2:
            stat *= 0.5
        elif multiplier == -3:
            stat *= 0.4
        elif multiplier == -4:
            stat *= 0.33
        elif multiplier == -5:
            stat *= 0.28
        elif multiplier == -6:
            stat *= 0.25

        return stat

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
            self.msg = 'Critical hit!'
            return 2
        else: 
            return 1

    def hit(self, damage):
        self.hp -= damage
        if self.hp <= 0: 
            self.hp = 0
            self.fainted = True
            self.msg = '{pkmn} fainted!'.format(pkmn = self.name)

    # attack function that handles the status modifier
    def try_atk_status(self, move, enemy):
        # PERMANENT STATUS
        if self.status != None:
            # PARALYSIS
            if self.status == 'PAR':
                # probability to attack if paralyzed
                p = random.random()
                if p <= 0.25:
                    self.atk(move, enemy)
                else:
                    self.msg = '{pkmn} is paralyzed and can\'t move!'.format(pkmn = self.name)
            # SLEEPING
            elif self.status == 'SLP':
                if self.sleeping_turns < 7:
                    # probability to wake up if sleeping
                    p = random.random()
                    if p <= 0.33:
                        self.status = None
                        self.atk(move, enemy)
                        self.msg += '\n{pkmn} woke up!'.format(pkmn = self.name)
                    else:
                        self.sleeping_turns += 1
                        self.msg = '{pkmn} is sleeping...'.format(pkmn = self.name)
                else:
                    self.status = None
                    self.msg = '{pkmn} woke up!'.format(pkmn = self.name)
                    self.atk(move, enemy)
        # CONFUSION STATUS
        elif self.temp_status != None:
            if self.confused_turns < 5:
                # probability to heal from confusion
                p = random.random()
                if p <= 0.33:
                    self.temp_status = None
                    self.atk(move, enemy)
                    self.msg += '\n{pkmn} is not confused anymore!'.format(pkmn = self.name)
                else:
                    self.confused_turns += 1
                    self.msg = '{pkmn} is confused...'.format(pkmn = self.name)
                    power = 40
                    a = self.level
                    b = self.attack
                    c = self.defense

                    damage = int((((2*a/5 + 2) * b * 40)/c)/50) + 2
                    self.hit(damage)
                    self.msg += '\nIt\'s so confused to hit itself!'.format(pkmn = self.name)
            else:
                self.temp_status = None
                self.atk(move, enemy)
                self.msg += '\n{pkmn} is not confused anymore!'.format(pkmn = self.name)
        else:
            self.atk(move, enemy)

    def atk(self, move, enemy):
        if move.pp > 0:
            # T will determine whether the move will hit
            T = move.accuracy * self.accuracy * enemy.evasion

            rand_t = random.randint(0, 255)
            self.msg = '{pkmn} used {mv}!'.format(pkmn = self.name, mv = move.name)

            # the first condition removes a bug that affects gen I
            # in fact, in gen I, if T == 255, the move will miss
            # this resulted in bug where no move can be guaranteed to hit
            if T == 255 or T < rand_t:
                if move.physical == 'Physical' or move.physical == 'Special':
                    power = move.power                                                                  # move base power
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

                    a = self.attack if move.physical == 'Physical' else self.sp_atk                     # attacking pkmn atk stat if physical move, sp_atk stat otherwise
                    d = enemy.defense if move.physical == 'Physical' else enemy.sp_def                  # target pkmn def stat if physical move, sp_def stat otherwise
                    type2 = 1
                    if len(enemy.typing) == 2:
                        type2, tmp = pkmn_types.get_effectiveness(move.typing, enemy.typing[1])         # effectiveness vs enemy's type2
                    type1, tmp = pkmn_types.get_effectiveness(move.typing, enemy.typing[0])             # effectiveness vs enemy's type1
                    
                    self.msg += tmp

                    if type1 == 0 or type2 == 0:
                        crit = 0
                    else:
                        crit = self.calculate_crit_multiplier()                                         # critical-hit multiplier
                        
                    rand_list = [random.randint(217, 255) for i in range(9)]
                    rand = 1
                    for r in rand_list:
                        rand *= r
                    rand = r/255
                    
                    # if pkmn is burned, damage is halved
                    if self.status == 'BRN':
                        damage = int(((((2*self.level*crit)/5 + 2) * power * (a/d)) /50 + 2) * stab * type1 * type2 * rand)/2
                    else:
                        damage = int(((((2*self.level*crit)/5 + 2) * power * (a/d)) /50 + 2) * stab * type1 * type2 * rand)
                    print(damage)

                    if self.temp_status != "CONF":
                        if enemy != self: 
                            enemy.hit(damage)
                            # print(move.name)
                            self.handle_special_physical_move(move)
                    else:
                        # if attacking pkmn is confused, it can hit hitself
                        prob = random.random()
                        if prob <= 0.5: 
                            self.msg = '{pkmn} is so confused to hit itself!'.format(pkmn = self.name)
                            self.hit(damage)
                else:
                    # print("Non damaging move")
                    self.handle_status_move(move, enemy)
            else:
                self.msg += '\nBut it failed...'

            move.pp = move.pp - 1

        else:
            self.msg = 'This move has any pp!\n'

    def handle_status_move(self, move, enemy):
        if move.name == 'Acid Armor':
            self.def_mult = self.inc_dec_stat_mult(self.def_mult, increase=True, highly=True)
            self.defense = self.update_battle_stat(self.defense, self.def_mult)
        elif move.name == 'Agility':
            self.speed_mult = self.inc_dec_stat_mult(self.speed_mult, increase=True, highly=True)
            self.speed = self.update_battle_stat(self.speed, self.speed_mult)
        elif move.name == 'Amnesia':
            self.sp_atk_mult = self.inc_dec_stat_mult(self.sp_atk_mult, increase=True, highly=True)
            self.sp_atk = self.update_battle_stat(self.sp_atk, self.sp_atk_mult)
            self.sp_def_mult = self.inc_dec_stat_mult(self.sp_def_mult, increase=True, highly=True)
            self.sp_def = self.update_battle_stat(self.sp_def, self.sp_def_mult)
        elif move.name == 'Confuse Ray' or move.name == 'Supersonic':
            enemy.temp_status = 'CONF'
            self.msg += '\n{pkmn} is now confused!'.format(pkmn = enemy.name)
        elif move.name == 'Conversion':
            self.typing = enemy.typing
            self.msg += '\n{player_mon} assumes {enemy_mon} types!'.format(player_mon = self.name, enemy_mon = enemy.name)
        elif move.name == 'Defense Curl' or move.name == 'Harden' or move.name == 'Withdraw':
            self.def_mult = self.inc_dec_stat_mult(self.def_mult, increase=True)
            self.defense = self.update_battle_stat(self.defense, self.def_mult)
        elif move.name == 'Disable':
            pass
        elif move.name == 'Double Team':
            self.ev_mult = self.inc_dec_stat_mult(self.ev_mult, increase=True)
            self.evasion = self.update_battle_stat(self.evasion, self.ev_mult)
        elif move.name == 'Focus Energy':
            pass
        elif move.name == 'Flash' or move.name == 'Kinesis' or move.name == 'Sand Attack':
            enemy.acc_mult = self.inc_dec_stat_mult(enemy.acc_mult, increase=False, enemy=enemy)
            enemy.accuracy = self.update_battle_stat(enemy.accuracy, enemy.acc_mult)
        elif move.name == 'Glare' or move.name == 'Stun Spore' or move.name == 'Thunder Wave':
            if enemy.status == None:
                enemy.status = 'PAR'
                enemy.speed -= (0.75 * enemy.speed)
                self.msg += '\n{pkmn} is now paralized!'.format(pkmn = enemy.name)
            else:
                self.msg += '\nBut nothing happened...'
        elif move.name == 'Growl':
            enemy.atk_mult = self.inc_dec_stat_mult(enemy.atk_mult, increase=False, enemy=enemy)
            enemy.attack = enemy.update_battle_stat(enemy.attack, enemy.atk_mult)
        elif move.name == 'Growth':
            self.sp_atk_mult = self.inc_dec_stat_mult(self.sp_atk_mult, increase=True)
            self.sp_atk = self.update_battle_stat(self.sp_atk, self.sp_atk_mult)
            self.sp_def_mult = self.inc_dec_stat_mult(self.sp_def_mult, increase=True)
            self.sp_def = self.update_battle_stat(self.sp_def, self.sp_def_mult)
        elif move.name == 'Haze':
            self.reset_stats_mult()
            enemy.reset_stats_mult()
            self.msg += '\nAll stats changes have been reset!'
        elif move.name == 'Hypnosis' or move.name == 'Lovely Kiss' or move.name == 'Sing' or move.name == 'Spore' or move.name == 'Sleep Powder':
            if enemy.status == None:
                enemy.status = 'SLP'
                self.msg += '\n{pkmn} is now sleeping!'.format(pkmn = enemy.name)
            else:
                self.msg += '\nBut nothing happened...'
        elif move.name == 'Leech Seed':
            pass
        elif move.name == 'Light Screen':
            self.sp_atk *= 2
            self.sp_def *= 2
        elif move.name == 'Meditate' or move.name == 'Minimize':
            self.ev_mult = self.inc_dec_stat_mult(self.ev_mult, increase=True)
            self.evasion = self.update_battle_stat(self.evasion, self.ev_mult)
        elif move.name == 'Metronome':
            rand_move_tmp = random.choice(moves.attacks)
            rand_move = Move(rand_move_tmp['name'], rand_move_tmp['type'], rand_move_tmp['power'], rand_move_tmp['pp'], rand_move_tmp['category'], rand_move_tmp['accuracy'])
            self.atk(rand_move, enemy)
        elif move.name == 'Mimic':
            self.msg += '\n{player_mon} copies one of {enemy_mon}\'s moves!'.format(player_mon = self.name, enemy_mon = enemy.name)
            for m in self.moves:
                print(m.name)
                if m.name == 'Mimic':
                    m = random.choice(enemy.moves)
                    break
        elif move.name == 'Mirror Move':
            pass
        elif move.name == 'Mist':
            pass
        elif move.name == 'Poison Gas' or move.name == 'Poison Powder':
            if enemy.status == None:
                if (len(enemy.typing) == 2):
                    if enemy.typing[0] != 'Poison' or enemy.typing[1] != 'Poison':
                        enemy.status = 'PSN'
                elif enemy.typing != 'Poison':
                    enemy.status = 'PSN'
                else: 
                    self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
            else:
                self.msg += '\nBut nothing happened...'
        elif move.name == 'Recover' or move.name == 'Soft Boiled':
            if self.hp < self.max_hp:
                self.hp += (0.5) * self.max_hp
                if self.hp > self.max_hp: self.hp = self.max_hp
                self.msg = '\n{pkmn} restores half of its hp!'.format(pkmn = self.name)
            else:
                self.msg = '\nBut {pkmn} already has all its hp!'.format(pkmn = self.name)
        elif move.name == 'Reflect':
            self.defense *= 2
        elif move.name == 'Rest':
            if self.hp < self.max_hp:
                self.hp = self.max_hp
                self.status = 'SLP'
                self.msg += '\n{pkmn} went to sleep and regained health!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut {pkmn} already has all its hp!'.format(pkmn = self.name)
        elif move.name == 'Roar' or move.name == 'Splash' or move.name == 'Teleport' or move.name == 'Whirlwind':
            self.msg += '\nBut nothing happened...'
        elif move.name == 'Screech':
            enemy.def_mult = self.inc_dec_stat_mult(enemy.def_mult, increase=False, enemy=enemy)
            enemy.defense = enemy.update_battle_stat(enemy.defense, enemy.def_mult)
        elif move.name == 'String Shot':
            enemy.speed_mult = self.inc_dec_stat_mult(enemy.speed_mult, increase=False, enemy=enemy)
            enemy.speed = enemy.update_battle_stat(enemy.speed, enemy.speed_mult)
        elif move.name == 'Substitute':
            if self.hp >= (0.3 * self.max_hp):
                self.hp -= math.floor(0.25 * self.max_hp)
                self.substitute = True
                self.msg += '\n{pkmn} is replaced by a substitute doll!'.format(pkmn = self.name)
        elif move.name == 'Sharpen':
            self.atk_mult = self.inc_dec_stat_mult(self.atk_mult, increase=True)
            self.attack = self.update_battle_stat(self.attack, self.atk_mult)
        elif move.name == 'Swords Dance':
            self.atk_mult = self.inc_dec_stat_mult(self.atk_mult, increase=True, highly=True)
            self.attack = self.update_battle_stat(self.attack, self.atk_mult)
        elif move.name == 'Tail Whip' or move.name == 'Leer':
            enemy.def_mult = self.inc_dec_stat_mult(enemy.def_mult, increase=False, enemy=enemy)
            enemy.defense = enemy.update_battle_stat(enemy.defense, enemy.def_mult)
        elif move.name == 'Toxic':
            if enemy.status == None:
                enemy.status = 'TOX'
                self.msg += '\n{pkmn} is intoxicated!'.format(pkmn = enemy.name)
            else:
                self.msg += '\nBut nothing happened...'
        elif move.name == 'Transorm':
            self.msg = '\n{player_mon} transforms into {enemy_mon}!'.format(player_mon = self.name, enemy_mon = enemy.name)
            self = enemy
            
            for m in self.moves:
                m.pp = m.max_pp/2

    def handle_special_physical_move(self, move):
        # Physical moves
        if move.name == 'Explosion':
            self.hp -= self.max_hp
            self.fainted = True