import os
import argparse
from distutils.util import strtobool
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

parser = argparse.ArgumentParser(description='Pokémon combat system (1st gen) re-implementation using MiniMax-type algorithms.\
                                            \nAuthor: nebuchadneZZar01 (Michele Ferro)\
                                            \nGitHub: https://github.com/nebuchadneZZar01/PokeMMon\
                                            \nAll credits of the material used (characters, sounds, images and ideas) belong to The Pokémon Company, Nintendo, Game Freak and Creatures Inc.',\
                                            formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--ai', type=str, help='artificial intelligence algorithm used [random/minimax/alphabeta] (default: minimax)', default='minimax')
parser.add_argument('--s', type=str, help='sound [Y/n] (default: yes)', default='y')
args = parser.parse_args()

import battle_system
import res_logger
import gui
from player import *

monitor = res_logger.ProcessMonitor()
monitor.start()

player = Trainer()

if args.ai == 'random':
    ai = RandomAI()
if args.ai == 'minimax':
    ai = MinimaxAI(player)
elif args.ai == 'alphabeta':
    ai = MMAlphaBetaAI(player)

bs = battle_system.TurnBattleSystem(player, ai)

ai.get_team()

gui.pygame.display.set_caption('PokéMMon')
icon = gui.pygame.image.load(os.path.join('assets/icon.svg'))
gui.pygame.display.set_icon(icon)
gui.pygame.init()
game_gui = gui.GameWindow(bs, strtobool(args.s))

while True:
    clock = gui.pygame.time.Clock()
    clock.tick(60)

    event = gui.pygame.event.poll()
    if event.type == gui.pygame.QUIT:
        gui.pygame.display.quit()
        gui.pygame.quit()
        monitor.stop()
        break

    game_gui.draw()
    bs.handle_turns()

monitor.plot()
sys.exit()