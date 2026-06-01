<h1 align="center">
  <img src="./docs/icon.svg" width=100>
  <br>
  <b>PokéMMon</b>
  <br>
  <sup><sup>(Pokémon battles AI simulator)</sup></sup>
</h1>

This is a *Pokémon* battles' implementation with the use of MiniMax-type algorithms, firstly developed as project for the Artificial Intelligence course (university subject) and now revamped just for fun.

All credits of the material used (characters and ideas) belong to The Pokémon Company, Nintendo, Game Freak and Creatures Inc.


## Description
This Python software is a terminal-based re-implementation of the 1st gen. Pokémon games' (Red/Blue/Yellow versions) **battle system** via `rich` TUI, with data models via `pydantic` v2.
It implements **MiniMax-type algorithms** to move the CPU player.

These are the possible **strategies** that could move the rival agent:
- _Random_;
- _MiniMax_ (vanilla);
- _Alpha-Beta pruning MiniMax_;
- _ExpectiMax_;
- _LLM-based_ (**OpenAI**, **Gemini**, **Anthropic**, **Ollama**).

## Usage
### Dependencies
- Python >=3.14
- [`uv`](https://docs.astral.sh/uv/) package manager (or `pip`)

### Installation
After ensuring that Python >=3.14 is available and `uv` is installed:
```
uv sync
```
Or with pip:
```
pip install pydantic rich
```
Then, make a `git clone` of this repository or simply download it.

### Execution
Run the `main.py` script via `uv` (or activate the venv and use `python` directly):

```
uv run python main.py -h

usage: main.py [-h] [--ai AI] [--depth DEPTH] [--log LOG]

Pokémon battle simulator — terminal edition.                                            

options:
  -h, --help     show this help message and exit
  --ai AI        AI algorithm [random/minimax/alphabeta/expectimax] (default: minimax)
  --depth DEPTH  max search depth (default: 7)
  --log LOG      show AI battle logs [info/debug]
```
Example using *Alpha-Beta pruning* algorithm (default depth), with AI logs:
```
uv run python main.py --ai alphabeta --log info
```
During the execution of the game you choose actions via keyboard: 1-4 to attack, 5 to open team view, 6 to forfeit.
The AI logs can be enabled via `--log {info,debug}` to explain the algorithm(s) computations.

- **Battle view** (default):
  ```
  ╭────────────────────────────────────  AI  ────────────────────────────────────╮
  │   Tangela    Lv100                                                           │
  │   HP ████████████████████  240/240                                           │
  │   OK               Team ●●●●●●                                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭──────────────────────────────────  Player  ──────────────────────────────────╮
  │   Flareon    Lv100                                                           │
  │   HP ████████████████████  240/240                                           │
  │   OK               Team ●●●●●●                                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─────────────────────────────────  Message  ──────────────────────────────────╮
  │ Flareon used Take Down!                                                      │
  ╰──────────────────────────────────────────────────────────────────────────────╯
    [1] Skull Bash       - NORMAL 15/15
    [2] Double Team      - NORMAL 15/15
    [3] Take Down        - NORMAL 20/20
    [4] Substitute       - NORMAL 10/10

    [5] Team     [6] Forfeit
  Action [1/2/3/4/5/6]:
  ```

- **Team view** (press <kbd>5</kbd>):
  ```
  ╭───────────────────────────────  Your Team  ──────────────────────────────────╮
  │                                                                              │
  │   [1] Flareon   ████████████████   240/240          OK                       │
  │                 NORMAL                                                       │
  │                                                                              │
  │   [2] Vaporeon  ████████████████   240/240          OK                       │
  │                 WATER                                                        │
  │                                                                              │
  │   [3] Jolteon   ████████████████   130/240          OK                       │
  │                 ELECTRIC                                                     │
  │                                                                              │
  │   [4] Espeon    ████████████████   240/240          OK                       │
  │                 PSYCHIC                                                      │
  │                                                                              │
  │   [5] Umbreon   ████████████████   240/240          OK                       │
  │                 DARK                                                         │
  │                                                                              │
  │   [6] Leafeon   ████████████████   240/240          OK                       │
  │                 GRASS                                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

    Choose (1-6) to switch, [0] back to battle
  ```

## Development

```bash
uv run ruff check          # lint
uv run pytest tests/ -v    # run tests
```

## Known bugs
- When using a non-damaging move that updates stat multipliers (like "Growl", "Tail Whip", "Double Team" etc.), the first use may display the wrong stat name in the message; subsequent uses display correctly.

## Author
- [@nebuchadneZZar01](https://github.com/nebuchadneZZar01) (Michele Ferro)
