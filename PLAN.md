# Qwirkle Simulator/Solver — Implementation Plan

## Overview
Build a Qwirkle game engine in Python with terminal UI, AI solver, and Monte Carlo simulator for probability analysis.

**Scope:** 2 players, standard rules, flexible stats tracking

---

## Project Structure

```
qwirkle/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tile.py          # Tile (shape, color)
│   │   ├── board.py         # Board grid + placement logic
│   │   ├── bag.py           # Tile bag (draw, return)
│   │   └── hand.py          # Player hand (6 tiles max)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── rules.py         # Move validation
│   │   ├── scoring.py       # Score calculation
│   │   └── game.py          # Game state, turn flow
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── move_gen.py      # Enumerate all legal moves
│   │   └── solver.py        # Pick best move (heuristics)
│   ├── sim/
│   │   ├── __init__.py
│   │   ├── runner.py        # Run N games
│   │   ├── stats.py         # Collect/aggregate statistics
│   │   └── win_prob.py      # Monte Carlo win probability
│   └── ui/
│       ├── __init__.py
│       ├── terminal.py      # ANSI board rendering
│       └── input.py         # Command parsing
├── tests/
│   ├── test_tile.py
│   ├── test_board.py
│   ├── test_rules.py
│   ├── test_scoring.py
│   └── test_game.py
├── main.py                  # Entry point
├── pyproject.toml
└── README.md
```

---

## Phase 1: Core Models

### Tile (`models/tile.py`)
```python
@dataclass(frozen=True)
class Tile:
    shape: Shape   # Enum: CIRCLE, SQUARE, DIAMOND, STAR, CLOVER, CROSS
    color: Color   # Enum: RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE
```
- Immutable, hashable (for sets/dicts)
- 36 unique combinations, 3 copies each = 108 tiles

### Board (`models/board.py`)
- Sparse dict representation: `Dict[Tuple[int, int], Tile]`
- Dynamic bounds (no fixed size)
- Methods: `place(pos, tile)`, `get(pos)`, `neighbors(pos)`, `bounds()`

### Bag (`models/bag.py`)
- List of 108 tiles, shuffled
- Methods: `draw(n)`, `return_tiles(tiles)`, `remaining()`

### Hand (`models/hand.py`)
- List of up to 6 tiles
- Methods: `add(tiles)`, `remove(tiles)`, `refill(bag)`

---

## Phase 2: Rules & Scoring

### Validation (`engine/rules.py`)
A move is valid if:
1. All tiles placed in same row OR same column
2. Tiles are contiguous (no gaps)
3. Connects to existing tiles (except first move)
4. Each resulting line has ≤6 tiles with no duplicates
5. Each line shares exactly one attribute (all same color OR all same shape)

### Scoring (`engine/scoring.py`)
- For each line created/extended: score = number of tiles in line
- Qwirkle bonus: if line has 6 tiles, score doubles (6 → 12)
- End game bonus: +6 for player who empties hand first

---

## Phase 3: Game Engine

### Game State (`engine/game.py`)
```python
@dataclass
class GameState:
    board: Board
    bag: Bag
    hands: List[Hand]        # [player0, player1]
    scores: List[int]
    current_player: int
    turn_number: int
    game_over: bool
```

### Turn Flow
1. Current player chooses: play tiles OR swap tiles
2. Validate move
3. Calculate and add score
4. Refill hand from bag
5. Check end condition (hand empty + bag empty)
6. Switch player

---

## Phase 4: Terminal UI

### Display (`ui/terminal.py`)
- ANSI colors for tile colors
- Unicode shapes: ● ■ ◆ ★ ✚ ✿
- Coordinate labels (A-Z columns, 1-99 rows)
- Show both hands (or hide opponent's for real play)
- Win probability after each turn (optional, requires AI/sim)

### Commands (`ui/input.py`)
- `play <tile> <pos> [<tile> <pos> ...]` — place tiles
- `swap <tile> [<tile> ...]` — exchange tiles
- `hint` — show best move (uses solver)
- `undo` — take back last move
- `quit` — exit game

---

## Phase 5: AI/Solver

### Move Generation (`ai/move_gen.py`)
- Find all valid single-tile placements
- Extend to multi-tile moves (same row/col, from hand)
- Prune invalid combinations

### Solver (`ai/solver.py`)
- **Greedy:** pick highest-scoring move
- **Future:** minimax with alpha-beta, or MCTS

---

## Phase 6: Simulator & Win Probability

### Runner (`sim/runner.py`)
- Run N games with specified AI strategies
- Configurable: random vs greedy vs optimal

### Statistics (`sim/stats.py`)
Track per-game:
- Final scores
- Number of Qwirkles (by player)
- Max single-turn score
- Turn count
- Tile distribution at game end

Aggregate:
- Win rate by strategy
- Qwirkle frequency
- Distribution of max scores
- Correlation analysis (what predicts winning?)

### Win Probability (`sim/win_prob.py`)
Calculate real-time win probability after each turn using Monte Carlo simulation:

**How it works:**
1. Snapshot current game state (board, scores, current player's hand)
2. Compute "unseen tiles" = all 108 tiles − board tiles − current player's hand
3. For N simulations (e.g., 1000):
   - Shuffle unseen tiles
   - Deal first 6 to opponent (simulated hand)
   - Remaining go to simulated bag
   - Play out game to completion using AI (greedy or random)
   - Record winner
4. Win probability = wins / N

**Information model:**
- You know: your hand, the board, the scores
- You don't know: opponent's hand (but you know it's from the unseen pool)
- This is "perfect information about the bag" — realistic for skilled players who track tiles

**Display:**
```
After turn 12:
  Player 1: 67 pts (48% win probability)
  Player 2: 54 pts (52% win probability)
```

**Performance considerations:**
- Run simulations in parallel (multiprocessing)
- Cache move generation where possible
- Configurable simulation count (quick=100, accurate=1000+)

---

## Layered Execution Plan

### Phase 1: Core Models
**Goal:** Data structures that represent game elements

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 1.1 | Create project structure + pyproject.toml | — | pytest runs |
| 1.2 | Implement `Color` and `Shape` enums | 1.1 | Unit: enum values |
| 1.3 | Implement `Tile` dataclass | 1.2 | Unit: equality, hashing |
| 1.4 | Implement `Bag` (create 108 tiles, shuffle, draw, return) | 1.3 | Unit: counts, draw/return |
| 1.5 | Implement `Hand` (add, remove, refill from bag) | 1.3, 1.4 | Unit: hand operations |
| 1.6 | Implement `Board` (sparse dict, place, get, neighbors) | 1.3 | Unit: placement, queries |

**Exit criteria:** All models instantiate, serialize, and pass unit tests

---

### Phase 2: Rules & Scoring
**Goal:** Validate moves and calculate scores

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 2.1 | Implement line extraction (get row/col from position) | 1.6 | Unit: line contents |
| 2.2 | Implement line validation (≤6, no dupes, shared attr) | 2.1 | Unit: valid/invalid lines |
| 2.3 | Implement move validation (contiguous, connects, all lines valid) | 2.2 | Unit: valid/invalid moves |
| 2.4 | Implement score calculation (line lengths + Qwirkle bonus) | 2.1 | Unit: scoring scenarios |
| 2.5 | Implement end-game bonus (+6 for emptying hand) | 2.4 | Unit: end bonus |

**Exit criteria:** Can validate any move and compute correct score

---

### Phase 3: Game Engine
**Goal:** Full turn-based game flow

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 3.1 | Implement `GameState` dataclass | 1.* | Unit: state creation |
| 3.2 | Implement `new_game()` factory (shuffle, deal hands) | 3.1 | Unit: initial state valid |
| 3.3 | Implement `apply_move()` (validate, score, update state) | 2.*, 3.1 | Unit: state transitions |
| 3.4 | Implement `apply_swap()` (exchange tiles with bag) | 3.1 | Unit: swap mechanics |
| 3.5 | Implement turn switching + end detection | 3.3, 3.4 | Unit: game flow |
| 3.6 | Implement `clone()` for state (needed for simulations) | 3.1 | Unit: deep copy works |

**Exit criteria:** Can play a full game programmatically with valid state transitions

---

### Phase 4: Terminal UI
**Goal:** Playable human vs human in terminal

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 4.1 | Implement tile rendering (ANSI color + unicode shape) | 1.3 | Visual: tiles display |
| 4.2 | Implement board rendering (grid with coordinates) | 4.1, 1.6 | Visual: board displays |
| 4.3 | Implement hand rendering | 4.1 | Visual: hand displays |
| 4.4 | Implement score/status display | 3.1 | Visual: scores show |
| 4.5 | Implement command parser (play, swap, quit) | — | Unit: parse commands |
| 4.6 | Implement game loop (render → input → apply → repeat) | 4.*, 3.* | Manual: play a game |
| 4.7 | Add undo support (state history stack) | 3.6 | Manual: undo works |

**Exit criteria:** Two humans can play a complete game in terminal

---

### Phase 5: AI / Solver
**Goal:** Computer opponent + hints

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 5.1 | Implement valid position finder (where can tiles go?) | 2.3, 1.6 | Unit: finds positions |
| 5.2 | Implement single-tile move generator | 5.1 | Unit: generates moves |
| 5.3 | Implement multi-tile move generator (extend from single) | 5.2 | Unit: multi-tile moves |
| 5.4 | Implement greedy solver (pick highest-scoring move) | 5.3, 2.4 | Unit: picks best |
| 5.5 | Implement random solver (pick any valid move) | 5.3 | Unit: picks valid |
| 5.6 | Add `hint` command to UI | 5.4, 4.5 | Manual: hints work |
| 5.7 | Add AI player mode (human vs AI) | 5.4, 4.6 | Manual: play vs AI |

**Exit criteria:** Human can play against greedy AI; hints work

---

### Phase 6: Simulator & Win Probability
**Goal:** Run simulations, collect stats, calculate win probability

| Step | Task | Depends On | Test |
|------|------|------------|------|
| 6.1 | Implement game runner (AI vs AI, return result) | 5.4, 5.5, 3.* | Unit: games complete |
| 6.2 | Implement batch runner (N games, collect results) | 6.1 | Unit: runs N games |
| 6.3 | Implement stats collector (scores, Qwirkles, max turn) | 6.2 | Unit: stats accurate |
| 6.4 | Implement stats aggregator (means, distributions, correlations) | 6.3 | Unit: aggregation |
| 6.5 | Implement unseen tile calculator | 1.*, 3.1 | Unit: correct unseen |
| 6.6 | Implement win probability (Monte Carlo from state) | 6.1, 6.5, 3.6 | Unit: probability in [0,1] |
| 6.7 | Add parallel simulation (multiprocessing) | 6.6 | Perf: speedup observed |
| 6.8 | Integrate win probability display into UI | 6.6, 4.4 | Manual: probs show |

**Exit criteria:** Can simulate 1000+ games, collect stats, show win probability after each turn

---

## Dependency Graph (Simplified)

```
Phase 1 (Models)
    ↓
Phase 2 (Rules) ←────────────────┐
    ↓                            │
Phase 3 (Engine) ───────────────→│
    ↓                            │
Phase 4 (UI) ←── human playable  │
    ↓                            │
Phase 5 (AI) ←───────────────────┘
    ↓
Phase 6 (Sim + Win Prob)
```

Each phase builds on the previous. Phases 4-6 can partially overlap once Phase 3 is stable.

## Parallelization Strategy

Use concurrent agents where dependencies allow:

**Phase 1:**
- 1.4 (Bag), 1.5 (Hand), 1.6 (Board) can run in parallel after 1.3 (Tile)

**Phase 2:**
- 2.2 (line validation) and 2.4 (scoring) can run in parallel after 2.1

**Phase 4:**
- 4.1-4.4 (rendering) can run in parallel
- 4.5 (parser) can run in parallel with rendering

**Phase 5:**
- 5.4 (greedy) and 5.5 (random) can run in parallel after 5.3

**Phase 6:**
- 6.3 (stats collector) and 6.5 (unseen calculator) can run in parallel

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Board representation | Sparse dict | Infinite growth, O(1) lookup |
| Tile | Frozen dataclass | Hashable, immutable, clean |
| Move validation | Separate module | Testable, reusable by AI |
| UI separation | Clean interface | Swap terminal for web later |
| Stats tracking | Event-based hooks | Don't pollute game logic |

---

## Progress

### Current Status
- [x] 1.1 - Project structure created
- [x] 1.2 - Color and Shape enums
- [x] 1.3 - Tile dataclass
- [x] 1.4 - Bag
- [x] 1.5 - Hand
- [x] 1.6 - Board

**Phase 1 complete** — 73 tests passing

- [x] 2.1 - Line extraction (get_line_horizontal, get_line_vertical)
- [x] 2.2 - Line validation (is_valid_line)
- [x] 2.3 - Move validation (validate_move)
- [x] 2.4 - Score calculation (calculate_move_score, score_move)
- [x] 2.5 - End-game bonus (calculate_end_game_bonus)

**Phase 2 complete** — 145 tests passing

- [x] 3.1 - GameState dataclass
- [x] 3.2 - new_game() factory
- [x] 3.3 - apply_move() with validation and scoring
- [x] 3.4 - apply_swap() for tile exchange
- [x] 3.5 - Turn switching and end-game detection
- [x] 3.6 - clone() for state copying

**Phase 3 complete** — 180 tests passing

- [x] 4.1 - Tile rendering (ANSI colors + Unicode shapes)
- [x] 4.2 - Board rendering (grid with coordinates)
- [x] 4.3 - Hand rendering (indexed tiles with labels)
- [x] 4.4 - Score/status display
- [x] 4.5 - Command parser (play, swap, undo, quit, hint, help)
- [x] 4.6 - Game loop with GameSession
- [x] 4.7 - Undo support (state history stack)

**Phase 4 complete** — 221 tests passing

- [x] 5.1 - Valid position finder (find_valid_positions)
- [x] 5.2 - Single-tile move generator (generate_single_tile_moves)
- [x] 5.3 - Multi-tile move generator (generate_multi_tile_moves)
- [x] 5.4 - Greedy solver (picks highest-scoring move)
- [x] 5.5 - Random solver (picks random valid move)
- [x] 5.6 - Hint command integration
- [x] 5.7 - AI player mode (--vs-ai flag)

**Phase 5 complete** — 243 tests passing

- [x] 6.1 - Game runner (run_game with AI vs AI)
- [x] 6.2 - Batch runner (run_batch for N games)
- [x] 6.3 - Stats collector (GameResult with scores, qwirkles, etc.)
- [x] 6.4 - Stats aggregator (compute_stats, format_stats)
- [x] 6.5 - Unseen tile calculator (get_unseen_tiles)
- [x] 6.6 - Win probability (estimate_win_probability with Monte Carlo)
- [x] 6.7 - Parallel simulation (ProcessPoolExecutor)
- [x] 6.8 - Win probability UI integration (prob command)

**Phase 6 complete** — 263 tests passing

Run with:
- `python main.py` — Human vs Human
- `python main.py --vs-ai` — Human vs AI (you are Player 1)
- `python main.py --ai-first` — AI vs Human (AI is Player 1)
- `python main.py --ai-strategy random` — Use random AI instead of greedy

In-game commands:
- `play <tiles> <positions>` — Place tiles (e.g., `play 1 0,0` or `play 1,2 0,0 0,1`)
- `swap <tiles>` — Exchange tiles with bag
- `hint` — Get best move suggestion
- `prob [n]` — Estimate win probability (default 50 simulations)
- `undo` — Take back last move
- `quit` — Exit game

---

## Future Enhancements

### Neural Network Integration

**NeuralNetSolver** — Plug in a trained model as a solver:
```python
class NeuralNetSolver(Solver):
    def __init__(self, model, temperature=1.0):
        self.model = model
        self.temperature = temperature

    def select_move(self, state, moves):
        # Encode state to tensor
        board_tensor = encode_board(state.board)
        hand_tensor = encode_hand(state.hands[state.current_player])

        # Get move probabilities from model
        move_probs = self.model.predict(board_tensor, hand_tensor)

        # Sample or argmax based on temperature
        return select_move_from_probs(moves, move_probs, self.temperature)
```

**Self-play training loop** (AlphaZero style):
1. Generate games with current model + epsilon exploration
2. Train on (state, action, reward) tuples
3. Replace model, repeat
4. Periodically evaluate against greedy baseline

### Additional Solver Strategies

- **Minimax with alpha-beta pruning** — Look ahead N moves
- **Monte Carlo Tree Search (MCTS)** — Balance exploration/exploitation
- **Tile-counting heuristics** — Track which tiles are still available

### Training Data Enhancements

- **Action encoding** — One-hot or embedding for (tile, position) pairs
- **Opponent hand estimation** — Bayesian inference from play history
- **Reward shaping** — Credit assignment beyond immediate score
- **Augmentation** — Board rotations/reflections for more training data

### Performance Optimizations

- **C extension for move generation** — Current bottleneck
- **Batch inference** — Process multiple states in parallel
- **Caching** — Memoize valid positions and line calculations

### UI Enhancements

- **Web interface** — Flask/FastAPI + React frontend
- **Game replay** — Step through recorded games
- **Training dashboard** — Visualize loss curves, win rates vs baseline
