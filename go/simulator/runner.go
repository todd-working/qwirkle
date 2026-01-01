// Package simulator runs batch AI vs AI games for training data generation.
package simulator

import (
	"encoding/json"
	"fmt"
	"io"
	"runtime"
	"sync"
	"sync/atomic"
	"time"

	"github.com/todd-working/qwirkle/ai"
	"github.com/todd-working/qwirkle/engine"
)

// GameResult stores the outcome of a single game.
type GameResult struct {
	ID          string       `json:"id"`
	Seed        int64        `json:"seed"`
	Players     [2]string    `json:"players"`
	Moves       []MoveJSON   `json:"moves"`
	Winner      int          `json:"winner"` // 0, 1, or -1 for tie
	FinalScores [2]int       `json:"final_scores"`
	TotalMoves  int          `json:"total_moves"`
	Duration    float64      `json:"duration_ms"`
}

// MoveJSON represents a move in JSON format.
type MoveJSON struct {
	Player     int              `json:"player"`
	Placements []PlacementJSON  `json:"placements,omitempty"`
	Score      int              `json:"score"`
	WasSwap    bool             `json:"was_swap,omitempty"`
	SwapCount  int              `json:"swap_count,omitempty"`
}

// PlacementJSON represents a tile placement.
type PlacementJSON struct {
	Row   int     `json:"row"`
	Col   int     `json:"col"`
	Tile  TileJSON `json:"tile"`
}

// TileJSON represents a tile.
type TileJSON struct {
	Shape int `json:"shape"`
	Color int `json:"color"`
}

// Config configures the simulation runner.
type Config struct {
	NumGames     int
	Player1      string // "greedy", "random", "weighted"
	Player2      string
	Workers      int    // Number of parallel workers (0 = num CPUs)
	Seed         int64  // Base seed (0 = random)
}

// Stats tracks simulation statistics.
type Stats struct {
	GamesPlayed   int64
	Player1Wins   int64
	Player2Wins   int64
	Ties          int64
	TotalMoves    int64
	TotalDuration int64 // nanoseconds
}

// Runner executes batch simulations.
type Runner struct {
	config Config
	stats  Stats
	mu     sync.Mutex
}

// NewRunner creates a new simulation runner.
func NewRunner(config Config) *Runner {
	if config.Workers <= 0 {
		config.Workers = runtime.NumCPU()
	}
	return &Runner{config: config}
}

// Run executes the simulation, writing results to the given writer.
func (r *Runner) Run(output io.Writer) error {
	start := time.Now()

	// Create work channel
	jobs := make(chan int64, r.config.NumGames)
	results := make(chan GameResult, r.config.Workers*2)

	// Start workers
	var wg sync.WaitGroup
	for i := 0; i < r.config.Workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r.worker(jobs, results)
		}()
	}

	// Start result writer
	var writerWg sync.WaitGroup
	writerWg.Add(1)
	go func() {
		defer writerWg.Done()
		encoder := json.NewEncoder(output)
		for result := range results {
			encoder.Encode(result)
		}
	}()

	// Dispatch jobs
	baseSeed := r.config.Seed
	if baseSeed == 0 {
		baseSeed = time.Now().UnixNano()
	}
	for i := 0; i < r.config.NumGames; i++ {
		jobs <- baseSeed + int64(i)
	}
	close(jobs)

	// Wait for workers to finish
	wg.Wait()
	close(results)

	// Wait for writer to finish
	writerWg.Wait()

	elapsed := time.Since(start)
	r.printStats(elapsed)

	return nil
}

// worker processes games from the jobs channel.
func (r *Runner) worker(jobs <-chan int64, results chan<- GameResult) {
	for seed := range jobs {
		result := r.runGame(seed)
		results <- result

		// Update stats
		atomic.AddInt64(&r.stats.GamesPlayed, 1)
		atomic.AddInt64(&r.stats.TotalMoves, int64(result.TotalMoves))
		atomic.AddInt64(&r.stats.TotalDuration, int64(result.Duration*1e6))

		switch result.Winner {
		case 0:
			atomic.AddInt64(&r.stats.Player1Wins, 1)
		case 1:
			atomic.AddInt64(&r.stats.Player2Wins, 1)
		default:
			atomic.AddInt64(&r.stats.Ties, 1)
		}
	}
}

// runGame plays a single game and returns the result.
func (r *Runner) runGame(seed int64) GameResult {
	start := time.Now()

	game := engine.NewGame(seed)

	// Create solvers
	solvers := [2]ai.Solver{
		r.createSolver(r.config.Player1, seed),
		r.createSolver(r.config.Player2, seed+1),
	}

	moves := make([]MoveJSON, 0)

	// Play until game over
	for !game.GameOver {
		player := game.CurrentPlayer
		solver := solvers[player]

		allMoves := ai.GenerateAllMoves(game)
		move := solver.SelectMove(game, allMoves)

		if move != nil {
			// Convert to JSON format before applying
			placements := make([]PlacementJSON, len(move.Placements))
			for i, p := range move.Placements {
				placements[i] = PlacementJSON{
					Row:  p.Pos.Row,
					Col:  p.Pos.Col,
					Tile: TileJSON{Shape: int(p.Tile.Shape), Color: int(p.Tile.Color)},
				}
			}

			score := game.PlayTiles(move.Placements)
			moves = append(moves, MoveJSON{
				Player:     player,
				Placements: placements,
				Score:      score,
			})
		} else {
			// No valid moves - swap a tile
			game.SwapTiles([]int{0})
			moves = append(moves, MoveJSON{
				Player:    player,
				WasSwap:   true,
				SwapCount: 1,
			})
		}
	}

	elapsed := time.Since(start)

	return GameResult{
		ID:          fmt.Sprintf("game_%d", seed),
		Seed:        seed,
		Players:     [2]string{r.config.Player1, r.config.Player2},
		Moves:       moves,
		Winner:      game.Winner,
		FinalScores: game.Scores,
		TotalMoves:  len(moves),
		Duration:    float64(elapsed.Nanoseconds()) / 1e6,
	}
}

// createSolver creates a solver by name.
func (r *Runner) createSolver(name string, seed int64) ai.Solver {
	switch name {
	case "random":
		return ai.NewRandomSolver(seed)
	case "weighted":
		return ai.NewWeightedRandomSolver(seed, 1.0)
	default:
		return &ai.GreedySolver{}
	}
}

// printStats prints simulation statistics.
func (r *Runner) printStats(elapsed time.Duration) {
	games := atomic.LoadInt64(&r.stats.GamesPlayed)
	p1Wins := atomic.LoadInt64(&r.stats.Player1Wins)
	p2Wins := atomic.LoadInt64(&r.stats.Player2Wins)
	ties := atomic.LoadInt64(&r.stats.Ties)
	totalMoves := atomic.LoadInt64(&r.stats.TotalMoves)

	gamesPerSec := float64(games) / elapsed.Seconds()
	avgMoves := float64(totalMoves) / float64(games)

	fmt.Printf("\n=== Simulation Complete ===\n")
	fmt.Printf("Games:      %d\n", games)
	fmt.Printf("Duration:   %v\n", elapsed.Round(time.Millisecond))
	fmt.Printf("Speed:      %.1f games/sec\n", gamesPerSec)
	fmt.Printf("Avg moves:  %.1f\n", avgMoves)
	fmt.Printf("\n--- Results ---\n")
	fmt.Printf("%s wins: %d (%.1f%%)\n", r.config.Player1, p1Wins, 100*float64(p1Wins)/float64(games))
	fmt.Printf("%s wins: %d (%.1f%%)\n", r.config.Player2, p2Wins, 100*float64(p2Wins)/float64(games))
	fmt.Printf("Ties:       %d (%.1f%%)\n", ties, 100*float64(ties)/float64(games))
}
