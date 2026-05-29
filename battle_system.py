import math
from app.core.combat import hit, handle_burn_poison, handle_toxicity, handle_leech_seed

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
            print("----- END PLAYER TURN -----\n")
            print("\n----- START AI TURN -----")
        elif self.ai.token == True:
            self.ai.token = False
            self.player.token = True
            print("----- END AI TURN -----\n")
            print("\n----- START PLAYER TURN -----")
        
        self.turn_count += 1
        print('Turn n: {turn}'.format(turn = self.turn_count))

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
        ai_win_msg = 'AI Trainer won the battle...\nThe battle lasted {n_turns} turns.'.format(n_turns = self.turn_count)
        ai_lose_msg = 'AI Trainer lost the battle!\nThe battle lasted {n_turns} turns.'.format(n_turns = self.turn_count)

        if self.player.game_over_lose() or self.ai.game_over_lose():
            if self.player.game_over_lose():
                self.player_mon.msg = ai_win_msg
                self.enemy_mon.msg = ai_win_msg
            else:
                self.player_mon.msg = ai_lose_msg
                self.enemy_mon.msg = ai_lose_msg
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

        handle_burn_poison(self.player_mon, self.enemy_mon)

    def handle_toxicity(self):
        handle_toxicity(self.player_mon, self.enemy_mon)

    def handle_leech_seed(self):
        handle_leech_seed(self.player_mon, self.enemy_mon)

    def handle_status_by_turn(self):
        self.handle_burn_poison()
        self.handle_toxicity()            