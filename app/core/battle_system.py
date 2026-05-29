import logging

from app.core.combat import handle_burn_poison, handle_leech_seed, handle_toxicity

logger = logging.getLogger(__name__)

class TurnBattleSystem:
    """
    Manages the turn-based flow of a Pokémon battle between a player and an AI opponent.
    Tracks turn ownership, switches turns, and triggers per-turn status effects.

    Attributes:
        player (Trainer): The human or player-controlled trainer.
        ai (TrainerAI): The AI-controlled trainer.
        player_mon (BattlePokemon): The player's currently active Pokémon.
        enemy_mon (BattlePokemon): The AI's currently active Pokémon.
        turn_count (int): Counter for the number of turns elapsed since battle start.
    """

    def __init__(self, player, ai):
        self.player = player
        self.ai = ai
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        self.turn_count = 1

        self.player.token = True
        self.ai.token = False

        self.player_msg = 'You are challenged by AI Trainer!'
        self.enemy_msg = ''
    
    def switch_turn(self):
        if self.player.token:
            self.player.token = False
            self.ai.token = True
            logger.info("----- END PLAYER TURN -----")
            logger.info("----- START AI TURN -----")
        elif self.ai.token:
            self.ai.token = False
            self.player.token = True
            logger.info("----- END AI TURN -----")
            logger.info("----- START PLAYER TURN -----")
        
        self.turn_count += 1
        logger.info(f'Turn n: {self.turn_count}')

    def get_turn(self):
        if self.player.token:
            return 'PL'
        else:
            return 'AI'

    def get_player(self):
        return self.player

    def get_ai(self):
        return self.ai

    def handle_turns(self):
        self.player_mon = self.player.in_battle         # prevents non updating target
        ai_win_msg = f'AI Trainer won the battle...\nThe battle lasted {self.turn_count} turns.'
        ai_lose_msg = f'AI Trainer lost the battle!\nThe battle lasted {self.turn_count} turns.'

        if self.player.game_over_lose() or self.ai.game_over_lose():
            if self.player.game_over_lose():
                self.player_msg = ai_win_msg
                self.enemy_msg = ai_win_msg
            else:
                self.player_msg = ai_lose_msg
                self.enemy_msg = ai_lose_msg
        else:
            if self.player.is_turn():
                pass
            else:
                ai_msg = self.ai.get_choice(self.player_mon)
                if ai_msg:
                    self.enemy_msg = ai_msg
                self.handle_status_by_turn()
                self.switch_turn()

    def handle_status_by_turn(self):
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        msgs = []
        for fn in (handle_burn_poison, handle_toxicity, handle_leech_seed):
            msg = fn(self.player_mon, self.enemy_mon)
            if msg:
                msgs.append(msg)
        if msgs:
            self.player_msg = '\n'.join(msgs)