# PokéMMon
This is a *Pokémon* battles' implementation with the use of MiniMax-type algorithms, developed as project for the Artificial Intelligence course (university subject).

## Description
This Python software is a *PyGame* re-implementation of the 1st gen. Pokémon games' (Red/Blue/Yellow versions) **battle system**, with some QoL changes and bugfixes from the 2nd gen. (Gold/Silver/Crystal) ones.
It implements **MiniMax-type algoritms** to move the CPU player.\
All credits of the material used (characters, sounds, images and ideas) belong to *The Pokémon Company*, *Nintendo*, *Game Freak* and *Creatures Inc.*

## Getting Started
### Dependencies
- Python 3.10
- `pygame` module

### Installation
#### Linux

#### Windows

#### MacOS

### Execution
Run the `main.py` script to play the game. 

```
python main.py -h

usage: main.py [-h] [--ai AI] [--s S]

Pokémon combat system (1st gen) re-implementation using MiniMax-type algorithms.                                            
Author: nebuchadneZZar01 (Michele Ferro)                                            
GitHub: https://github.com/nebuchadneZZar01/PokeMMon                                            
All credits of the material used (characters, sounds, images and ideas) belong to The Pokémon Company, Nintendo, Game Freak and Creatures Inc.

options:
  -h, --help  show this help message and exit
  --ai AI     artificial intelligence algorithm used [random/minimax/alphabeta] (default: minimax)
  --s S       sound [Y/n] (default: yes)
```
Example using *Alpha-Beta pruning* algorithm, with sound activated:
```
python main.py --ai alphabeta --s y
```


### Author
- @nebuchadneZZar91 (Michele Ferro)