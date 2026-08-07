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
  ╭───────────────────────────  AI  ───────────────────────────╮
  │   Tangela    Lv100                                         │
  │   GRASS                                                    │
  │   HP ██████████████████  240/240                           │
  │   OK                 Team ●●●●●●                           │
  ╰────────────────────────────────────────────────────────────╯
  ╭─────────────────────────  Player  ─────────────────────────╮
  │   Flareon    Lv100                                         │
  │   FIRE                                                     │
  │   HP ██████████████████  240/240                           │
  │   OK                 Team ●○○○○○                           │
  │    Boosts  Atk ↑2                                          │
  │    Drops   Def ↓1                                          │
  ╰────────────────────────────────────────────────────────────╯
  ╭───────────────────────  Battle Log  ───────────────────────╮
  │   R1    Player    Flareon used Take Down!                  │
  │                                                            │
  │   R0    AI        Tangela used Mega Drain!                 │
  ╰────────────────────────────────────────────────────────────╯
    [1] Skull Bash     NORMAL      15/15
    [2] Double Team    NORMAL      15/15
    [3] Take Down      NORMAL      20/20
    [4] Substitute     NORMAL      10/10

    [5] Team     [6] Forfeit
  Action [1/2/3/4/5/6]:
  ```

- **Team view** (press <kbd>5</kbd>):
  ```
  ╭───────────────────────────────  AI  ───────────────────────────────╮
  │   Tangela    Lv100                                                 │
  │   GRASS                                                            │
  │   HP █████████░░░░░░░░░  132/240                                   │
  │   OK                 Team ●                                        │
  ╰────────────────────────────────────────────────────────────────────╯

  ╭──────────────────────────  Your Team  ────────────────────────────╮
  │   [1] Flareon    ██████████████  240/240  OK  ←                   │
  │                 FIRE                                              │
  │       Skull Bash      NORMAL  15/15   Double Team   NORMAL  15/15  │
  │       Take Down       NORMAL  20/20  Substitute   NORMAL  10/10   │
  │                                                                   │
  │   [2] Vaporeon   ██████████████  240/240  OK                      │
  │                 WATER                                             │
  │       Surf           WATER   35/35   Aurora Beam  ICE     35/35   │
  │       Blizzard       ICE     35/35   Hydro Pump   WATER   35/35   │
  │                                                                   │
  │   [3] Jolteon    ███████░░░░░░░  130/240  OK                      │
  │                 ELECTRIC                                          │
  │       ThunderShock  ELECTRIC 35/35   Thunderbolt  ELECTRIC 35/35  │
  │       ...                                                         │
  ╰────────────────────────────────────────────────────────────────────╯

    Choose (1-6) to switch, [0] back to battle
  ```

## Development

```bash
uv run ruff check          # lint
uv run mypy app main.py    # type check
uv run pytest tests/ -v    # run tests
uv run pytest --cov=app    # test coverage (fail_under 90)
```

## Author
- [@nebuchadneZZar01](https://github.com/nebuchadneZZar01) (Michele Ferro)
