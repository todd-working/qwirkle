"""FastAPI application for Qwirkle Web UI.

REST API wrapping the game engine for web/mobile clients.
"""

from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.models.tile import Shape, Color
from src.models.board import Position
from src.web.models import (
    NewGameRequest, NewGameResponse,
    PlayRequest, PlayResponse,
    SwapRequest, SwapResponse,
    UndoResponse,
    HintResponse, PlacementModel,
    ValidPositionsRequest, ValidPositionsResponse,
    GameStateResponse, TileModel,
)
from src.web.session import session_manager, GameSession
from src.ai.move_gen import find_valid_positions


# Create FastAPI app
app = FastAPI(
    title="Qwirkle API",
    description="REST API for Qwirkle game",
    version="1.0.0"
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _tile_to_model(tile) -> TileModel:
    """Convert Tile to TileModel."""
    shapes = list(Shape)
    colors = list(Color)
    return TileModel(
        shape=shapes.index(tile.shape),
        color=colors.index(tile.color)
    )


def _session_to_state_response(session: GameSession) -> GameStateResponse:
    """Convert session to GameStateResponse."""
    state = session.state

    # Convert board
    board: Dict[str, TileModel] = {}
    for pos, tile in state.board.all_tiles():
        key = f"{pos[0]},{pos[1]}"
        board[key] = _tile_to_model(tile)

    # Convert current player's hand
    hand = [_tile_to_model(t) for t in state.hands[state.current_player].tiles()]

    # Convert last move positions
    last_positions = [[p[0], p[1]] for p in session.last_move_positions]

    return GameStateResponse(
        game_id=session.game_id,
        board=board,
        hand=hand,
        current_player=state.current_player,
        scores=state.scores,
        bag_remaining=state.bag.remaining(),
        game_over=state.game_over,
        winner=state.winner,
        last_move_positions=last_positions,
        message=session.message
    )


@app.post("/api/game/new", response_model=NewGameResponse)
async def create_game(request: NewGameRequest):
    """Create a new game session."""
    session = session_manager.create_game(
        seed=request.seed,
        vs_ai=request.vs_ai,
        ai_vs_ai=request.ai_vs_ai,
        ai_strategy=request.ai_strategy
    )

    return NewGameResponse(
        game_id=session.game_id,
        state=_session_to_state_response(session)
    )


@app.get("/api/game/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    """Get current game state."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    return _session_to_state_response(session)


@app.post("/api/game/{game_id}/play", response_model=PlayResponse)
async def play_tiles(game_id: str, request: PlayRequest):
    """Play tiles on the board."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    # Convert placements to (tile_index, position) format
    placements = [
        (p.tile_index, (p.row, p.col))
        for p in request.placements
    ]

    success, points, qwirkles, error = session_manager.play_tiles(session, placements)

    if not success:
        return PlayResponse(
            success=False,
            error=error
        )

    response = PlayResponse(
        success=True,
        points=points,
        qwirkles=qwirkles,
        state=_session_to_state_response(session)
    )

    # If vs AI and it's now AI's turn, play AI move
    if session.vs_ai and not session.state.game_over and session.state.current_player == 1:
        ai_success, ai_points, ai_message = session_manager.play_ai_turn(session)
        # Update response with new state after AI move
        response.state = _session_to_state_response(session)

    return response


@app.post("/api/game/{game_id}/swap", response_model=SwapResponse)
async def swap_tiles(game_id: str, request: SwapRequest):
    """Swap tiles with the bag."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    success, error = session_manager.swap_tiles(session, request.tile_indices)

    if not success:
        return SwapResponse(success=False, error=error)

    response = SwapResponse(
        success=True,
        state=_session_to_state_response(session)
    )

    # If vs AI and it's now AI's turn, play AI move
    if session.vs_ai and not session.state.game_over and session.state.current_player == 1:
        session_manager.play_ai_turn(session)
        response.state = _session_to_state_response(session)

    return response


@app.post("/api/game/{game_id}/undo", response_model=UndoResponse)
async def undo_move(game_id: str):
    """Undo the last move."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    success, error = session_manager.undo(session)

    if not success:
        return UndoResponse(success=False, error=error)

    return UndoResponse(
        success=True,
        state=_session_to_state_response(session)
    )


@app.get("/api/game/{game_id}/hint", response_model=HintResponse)
async def get_hint(game_id: str):
    """Get AI hint for current player."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.state.game_over:
        return HintResponse(
            has_move=False,
            message="Game is over"
        )

    move = session_manager.get_hint(session)

    if move is None:
        return HintResponse(
            has_move=False,
            message="No valid moves. Try swapping tiles."
        )

    # Convert move to response format
    hand = session.state.hands[session.state.current_player].tiles()
    placements = []

    for pos, tile in move.placements:
        # Find tile index in hand
        try:
            idx = hand.index(tile) + 1
            placements.append(PlacementModel(
                row=pos[0],
                col=pos[1],
                tile_index=idx
            ))
        except ValueError:
            # Tile not found (shouldn't happen)
            pass

    return HintResponse(
        has_move=True,
        placements=placements,
        expected_score=move.score,
        message=f"Play for {move.score} points"
    )


@app.post("/api/game/{game_id}/valid-positions", response_model=ValidPositionsResponse)
async def get_valid_positions(game_id: str, request: ValidPositionsRequest):
    """Get valid positions for a specific tile."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.state.game_over:
        return ValidPositionsResponse(positions=[])

    hand = session.state.hands[session.state.current_player].tiles()

    if request.tile_index < 1 or request.tile_index > len(hand):
        raise HTTPException(status_code=400, detail="Invalid tile index")

    # Get valid positions from move generator
    positions = find_valid_positions(session.state.board)

    # Convert to response format
    return ValidPositionsResponse(
        positions=[[p[0], p[1]] for p in positions]
    )


@app.post("/api/game/{game_id}/ai-step", response_model=PlayResponse)
async def ai_step(game_id: str):
    """Execute one AI move (for AI vs AI mode)."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.state.game_over:
        return PlayResponse(
            success=False,
            error="Game is over",
            state=_session_to_state_response(session)
        )

    if not session.ai_vs_ai:
        raise HTTPException(status_code=400, detail="Not in AI vs AI mode")

    success, points, message = session_manager.play_ai_turn(session)

    return PlayResponse(
        success=success,
        points=points if success else 0,
        error=message if not success else None,
        state=_session_to_state_response(session)
    )


@app.delete("/api/game/{game_id}")
async def delete_game(game_id: str):
    """Delete a game session."""
    success = session_manager.delete_session(game_id)
    if not success:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"message": "Game deleted"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
