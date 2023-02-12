import time

class TurnBattleSystem:
    def __init__(self, player, ai):
        self.player = player
        self.ai = ai
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        self.turn_count = 1                     # turn counter

        # first turn is of the player
        self.player.token = True
    
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
            print('Player\'s turn')
            return 'PL'
        else:
            print('AI\'s turn')
            return 'AI'

    def get_player(self):
        return self.player

    def get_ai(self):
        return self.ai

    def handle_turns(self):
        if self.player.is_turn():
            pass
        else:
            self.player_mon = self.player.in_battle
            self.ai.get_choice(self.player_mon)
            self.switch_turn()
            