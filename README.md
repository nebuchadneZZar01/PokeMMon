# PokéMMon

Pokémon 1st-gen battle simulator with MiniMax AI algorithms.  
Terminal UI via `rich`, data layer via `pydantic` v2.

## AI algorithms

| Flag | Algorithm |
|------|-----------|
| `random` | Random move selection |
| `minimax` | Vanilla MiniMax search |
| `alphabeta` | MiniMax with alpha-beta pruning |
| `expectimax` | MiniMax with expectation nodes |

## Usage

```
python main.py --ai minimax --depth 7
```

Optional flags:
- `--log info` — show AI turn markers and chosen moves
- `--log debug` — full tree-search logging (verbose)

## Setup

```bash
uv sync          # create venv, install deps
python main.py   # default: minimax depth 7
```

## Development

```bash
uv run ruff check          # lint
uv run pytest tests/ -v    # run tests
```

## Requirements

- Python >=3.14
- [`uv`](https://docs.astral.sh/uv/) (or `pip` + `requirements.txt`)

Dependencies: `pydantic`, `rich`, `pytest` (dev), `ruff` (dev).

## Credits

Pokémon is © The Pokémon Company, Nintendo, Game Freak, Creatures Inc.  
No copyrighted assets are distributed with this software.
