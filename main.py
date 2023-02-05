from player import *
import gui
import time
import sys

player = Trainer()
ai = Trainer()

player.get_team()

args = sys.argv

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