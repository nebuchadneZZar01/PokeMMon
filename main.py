import os, sys
import argparse
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import battle_system
import gui
from player import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pokémon combat system (1st gen) re-implementation using MiniMax-type algorithms.\
                                            \nAuthor: nebuchadneZZar01 (Michele Ferro)\
                                            \nGitHub: https://github.com/nebuchadneZZar01/PokeMMon\
                                            \nAll credits of the material used (characters, sounds, images and ideas) belong to The Pokémon Company, Nintendo, Game Freak and Creatures Inc.',\
                                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ai', type=str, help='artificial intelligence algorithm used [random/minimax/alphabeta/expectimax] (default: minimax)', default='minimax')
    parser.add_argument('--depth', type=int, help='maximum depth of the nodes to visit in game\'s tree (default: 7)', default='7')
    parser.add_argument('--s', type=str, help='sound [Y/n] (default: yes)', default='y')
    args = parser.parse_args()
    
    if args.s.lower() == 'y':
        sound = True
    else:
        sound = False

    player = Trainer()

    if args.ai == 'random':
        ai = RandomAI()
    if args.ai == 'minimax':
        ai = MinimaxAI(player, args.depth)
    elif args.ai == 'alphabeta':
        ai = MMAlphaBetaAI(player, args.depth)
    elif args.ai == 'expectimax':
        ai = ExpectiMaxAI(player, args.depth)

    ai.get_team()

    bs = battle_system.TurnBattleSystem(player, ai)

    gui.pygame.display.set_caption('PokéMMon')
    icon = gui.pygame.image.load(os.path.join('assets/icon.svg'))
    gui.pygame.display.set_icon(icon)
    gui.pygame.init()
    game_gui = gui.GameWindow(bs, sound)

    while True:
        clock = gui.pygame.time.Clock()
        clock.tick(60)
        
        event = gui.pygame.event.poll()
        if event.type == gui.pygame.QUIT:
            gui.pygame.display.quit()
            gui.pygame.quit()
            break

        game_gui.draw()
        bs.handle_turns()