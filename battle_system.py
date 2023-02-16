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
        if self.player.game_over_lose() or self.ai.game_over_lose():
            if self.player.game_over_lose():
                self.player_mon.msg = 'AI Trainer won the battle!'
            else:
                self.player_mon.msg = 'AI Trainer lost the battle!' 
        else:
            if self.player.is_turn():
                pass
            else:
                self.ai.get_choice(self.player_mon)
                self.handle_status_by_turn()
                self.switch_turn()
        
    def handle_burn_poison(self):
        # prevents non updating in battle pokemons
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        if self.player_mon.status == 'BRN' or self.player_mon.status == 'PSN':
            player_mon_max_hp = self.player_mon.max_hp
            self.player_mon.hit(math.floor((1/16)*player_mon_max_hp))
        elif self.enemy_mon.status == 'BRN' or self.enemy_mon.status == 'PSN':
            enemy_mon_max_hp = self.enemy_mon.max_hp
            self.enemy_mon.hit(math.floor(1/16)*enemy_mon_max_hp)

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
        elif self.enemy_mon.status == 'TOX':
            self.enemy_mon.toxic_turns += 1
            enemy_mon_max_hp = self.enemy_mon.max_hp
            damage = math.floor(1/16 * enemy_mon_max_hp) * self.enemy_mon.toxic_turns
            if damage >= 15 * math.floor(1/16 * enemy_mon_max_hp):
                damage = math.floor(1/16 * enemy_mon_max_hp)
            self.enemy_mon.hit(damage)

    def handle_status_by_turn(self):
        self.handle_burn_poison()
        self.handle_toxicity()            