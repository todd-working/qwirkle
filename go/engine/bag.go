package engine

import (
	"math/rand"
)

// =============================================================================
// BAG TYPE
// =============================================================================

// Bag holds the pool of tiles that players draw from.
//
// Key concepts:
// - Starts with all 108 tiles, shuffled
// - Players draw to fill their hand (up to 6 tiles)
// - Tiles can be returned (for swapping)
// - When empty, players can't refill
//
// Design: Uses a seeded RNG for reproducibility.
// In simulations and tests, you can recreate exact game sequences by using
// the same seed. For real games, use a time-based seed for randomness.
type Bag struct {
	tiles []Tile     // Remaining tiles (draw from front, like a queue)
	rng   *rand.Rand // Random number generator (seeded for reproducibility)
}

// NewBag creates a shuffled bag with all 108 tiles.
//
// The seed parameter controls randomness:
//   - seed > 0: Reproducible shuffle (same seed = same order)
//   - seed = 0: In this implementation, uses 0 as seed (not random!)
//
// For true randomness, pass time.Now().UnixNano() as the seed.
//
// Why seeded randomness matters:
//   - Tests: Verify specific game scenarios
//   - Debugging: Reproduce bugs exactly
//   - Simulations: Control for randomness when comparing AI strategies
func NewBag(seed int64) *Bag {
	// Create a new random source and generator
	// rand.NewSource creates an independent RNG that doesn't affect global state
	// This is important for concurrent simulations
	rng := rand.New(rand.NewSource(seed))

	// Get all 108 tiles
	tiles := AllTiles()

	// Fisher-Yates shuffle - the standard unbiased shuffle algorithm
	// Iterate backwards, swapping each element with a random earlier element
	// Time complexity: O(n), Space complexity: O(1) extra
	for i := len(tiles) - 1; i > 0; i-- {
		// Pick a random index from 0 to i (inclusive)
		j := rng.Intn(i + 1)
		// Swap elements - Go allows parallel assignment
		tiles[i], tiles[j] = tiles[j], tiles[i]
	}

	return &Bag{
		tiles: tiles,
		rng:   rng,
	}
}

// =============================================================================
// ACCESSORS
// =============================================================================

// Remaining returns the number of tiles left in the bag.
func (b *Bag) Remaining() int {
	return len(b.tiles)
}

// IsEmpty returns true if no tiles remain.
func (b *Bag) IsEmpty() bool {
	return len(b.tiles) == 0
}

// =============================================================================
// DRAWING AND RETURNING TILES
// =============================================================================

// Draw removes and returns n tiles from the bag.
//
// If the bag has fewer than n tiles, returns all remaining tiles.
// This is intentional - at game end, players draw what's available.
//
// Implementation note: We draw from the front of the slice (like a queue).
// This is slightly less efficient than drawing from the back, but makes
// the tiles[:n] slicing cleaner. For 108 tiles max, this doesn't matter.
func (b *Bag) Draw(n int) []Tile {
	// Can't draw more than we have
	if n > len(b.tiles) {
		n = len(b.tiles)
	}

	// Take the first n tiles
	// tiles[:n] creates a slice of the first n elements
	drawn := b.tiles[:n]

	// Remove drawn tiles from bag
	// tiles[n:] creates a slice starting at index n
	b.tiles = b.tiles[n:]

	// Return a copy to prevent caller from modifying bag internals
	// (Technically not needed here since we've already removed them,
	// but it's good practice for API clarity)
	result := make([]Tile, len(drawn))
	copy(result, drawn)

	return result
}

// Return puts tiles back into the bag and reshuffles.
//
// Used for tile swapping - player returns tiles to bag, then draws new ones.
// We reshuffle to maintain randomness (so you can't track returned tiles).
func (b *Bag) Return(tiles []Tile) {
	// Add tiles back to the bag
	b.tiles = append(b.tiles, tiles...)

	// Reshuffle the entire bag
	// This prevents players from knowing where returned tiles went
	for i := len(b.tiles) - 1; i > 0; i-- {
		j := b.rng.Intn(i + 1)
		b.tiles[i], b.tiles[j] = b.tiles[j], b.tiles[i]
	}
}

// =============================================================================
// UTILITIES
// =============================================================================

// Peek returns the next n tiles without removing them.
// Useful for debugging and testing.
func (b *Bag) Peek(n int) []Tile {
	if n > len(b.tiles) {
		n = len(b.tiles)
	}

	// Return a copy so caller can't modify bag internals
	result := make([]Tile, n)
	copy(result, b.tiles[:n])

	return result
}

// Clone creates a deep copy of the bag.
// Useful for AI lookahead - simulate drawing without affecting real bag.
//
// Note: The RNG state is NOT cloned. The clone gets a new RNG with a
// derived seed. This is usually fine for simulations.
func (b *Bag) Clone(newSeed int64) *Bag {
	clone := &Bag{
		tiles: make([]Tile, len(b.tiles)),
		rng:   rand.New(rand.NewSource(newSeed)),
	}
	copy(clone.tiles, b.tiles)
	return clone
}
