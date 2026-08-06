import logging

from app.core.combat import handle_burn_poison, handle_leech_seed, handle_toxicity, handle_trapped

logger = logging.getLogger(__name__)

class TurnBattleSystem:
    """
    Manages the turn-based flow of a Pokémon battle between a player and an AI opponent.
    Tracks turn ownership, switches turns, and triggers per-turn status effects.

    Attributes:
        player (Trainer): The human or player-controlled trainer.
        ai (Trainer): The AI-controlled trainer.
        player_mon (BattlePokemon): The player's currently active Pokémon.
        enemy_mon (BattlePokemon): The AI's currently active Pokémon.
        turn_count (int): Counter for the number of turns elapsed since battle start.
    """

    def __init__(self, player, ai):
        """Initialize a turn-based battle between a player and an AI trainer.

        Args:
            player (Trainer): The player-controlled trainer.
            ai (Trainer): The AI-controlled trainer.
        """
        self.player = player
        self.ai = ai
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        self.turn_count = 1

        self.player.token = True
        self.ai.token = False

        self.player_msg = f'You are challenged by {self.ai.name}!'
        self.enemy_msg = ''

        self.message_log: list[tuple[int, str, str]] = []
    
    def log_message(self, side: str, text: str) -> None:
        """Append a message to the battle log, skipping duplicates and empties.

        Args:
            side (str): 'player', 'ai', or 'field'.
            text (str): The message text.
        """
        if not text.strip():
            return
        if self.message_log and self.message_log[-1][1:] == (side, text):
            return
        round_n = (self.turn_count + 1) // 2
        self.message_log.append((round_n, side, text))
        if len(self.message_log) > 30:
            del self.message_log[:len(self.message_log) - 30]

    def switch_turn(self):
        """Swap the turn token between player and AI and increment turn counter."""
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
        """Get the current turn owner.

        Returns:
            str: 'PL' for player turn, 'AI' for AI turn.
        """
        if self.player.token:
            return 'PL'
        else:
            return 'AI'

    def get_player(self):
        """Get the player trainer.

        Returns:
            Trainer: The player trainer instance.
        """
        return self.player

    def get_ai(self):
        """Get the AI trainer.

        Returns:
            Trainer: The AI trainer instance.
        """
        return self.ai

    def handle_turns(self):
        """Process a single turn: check win conditions, execute AI move, apply status effects."""
        self.player_mon = self.player.in_battle         # prevents non updating target
        ai_win_msg = f'{self.ai.name} won the battle...\nThe battle lasted {self.turn_count} turns.'
        ai_lose_msg = f'{self.ai.name} lost the battle!\nThe battle lasted {self.turn_count} turns.'

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
                ai_msg = self.ai.get_choice(self.player)
                if ai_msg:
                    self.enemy_msg = ai_msg
                self.handle_status_by_turn()
                self.switch_turn()

    def handle_status_by_turn(self):
        """Apply end-of-turn status effects to both sides."""
        self.player_mon = self.player.in_battle
        self.enemy_mon = self.ai.in_battle

        msgs = []
        for fn in (handle_burn_poison, handle_toxicity, handle_leech_seed, handle_trapped):
            msg = fn(self.player_mon, self.enemy_mon)
            if msg:
                msgs.append(msg)
        if msgs:
            sep = '\n' if self.player_msg else ''
            self.player_msg += sep + '\n'.join(msgs)