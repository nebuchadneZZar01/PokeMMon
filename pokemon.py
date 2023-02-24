import math
import random
import moves
import pkmn_types
from copy import deepcopy

# service procedure to calculate maximum value of the stats
def calculate_max_stat(base_stat, level):
    return math.floor((base_stat*2*level)/100) + 5


# identifies every move
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


# Identifies every pokemon
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
        self.moves = [None] * 4  

        self.status = None              
        self.temp_status = None
        self.on_field = False
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
        
        self.substitute = False             # defines if there is a substitute doll
        self.sub_damage = 0                 # defines substitute damage (if equal to 255, it vanishes)

        # defines if pkmn is transformed (for mew and ditto)
        self.transformed = False

        # defines if leech seed was used on pkmn
        self.seeded = False

        # defines how many turn pkmn is sleeping
        self.sleeping_turns = 0
        
        # defines how many turns pkmn have been confused
        self.confused_turns = 0

        # defines how many turns pkmn have been intoxicated
        self.toxic_turns = 0

        # define if there is already a (sp.) def. barrier
        self.reflect = False
        self.light_screen = False

        # define if the pkmn put a mist
        self.mist = False

        # message to gui
        self.msg = 'You are challenged by AI Trainer!'

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

    # resets the multipliers and barriers
    def reset_stats_mult(self):
        self.atk_mult = 0
        self.def_mult = 0
        self.sp_atk_mult = 0
        self.sp_def_mult = 0
        self.speed_mult = 0
        self.ev_mult = 0
        self.acc_mult = 0

        self.reflect = False
        self.light_screen = False
        self.mist = False

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

    # resets all stats
    def reset_battle_stats(self):
        self.attack = self.max_attack
        self.defense = self.max_defense
        self.sp_atk = self.max_sp_atk
        self.sp_def = self.max_sp_def
        self.speed = self.max_speed
        self.accuracy = 1
        self.evasion = 1

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
            self.msg += '\nCritical hit!'
            return 2
        else: 
            return 1

    # calculates the damage to enemy using a certain move
    def calculate_damage(self, move, enemy):
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
        type1 = pkmn_types.get_effectiveness(move.typing, enemy.typing[0])                  # effectiveness vs enemy's type1

        if type1 == 0 or type2 == 0:
            crit = 0
        else:
            crit = self.calculate_crit_multiplier()                                         # critical-hit multiplier
            
        rand_list = [random.randint(217, 255) for i in range(9)]
        rand = 1
        for r in rand_list:
            rand *= r
        rand = r/255
        
        damage = int(((((2*self.level*crit)/5 + 2) * power * (a/d)) /50 + 2) * stab * type1 * type2 * rand)

        return damage

    # causes enemy's hp update throug the damage
    def hit(self, damage, attacker = None):
        # if there is not substitute, simply take damage
        if not self.substitute:
            self.hp -= damage
            if self.hp <= 0: 
                self.hp = 0
                self.fainted = True
        # else the substitute will take the damage
        else:
            self.sub_damage += damage
            attacker.msg += '\n{pkmn}\'s substitute was hit!'.format(pkmn = self.name)
            if self.sub_damage >= 255:
                self.substitute = False
                self.sub_damage = 0
                attacker.msg += '\n{pkmn}\'s substitute vanished!'.format(pkmn = self.name) 

    # attack function that handles the actual status modifier
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
            else:
                self.atk(move, enemy)
        # CONFUSION STATUS
        if self.temp_status != None:
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
                    a = self.attack
                    d = self.defense

                    damage = int((((2*self.level)/5 + 2) * power * (a/d)) /50 + 2)
                    self.hit(damage)
                    self.msg += '\nIt\'s so confused to hit itself!'.format(pkmn = self.name)
            else:
                self.temp_status = None
                self.atk(move, enemy)
                self.msg += '\n{pkmn} is not confused anymore!'.format(pkmn = self.name)
        # NO STATUSES
        elif self.temp_status == None and self.status == None:
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
                    # handling effectiveness
                    type2 = 1
                    type1 = pkmn_types.get_effectiveness(move.typing, enemy.typing[0])                  # effectiveness vs enemy's type1
                    tmp = '' 
                    if move.name != 'Dream Eater' and enemy.status != 'SLP':                                                                           # tmp variable with effectiveness status, to send to textbox
                        if len(enemy.typing) == 2:
                            type2 = pkmn_types.get_effectiveness(move.typing, enemy.typing[1])              # effectiveness vs enemy's type2
                            if ((type1 == 0.5 and type2 == 1) or (type1 == 1 and type2 == 0.5)) or (type1 == 0.5 and type2 == 0.5):
                                tmp += '\nIt\'s not very effective...'
                            elif ((type1 == 2 and type2 == 1) or (type1 == 1 and type2 == 2)) or (type1 == 2 and type2 == 2):
                                tmp += '\nIt\'s super effective!'
                            elif type1 == 0 or type2 == 0:
                                tmp += '\nIt has no effect...'
                        else:
                            if type1 == 0.5:
                                tmp += '\nIt\'s not very effective...'
                            elif type1 == 2:
                                tmp += '\nIt\'s super effective!'
                            elif type1 == 0:
                                tmp += '\nIt has no effect...'

                    self.msg += tmp
                    
                    damage = self.calculate_damage(move, enemy)
                    if self.status == 'BRN': damage /= 2

                    # handlng moves with regain
                    if move.name == 'Absorb' or move.name == 'Mega Drain' or move.name == 'Leech Life':
                        regain = self.handle_recoil(enemy, damage, 50)
                        if self.hp + regain > self.max_hp:
                            self.hp = self.max_hp
                        else:
                            self.hp += regain
                        self.msg += '\nSucked health from {pkmn}!'.format(pkmn = enemy.name)
                    elif move.name == 'Dream Eater':
                        if enemy.status == 'SLP':
                            regain = self.handle_recoil(enemy, damage, 50)
                            if self.hp + regain > self.max_hp:
                                self.hp = self.max_hp
                            else:
                                self.hp += regain
                            self.msg += '\n{pkmn} dream was eaten!'.format(pkmn = self.enemy.name)
                        else:
                            self.msg += '\nIt does nothing...'
                            return

                    if self.temp_status != "CONF":
                        if enemy != self: 
                            self.handle_special_physical_move(move, enemy, damage)
                            if enemy.fainted:
                                self.msg += '\n{enemy} fainted!'.format(enemy = enemy.name)
                    else:
                        # if attacking pkmn is confused, it can hit hitself
                        prob = random.random()
                        if prob <= 0.5: 
                            self.msg = '{pkmn} is so confused to hit itself!'.format(pkmn = self.name)
                            self.hit(damage)
                            if self.fainted:
                                self.msg += '\n{pkmn} fainted!'.format(pkmn = self.name)
                else:
                    # print("Non damaging move")
                    self.handle_status_move(move, enemy)
            else:
                if 'jump kick' in move.name.lower():
                    self.msg += '\n{pkmn} lost its poise and damaged itself!'.format(pkmn = self.name)
                    self.hit(1)
                else:
                    self.msg += '\nBut it failed...'

            move.pp = move.pp - 1
        # if move has any pp left
        else:
            cnt_moves = 0                           # number of actual moves in moveset
            cnt_no_pp = 0                           # number of moves with no pp
            for mv in self.moves:
                if mv != None:
                    cnt_moves += 1 
                    if mv.pp == 0:
                        cnt_no_pp += 1

            # if no move has pp left
            if cnt_no_pp == cnt_moves:
                power = 50
                a = self.level
                b = self.attack
                c = enemy.defense

                damage = int((((2*a/5 + 2) * b * 40)/c)/50) + 2
                    
                recoil = self.handle_recoil(enemy, damage, 50)
                self.msg = '{pkmn} has no moves left!\n{pkmn} uses Struggle!\n{pkmn} is hit with recoil!'.format(pkmn = self.name)
                enemy.hit(damage, self)
                self.hit(recoil, self)
            # if other moves have pp left
            else:
                self.msg = 'This move has any pp left!'

    # calculate recoil with moves that cause recoil
    def handle_recoil(self, enemy, damage, perc_scaler):
        scaler = perc_scaler / 100
        if enemy.hp - damage < 0:
            damage_caused = damage - (enemy.hp - damage)
        else:
            damage_caused = damage
            
        recoil = int(damage_caused * scaler)
        return recoil

    # handles all moves that cause a
    # status or stat-multiplier update
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
        elif move.name == 'Barrier':
            self.def_mult = self.inc_dec_stat_mult(self.defense, increase=True, highly=True)
            self.defense = self.update_battle_stat(self.defense, self.def_mult)
        elif move.name == 'Confuse Ray' or move.name == 'Supersonic':
            enemy.temp_status = 'CONF'
            self.msg += '\n{pkmn} is now confused!'.format(pkmn = enemy.name)
        elif move.name == 'Conversion':
            self.typing = enemy.typing
            self.msg += '\n{player_mon} assumes {enemy_mon} types!'.format(player_mon = self.name, enemy_mon = enemy.name)
        elif move.name == 'Defense Curl' or move.name == 'Harden' or move.name == 'Withdraw':
            self.def_mult = self.inc_dec_stat_mult(self.def_mult, increase=True)
            self.defense = self.update_battle_stat(self.defense, self.def_mult)
        elif move.name == 'Double Team':
            self.ev_mult = self.inc_dec_stat_mult(self.ev_mult, increase=True)
            self.evasion = self.update_battle_stat(self.evasion, self.ev_mult)
        elif move.name == 'Flash' or move.name == 'Kinesis' or move.name == 'Sand Attack':
            if not enemy.mist:
                enemy.acc_mult = self.inc_dec_stat_mult(enemy.acc_mult, increase=False, enemy=enemy)
                enemy.accuracy = self.update_battle_stat(enemy.accuracy, enemy.acc_mult)
            else:
                self.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
        elif move.name == 'Glare' or move.name == 'Stun Spore' or move.name == 'Thunder Wave':
            if not enemy.substitute:
                if enemy.status == None:
                    enemy.status = 'PAR'
                    enemy.speed -= (0.75 * enemy.speed)
                    self.msg += '\n{pkmn} is paralized! Maybe it can\'t attack!'.format(pkmn = enemy.name)
                else:
                    self.msg += '\nBut nothing happened...'
            else:
                self.msg += '\n{pkmn}\'s Substitute prevents its status change!'.format(pkmn = enemy.name)
        elif move.name == 'Growl':
            if not enemy.mist:
                enemy.atk_mult = self.inc_dec_stat_mult(enemy.atk_mult, increase=False, enemy=enemy)
                enemy.attack = enemy.update_battle_stat(enemy.attack, enemy.atk_mult)
            else:
                self.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
        elif move.name == 'Growth':
            self.sp_atk_mult = self.inc_dec_stat_mult(self.sp_atk_mult, increase=True)
            self.sp_atk = self.update_battle_stat(self.sp_atk, self.sp_atk_mult)
            self.sp_def_mult = self.inc_dec_stat_mult(self.sp_def_mult, increase=True)
            self.sp_def = self.update_battle_stat(self.sp_def, self.sp_def_mult)
        elif move.name == 'Haze':
            self.reset_stats_mult()
            self.reset_battle_stats()
            enemy.reset_stats_mult()
            enemy.reset_battle_stats()
            self.msg += '\nAll stats changes have been reset!'
        elif move.name == 'Hypnosis' or move.name == 'Lovely Kiss' or move.name == 'Sing' or move.name == 'Spore' or move.name == 'Sleep Powder':
            if not enemy.substitute:
                if enemy.status == None:
                    enemy.status = 'SLP'
                    self.msg += '\n{pkmn} is now sleeping!'.format(pkmn = enemy.name)
                else:
                    self.msg += '\nBut nothing happened...'
            else:
                self.msg += '\n{pkmn}\'s Substitute prevents its status change!'.format(pkmn = enemy.name)
        elif move.name == 'Leech Seed':
            if not enemy.substitute:
                if not enemy.seeded:
                    # if there are two types
                    if (len(enemy.typing) == 2):
                        # if no one of the types is grass
                        if enemy.typing[0] != 'GRASS' and enemy.typing[1] != 'GRASS':
                            enemy.seeded = True
                            self.msg += '\n{pkmn} was seeded!'.format(pkmn = enemy.name)
                        else: 
                            self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                    # if the only type is not grass
                    elif enemy.typing[0] != 'GRASS':
                        enemy.seeded = True
                        self.msg += '\n{pkmn} was seeded!'.format(pkmn = enemy.name)
                    else:
                        self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                # if enemy is already seeded
                else:
                    self.msg += '\nBut {pkmn}\'s is already seeded...'.format(pkmn = enemy.name)
            # there is a substitute
            else:
                self.msg += '\n{pkmn}\'s Substitute prevents Leech Seed!'.format(pkmn = enemy.name)
        elif move.name == 'Light Screen':
            if not self.light_screen:
                self.light_screen = True
                if (self.sp_def * 2) > 1024:
                    self.sp_def = 1024
                else:
                    self.sp_def *= 2
                self.msg += '\n{pkmn} protected against special attacks!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut Light Screen is already covering {pkmn}...'.format(pkmn = self.name)
        elif move.name == 'Meditate' or move.name == 'Minimize':
            self.ev_mult = self.inc_dec_stat_mult(self.ev_mult, increase=True)
            self.evasion = self.update_battle_stat(self.evasion, self.ev_mult)
        elif move.name == 'Metronome':
            rand_move_tmp = random.choice(moves.attacks)
            rand_move = Move(rand_move_tmp['name'], rand_move_tmp['type'], rand_move_tmp['power'], rand_move_tmp['pp'], rand_move_tmp['category'], rand_move_tmp['accuracy'])
            self.atk(rand_move, enemy)
        elif move.name == 'Mimic':
            m = random.choice(enemy.moves)
            if m != None:
                if m.name == 'Mimic':
                    self.msg += '\nBut it failed...'
                else:
                    self.atk(m, enemy)
                    self.msg += '\n{player_mon} copies one of {enemy_mon}\'s moves!'.format(player_mon = self.name, enemy_mon = enemy.name)
            else: 
                self.msg += '\nBut it failed...'
        elif move.name == 'Mist':
            if not self.mist:
                self.mist = True
                self.msg += '\n{pkmn} is shrouded in Mist!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut there is already a Mist covering {pkmn}...'.format(pkmn = self.name)
        elif move.name == 'Poison Gas' or move.name == 'Poison Powder':
            if not enemy.substitute:
                if enemy.status == None:
                    if (len(enemy.typing) == 2):
                        if enemy.typing[0] != 'POISON' and enemy.typing[1] != 'POISON':
                            enemy.status = 'PSN'
                            self.msg += '\n{pkmn} is poisoned!'.format(pkmn = enemy.name)
                        else: 
                            self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                    elif enemy.typing[0] != 'POISON':
                        enemy.status = 'PSN'
                        self.msg += '\n{pkmn} is poisoned!'.format(pkmn = enemy.name)
                    else: 
                        self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                else:
                    self.msg += '\nBut nothing happened...'
            else:
                self.msg += '\n{pkmn}\'s Substitute prevents its status change!'.format(pkmn = enemy.name)
        elif move.name == 'Recover' or move.name == 'Soft Boiled':
            if self.hp < self.max_hp:
                self.hp += (0.5) * self.max_hp
                if self.hp > self.max_hp: self.hp = self.max_hp
                self.msg += '\n{pkmn} restores half of its hp!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut {pkmn} already has all its hp!'.format(pkmn = self.name)
        elif move.name == 'Reflect':
            if not self.reflect: 
                self.reflect = True
                if (self.defense * 2) > 1024:
                    self.defense = 1024
                else:
                    self.defense *= 2
                self.msg += '\n{pkmn} gained armor!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut Reflect is already covering {pkmn}...'.format(pkmn = self.name)
        elif move.name == 'Rest':
            if self.hp < self.max_hp or self.status != None:
                # reset status
                if self.status != None: self.status = None                  
                if self.temp_status != None: self.temp_status = None
                self.hp = self.max_hp
                self.status = 'SLP'
                self.msg += '\n{pkmn} went to sleep and regained health!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut {pkmn} already has all its hp!'.format(pkmn = self.name)
        elif move.name == 'Roar' or move.name == 'Splash' or move.name == 'Teleport' or move.name == 'Whirlwind':
            self.msg += '\nBut nothing happened...'
        elif move.name == 'Screech':
            if not enemy.mist:
                enemy.def_mult = self.inc_dec_stat_mult(enemy.def_mult, increase=False, enemy=enemy)
                enemy.defense = enemy.update_battle_stat(enemy.defense, enemy.def_mult)
            else:
                self.msg += '\nBut {pkmn}\'s Mist prevents its stats decrease...'.format(pkmn = enemy.name)
        elif move.name == 'String Shot':
            if not enemy.mist:
                enemy.speed_mult = self.inc_dec_stat_mult(enemy.speed_mult, increase=False, enemy=enemy)
                enemy.speed = enemy.update_battle_stat(enemy.speed, enemy.speed_mult)
            else:
                self.msg += '\nBut {pkmn}\'s Mist prevents its stats decrease...'.format(pkmn = enemy.name)
        elif move.name == 'Substitute':
            if not self.substitute:
                if self.hp >= (0.3 * self.max_hp):
                    self.hp -= math.floor(0.25 * self.max_hp)
                    self.substitute = True
                    self.msg += '\n{pkmn} is replaced by a substitute doll!'.format(pkmn = self.name)
            else:
                self.msg += '\nBut {pkmn} is already protected by a substitute doll...'.format(pkmn = self.name)
        elif move.name == 'Sharpen':
            self.atk_mult = self.inc_dec_stat_mult(self.atk_mult, increase=True)
            self.attack = self.update_battle_stat(self.attack, self.atk_mult)
        elif move.name == 'Swords Dance':
            self.atk_mult = self.inc_dec_stat_mult(self.atk_mult, increase=True, highly=True)
            self.attack = self.update_battle_stat(self.attack, self.atk_mult)
        elif move.name == 'Tail Whip' or move.name == 'Leer':
            if not enemy.mist:
                enemy.def_mult = self.inc_dec_stat_mult(enemy.def_mult, increase=False, enemy=enemy)
                enemy.defense = enemy.update_battle_stat(enemy.defense, enemy.def_mult)
            else:
                self.msg += '\nBut {enemy_mon}\'s Mist prevents its stats decrease...'
        elif move.name == 'Toxic':
            if not enemy.substitute:
                if enemy.status == None:
                    if (len(enemy.typing) == 2):
                        if enemy.typing[0] != 'POISON' and enemy.typing[1] != 'POISON':
                            enemy.status = 'TOX'
                            self.msg += '\n{pkmn} is intoxicated!'.format(pkmn = enemy.name)
                        else: 
                            self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                    elif enemy.typing[0] != 'POISON':
                        enemy.status = 'TOX'
                        self.msg += '\n{pkmn} is intoxicated!'.format(pkmn = enemy.name)
                    else: 
                        self.msg += '\nIt has not effect on {pkmn}...'.format(pkmn = enemy.name)
                else:
                    self.msg += '\nBut nothing happened...'
            else:
                self.msg += '\n{pkmn}\'s Substitute prevents its status change!'.format(pkmn = enemy.name)
        elif move.name == 'Transform':
            self.msg += '\n{player_mon} transforms into {enemy_mon}!'.format(player_mon = self.name, enemy_mon = enemy.name)
            self.transformed = True

            self.id = enemy.id
            self.typing = enemy.typing
            self.moves = deepcopy(enemy.moves)

            self.max_attack = deepcopy(enemy.max_attack)
            self.max_defense = deepcopy(enemy.max_defense)
            self.max_sp_atk = deepcopy(enemy.max_sp_atk)
            self.max_sp_def = deepcopy(enemy.max_sp_def)
            self.max_speed = deepcopy(enemy.max_speed)

            self.attack = deepcopy(enemy.attack)
            self.defense = deepcopy(enemy.defense)
            self.sp_atk = deepcopy(enemy.sp_atk)
            self.sp_def = deepcopy(enemy.sp_def)
            self.speed = deepcopy(enemy.speed)
            
            for m in self.moves:
                if m != None:
                    m.pp = int(m.max_pp/2)
    
    # handles all physical/special moves that have
    # particular or secondary effects (like status modifier)
    def handle_special_physical_move(self, move, enemy, damage):
        if move.typing == 'Fire':
            enemy.hit(damage, self)
            if not enemy.substitute:
                prob = random.randint(0, 100)
                if prob <= 10:
                    enemy.status = 'BRN'
                    self.msg += '\n{pkmn} is burned!'.format(pkmn = enemy.name)
        if move.name == 'Body Slam':
            enemy.hit(damage, self)
            if not enemy.substitute:
                prob = random.randint(0, 100)
                if prob <= 30:
                    enemy.status = 'PAR'
                    enemy.speed -= (0.75 * enemy.speed)
                    self.msg += '\n{pkmn} is paralized! Maybe it can\'t attack!'.format(pkmn = enemy.name)
        if move.name == 'Confusion':
            enemy.hit(damage, self)
            prob = random.randint(0, 100)
            if prob <= 10:
                enemy.temp_status = 'CONF'
                self.msg += '\n{pkmn} is now confused!'.format(pkmn = enemy.name)
        if move.name == 'Explosion':
            enemy.hit(damage, self)
            self.hit(self.max_hp)
        elif move.name == 'Fissure' or move.name == 'Guillotine':
            enemy.hit(enemy.max_hp, self)
        elif move.name == 'Fury Swipes' or move.name == 'Fury Attack' or move.name == 'Double Slap' or move.name == 'Wrap':
            cnt = 1
            enemy.hit(damage, self)
            while cnt < 5:
                prob = random.randint(0, 100)
                if cnt < 2:
                    if prob <= 37:
                        enemy.hit(damage, self)
                        cnt += 1
                    else:
                        break
                elif cnt >= 2 and cnt < 5:
                    if prob <= 12:
                        enemy.hit(damage, self)
                        cnt += 1
                    else:
                        break
            self.msg += '\nHit {cnt} time(s)!'.format(cnt = cnt)
        elif move.name == 'Poison Sting':
            enemy.hit(damage, self)
            if not enemy.substitute:
                if (len(enemy.typing) == 2):
                    if enemy.typing[0] != 'POISON' and enemy.typing[1] != 'POISON':
                        prob = random.randint(0, 100)
                        if prob <= 20:
                            enemy.status = 'PSN'
                            self.msg += '\n{pkmn} is poisoned!'.format(pkmn = enemy.name)
                    else: 
                        pass
                elif enemy.typing[0] != 'POISON':
                    prob = random.randint(0, 100)
                    if prob <= 20:
                        enemy.status = 'PSN'
                        self.msg += '\n{pkmn} is poisoned!'.format(pkmn = enemy.name)
                else: 
                    pass
        else:
            # normal attack, without any particular effects
            enemy.hit(damage, self)