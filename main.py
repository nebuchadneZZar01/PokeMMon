import battle_system
import gui
import time
import sys
from player import Trainer

player = Trainer()
ai = Trainer()

bs = battle_system.TurnBattleSystem(player, ai)

player.get_team()

args = sys.argv

gui.pygame.init()

if len(args) > 1:
    game_gui = gui.GameWindow(player, ai, True)
else:
    game_gui = gui.GameWindow(player, ai, False)

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.quit()
        break

    game_gui.draw()