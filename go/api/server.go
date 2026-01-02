// Package api provides the HTTP server for the Qwirkle web UI.
package api

import (
	"encoding/json"
	"log"
	"math/rand"
	"net/http"
	"runtime"
	"sync"

	"github.com/todd-working/qwirkle/ai"
	"github.com/todd-working/qwirkle/engine"
)

// Package-level singleton solver for simulations (avoids allocation per sim)
var simSolver = &ai.GreedySolver{}

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

type WinProbabilityResponse struct {
	P0Prob       float64 `json:"p0_prob"`
	P1Prob       float64 `json:"p1_prob"`
	TieProb      float64 `json:"tie_prob"`
	NSimulations int     `json:"n_simulations"`
	Confidence   float64 `json:"confidence"`
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

func (s *Server) HandleWinProbability(w http.ResponseWriter, r *http.Request) {
	gameID := r.PathValue("id")

	s.mu.RLock()
	session, ok := s.sessions[gameID]
	s.mu.RUnlock()

	if !ok {
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	// If game over, return definitive result
	if session.Game.GameOver {
		var p0, p1, tie float64
		switch session.Game.Winner {
		case 0:
			p0 = 1.0
		case 1:
			p1 = 1.0
		default:
			tie = 1.0
		}
		json.NewEncoder(w).Encode(WinProbabilityResponse{
			P0Prob:       p0,
			P1Prob:       p1,
			TieProb:      tie,
			NSimulations: 1,
			Confidence:   1.0,
		})
		return
	}

	// Run Monte Carlo simulations in parallel with full greedy
	// 400 sims gives ±5% margin of error at 95% confidence
	nSimulations := 400
	p0Wins, p1Wins, ties := s.runSimulationsParallel(session.Game, nSimulations)

	total := float64(nSimulations)
	confidence := 1.0 - (0.5 / float64(nSimulations))
	if confidence > 0.99 {
		confidence = 0.99
	}

	json.NewEncoder(w).Encode(WinProbabilityResponse{
		P0Prob:       float64(p0Wins) / total,
		P1Prob:       float64(p1Wins) / total,
		TieProb:      float64(ties) / total,
		NSimulations: nSimulations,
		Confidence:   confidence,
	})
}

// runSimulationsParallel runs Monte Carlo simulations in parallel using goroutines.
// Uses fast single-tile move generation for speed.
func (s *Server) runSimulationsParallel(game *engine.GameState, n int) (p0Wins, p1Wins, ties int) {
	// Use worker pool pattern for parallel simulations
	// Use all available CPU cores for maximum throughput
	numWorkers := runtime.NumCPU()
	jobs := make(chan int, n)
	results := make(chan int, n) // 0=p0 win, 1=p1 win, 2=tie

	// Start workers
	for w := 0; w < numWorkers; w++ {
		go func(workerID int) {
			for simIdx := range jobs {
				result := s.runSingleSimulation(game, simIdx)
				results <- result
			}
		}(w)
	}

	// Send jobs
	for i := 0; i < n; i++ {
		jobs <- i
	}
	close(jobs)

	// Collect results
	for i := 0; i < n; i++ {
		switch <-results {
		case 0:
			p0Wins++
		case 1:
			p1Wins++
		case 2:
			ties++
		}
	}

	return
}

// runSingleSimulation plays out one game and returns: 0=p0 win, 1=p1 win, 2=tie
func (s *Server) runSingleSimulation(game *engine.GameState, simIdx int) int {
	// Clone game state (lightweight - skips move history)
	simGame := game.CloneForSimulation()
	simGame.Bag = game.Bag.Clone(game.Seed + int64(simIdx) + 1)

	// Play out the game using singleton solver
	maxTurns := 100
	turns := 0
	for !simGame.GameOver && turns < maxTurns {
		turns++

		// Generate all moves and pick best (full greedy)
		allMoves := ai.GenerateAllMoves(simGame)
		move := simSolver.SelectMove(simGame, allMoves)

		if move != nil {
			// Use prevalidated version - move already validated by GenerateAllMoves
			simGame.PlayTilesPrevalidated(move.Placements, move.Score)
		} else {
			// No valid moves - swap if possible
			if simGame.Bag.Remaining() > 0 && simGame.CurrentHand().Size() > 0 {
				simGame.SwapTiles([]int{0})
			} else {
				simGame.GameOver = true
				break
			}
		}
	}

	// Return result
	if simGame.Scores[0] > simGame.Scores[1] {
		return 0
	} else if simGame.Scores[1] > simGame.Scores[0] {
		return 1
	}
	return 2
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

// corsMiddleware adds CORS headers to all responses.
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// Handle preflight requests
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
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
	mux.HandleFunc("GET /api/game/{id}/win-probability", s.HandleWinProbability)

	// Serve static files (React build)
	mux.Handle("/", http.FileServer(http.Dir("./static")))

	log.Printf("Server starting on %s", addr)
	return http.ListenAndServe(addr, corsMiddleware(mux))
}
