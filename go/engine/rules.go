package engine

// =============================================================================
// MOVE TYPES
// =============================================================================

// Placement represents placing a single tile at a position.
//
// A move consists of one or more placements, all in the same row or column.
type Placement struct {
	Pos  Position // Where to place the tile
	Tile Tile     // The tile being placed
}

// Move represents a complete player move.
//
// A valid move in Qwirkle:
//   - Places 1-6 tiles from hand
//   - All tiles in same row OR same column
//   - Tiles form a continuous line (possibly filling gaps)
//   - Each formed line is valid (same color or same shape, no duplicates)
type Move struct {
	Placements []Placement // The tiles and positions
	Score      int         // Points this move would earn
}

// =============================================================================
// LINE EXTRACTION
// =============================================================================

// GetLine returns all tiles in a line starting from pos, moving in direction (dr, dc).
//
// Parameters:
//   - board: The game board
//   - pos: Starting position (not included in result)
//   - dr: Row delta (-1=up, 0=stay, 1=down)
//   - dc: Column delta (-1=left, 0=stay, 1=right)
//
// Returns tiles in order from pos outward.
//
// Example: GetLine(board, {0,0}, 0, 1) returns tiles at (0,1), (0,2), ... until empty.
func GetLine(board *Board, pos Position, dr, dc int) []Tile {
	tiles := make([]Tile, 0)

	// Start one step in the direction
	r, c := pos.Row+dr, pos.Col+dc

	// Keep going while we find tiles
	for {
		p := Position{Row: r, Col: c}
		if t := board.Get(p); t != nil {
			tiles = append(tiles, *t)
			r += dr // Move to next position
			c += dc
		} else {
			break // Empty cell - end of line
		}
	}

	return tiles
}

// GetHorizontalLine returns all tiles in the horizontal line through pos.
//
// Includes the tile at pos (if any) and extends left and right until empty cells.
// Used for scoring - we need to count the complete line a tile joins.
func GetHorizontalLine(board *Board, pos Position) []Tile {
	// Get tiles to the left (will be in reverse order)
	left := GetLine(board, pos, 0, -1)

	// Get tiles to the right
	right := GetLine(board, pos, 0, 1)

	// Build result: reversed left + center + right
	// Pre-allocate for efficiency
	result := make([]Tile, 0, len(left)+len(right)+1)

	// Reverse the left tiles (they were collected going away from pos)
	for i := len(left) - 1; i >= 0; i-- {
		result = append(result, left[i])
	}

	// Add center tile if present
	if t := board.Get(pos); t != nil {
		result = append(result, *t)
	}

	// Add right tiles
	result = append(result, right...)

	return result
}

// GetVerticalLine returns all tiles in the vertical line through pos.
func GetVerticalLine(board *Board, pos Position) []Tile {
	up := GetLine(board, pos, -1, 0)
	down := GetLine(board, pos, 1, 0)

	result := make([]Tile, 0, len(up)+len(down)+1)

	// Reverse up tiles
	for i := len(up) - 1; i >= 0; i-- {
		result = append(result, up[i])
	}

	if t := board.Get(pos); t != nil {
		result = append(result, *t)
	}

	result = append(result, down...)

	return result
}

// =============================================================================
// LINE VALIDATION
// =============================================================================

// IsValidLine checks if a line of tiles follows Qwirkle rules.
//
// Rules for a valid line:
// 1. All tiles share the same color (with different shapes), OR
// 2. All tiles share the same shape (with different colors)
// 3. No duplicate tiles (same shape AND color)
// 4. Maximum 6 tiles (one of each in the shared attribute)
//
// Examples:
//   - [Red Circle, Red Square, Red Star] - Valid (same color, different shapes)
//   - [Red Circle, Blue Circle, Green Circle] - Valid (same shape, different colors)
//   - [Red Circle, Blue Square] - Invalid (neither same color nor same shape)
//   - [Red Circle, Red Circle] - Invalid (duplicate)
func IsValidLine(tiles []Tile) bool {
	// Empty or single tile is always valid
	if len(tiles) <= 1 {
		return true
	}

	// Maximum line length is 6 (one of each in a set)
	if len(tiles) > 6 {
		return false
	}

	// Check for duplicates using a map as a set
	// In Go, map[T]bool with value true is a common set pattern
	seen := make(map[Tile]bool)
	for _, t := range tiles {
		if seen[t] {
			return false // Duplicate found
		}
		seen[t] = true
	}

	// Check if all same color
	sameColor := true
	for i := 1; i < len(tiles); i++ {
		if tiles[i].Color != tiles[0].Color {
			sameColor = false
			break
		}
	}

	// Check if all same shape
	sameShape := true
	for i := 1; i < len(tiles); i++ {
		if tiles[i].Shape != tiles[0].Shape {
			sameShape = false
			break
		}
	}

	// Must be one or the other (if same color AND same shape with no dupes,
	// that's only possible with a single tile, which we handled above)
	return sameColor || sameShape
}

// =============================================================================
// PLACEMENT VALIDATION
// =============================================================================

// ValidatePlacement checks if placing a tile at pos is valid.
//
// This temporarily places the tile to check both lines it would form.
// Caller should ensure the position is empty before calling.
//
// Parameters:
//   - board: Current board state (may be modified temporarily)
//   - pos: Where to place the tile
//   - tile: The tile to place
//   - isFirstMove: True if this is the first tile of the game
//
// Note: This function temporarily modifies the board but restores it.
// We use defer to ensure cleanup even if something panics.
func ValidatePlacement(board *Board, pos Position, tile Tile, isFirstMove bool) bool {
	// Position must be empty
	if board.Has(pos) {
		return false
	}

	// First tile of game must be at origin (0,0)
	if isFirstMove && board.IsEmpty() {
		return pos.Row == 0 && pos.Col == 0
	}

	// After first move, tile must connect to existing tiles
	if !isFirstMove && !board.HasNeighbor(pos) {
		return false
	}

	// Temporarily place tile to check lines
	board.Set(pos, tile)
	// defer ensures Remove is called when function returns
	// This is Go's way of doing cleanup (like try-finally in Java)
	defer board.Remove(pos)

	// Check horizontal line validity
	hLine := GetHorizontalLine(board, pos)
	if !IsValidLine(hLine) {
		return false
	}

	// Check vertical line validity
	vLine := GetVerticalLine(board, pos)
	if !IsValidLine(vLine) {
		return false
	}

	return true
}

// ValidateMove checks if a complete move (multiple placements) is valid.
//
// Move validity rules:
// 1. At least one tile must be placed
// 2. All tiles must be in same row OR same column
// 3. Tiles must form a contiguous line (can fill gaps between existing tiles)
// 4. Each individual placement must be valid
func ValidateMove(board *Board, placements []Placement, isFirstMove bool) bool {
	if len(placements) == 0 {
		return false
	}

	// Check collinearity: all tiles in same row OR same column
	allSameRow := true
	allSameCol := true
	for i := 1; i < len(placements); i++ {
		if placements[i].Pos.Row != placements[0].Pos.Row {
			allSameRow = false
		}
		if placements[i].Pos.Col != placements[0].Pos.Col {
			allSameCol = false
		}
	}

	// Must be collinear (or single tile, which is trivially both)
	if !allSameRow && !allSameCol {
		return false
	}

	// Clone board to test placements
	// We need to apply them one by one and validate
	testBoard := board.Clone()

	for i, p := range placements {
		// First placement of first move gets special handling
		isFirst := isFirstMove && i == 0 && board.IsEmpty()
		if !ValidatePlacement(testBoard, p.Pos, p.Tile, isFirst) {
			return false
		}
		// Apply this placement before validating next
		testBoard.Set(p.Pos, p.Tile)
	}

	// Check contiguity: all placements must form a continuous line
	// This means no empty gaps between the placed tiles
	if len(placements) > 1 {
		if allSameRow {
			// All in same row - check column continuity
			row := placements[0].Pos.Row

			// Find min and max columns
			minCol, maxCol := placements[0].Pos.Col, placements[0].Pos.Col
			for _, p := range placements[1:] {
				if p.Pos.Col < minCol {
					minCol = p.Pos.Col
				}
				if p.Pos.Col > maxCol {
					maxCol = p.Pos.Col
				}
			}

			// Every position between min and max must be filled
			// (either by existing tile or new placement)
			for c := minCol; c <= maxCol; c++ {
				if !testBoard.Has(Position{Row: row, Col: c}) {
					return false // Gap found
				}
			}
		} else { // allSameCol
			// All in same column - check row continuity
			col := placements[0].Pos.Col

			minRow, maxRow := placements[0].Pos.Row, placements[0].Pos.Row
			for _, p := range placements[1:] {
				if p.Pos.Row < minRow {
					minRow = p.Pos.Row
				}
				if p.Pos.Row > maxRow {
					maxRow = p.Pos.Row
				}
			}

			for r := minRow; r <= maxRow; r++ {
				if !testBoard.Has(Position{Row: r, Col: col}) {
					return false
				}
			}
		}
	}

	return true
}

// =============================================================================
// SCORING
// =============================================================================

// ScoreMove calculates points for a move.
//
// Scoring rules:
//   - Each tile in a completed line scores 1 point
//   - A tile can be part of two lines (horizontal and vertical)
//   - A "Qwirkle" (6-tile line) scores 6 bonus points
//   - Placing a single tile with no neighbors scores 1 point
//
// IMPORTANT: Call this AFTER placements are applied to the board.
// The board should have the new tiles in place.
func ScoreMove(board *Board, placements []Placement) int {
	if len(placements) == 0 {
		return 0
	}

	score := 0

	// Track which lines we've scored to avoid double-counting
	// A line is identified by its direction and first tile position
	scoredLines := make(map[string]bool)

	for _, p := range placements {
		// Score horizontal line
		hLine := GetHorizontalLine(board, p.Pos)
		if len(hLine) > 1 {
			// Create unique key for this line
			// We use the first tile's position and direction
			key := "h" + hLine[0].String()
			if !scoredLines[key] {
				scoredLines[key] = true
				score += len(hLine)
				// Qwirkle bonus!
				if len(hLine) == 6 {
					score += 6
				}
			}
		}

		// Score vertical line
		vLine := GetVerticalLine(board, p.Pos)
		if len(vLine) > 1 {
			key := "v" + vLine[0].String()
			if !scoredLines[key] {
				scoredLines[key] = true
				score += len(vLine)
				if len(vLine) == 6 {
					score += 6
				}
			}
		}
	}

	// Single tile with no line neighbors scores 1 point
	if score == 0 && len(placements) == 1 {
		score = 1
	}

	return score
}
