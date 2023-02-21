import math

class TurnBattleSystem:
    def __init__(self, player, ai):
        self.player = player
        self.ai = ai
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        self.turn_count = 1                     # turn counter

        # first turn is of the player
        self.player.token = True
        self.ai.token = False
    
    def switch_turn(self):
        if self.player.token == True:
            self.player.token = False
            self.ai.token = True
        elif self.ai.token == True:
            self.ai.token = False
            self.player.token = True
        
        self.turn_count += 1

    def get_turn(self):
        if self.player.token == True:
            # player turn
            return 'PL'
        else:
            # AI turn
            return 'AI'

    def get_player(self):
        return self.player

    def get_ai(self):
        return self.ai

    def handle_turns(self):
        self.player_mon = self.player.in_battle         # prevents non updating target

        if self.player.game_over_lose() or self.ai.game_over_lose():
            if self.player.game_over_lose():
                self.player_mon.msg = 'AI Trainer won the battle!'
                self.enemy_mon.msg = 'AI Trainer won the battle!'
            else:
                self.player_mon.msg = 'AI Trainer lost the battle!' 
                self.enemy_mon.msg = 'AI Trainer lost the battle!'
        else:
            if self.player.is_turn():
                pass
            else:
                self.ai.get_choice(self.player_mon)
                self.handle_status_by_turn()
                self.handle_leech_seed()
                self.switch_turn()

    # damages every turn
    def handle_burn_poison(self):
        # prevents non updating in battle pokemons
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        if self.player_mon.status == 'BRN' or self.player_mon.status == 'PSN':
            player_mon_max_hp = self.player_mon.max_hp
            self.player_mon.hit(math.floor((1/16)*player_mon_max_hp))
            if self.player_mon.status == 'BRN':
                self.player_mon.msg += '\n{pkmn} is hurt by its burn!'.format(pkmn = self.player_mon.name)
            else:
                self.player_mon.msg += '\n{pkmn} is hurt by poison!'.format(pkmn = self.player_mon.name)
        if self.enemy_mon.status == 'BRN' or self.enemy_mon.status == 'PSN':
            enemy_mon_max_hp = self.enemy_mon.max_hp
            self.enemy_mon.hit(math.floor((1/16)*enemy_mon_max_hp))
            if self.player_mon.status == 'BRN':
                self.enemy_mon.msg += '\n{pkmn} is hurt by its burn!'.format(pkmn = self.enemy_mon.name)
            else:
                self.enemy_mon.msg += '\n{pkmn} is hurt by poison!'.format(pkmn = self.enemy_mon.name)

    # like PSN, but it encreases the damage every turn
    def handle_toxicity(self):
        # prevents non updating in battle pokemons
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        if self.player_mon.status == 'TOX':
            self.player_mon.toxic_turns += 1
            player_mon_max_hp = self.player_mon.max_hp
            damage = math.floor(1/16 * player_mon_max_hp) * self.player_mon.toxic_turns
            if damage >= 15 * math.floor(1/16 * player_mon_max_hp):
                damage = math.floor(1/16 * player_mon_max_hp)
            self.player_mon.hit(damage)
            self.player_mon.msg += '\n{pkmn} is hurt by toxine!'.format(pkmn = self.player_mon.name)
        if self.enemy_mon.status == 'TOX':
            self.enemy_mon.toxic_turns += 1
            enemy_mon_max_hp = self.enemy_mon.max_hp
            damage = math.floor(1/16 * enemy_mon_max_hp) * self.enemy_mon.toxic_turns
            if damage >= 15 * math.floor(1/16 * enemy_mon_max_hp):
                damage = math.floor(1/16 * enemy_mon_max_hp)
            self.enemy_mon.hit(damage)
            self.enemy_mon.msg += '\n{pkmn} is hurt by toxine!'.format(pkmn = self.enemy_mon.name)

    # damage mon and heals enemy_mon every turn if mon is seeded (and viceversa)
    def handle_leech_seed(self):
        # prevents non updating in battle pokemons
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        if self.player_mon.seeded:
            player_mon_max_hp = self.player_mon.max_hp
            damage = math.floor((1/16)*player_mon_max_hp)
            self.player_mon.hit(damage)
            if (self.enemy_mon.hp + damage) > self.enemy_mon.max_hp:
                self.enemy_mon.hp = self.enemy_mon.max_hp
            else:
                self.enemy_mon.hp += damage
            self.player_mon.msg += '\nLeech Seed saps {pkmn}!'.format(pkmn = self.player_mon.name)

        if self.enemy_mon.seeded:
            enemy_mon_max_hp = self.enemy_mon.max_hp
            damage = math.floor(math.floor((1/16)*enemy_mon_max_hp))
            self.enemy_mon.hit(damage)
            if (self.player_mon.hp + damage) > self.player_mon.max_hp:
                self.player_mon.hp = self.player_mon.max_hp
            else:
                self.player_mon.hp += damage
            self.enemy_mon.msg += '\nLeech Seeds saps {pkmn}!'.format(pkmn = self.enemy_mon.name)

    def handle_status_by_turn(self):
        self.handle_burn_poison()
        self.handle_toxicity()            