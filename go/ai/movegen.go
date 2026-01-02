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
// MOVE GENERATION (OPTIMIZED)
// =============================================================================

// GenerateAllMoves returns all valid moves for the current player.
//
// Optimizations applied:
// 1. Pre-filter tile subsets that can't form valid lines
// 2. Avoid board cloning - use place/score/remove pattern
// 3. Skip duplicate permutations for identical tiles
// 4. Cache candidate positions
// 5. Early termination when finding a Qwirkle (12+ points)
//
// Returns moves sorted by score (highest first).
func GenerateAllMoves(game *engine.GameState) []engine.Move {
	hand := game.CurrentHand()
	board := game.Board
	isFirst := board.IsEmpty()

	// Pre-allocate with reasonable capacity
	moves := make([]engine.Move, 0, 64)
	bestScore := 0

	// Step 1: Find candidate positions (cached for all subsets)
	candidates := getCandidatePositions(board, isFirst)

	// Step 2: Get tiles from hand (use unsafe accessor to avoid copy)
	tiles := hand.TilesUnsafe()
	n := len(tiles)

	// Step 3: Try larger subsets first (more likely to score high)
	// This helps early termination kick in sooner
	for size := n; size >= 1; size-- {
		// Generate all subsets of this size
		for mask := 1; mask < (1 << n); mask++ {
			// Count bits to check subset size
			bits := 0
			for m := mask; m > 0; m >>= 1 {
				bits += int(m & 1)
			}
			if bits != size {
				continue
			}

			// Build subset based on bitmask
			subset := make([]engine.Tile, 0, 6)
			for i := 0; i < n; i++ {
				if mask&(1<<i) != 0 {
					subset = append(subset, tiles[i])
				}
			}

			// OPTIMIZATION: Skip subsets that can't possibly form a valid line
			if len(subset) > 1 && !canFormValidLine(subset) {
				continue
			}

			// Step 4: Try placing this subset
			subsetMoves := generateMovesForTilesOptimized(board, subset, candidates, isFirst)
			moves = append(moves, subsetMoves...)

			// Track best score for early termination
			for _, m := range subsetMoves {
				if m.Score > bestScore {
					bestScore = m.Score
				}
			}
		}

		// EARLY TERMINATION: If we found a Qwirkle (12+ points), stop searching
		// A Qwirkle is the maximum possible score for a single line
		if bestScore >= 12 {
			break
		}
	}

	// Step 5: Sort by score (highest first)
	sort.Slice(moves, func(i, j int) bool {
		return moves[i].Score > moves[j].Score
	})

	return moves
}

// canFormValidLine checks if a set of tiles could possibly form a valid Qwirkle line.
// This is a quick pre-check to avoid expensive permutation enumeration.
//
// A valid line requires: all same color (different shapes) OR all same shape (different colors)
// Also: no duplicate tiles allowed
//
// OPTIMIZED: Uses fixed [36]bool array instead of map for duplicate checking (no allocation)
func canFormValidLine(tiles []engine.Tile) bool {
	if len(tiles) <= 1 {
		return true
	}
	if len(tiles) > 6 {
		return false
	}

	// Check for duplicates using fixed array (no allocation)
	// 36 unique tiles: 6 shapes × 6 colors
	var seen [36]bool
	for _, t := range tiles {
		idx := t.Index()
		if seen[idx] {
			return false
		}
		seen[idx] = true
	}

	// Check if all same color
	sameColor := true
	for i := 1; i < len(tiles); i++ {
		if tiles[i].Color != tiles[0].Color {
			sameColor = false
			break
		}
	}
	if sameColor {
		return true
	}

	// Check if all same shape
	for i := 1; i < len(tiles); i++ {
		if tiles[i].Shape != tiles[0].Shape {
			return false
		}
	}
	return true
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

// generateMovesForTilesOptimized tries to place tiles without board cloning.
// Uses place/score/remove pattern for efficiency.
func generateMovesForTilesOptimized(
	board *engine.Board,
	tiles []engine.Tile,
	candidates []engine.Position,
	isFirst bool,
) []engine.Move {
	moves := make([]engine.Move, 0, 16)

	if len(tiles) == 1 {
		// Single tile - try each candidate position
		tile := tiles[0]
		for _, pos := range candidates {
			// Use fast validation (no board clone)
			if engine.ValidateSingleTile(board, pos, tile) {
				// Place, score, remove - no clone needed
				board.Set(pos, tile)
				placements := []engine.Placement{{Pos: pos, Tile: tile}}
				score := engine.ScoreMove(board, placements)
				board.Remove(pos)

				moves = append(moves, engine.Move{
					Placements: placements,
					Score:      score,
				})
			}
		}
	} else {
		// Multiple tiles - try both orientations
		moves = append(moves, tryLinePlacementsOptimized(board, tiles, candidates, isFirst, true)...)
		moves = append(moves, tryLinePlacementsOptimized(board, tiles, candidates, isFirst, false)...)
	}

	return moves
}

// tryLinePlacementsOptimized places tiles in a line without board cloning.
// Uses place/score/remove pattern and skips duplicate permutations.
func tryLinePlacementsOptimized(
	board *engine.Board,
	tiles []engine.Tile,
	candidates []engine.Position,
	isFirst bool,
	horizontal bool,
) []engine.Move {
	moves := make([]engine.Move, 0, 32)
	n := len(tiles)

	// Get unique permutations (skip duplicates for identical tiles)
	permutations := permuteUnique(tiles)

	// Pre-allocate placement slice (reused across iterations)
	placements := make([]engine.Placement, n)

	for _, perm := range permutations {
		// For each starting position
		for _, start := range candidates {
			// Build placements extending from start
			valid := true

			for i, tile := range perm {
				var pos engine.Position
				if horizontal {
					pos = engine.Position{Row: start.Row, Col: start.Col + i}
				} else {
					pos = engine.Position{Row: start.Row + i, Col: start.Col}
				}

				// Position must be empty
				if board.Has(pos) {
					valid = false
					break
				}

				placements[i] = engine.Placement{Pos: pos, Tile: tile}
			}

			if !valid {
				continue
			}

			// Place all tiles temporarily
			for _, p := range placements {
				board.Set(p.Pos, p.Tile)
			}

			// Validate the formed lines
			validMove := validateMultiTilePlacement(board, placements, isFirst)

			if validMove {
				// Score the move
				score := engine.ScoreMove(board, placements)

				// Make a copy of placements for the move
				placementsCopy := make([]engine.Placement, n)
				copy(placementsCopy, placements)

				moves = append(moves, engine.Move{
					Placements: placementsCopy,
					Score:      score,
				})
			}

			// Remove all tiles
			for _, p := range placements {
				board.Remove(p.Pos)
			}
		}
	}

	return moves
}

// validateMultiTilePlacement validates a multi-tile placement without cloning.
// Board should already have tiles placed. Uses zero-allocation line checks.
func validateMultiTilePlacement(board *engine.Board, placements []engine.Placement, isFirst bool) bool {
	if len(placements) == 0 {
		return false
	}

	// For first move, one tile must be at origin
	if isFirst {
		hasOrigin := false
		for _, p := range placements {
			if p.Pos.Row == 0 && p.Pos.Col == 0 {
				hasOrigin = true
				break
			}
		}
		if !hasOrigin {
			return false
		}
	} else {
		// Must connect to existing tiles (tiles not in this move)
		// Use fixed array instead of map for small sets
		connected := false
		for _, p := range placements {
			neighbors := p.Pos.Neighbors()
			for _, neighbor := range neighbors {
				if board.Has(neighbor) {
					// Check if neighbor is in our placements
					isOurs := false
					for _, op := range placements {
						if op.Pos == neighbor {
							isOurs = true
							break
						}
					}
					if !isOurs {
						connected = true
						break
					}
				}
			}
			if connected {
				break
			}
		}
		if !connected {
			return false
		}
	}

	// Check all lines formed by the placements using fast functions
	var hBuf, vBuf engine.LineTiles
	for _, p := range placements {
		engine.GetHorizontalLineFast(board, p.Pos, &hBuf)
		if !engine.IsValidLineFast(&hBuf) {
			return false
		}
		engine.GetVerticalLineFast(board, p.Pos, &vBuf)
		if !engine.IsValidLineFast(&vBuf) {
			return false
		}
	}

	return true
}

// permuteUnique generates permutations, skipping duplicates for identical tiles.
// Uses numeric keys instead of strings for faster comparison.
func permuteUnique(tiles []engine.Tile) [][]engine.Tile {
	n := len(tiles)
	if n <= 1 {
		result := make([]engine.Tile, n)
		copy(result, tiles)
		return [][]engine.Tile{result}
	}

	// Use uint64 key: each tile index (0-35) fits in 6 bits, so 6 tiles = 36 bits
	seen := make(map[uint64]bool)
	result := make([][]engine.Tile, 0, 24) // Pre-allocate for typical case

	// Use indices array to avoid slice allocations during recursion
	indices := make([]int, n)
	for i := range indices {
		indices[i] = i
	}

	var generate func(depth int)
	generate = func(depth int) {
		if depth == n {
			// Compute numeric key from current permutation
			var key uint64
			for i := 0; i < n; i++ {
				key = key*36 + uint64(tiles[indices[i]].Index())
			}
			if !seen[key] {
				seen[key] = true
				perm := make([]engine.Tile, n)
				for i := 0; i < n; i++ {
					perm[i] = tiles[indices[i]]
				}
				result = append(result, perm)
			}
			return
		}

		for i := depth; i < n; i++ {
			indices[depth], indices[i] = indices[i], indices[depth]
			generate(depth + 1)
			indices[depth], indices[i] = indices[i], indices[depth]
		}
	}

	generate(0)
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

// =============================================================================
// FAST MOVE GENERATION (for Monte Carlo simulations)
// =============================================================================

// GenerateFastMove finds the best single-tile move quickly.
// Used for fast Monte Carlo simulations - greedy over single tiles only.
//
// Strategy: Evaluate all single-tile placements, return highest scoring.
// This is O(n * p) where n=hand size, p=candidate positions.
// Much faster than full move generation which is O(2^n * n! * p).
func GenerateFastMove(game *engine.GameState) *engine.Move {
	hand := game.CurrentHand()
	board := game.Board
	isFirst := board.IsEmpty()

	candidates := getCandidatePositions(board, isFirst)
	tiles := hand.TilesUnsafe()

	var bestMove *engine.Move
	bestScore := -1

	// Find best single-tile placement (greedy over single tiles)
	for _, tile := range tiles {
		for _, pos := range candidates {
			placements := []engine.Placement{{Pos: pos, Tile: tile}}

			if engine.ValidateSingleTile(board, pos, tile) {
				// Calculate score - place tile, score, remove
				board.Set(pos, tile)
				score := engine.ScoreMove(board, placements)
				board.Remove(pos)

				if score > bestScore {
					bestScore = score
					bestMove = &engine.Move{Placements: placements, Score: score}
				}
			}
		}
	}

	return bestMove
}
