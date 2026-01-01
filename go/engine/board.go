package engine

import "fmt"

// =============================================================================
// POSITION TYPE
// =============================================================================

// Position represents a coordinate on the game board.
//
// The board uses a Cartesian coordinate system:
//   - Row increases downward (row 0 is top)
//   - Col increases rightward (col 0 is left)
//   - Origin (0,0) is where the first tile must be placed
//
// Positions can be negative - the board grows infinitely in all directions.
type Position struct {
	Row int // Vertical position (negative = up, positive = down)
	Col int // Horizontal position (negative = left, positive = right)
}

// String returns the position as "row,col" (matches the JSON key format).
// Used both for debugging and as map keys in the API.
func (p Position) String() string {
	// fmt.Sprintf is like printf but returns a string instead of printing
	return fmt.Sprintf("%d,%d", p.Row, p.Col)
}

// Neighbors returns the 4 orthogonally adjacent positions.
//
// In Qwirkle, tiles must connect orthogonally (not diagonally).
// Returns a fixed-size array [4]Position, not a slice, because
// we always have exactly 4 neighbors. Arrays are value types in Go.
//
// Order: up, down, left, right (arbitrary but consistent)
func (p Position) Neighbors() [4]Position {
	return [4]Position{
		{p.Row - 1, p.Col}, // up
		{p.Row + 1, p.Col}, // down
		{p.Row, p.Col - 1}, // left
		{p.Row, p.Col + 1}, // right
	}
}

// =============================================================================
// BOARD TYPE
// =============================================================================

// Board represents the game board as a sparse map.
//
// Design choice: Sparse map vs 2D array
//
// We use map[Position]Tile instead of [][]Tile because:
// 1. Board size is unbounded - tiles can be placed anywhere
// 2. Most positions are empty - sparse storage is memory-efficient
// 3. O(1) lookup by position (same as array)
// 4. Easy to iterate over only placed tiles
//
// Trade-offs:
// - Slightly more overhead per tile than array
// - No spatial locality (cache-unfriendly for scanning)
// - But for Qwirkle's small boards (~50-100 tiles max), this is fine
//
// The struct has a single unexported field `tiles`. We use unexported fields
// (lowercase) to encapsulate the internal representation. External code must
// use our methods (Get, Set, etc.) to interact with the board.
type Board struct {
	tiles map[Position]Tile // Private: only accessible within this package
}

// NewBoard creates an empty board.
//
// This is a constructor function - Go doesn't have constructors built into
// the language, so we use a conventional New* function pattern.
//
// We must initialize the map with make() because the zero value of a map
// is nil, and you can't write to a nil map.
func NewBoard() *Board {
	// Return a pointer (*Board) so callers share the same board instance.
	// If we returned Board (value), every function call would copy the entire map.
	return &Board{
		tiles: make(map[Position]Tile),
	}
}

// =============================================================================
// BASIC OPERATIONS
// =============================================================================

// Get returns a pointer to the tile at the given position, or nil if empty.
//
// Why return *Tile instead of (Tile, bool)?
// - Nil check is idiomatic Go for "not found"
// - Caller can check `if tile := board.Get(pos); tile != nil`
// - Avoids copying the tile when returning (though Tile is small, so minor benefit)
//
// Alternative signature: func (b *Board) Get(pos Position) (Tile, bool)
// This is also valid and sometimes preferred. We chose pointer for consistency.
func (b *Board) Get(pos Position) *Tile {
	// Map lookup with "comma ok" idiom
	// t is the value (zero value if not found)
	// ok is true if key exists, false otherwise
	if t, ok := b.tiles[pos]; ok {
		// Return pointer to a copy of t (not to map internals)
		// This is important - returning &b.tiles[pos] directly doesn't work
		// because map elements are not addressable in Go
		return &t
	}
	return nil
}

// Set places a tile at the given position.
//
// If a tile already exists at this position, it's replaced.
// The caller should validate the move before calling Set.
func (b *Board) Set(pos Position, tile Tile) {
	b.tiles[pos] = tile
}

// Remove deletes the tile at the given position.
//
// Removing a non-existent key is safe in Go - it's a no-op.
// This is useful for undo operations.
func (b *Board) Remove(pos Position) {
	delete(b.tiles, pos)
}

// Has returns true if there's a tile at the given position.
//
// More efficient than Get when you only need to check existence,
// as it doesn't create a pointer.
func (b *Board) Has(pos Position) bool {
	// The "comma ok" idiom - we only care about ok, not the value
	_, ok := b.tiles[pos]
	return ok
}

// =============================================================================
// SIZE AND BOUNDS
// =============================================================================

// IsEmpty returns true if the board has no tiles.
func (b *Board) IsEmpty() bool {
	// len() on map returns number of key-value pairs
	return len(b.tiles) == 0
}

// Size returns the number of tiles on the board.
func (b *Board) Size() int {
	return len(b.tiles)
}

// Positions returns all occupied positions as a slice.
//
// Note: Map iteration order is randomized in Go for security reasons.
// Don't rely on the order of returned positions being consistent.
func (b *Board) Positions() []Position {
	// Pre-allocate slice with exact capacity needed
	positions := make([]Position, 0, len(b.tiles))

	// range over map gives (key, value) pairs
	// We only need the keys (positions)
	for pos := range b.tiles {
		positions = append(positions, pos)
	}

	return positions
}

// Bounds returns the bounding box of all tiles on the board.
//
// Returns (minRow, maxRow, minCol, maxCol).
// For an empty board, returns (0, 0, 0, 0).
//
// Go allows multiple return values - use this instead of creating
// a struct when the values are simple and used together.
func (b *Board) Bounds() (minRow, maxRow, minCol, maxCol int) {
	if b.IsEmpty() {
		return 0, 0, 0, 0
	}

	// Track whether we've seen the first position
	first := true

	for pos := range b.tiles {
		if first {
			// Initialize bounds with first position
			minRow, maxRow = pos.Row, pos.Row
			minCol, maxCol = pos.Col, pos.Col
			first = false
		} else {
			// Expand bounds if this position is outside current bounds
			if pos.Row < minRow {
				minRow = pos.Row
			}
			if pos.Row > maxRow {
				maxRow = pos.Row
			}
			if pos.Col < minCol {
				minCol = pos.Col
			}
			if pos.Col > maxCol {
				maxCol = pos.Col
			}
		}
	}

	// Named return values are automatically returned
	return
}

// =============================================================================
// NEIGHBOR OPERATIONS
// =============================================================================

// HasNeighbor returns true if any orthogonally adjacent position has a tile.
//
// Used to check connectivity - in Qwirkle, every tile (except the first)
// must connect to an existing tile.
func (b *Board) HasNeighbor(pos Position) bool {
	// Iterate over the 4 neighbors
	for _, neighbor := range pos.Neighbors() {
		if b.Has(neighbor) {
			return true
		}
	}
	return false
}

// GetNeighbors returns all tiles adjacent to the given position.
//
// Returns a slice of (Position, Tile) pairs for occupied neighbors.
// Useful for analyzing what a new tile would connect to.
func (b *Board) GetNeighbors(pos Position) []struct {
	Pos  Position
	Tile Tile
} {
	// Anonymous struct type - useful for one-off return types
	// In production code, you might define a named type for clarity
	var neighbors []struct {
		Pos  Position
		Tile Tile
	}

	for _, neighborPos := range pos.Neighbors() {
		if tile := b.Get(neighborPos); tile != nil {
			neighbors = append(neighbors, struct {
				Pos  Position
				Tile Tile
			}{neighborPos, *tile})
		}
	}

	return neighbors
}

// =============================================================================
// CLONING
// =============================================================================

// Clone creates a deep copy of the board.
//
// Essential for:
// - Move validation (test moves without modifying original)
// - AI lookahead (explore different move sequences)
// - Undo support
//
// We must manually copy the map contents because maps are reference types.
// Just copying the Board struct would share the same underlying map.
func (b *Board) Clone() *Board {
	clone := NewBoard()

	// Copy each tile to the new board
	// This creates new map entries, not references to the original
	for pos, tile := range b.tiles {
		clone.tiles[pos] = tile
	}

	return clone
}

// =============================================================================
// DEBUG HELPERS
// =============================================================================

// Debug returns a simple text representation of the board.
// Useful for debugging in tests and logs.
func (b *Board) Debug() string {
	if b.IsEmpty() {
		return "(empty board)"
	}

	minRow, maxRow, minCol, maxCol := b.Bounds()
	result := ""

	for row := minRow; row <= maxRow; row++ {
		for col := minCol; col <= maxCol; col++ {
			if tile := b.Get(Position{Row: row, Col: col}); tile != nil {
				// Show first letter of color and shape
				result += fmt.Sprintf("[%c%c]", tile.Color.String()[0], tile.Shape.String()[0])
			} else {
				result += " .  "
			}
		}
		result += "\n"
	}

	return result
}
