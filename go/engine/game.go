package engine

import "time"

// =============================================================================
// GAME STATE
// =============================================================================

// GameState represents the complete state of a Qwirkle game.
//
// This is the central type for the game engine. It holds:
//   - The board with all placed tiles
//   - Both players' hands
//   - The bag of remaining tiles
//   - Scores and turn information
//   - Move history for undo/replay
//
// Design decisions:
//   - 2-player fixed (Qwirkle supports 2-4, but we start simple)
//   - Hands array indexed by player number (0 or 1)
//   - Move history enables undo and game replay
type GameState struct {
	Board         *Board       // The game board with placed tiles
	Bag           *Bag         // Tiles remaining to draw
	Hands         [2]*Hand     // Player hands: Hands[0] is Player 1, Hands[1] is Player 2
	Scores        [2]int       // Player scores: Scores[0] is Player 1's score
	CurrentPlayer int          // Whose turn: 0 or 1
	GameOver      bool         // True when game has ended
	Winner        int          // -1 = tie, 0 = Player 1 wins, 1 = Player 2 wins
	MoveHistory   []MoveRecord // All moves played (for undo/replay)
	Seed          int64        // Random seed used (for reproducibility)
}

// MoveRecord stores information about a played move.
//
// Used for:
//   - Undo functionality (restore previous state)
//   - Game replay (recreate entire game)
//   - Training data (record what moves were made)
type MoveRecord struct {
	Player     int         // Which player made this move (0 or 1)
	Placements []Placement // Tiles placed (empty for swap moves)
	Score      int         // Points earned (0 for swaps)
	WasSwap    bool        // True if this was a tile swap
	SwapCount  int         // How many tiles were swapped
}

// =============================================================================
// GAME CREATION
// =============================================================================

// NewGame creates a new game with the given random seed.
//
// The seed controls all randomness in the game:
//   - Initial bag shuffle
//   - Tile draws throughout the game
//
// Use seed=0 for a random game (uses current time as seed).
// Use a specific seed to recreate the exact same game.
func NewGame(seed int64) *GameState {
	// Use current time if no seed provided
	// time.Now().UnixNano() gives nanosecond precision for good randomness
	if seed == 0 {
		seed = time.Now().UnixNano()
	}

	// Create the shuffled bag
	bag := NewBag(seed)

	// Create empty hands for both players
	// [2]*Hand is an array of 2 pointers to Hand
	hands := [2]*Hand{NewHand(), NewHand()}

	// Deal initial hands (6 tiles each)
	hands[0].Refill(bag)
	hands[1].Refill(bag)

	return &GameState{
		Board:         NewBoard(),
		Bag:           bag,
		Hands:         hands,
		Scores:        [2]int{0, 0}, // Both start at 0
		CurrentPlayer: 0,            // Player 1 goes first
		GameOver:      false,
		Winner:        -1,                      // No winner yet (also used for tie)
		MoveHistory:   make([]MoveRecord, 0),   // Empty history
		Seed:          seed,
	}
}

// =============================================================================
// STATE ACCESSORS
// =============================================================================

// CurrentHand returns the current player's hand.
//
// Convenience method to avoid game.Hands[game.CurrentPlayer] everywhere.
func (g *GameState) CurrentHand() *Hand {
	return g.Hands[g.CurrentPlayer]
}

// OtherPlayer returns the other player's number (0→1, 1→0).
func (g *GameState) OtherPlayer() int {
	return 1 - g.CurrentPlayer
}

// =============================================================================
// PLAYING TILES
// =============================================================================

// PlayTiles executes a move: validates, places tiles, scores, refills hand.
//
// Parameters:
//   - placements: The tiles and positions to place
//
// Returns:
//   - The score earned, or -1 if the move was invalid
//
// Side effects (if valid):
//   - Tiles are placed on the board
//   - Score is added to current player
//   - Tiles are removed from hand and hand is refilled
//   - Current player switches (unless game ends)
//   - Move is recorded in history
func (g *GameState) PlayTiles(placements []Placement) int {
	// Can't play if game is over
	if g.GameOver {
		return -1
	}

	// Validate the move
	isFirst := g.Board.IsEmpty()
	if !ValidateMove(g.Board, placements, isFirst) {
		return -1
	}

	// Apply placements to board
	for _, p := range placements {
		g.Board.Set(p.Pos, p.Tile)
	}

	// Calculate score
	score := ScoreMove(g.Board, placements)
	g.Scores[g.CurrentPlayer] += score

	// Remove played tiles from hand
	hand := g.CurrentHand()
	for _, p := range placements {
		// Find the tile in hand and remove it
		// We match by tile value (shape + color)
		for i := 0; i < hand.Size(); i++ {
			if t := hand.Get(i); t != nil && t.Equal(p.Tile) {
				hand.Remove(i)
				break // Remove only one matching tile
			}
		}
	}

	// Refill hand from bag
	hand.Refill(g.Bag)

	// Record move in history
	g.MoveHistory = append(g.MoveHistory, MoveRecord{
		Player:     g.CurrentPlayer,
		Placements: placements,
		Score:      score,
		WasSwap:    false,
	})

	// Check for game over
	g.checkGameOver()

	// Switch to other player (if game continues)
	if !g.GameOver {
		g.CurrentPlayer = g.OtherPlayer()
	}

	return score
}

// =============================================================================
// SWAPPING TILES
// =============================================================================

// SwapTiles swaps tiles from hand with the bag.
//
// In Qwirkle, a player can swap any number of tiles instead of playing.
// This is useful when no good moves are available.
//
// Parameters:
//   - indices: Which tiles to swap (0-based indices in hand)
//
// Returns:
//   - true if swap succeeded, false if invalid
//
// Rules:
//   - Can only swap if bag has at least as many tiles as you want to swap
//   - After swapping, turn passes to other player
func (g *GameState) SwapTiles(indices []int) bool {
	// Can't swap if game is over
	if g.GameOver {
		return false
	}

	// Must swap at least one tile
	if len(indices) == 0 {
		return false
	}

	// Must have enough tiles in bag
	if g.Bag.Remaining() < len(indices) {
		return false
	}

	hand := g.CurrentHand()

	// Remove selected tiles from hand
	removed := hand.RemoveMultiple(indices)
	if len(removed) != len(indices) {
		return false // Some indices were invalid
	}

	// Draw new tiles from bag
	hand.Refill(g.Bag)

	// Return old tiles to bag (shuffles them in)
	g.Bag.Return(removed)

	// Record swap in history
	g.MoveHistory = append(g.MoveHistory, MoveRecord{
		Player:    g.CurrentPlayer,
		WasSwap:   true,
		SwapCount: len(indices),
	})

	// Switch to other player
	g.CurrentPlayer = g.OtherPlayer()

	return true
}

// =============================================================================
// GAME END DETECTION
// =============================================================================

// checkGameOver determines if the game has ended.
//
// Game ends when:
//   - A player plays their last tile AND the bag is empty
//
// When game ends:
//   - The player who went out gets 6 bonus points
//   - Winner is player with higher score (or tie)
func (g *GameState) checkGameOver() {
	// Check if any player has emptied their hand with empty bag
	for i, hand := range g.Hands {
		if hand.Size() == 0 && g.Bag.IsEmpty() {
			g.GameOver = true

			// Bonus for going out
			g.Scores[i] += 6

			break
		}
	}

	// Determine winner if game over
	if g.GameOver {
		if g.Scores[0] > g.Scores[1] {
			g.Winner = 0 // Player 1 wins
		} else if g.Scores[1] > g.Scores[0] {
			g.Winner = 1 // Player 2 wins
		} else {
			g.Winner = -1 // Tie
		}
	}
}

// =============================================================================
// CLONING (for AI lookahead)
// =============================================================================

// Clone creates a deep copy of the game state.
//
// Essential for AI algorithms that need to simulate future moves
// without affecting the actual game state.
//
// Note: Bag is NOT cloned (RNG state is complex to clone).
// For full simulation fidelity, you'd need to also clone the bag.
func (g *GameState) Clone() *GameState {
	// Create new state with copied values
	clone := &GameState{
		Board:         g.Board.Clone(),
		Hands:         [2]*Hand{g.Hands[0].Clone(), g.Hands[1].Clone()},
		Scores:        g.Scores, // Arrays are copied by value
		CurrentPlayer: g.CurrentPlayer,
		GameOver:      g.GameOver,
		Winner:        g.Winner,
		Seed:          g.Seed,
		MoveHistory:   make([]MoveRecord, len(g.MoveHistory)),
	}

	// Copy move history
	copy(clone.MoveHistory, g.MoveHistory)

	// Note: Bag is NOT cloned - for AI simulation, we typically
	// don't need perfect bag simulation, just move validation

	return clone
}

// =============================================================================
// DEBUG HELPERS
// =============================================================================

// String returns a debug representation of the game state.
func (g *GameState) String() string {
	status := "In Progress"
	if g.GameOver {
		if g.Winner == -1 {
			status = "Tie"
		} else {
			status = "Player " + string('1'+g.Winner) + " Wins"
		}
	}

	return "Game State:\n" +
		"  Status: " + status + "\n" +
		"  Scores: P1=" + itoa(g.Scores[0]) + " P2=" + itoa(g.Scores[1]) + "\n" +
		"  Current: Player " + string('1'+g.CurrentPlayer) + "\n" +
		"  Bag: " + itoa(g.Bag.Remaining()) + " tiles\n" +
		"  Board:\n" + g.Board.Debug()
}

// itoa converts int to string (simple implementation).
// Using this instead of strconv.Itoa to avoid import for simple case.
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	if n < 0 {
		return "-" + itoa(-n)
	}
	s := ""
	for n > 0 {
		s = string('0'+byte(n%10)) + s
		n /= 10
	}
	return s
}
