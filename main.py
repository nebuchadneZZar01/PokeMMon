from pokemon import Pokemon
import gui
import time

char = Pokemon('Charmander', 'FIRE', 100, [39, 52, 43, 60, 50, 65])

bulba = Pokemon('Bulbasaur', ['GRASS', 'POISON'], 100, [39, 52, 43, 60, 50, 65])

game_gui = gui.GameWindow(char, bulba, False)

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.quit()
        break

    game_gui.draw()