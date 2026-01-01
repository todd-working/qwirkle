package ai

import (
	"math"
	"math/rand"

	"github.com/todd-working/qwirkle/engine"
)

// =============================================================================
// SOLVER INTERFACE
// =============================================================================

// Solver defines the interface for AI strategies.
//
// A Solver takes a game state and list of valid moves, and chooses one.
// Different implementations use different selection strategies.
//
// Why separate move generation from selection?
//   - Move generation is expensive and shared by all solvers
//   - Selection strategies are the differentiating factor
//   - Allows easy comparison of strategies using same move set
type Solver interface {
	// SelectMove chooses a move from the available moves.
	// Returns nil if no valid moves exist.
	SelectMove(game *engine.GameState, moves []engine.Move) *engine.Move

	// Name returns a human-readable name for this solver.
	// Used in logging and result reporting.
	Name() string
}

// GetMove is a convenience function that generates moves and selects one.
//
// This is the main entry point for AI move selection.
// It combines move generation with solver selection.
func GetMove(solver Solver, game *engine.GameState) *engine.Move {
	moves := GenerateAllMoves(game)
	return solver.SelectMove(game, moves)
}

// =============================================================================
// GREEDY SOLVER
// =============================================================================

// GreedySolver always picks the highest-scoring move.
//
// Strategy: Pure immediate reward maximization.
//
// Strengths:
//   - Fast (O(1) selection, moves are pre-sorted)
//   - Maximizes points on every turn
//   - Beats random strategies ~100% of the time
//
// Weaknesses:
//   - No lookahead (doesn't consider future consequences)
//   - May block its own future Qwirkles
//   - Can be predictable
//
// Good for: Baseline AI, testing, fast simulations.
type GreedySolver struct{}

// Name returns "greedy" for identification.
func (s *GreedySolver) Name() string {
	return "greedy"
}

// SelectMove picks the first move (highest score since moves are sorted).
func (s *GreedySolver) SelectMove(game *engine.GameState, moves []engine.Move) *engine.Move {
	if len(moves) == 0 {
		return nil
	}
	// Moves are sorted by score descending, so first is best
	return &moves[0]
}

// =============================================================================
// RANDOM SOLVER
// =============================================================================

// RandomSolver picks a random valid move.
//
// Strategy: Uniform random selection.
//
// Strengths:
//   - Unpredictable
//   - Useful for Monte Carlo simulations
//   - Good baseline for measuring AI improvement
//
// Weaknesses:
//   - Very weak play (ignores scores entirely)
//   - Will rarely beat any intelligent strategy
//
// Good for: Testing, baseline comparisons, exploration in MCTS.
type RandomSolver struct {
	rng *rand.Rand // Private RNG for reproducibility
}

// NewRandomSolver creates a random solver with the given seed.
//
// Use seed=0 for non-reproducible randomness (not recommended for testing).
// Use specific seeds for reproducible simulations.
func NewRandomSolver(seed int64) *RandomSolver {
	return &RandomSolver{
		rng: rand.New(rand.NewSource(seed)),
	}
}

// Name returns "random" for identification.
func (s *RandomSolver) Name() string {
	return "random"
}

// SelectMove picks a uniformly random move.
func (s *RandomSolver) SelectMove(game *engine.GameState, moves []engine.Move) *engine.Move {
	if len(moves) == 0 {
		return nil
	}
	// Intn returns [0, n), so this picks a valid index
	idx := s.rng.Intn(len(moves))
	return &moves[idx]
}

// =============================================================================
// WEIGHTED RANDOM SOLVER
// =============================================================================

// WeightedRandomSolver picks moves with probability proportional to score.
//
// Strategy: Soft-greedy with controlled randomness.
//
// Higher-scoring moves are more likely to be selected, but lower-scoring
// moves still have a chance. The "temperature" parameter controls the
// balance between greedy and random:
//   - temperature → 0: Becomes pure greedy (always picks highest)
//   - temperature → ∞: Becomes pure random (uniform selection)
//   - temperature = 1: Balanced probabilistic selection
//
// The probability formula is: P(move) ∝ (score + 1)^(1/temperature)
// We add 1 to avoid zero probabilities for 0-score moves.
//
// Strengths:
//   - Adds exploration while favoring good moves
//   - Useful for MCTS-style algorithms
//   - More varied play than pure greedy
//
// Weaknesses:
//   - Sometimes picks suboptimal moves
//   - Requires tuning temperature for best results
type WeightedRandomSolver struct {
	rng         *rand.Rand
	temperature float64
}

// NewWeightedRandomSolver creates a weighted random solver.
//
// Parameters:
//   - seed: Random seed for reproducibility
//   - temperature: Controls randomness (1.0 is balanced, lower = more greedy)
func NewWeightedRandomSolver(seed int64, temperature float64) *WeightedRandomSolver {
	return &WeightedRandomSolver{
		rng:         rand.New(rand.NewSource(seed)),
		temperature: temperature,
	}
}

// Name returns "weighted" for identification.
func (s *WeightedRandomSolver) Name() string {
	return "weighted"
}

// SelectMove picks a move with probability weighted by score.
func (s *WeightedRandomSolver) SelectMove(game *engine.GameState, moves []engine.Move) *engine.Move {
	if len(moves) == 0 {
		return nil
	}

	// Single move - no choice to make
	if len(moves) == 1 {
		return &moves[0]
	}

	// Calculate weights for each move
	// weight = (score + 1)^(1/temperature)
	// Adding 1 ensures even 0-score moves have some probability
	weights := make([]float64, len(moves))
	total := 0.0

	for i, m := range moves {
		// math.Pow computes x^y
		w := math.Pow(float64(m.Score+1), 1/s.temperature)
		weights[i] = w
		total += w
	}

	// Weighted random selection using cumulative distribution
	// Pick a random point in [0, total) and find which bucket it falls in
	r := s.rng.Float64() * total
	cumulative := 0.0

	for i, w := range weights {
		cumulative += w
		if r <= cumulative {
			return &moves[i]
		}
	}

	// Fallback (shouldn't reach here due to floating point precision)
	return &moves[len(moves)-1]
}

// =============================================================================
// FUTURE SOLVER IDEAS
// =============================================================================

// TODO: MinimaxSolver - Look ahead N moves using minimax with alpha-beta pruning
// TODO: MCTSSolver - Monte Carlo Tree Search for stronger play
// TODO: NeuralSolver - Neural network evaluation (would need training data)

// =============================================================================
// SOLVER UTILITIES
// =============================================================================

// SolverByName returns a solver instance by name string.
//
// Useful for configuration-driven solver selection (e.g., from command line).
func SolverByName(name string, seed int64) Solver {
	switch name {
	case "random":
		return NewRandomSolver(seed)
	case "weighted":
		return NewWeightedRandomSolver(seed, 1.0)
	case "greedy":
		fallthrough
	default:
		return &GreedySolver{}
	}
}

// CompareSolvers runs games between two solvers and returns win statistics.
//
// Useful for evaluating solver strength. Alternates who goes first.
//
// Returns: (solver1 wins, solver2 wins, ties)
func CompareSolvers(solver1, solver2 Solver, numGames int, baseSeed int64) (int, int, int) {
	wins1, wins2, ties := 0, 0, 0

	for i := 0; i < numGames; i++ {
		// Create game with unique seed
		game := engine.NewGame(baseSeed + int64(i))

		// Alternate who goes first (solver1 goes first on even games)
		solvers := [2]Solver{solver1, solver2}
		if i%2 == 1 {
			solvers[0], solvers[1] = solver2, solver1
		}

		// Play game
		for !game.GameOver {
			solver := solvers[game.CurrentPlayer]
			move := GetMove(solver, game)

			if move != nil {
				game.PlayTiles(move.Placements)
			} else {
				// No valid moves - swap a tile
				game.SwapTiles([]int{0})
			}
		}

		// Record result (accounting for alternation)
		winner := game.Winner
		if i%2 == 1 && winner >= 0 {
			winner = 1 - winner // Flip winner if we swapped order
		}

		switch winner {
		case 0:
			wins1++
		case 1:
			wins2++
		default:
			ties++
		}
	}

	return wins1, wins2, ties
}
