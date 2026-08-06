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
- _LLM agent_ (LangGraph-based, via OpenAI/Anthropic/Gemini/Ollama).

## Usage
### Dependencies
- Python >=3.14
- [`uv`](https://docs.astral.sh/uv/) package manager

### Installation
After ensuring that Python >=3.14 is available and `uv` is installed:
```
uv sync
```
Then, make a `git clone` of this repository or simply download it.

### Execution
Run the `main.py` script via `uv` (or activate the venv and use `python` directly):
```
uv run python main.py
```
The game starts with an interactive **battle setup menu** where you choose:
- the **AI algorithm** (`random`/`minimax`/`alphabeta`/`expectimax`/`llm`, default `minimax`);
- the **search depth** for the minimax-based algorithms (default 7);
- the **LLM provider**, model and API key/URL when `llm` is selected;
- the **log level** (`silent`/`info`/`debug`, default `silent`).

Once the battle starts, you choose actions via keyboard: 1-4 to attack, 5 to open team view, 6 to forfeit.
The AI logs can be enabled by picking `info` or `debug` in the setup menu to explain the algorithm computations.

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
uv run mypy app main.py    # type check
uv run pytest tests/ -v    # run tests
uv run pytest --cov=app    # test coverage (fail_under 90)
```

## Known bugs
- When using a non-damaging move that updates stat multipliers (like "Growl", "Tail Whip", "Double Team" etc.), the first use may display the wrong stat name in the message; subsequent uses display correctly.

## Author
- [@nebuchadneZZar01](https://github.com/nebuchadneZZar01) (Michele Ferro)
