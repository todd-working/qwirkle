// Package api provides the HTTP server for the Qwirkle web UI.
package api

import (
	"encoding/json"
	"log"
	"math/rand"
	"net/http"
	"sync"

	"github.com/todd-working/qwirkle/ai"
	"github.com/todd-working/qwirkle/engine"
)

// Server holds the HTTP server and game sessions.
type Server struct {
	sessions map[string]*Session
	mu       sync.RWMutex
}

// Session represents an active game session.
type Session struct {
	Game       *engine.GameState
	VsAI       bool
	AIStrategy string
	AIVsAI     bool
}

// NewServer creates a new API server.
func NewServer() *Server {
	return &Server{
		sessions: make(map[string]*Session),
	}
}

// --- Request/Response types ---

type NewGameRequest struct {
	VsAI       bool   `json:"vs_ai"`
	AIStrategy string `json:"ai_strategy"`
	AIVsAI     bool   `json:"ai_vs_ai"`
}

type GameStateResponse struct {
	GameID            string              `json:"game_id"`
	Board             map[string]TileJSON `json:"board"`
	Hand              []TileJSON          `json:"hand"`
	CurrentPlayer     int                 `json:"current_player"`
	Scores            [2]int              `json:"scores"`
	BagRemaining      int                 `json:"bag_remaining"`
	GameOver          bool                `json:"game_over"`
	Winner            *int                `json:"winner"`
	LastMovePositions [][]int             `json:"last_move_positions"`
	Message           string              `json:"message,omitempty"`
}

type TileJSON struct {
	Shape int `json:"shape"`
	Color int `json:"color"`
}

type PlayRequest struct {
	Placements []PlacementJSON `json:"placements"`
}

type PlacementJSON struct {
	Row       int `json:"row"`
	Col       int `json:"col"`
	TileIndex int `json:"tile_index"` // 1-based index in hand
}

type PlayResponse struct {
	Success bool               `json:"success"`
	State   *GameStateResponse `json:"state,omitempty"`
	Error   string             `json:"error,omitempty"`
}

type SwapRequest struct {
	Indices []int `json:"indices"` // 1-based indices
}

type HintResponse struct {
	HasMove    bool            `json:"has_move"`
	Message    string          `json:"message"`
	Placements []PlacementJSON `json:"placements"`
}

// --- Handlers ---

func (s *Server) HandleNewGame(w http.ResponseWriter, r *http.Request) {
	var req NewGameRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	game := engine.NewGame(0) // Random seed
	gameID := generateID()

	session := &Session{
		Game:       game,
		VsAI:       req.VsAI,
		AIStrategy: req.AIStrategy,
		AIVsAI:     req.AIVsAI,
	}

	s.mu.Lock()
	s.sessions[gameID] = session
	s.mu.Unlock()

	resp := s.buildStateResponse(gameID, game, "Game started!")
	json.NewEncoder(w).Encode(resp)
}

func (s *Server) HandleGetState(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.RLock()
	session, ok := s.sessions[gameID]
	s.mu.RUnlock()

	if !ok {
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	resp := s.buildStateResponse(gameID, session.Game, "")
	json.NewEncoder(w).Encode(resp)
}

func (s *Server) HandlePlay(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.Lock()
	session, ok := s.sessions[gameID]
	if !ok {
		s.mu.Unlock()
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	var req PlayRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.mu.Unlock()
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	game := session.Game
	hand := game.CurrentHand()

	// Convert placements
	placements := make([]engine.Placement, len(req.Placements))
	for i, p := range req.Placements {
		tile := hand.Get(p.TileIndex - 1) // Convert to 0-based
		if tile == nil {
			s.mu.Unlock()
			json.NewEncoder(w).Encode(PlayResponse{Success: false, Error: "Invalid tile index"})
			return
		}
		placements[i] = engine.Placement{
			Pos:  engine.Position{Row: p.Row, Col: p.Col},
			Tile: *tile,
		}
	}

	// Execute move
	score := game.PlayTiles(placements)
	if score < 0 {
		s.mu.Unlock()
		json.NewEncoder(w).Encode(PlayResponse{Success: false, Error: "Invalid move"})
		return
	}

	message := ""
	if score > 0 {
		message = "Scored " + itoa(score) + " points!"
	}

	// If vs AI and not game over, make AI move
	if session.VsAI && !game.GameOver && game.CurrentPlayer == 1 {
		s.makeAIMove(session)
	}

	s.mu.Unlock()

	resp := s.buildStateResponse(gameID, game, message)
	json.NewEncoder(w).Encode(PlayResponse{Success: true, State: &resp})
}

func (s *Server) HandleSwap(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.Lock()
	session, ok := s.sessions[gameID]
	if !ok {
		s.mu.Unlock()
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	var req SwapRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.mu.Unlock()
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Convert to 0-based indices
	indices := make([]int, len(req.Indices))
	for i, idx := range req.Indices {
		indices[i] = idx - 1
	}

	if !session.Game.SwapTiles(indices) {
		s.mu.Unlock()
		json.NewEncoder(w).Encode(PlayResponse{Success: false, Error: "Cannot swap tiles"})
		return
	}

	// If vs AI and not game over, make AI move
	if session.VsAI && !session.Game.GameOver && session.Game.CurrentPlayer == 1 {
		s.makeAIMove(session)
	}

	s.mu.Unlock()

	resp := s.buildStateResponse(gameID, session.Game, "Tiles swapped")
	json.NewEncoder(w).Encode(PlayResponse{Success: true, State: &resp})
}

func (s *Server) HandleHint(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.RLock()
	session, ok := s.sessions[gameID]
	s.mu.RUnlock()

	if !ok {
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	solver := &ai.GreedySolver{}
	move := ai.GetMove(solver, session.Game)

	if move == nil {
		json.NewEncoder(w).Encode(HintResponse{
			HasMove: false,
			Message: "No valid moves - consider swapping tiles",
		})
		return
	}

	placements := make([]PlacementJSON, len(move.Placements))
	for i, p := range move.Placements {
		// Find tile index in hand
		hand := session.Game.CurrentHand()
		tileIndex := 1
		for j := 0; j < hand.Size(); j++ {
			if t := hand.Get(j); t != nil && t.Equal(p.Tile) {
				tileIndex = j + 1
				break
			}
		}
		placements[i] = PlacementJSON{
			Row:       p.Pos.Row,
			Col:       p.Pos.Col,
			TileIndex: tileIndex,
		}
	}

	json.NewEncoder(w).Encode(HintResponse{
		HasMove:    true,
		Message:    "Best move scores " + itoa(move.Score) + " points",
		Placements: placements,
	})
}

func (s *Server) HandleAIStep(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.Lock()
	session, ok := s.sessions[gameID]
	if !ok {
		s.mu.Unlock()
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	if session.Game.GameOver {
		s.mu.Unlock()
		resp := s.buildStateResponse(gameID, session.Game, "Game over")
		json.NewEncoder(w).Encode(PlayResponse{Success: true, State: &resp})
		return
	}

	s.makeAIMove(session)
	s.mu.Unlock()

	resp := s.buildStateResponse(gameID, session.Game, "AI moved")
	json.NewEncoder(w).Encode(PlayResponse{Success: true, State: &resp})
}

// --- Helpers ---

func (s *Server) makeAIMove(session *Session) {
	var solver ai.Solver
	switch session.AIStrategy {
	case "random":
		solver = ai.NewRandomSolver(0)
	case "weighted":
		solver = ai.NewWeightedRandomSolver(0, 1.0)
	default:
		solver = &ai.GreedySolver{}
	}

	move := ai.GetMove(solver, session.Game)
	if move != nil {
		session.Game.PlayTiles(move.Placements)
	} else {
		// No valid moves - swap random tile
		session.Game.SwapTiles([]int{0})
	}
}

func (s *Server) buildStateResponse(gameID string, game *engine.GameState, message string) GameStateResponse {
	// Build board map
	board := make(map[string]TileJSON)
	for _, pos := range game.Board.Positions() {
		tile := game.Board.Get(pos)
		if tile != nil {
			key := pos.String()
			board[key] = TileJSON{Shape: int(tile.Shape), Color: int(tile.Color)}
		}
	}

	// Build hand
	hand := make([]TileJSON, 0)
	currentHand := game.CurrentHand()
	for i := 0; i < currentHand.Size(); i++ {
		if t := currentHand.Get(i); t != nil {
			hand = append(hand, TileJSON{Shape: int(t.Shape), Color: int(t.Color)})
		}
	}

	// Get last move positions
	lastMovePositions := make([][]int, 0)
	if len(game.MoveHistory) > 0 {
		lastMove := game.MoveHistory[len(game.MoveHistory)-1]
		for _, p := range lastMove.Placements {
			lastMovePositions = append(lastMovePositions, []int{p.Pos.Row, p.Pos.Col})
		}
	}

	var winner *int
	if game.GameOver {
		w := game.Winner
		winner = &w
	}

	return GameStateResponse{
		GameID:            gameID,
		Board:             board,
		Hand:              hand,
		CurrentPlayer:     game.CurrentPlayer,
		Scores:            game.Scores,
		BagRemaining:      game.Bag.Remaining(),
		GameOver:          game.GameOver,
		Winner:            winner,
		LastMovePositions: lastMovePositions,
		Message:           message,
	}
}

func generateID() string {
	const chars = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, 8)
	for i := range b {
		b[i] = chars[int(rand.Int63())%len(chars)]
	}
	return string(b)
}

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

// Run starts the HTTP server.
func (s *Server) Run(addr string) error {
	mux := http.NewServeMux()

	// Health check
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok"}`))
	})

	// API routes
	mux.HandleFunc("POST /api/game/new", s.HandleNewGame)
	mux.HandleFunc("GET /api/game/{id}", s.HandleGetState)
	mux.HandleFunc("POST /api/game/{id}/play", s.HandlePlay)
	mux.HandleFunc("POST /api/game/{id}/swap", s.HandleSwap)
	mux.HandleFunc("GET /api/game/{id}/hint", s.HandleHint)
	mux.HandleFunc("POST /api/game/{id}/ai-step", s.HandleAIStep)

	// Serve static files (React build)
	mux.Handle("/", http.FileServer(http.Dir("./static")))

	log.Printf("Server starting on %s", addr)
	return http.ListenAndServe(addr, mux)
}
