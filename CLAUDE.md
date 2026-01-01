# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Qwirkle game simulator in Python: game engine with terminal UI, AI solver, and Monte Carlo simulator for win probability analysis. 2-player standard rules.

**Current status:** All phases complete (1-6). Fully playable with AI, hints, and win probability estimation.

See `PLAN.md` for the detailed implementation roadmap with phases and dependencies.

## Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tile.py

# Run with coverage
pytest --cov=src

# Run single test by name
pytest -k "test_draw_respects_count"
```

## Architecture

### Models (`src/models/`)
- **Tile**: Immutable dataclass with `Shape` and `Color` enums. 36 unique tiles × 3 copies = 108 total.
- **Board**: Sparse dict `Dict[Position, Tile]` where `Position = Tuple[int, int]`. No fixed bounds—grows dynamically. Origin at (0,0).
- **Bag**: 108 shuffled tiles. Supports seeded RNG for reproducibility.
- **Hand**: Player's tiles (max 6). Refills from bag.

### Engine (`src/engine/`)
- **rules.py**: Move validation logic. Key functions:
  - `validate_move()`: Main entry point—checks collinearity, contiguity, connection, and line validity
  - `get_line_horizontal/vertical()`: Extract complete lines from a position
  - `is_valid_line()`: Tiles share exactly one attribute (color XOR shape), no duplicates, ≤6 tiles

### Engine (`src/engine/`)
- **scoring.py**: Score calculation (line length + Qwirkle bonus)
- **game.py**: GameState, turn flow, apply_move, apply_swap, clone

### AI (`src/ai/`)
- **move_gen.py**: Move enumeration (single and multi-tile)
- **solver.py**: GreedySolver, RandomSolver, WeightedRandomSolver

### Simulator (`src/sim/`)
- **runner.py**: Game runner, batch runner with parallel execution
- **stats.py**: Statistics collection and aggregation
- **win_prob.py**: Monte Carlo win probability estimation

### UI (`src/ui/`)
- **terminal.py**: ANSI color rendering with Unicode shapes
- **input.py**: Command parsing (play, swap, hint, prob, undo, quit)
- **game_loop.py**: Interactive game session with AI support

## Key Design Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Board | Sparse dict | O(1) lookup, infinite growth |
| Tile | Frozen dataclass | Hashable for sets/dicts |
| RNG | Seeded in Bag | Reproducible tests and simulations |
| Imports | `src.models.X` | Package-style imports throughout |

## Qwirkle Rules Summary

Valid move requirements:
1. All tiles in same row OR same column
2. Contiguous placement (no gaps)
3. Must connect to existing tiles (except first move)
4. Each line ≤6 tiles, no duplicate tiles
5. Line shares exactly one attribute: all same color with different shapes, OR all same shape with different colors
