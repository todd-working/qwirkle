# Qwirkle Go Implementation

High-performance Go implementation of the Qwirkle game engine, designed for:
- Fast AI vs AI simulations (10,000+ games/sec)
- Web UI backend (same API as Python version)
- Training data generation for ML models

## Directory Structure

```
go/
├── engine/           # Core game logic
│   ├── tile.go       # Tile, Shape, Color types
│   ├── board.go      # Sparse board with positions
│   ├── bag.go        # Shuffled tile bag with seeded RNG
│   ├── hand.go       # Player hand (max 6 tiles)
│   ├── rules.go      # Move validation and scoring
│   └── game.go       # GameState and turn management
│
├── ai/               # AI strategies
│   ├── movegen.go    # Generate all valid moves
│   └── solver.go     # Greedy, Random, Weighted solvers
│
├── api/              # HTTP server
│   └── server.go     # REST API for web UI
│
├── simulator/        # Batch game runner
│   └── runner.go     # Parallel simulation with JSONL output
│
├── cmd/              # CLI entry point
│   └── main.go       # Commands: serve, simulate
│
├── Dockerfile        # Container build
└── go.mod            # Module definition
```

## Quick Start

```bash
# Install Go (if needed)
brew install go

# Build
cd go
go build -o qwirkle ./cmd

# Run web server
./qwirkle serve -addr :8080

# Run simulations
./qwirkle simulate -n 1000 -p1 greedy -p2 random -o games.jsonl
```

## Key Go Concepts Explained

The code is heavily commented for learning. Here are some key patterns:

### Structs and Methods

```go
// Struct definition
type Tile struct {
    Shape Shape
    Color Color
}

// Method with value receiver (doesn't modify tile)
func (t Tile) Equal(other Tile) bool {
    return t.Shape == other.Shape && t.Color == other.Color
}

// Method with pointer receiver (can modify board)
func (b *Board) Set(pos Position, tile Tile) {
    b.tiles[pos] = tile
}
```

### Interfaces

```go
// Interface defines behavior, not data
type Solver interface {
    SelectMove(game *GameState, moves []Move) *Move
    Name() string
}

// Any type with these methods satisfies Solver
type GreedySolver struct{}
func (s *GreedySolver) SelectMove(...) *Move { ... }
func (s *GreedySolver) Name() string { return "greedy" }
```

### Slices and Maps

```go
// Slice (dynamic array)
tiles := make([]Tile, 0, 108)  // length=0, capacity=108
tiles = append(tiles, tile)    // add element

// Map (hash table)
board := make(map[Position]Tile)
board[pos] = tile              // set
tile, ok := board[pos]         // get with existence check
delete(board, pos)             // remove
```

### Error Handling

```go
// Go uses explicit error returns, not exceptions
func (b *Bag) Draw(n int) []Tile {
    if n > len(b.tiles) {
        n = len(b.tiles)  // Handle gracefully, don't panic
    }
    // ...
}

// For functions that can fail:
result, err := someFunction()
if err != nil {
    return nil, err  // Propagate error up
}
```

### Concurrency

```go
// Goroutines for parallel work
for i := 0; i < numWorkers; i++ {
    go func() {
        // Runs concurrently
    }()
}

// Channels for communication
jobs := make(chan int64, 100)     // buffered channel
results := make(chan Result, 10)

// Send/receive
jobs <- value       // send
value := <-jobs     // receive (blocks until available)
```

## Game Rules (Qwirkle)

1. **Tiles**: 6 shapes × 6 colors = 36 unique tiles, 3 copies each = 108 total
2. **Hands**: Each player holds up to 6 tiles
3. **Placement**: Tiles must form a line (horizontal or vertical)
4. **Line Rules**: All tiles share color OR shape, no duplicates, max 6
5. **Scoring**: 1 point per tile in each line formed, +6 for "Qwirkle" (6-tile line)
6. **Game End**: When a player plays their last tile and bag is empty (+6 bonus)

## AI Strategies

| Strategy | Description | Win Rate vs Random |
|----------|-------------|--------------------|
| Greedy | Always picks highest-scoring move | ~100% |
| Random | Picks uniformly random move | 50% (baseline) |
| Weighted | Probabilistic, favors high scores | ~80% |

## Simulation Output Format

Games are output as JSONL (one JSON object per line):

```json
{
  "id": "game_12345",
  "seed": 12345,
  "players": ["greedy", "random"],
  "moves": [
    {"player": 0, "placements": [...], "score": 5},
    {"player": 1, "placements": [...], "score": 3}
  ],
  "winner": 0,
  "final_scores": [142, 98],
  "total_moves": 47,
  "duration_ms": 2.5
}
```

## Docker Usage

```bash
# Build image
docker build -t qwirkle-go .

# Run web server
docker run -p 8080:8080 qwirkle-go

# Run simulations (output to stdout)
docker run qwirkle-go simulate -n 1000

# Run simulations with output file
docker run -v $(pwd):/data qwirkle-go simulate -n 1000 -o /data/games.jsonl
```

## Development

```bash
# Run tests
go test ./...

# Run with race detector (finds concurrency bugs)
go test -race ./...

# Format code
go fmt ./...

# Check for issues
go vet ./...
```
