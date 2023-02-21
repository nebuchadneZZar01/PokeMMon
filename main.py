import battle_system
import gui
import time
import sys
import os
from player import *

player = Trainer()
ai = MMAlphaBetaAI(player)

bs = battle_system.TurnBattleSystem(player, ai)

player.get_team()

args = sys.argv

gui.pygame.display.set_caption('PokéMMon')
icon = gui.pygame.image.load(os.path.join('assets/icon.svg'))
gui.pygame.display.set_icon(icon)
gui.pygame.init()
game_gui = gui.GameWindow(bs, True)

# if len(args) > 1:
#     game_gui = gui.GameWindow(bs, True)
# else:
#     game_gui = gui.GameWindow(bs, False)

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.display.quit()
        gui.pygame.quit()
        sys.exit()
        break

    game_gui.draw()
    bs.handle_turns()