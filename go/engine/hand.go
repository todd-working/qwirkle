package engine

// MaxHandSize is the maximum number of tiles a player can hold.
// This is a constant in Qwirkle - players always try to maintain 6 tiles.
const MaxHandSize = 6

// =============================================================================
// HAND TYPE
// =============================================================================

// Hand represents a player's current tiles.
//
// In Qwirkle:
//   - Each player holds up to 6 tiles
//   - After playing tiles, hand is refilled from the bag
//   - Players can see their own tiles but not opponents'
//
// Implementation uses a slice for flexibility in adding/removing tiles.
// The order of tiles in hand doesn't matter for gameplay, but we maintain
// insertion order for UI consistency.
type Hand struct {
	tiles []Tile
}

// NewHand creates an empty hand.
//
// Pre-allocates capacity for 6 tiles to avoid reallocations during refill.
func NewHand() *Hand {
	return &Hand{
		// make([]T, length, capacity)
		// length=0: starts empty
		// capacity=MaxHandSize: room for 6 tiles without reallocation
		tiles: make([]Tile, 0, MaxHandSize),
	}
}

// =============================================================================
// ACCESSORS
// =============================================================================

// Tiles returns a copy of the hand's tiles.
//
// Returns a copy (not the internal slice) to prevent external modification.
// This is defensive programming - callers can't accidentally corrupt the hand.
func (h *Hand) Tiles() []Tile {
	// Create a new slice with the same length
	result := make([]Tile, len(h.tiles))
	// copy(dst, src) copies elements from src to dst
	copy(result, h.tiles)
	return result
}

// Size returns the number of tiles in hand.
func (h *Hand) Size() int {
	return len(h.tiles)
}

// Get returns a pointer to the tile at index (0-based), or nil if invalid.
//
// Why 0-based internally but 1-based in API?
//   - Go slices are 0-indexed, so internal code uses 0-based
//   - User interface uses 1-based (tiles numbered 1-6) for friendliness
//   - API layer handles the conversion
func (h *Hand) Get(index int) *Tile {
	// Bounds check - return nil for invalid indices
	if index < 0 || index >= len(h.tiles) {
		return nil
	}
	// Return pointer to the tile
	// Note: This is a pointer to our internal slice element
	// Caller should not modify it
	return &h.tiles[index]
}

// =============================================================================
// MODIFICATION
// =============================================================================

// Add adds tiles to the hand (up to MaxHandSize).
//
// Silently stops adding when hand is full - no error.
// This matches Qwirkle rules: you can't hold more than 6 tiles.
func (h *Hand) Add(tiles []Tile) {
	for _, t := range tiles {
		// Stop if hand is full
		if len(h.tiles) >= MaxHandSize {
			break
		}
		h.tiles = append(h.tiles, t)
	}
}

// Remove removes the tile at index and returns it.
//
// Returns nil if index is invalid.
// Shifts remaining tiles to fill the gap (maintains order).
func (h *Hand) Remove(index int) *Tile {
	// Validate index
	if index < 0 || index >= len(h.tiles) {
		return nil
	}

	// Store tile to return
	tile := h.tiles[index]

	// Remove by creating new slice without this element
	// append(slice[:i], slice[i+1:]...) is the standard removal idiom
	// The ... spreads the second slice's elements as individual arguments
	h.tiles = append(h.tiles[:index], h.tiles[index+1:]...)

	return &tile
}

// RemoveMultiple removes tiles at multiple indices and returns them.
//
// IMPORTANT: Indices must be handled carefully because removing elements
// shifts later elements. We solve this by sorting indices in descending
// order and removing from highest to lowest.
//
// Example problem without sorting:
//   Hand: [A, B, C, D], want to remove indices [1, 2]
//   Remove index 1 (B): [A, C, D]
//   Remove index 2 (D, not C!): Wrong tile removed!
//
// With descending sort:
//   Remove index 2 (C): [A, B, D]
//   Remove index 1 (B): [A, D]  ✓ Correct!
func (h *Hand) RemoveMultiple(indices []int) []Tile {
	// Make a copy to avoid modifying caller's slice
	sorted := make([]int, len(indices))
	copy(sorted, indices)

	// Sort descending using simple bubble sort
	// For small slices (max 6 elements), this is fine
	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j] > sorted[i] {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	// Remove tiles from highest index to lowest
	removed := make([]Tile, 0, len(indices))
	for _, idx := range sorted {
		if t := h.Remove(idx); t != nil {
			removed = append(removed, *t)
		}
	}

	return removed
}

// =============================================================================
// GAME OPERATIONS
// =============================================================================

// Refill draws tiles from bag to fill hand to MaxHandSize.
//
// This is called after every play - players always try to have 6 tiles.
// If bag is empty or nearly empty, player may end up with fewer than 6.
func (h *Hand) Refill(bag *Bag) {
	// Calculate how many tiles we need
	need := MaxHandSize - len(h.tiles)

	// Draw from bag and add to hand
	if need > 0 {
		drawn := bag.Draw(need)
		h.Add(drawn)
	}
}

// =============================================================================
// CLONING
// =============================================================================

// Clone creates a deep copy of the hand.
//
// Essential for AI lookahead - simulate plays without affecting real hand.
func (h *Hand) Clone() *Hand {
	clone := NewHand()
	clone.tiles = make([]Tile, len(h.tiles))
	copy(clone.tiles, h.tiles)
	return clone
}

// =============================================================================
// UTILITIES
// =============================================================================

// Contains checks if the hand has a tile matching the given tile.
// Useful for validation - can the player actually play this tile?
func (h *Hand) Contains(tile Tile) bool {
	for _, t := range h.tiles {
		if t.Equal(tile) {
			return true
		}
	}
	return false
}

// IndexOf returns the index of a matching tile, or -1 if not found.
func (h *Hand) IndexOf(tile Tile) int {
	for i, t := range h.tiles {
		if t.Equal(tile) {
			return i
		}
	}
	return -1
}

// String returns a string representation of the hand.
// Useful for debugging: "[Red Circle, Blue Square, ...]"
func (h *Hand) String() string {
	if len(h.tiles) == 0 {
		return "(empty hand)"
	}

	result := "["
	for i, t := range h.tiles {
		if i > 0 {
			result += ", "
		}
		result += t.String()
	}
	result += "]"
	return result
}
