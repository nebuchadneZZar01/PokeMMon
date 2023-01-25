from player import *
import gui
import time

ember = Move('Ember', 'FIRE', 40, 25, False)
# char_moves = [ember, None, None, None]
# char = Pokemon('Charmander', char_moves, 'FIRE', 100, [39, 52, 43, 60, 50, 65])

# bulba_moves = [None, None, None, None]
# bulba = Pokemon('Bulbasaur', bulba_moves, ['GRASS', 'POISON'], 100, [39, 52, 43, 60, 50, 65])

player = Trainer()
ai = Trainer()

game_gui = gui.GameWindow(player, ai, True)

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.quit()
        break

    game_gui.draw()