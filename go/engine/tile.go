// Package engine implements the core Qwirkle game logic.
//
// This package contains all the fundamental types and rules for playing Qwirkle:
//   - Tile: The basic game piece with a shape and color
//   - Board: A sparse grid where tiles are placed
//   - Bag: The pool of tiles players draw from
//   - Hand: A player's current tiles (max 6)
//   - Rules: Validation and scoring logic
//   - Game: Full game state and turn management
//
// The design prioritizes:
//   - Immutability where practical (tiles never change)
//   - Efficiency (sparse board, minimal allocations)
//   - Testability (seeded randomness, cloneable state)
package engine

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

// Shape represents one of the 6 Qwirkle tile shapes.
//
// In Go, we use `type X uint8` to create a new type based on uint8.
// This gives us type safety - you can't accidentally pass a Color where
// a Shape is expected, even though both are uint8 underneath.
//
// The `iota` keyword auto-increments: Circle=0, Square=1, Diamond=2, etc.
type Shape uint8

// Shape constants using iota for auto-incrementing values.
// This is a common Go pattern for enums. The first const gets iota=0,
// and each subsequent const gets iota+1.
const (
	Circle    Shape = iota // 0 - Simple circle
	Square                 // 1 - Four-sided square
	Diamond                // 2 - Rotated square (rhombus)
	Clover                 // 3 - Four-leaf clover shape
	Star                   // 4 - Six-pointed star
	Starburst              // 5 - Eight-pointed starburst
)

// String returns a human-readable name for the shape.
// This implements the fmt.Stringer interface, so when you print a Shape
// with fmt.Printf("%v", shape), it shows "Circle" instead of "0".
func (s Shape) String() string {
	// Go switch statements don't need "break" - they don't fall through by default.
	// If you want fall-through behavior, use the `fallthrough` keyword.
	switch s {
	case Circle:
		return "Circle"
	case Square:
		return "Square"
	case Diamond:
		return "Diamond"
	case Clover:
		return "Clover"
	case Star:
		return "Star"
	case Starburst:
		return "Starburst"
	default:
		return "Unknown"
	}
}

// Color represents one of the 6 Qwirkle tile colors.
// Same pattern as Shape - a distinct type based on uint8.
type Color uint8

// Color constants - matches the order used in the UI.
const (
	Red    Color = iota // 0
	Orange              // 1
	Yellow              // 2
	Green               // 3
	Blue                // 4
	Purple              // 5
)

// String returns a human-readable name for the color.
func (c Color) String() string {
	switch c {
	case Red:
		return "Red"
	case Orange:
		return "Orange"
	case Yellow:
		return "Yellow"
	case Green:
		return "Green"
	case Blue:
		return "Blue"
	case Purple:
		return "Purple"
	default:
		return "Unknown"
	}
}

// =============================================================================
// TILE STRUCT
// =============================================================================

// Tile represents a single Qwirkle tile with a shape and color.
//
// In Go, structs are value types (like C structs), not reference types.
// When you pass a Tile to a function, Go copies the entire struct.
// For small structs like this (2 bytes), that's efficient.
//
// Qwirkle has 36 unique tiles (6 shapes × 6 colors) with 3 copies each = 108 total.
type Tile struct {
	Shape Shape // The tile's shape (Circle, Square, etc.)
	Color Color // The tile's color (Red, Orange, etc.)
}

// Equal checks if two tiles have the same shape and color.
//
// We use a value receiver `(t Tile)` instead of pointer `(t *Tile)` because:
// 1. Tile is small (2 bytes) - copying is cheap
// 2. We don't need to modify the tile
// 3. Value receivers work with both values and pointers
//
// Go convention: Use value receivers for small, immutable types.
func (t Tile) Equal(other Tile) bool {
	return t.Shape == other.Shape && t.Color == other.Color
}

// String returns a human-readable representation like "Red Circle".
// Useful for debugging and logging.
func (t Tile) String() string {
	return t.Color.String() + " " + t.Shape.String()
}

// Index returns a unique index 0-35 for this tile.
// Used for fast duplicate checking with fixed-size arrays instead of maps.
// Formula: shape * 6 + color (6 shapes × 6 colors = 36 unique tiles)
func (t Tile) Index() int {
	return int(t.Shape)*6 + int(t.Color)
}

// =============================================================================
// TILE GENERATION
// =============================================================================

// AllTiles returns a slice containing all 108 Qwirkle tiles.
//
// A slice in Go is like a dynamic array. It has three parts:
//   - Pointer to underlying array
//   - Length (current number of elements)
//   - Capacity (max elements before reallocation)
//
// We use make([]Tile, 0, 108) to pre-allocate capacity for 108 tiles,
// avoiding reallocations as we append. This is a common optimization.
func AllTiles() []Tile {
	// make([]Type, length, capacity)
	// - length=0: slice starts empty
	// - capacity=108: pre-allocate space for all tiles
	tiles := make([]Tile, 0, 108)

	// Three copies of each unique tile
	for copy := 0; copy < 3; copy++ {
		// Iterate through all shapes (0-5)
		// Shape(0) converts int 0 to Shape type
		for shape := Shape(0); shape <= Starburst; shape++ {
			// Iterate through all colors (0-5)
			for color := Color(0); color <= Purple; color++ {
				// append() adds to slice, may reallocate if capacity exceeded
				// Since we pre-allocated, this won't reallocate
				tiles = append(tiles, Tile{Shape: shape, Color: color})
			}
		}
	}

	return tiles
}

// CountByShape returns how many tiles of each shape exist in a slice.
// Useful for debugging and statistics.
func CountByShape(tiles []Tile) map[Shape]int {
	// make(map[K]V) creates an empty map
	// Maps in Go are reference types (unlike structs)
	counts := make(map[Shape]int)

	// range over slice gives (index, value)
	// We use _ to ignore the index since we don't need it
	for _, t := range tiles {
		// Map access with ++ works even if key doesn't exist yet
		// (zero value for int is 0, so counts[shape] starts at 0)
		counts[t.Shape]++
	}

	return counts
}

// CountByColor returns how many tiles of each color exist in a slice.
func CountByColor(tiles []Tile) map[Color]int {
	counts := make(map[Color]int)
	for _, t := range tiles {
		counts[t.Color]++
	}
	return counts
}
