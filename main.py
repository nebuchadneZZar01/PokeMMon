from player import *
import gui
import time

player = Trainer()
ai = Trainer()

player.get_team()

game_gui = gui.GameWindow(player, ai, True)

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.quit()
        break

    game_gui.draw()