// Package ai implements AI strategies for playing Qwirkle.
//
// This package provides:
//   - Move generation: Find all valid moves for a game state
//   - AI solvers: Different strategies for selecting moves
//
// The move generator is the core of the AI - it exhaustively finds
// all legal moves so solvers can choose among them.
package ai

import (
	"sort"

	"github.com/todd-working/qwirkle/engine"
)

// =============================================================================
// MOVE GENERATION
// =============================================================================

// GenerateAllMoves returns all valid moves for the current player.
//
// This is a brute-force search that:
// 1. Finds all candidate positions (adjacent to existing tiles)
// 2. Tries all subsets of tiles from hand
// 3. Tries all permutations and orientations
// 4. Validates each potential move
//
// Returns moves sorted by score (highest first), which is useful for
// greedy strategies and alpha-beta pruning.
//
// Time complexity: O(2^n * n! * p) where n=hand size (≤6), p=positions
// In practice, much faster due to early pruning of invalid moves.
func GenerateAllMoves(game *engine.GameState) []engine.Move {
	hand := game.CurrentHand()
	board := game.Board
	isFirst := board.IsEmpty()

	moves := make([]engine.Move, 0)

	// Step 1: Find candidate positions
	candidates := getCandidatePositions(board, isFirst)

	// Step 2: Get tiles from hand
	tiles := hand.Tiles()
	n := len(tiles)

	// Step 3: Try all non-empty subsets of tiles
	// Use bitmask to enumerate subsets: 1 to 2^n - 1
	// Each bit represents whether a tile is included
	for mask := 1; mask < (1 << n); mask++ {
		// Build subset based on bitmask
		subset := make([]engine.Tile, 0)
		for i := 0; i < n; i++ {
			// Check if bit i is set
			if mask&(1<<i) != 0 {
				subset = append(subset, tiles[i])
			}
		}

		// Step 4: Try placing this subset
		subsetMoves := generateMovesForTiles(board, subset, candidates, isFirst)
		moves = append(moves, subsetMoves...)
	}

	// Step 5: Sort by score (highest first)
	// sort.Slice uses a custom comparator function
	sort.Slice(moves, func(i, j int) bool {
		return moves[i].Score > moves[j].Score
	})

	return moves
}

// getCandidatePositions returns positions where tiles might be legally placed.
//
// For the first move: only (0,0) is valid.
// After that: any empty position adjacent to an existing tile.
func getCandidatePositions(board *engine.Board, isFirst bool) []engine.Position {
	// First tile must go at origin
	if isFirst && board.IsEmpty() {
		return []engine.Position{{Row: 0, Col: 0}}
	}

	// Find all empty positions adjacent to tiles
	// Use map as set to avoid duplicates
	candidates := make(map[engine.Position]bool)

	for _, pos := range board.Positions() {
		// Check each neighbor of each placed tile
		for _, neighbor := range pos.Neighbors() {
			if !board.Has(neighbor) {
				candidates[neighbor] = true
			}
		}
	}

	// Convert map keys to slice
	result := make([]engine.Position, 0, len(candidates))
	for pos := range candidates {
		result = append(result, pos)
	}

	return result
}

// generateMovesForTiles tries to place a specific set of tiles on the board.
//
// For single tiles: try each candidate position.
// For multiple tiles: try horizontal and vertical line placements.
func generateMovesForTiles(
	board *engine.Board,
	tiles []engine.Tile,
	candidates []engine.Position,
	isFirst bool,
) []engine.Move {
	moves := make([]engine.Move, 0)

	if len(tiles) == 1 {
		// Single tile - try each candidate position
		for _, pos := range candidates {
			placements := []engine.Placement{{Pos: pos, Tile: tiles[0]}}

			// Validate move
			if engine.ValidateMove(board, placements, isFirst) {
				// Calculate score (need to temporarily place tile)
				testBoard := board.Clone()
				testBoard.Set(pos, tiles[0])
				score := engine.ScoreMove(testBoard, placements)

				moves = append(moves, engine.Move{
					Placements: placements,
					Score:      score,
				})
			}
		}
	} else {
		// Multiple tiles - must form a line
		// Try both horizontal and vertical orientations
		moves = append(moves, tryLinePlacements(board, tiles, candidates, isFirst, true)...)
		moves = append(moves, tryLinePlacements(board, tiles, candidates, isFirst, false)...)
	}

	return moves
}

// tryLinePlacements attempts to place tiles in a line from each candidate position.
//
// Parameters:
//   - board: Current board state
//   - tiles: Tiles to place (in any order)
//   - candidates: Starting positions to try
//   - isFirst: Is this the first move of the game?
//   - horizontal: True for horizontal line, false for vertical
//
// We try all permutations of the tiles because order matters for validity.
// A line [Red Circle, Blue Circle, Red Square] might be invalid, but
// [Red Circle, Red Square, Blue Square] (reordered) might be valid.
func tryLinePlacements(
	board *engine.Board,
	tiles []engine.Tile,
	candidates []engine.Position,
	isFirst bool,
	horizontal bool,
) []engine.Move {
	moves := make([]engine.Move, 0)
	n := len(tiles)

	// Get all permutations of the tiles
	// For 6 tiles, this is 720 permutations - manageable
	permutations := permute(tiles)

	for _, perm := range permutations {
		// For each starting position
		for _, start := range candidates {
			// Build placements extending from start
			placements := make([]engine.Placement, n)
			valid := true

			for i, tile := range perm {
				var pos engine.Position
				if horizontal {
					// Extend rightward
					pos = engine.Position{Row: start.Row, Col: start.Col + i}
				} else {
					// Extend downward
					pos = engine.Position{Row: start.Row + i, Col: start.Col}
				}

				// Position must be empty on original board
				if board.Has(pos) {
					valid = false
					break
				}

				placements[i] = engine.Placement{Pos: pos, Tile: tile}
			}

			// Skip if any position was occupied
			if !valid {
				continue
			}

			// Validate the complete move
			if engine.ValidateMove(board, placements, isFirst) {
				// Calculate score
				testBoard := board.Clone()
				for _, p := range placements {
					testBoard.Set(p.Pos, p.Tile)
				}
				score := engine.ScoreMove(testBoard, placements)

				moves = append(moves, engine.Move{
					Placements: placements,
					Score:      score,
				})
			}
		}
	}

	return moves
}

// =============================================================================
// PERMUTATION GENERATOR
// =============================================================================

// permute generates all permutations of a tile slice.
//
// Uses recursive Heap's algorithm approach.
// For n elements, generates n! permutations.
//
// Example: [A, B] → [[A, B], [B, A]]
//
// Time complexity: O(n!) - unavoidable for generating all permutations.
// Space complexity: O(n! * n) for storing all permutations.
func permute(tiles []engine.Tile) [][]engine.Tile {
	// Base case: single element or empty
	if len(tiles) <= 1 {
		// Return a copy to avoid modifying the original
		result := make([]engine.Tile, len(tiles))
		copy(result, tiles)
		return [][]engine.Tile{result}
	}

	result := make([][]engine.Tile, 0)

	// For each tile, make it the first element and recurse on the rest
	for i, tile := range tiles {
		// Build "rest" slice without element i
		rest := make([]engine.Tile, 0, len(tiles)-1)
		rest = append(rest, tiles[:i]...)
		rest = append(rest, tiles[i+1:]...)

		// Get permutations of the rest
		for _, perm := range permute(rest) {
			// Prepend current tile to each permutation
			full := make([]engine.Tile, 0, len(tiles))
			full = append(full, tile)
			full = append(full, perm...)
			result = append(result, full)
		}
	}

	return result
}

// =============================================================================
// MOVE FILTERING (optional utilities)
// =============================================================================

// FilterMovesByScore returns only moves with score >= minScore.
// Useful for pruning low-value moves in time-constrained situations.
func FilterMovesByScore(moves []engine.Move, minScore int) []engine.Move {
	filtered := make([]engine.Move, 0)
	for _, m := range moves {
		if m.Score >= minScore {
			filtered = append(filtered, m)
		}
	}
	return filtered
}

// TopNMoves returns the top N highest-scoring moves.
// Assumes moves are already sorted by score.
func TopNMoves(moves []engine.Move, n int) []engine.Move {
	if n >= len(moves) {
		return moves
	}
	return moves[:n]
}
