"""Pydantic models for Qwirkle Web API.

Request and response models for REST endpoints.
"""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field


class TileModel(BaseModel):
    """A tile with shape and color indices."""
    shape: int = Field(ge=0, le=5, description="Shape index (0-5)")
    color: int = Field(ge=0, le=5, description="Color index (0-5)")


class PositionModel(BaseModel):
    """Board position as row, col."""
    row: int
    col: int


class PlacementModel(BaseModel):
    """A tile placement: position + tile index from hand."""
    row: int
    col: int
    tile_index: int = Field(ge=1, le=6, description="1-based tile index in hand")


# Request Models

class NewGameRequest(BaseModel):
    """Request to create a new game."""
    seed: Optional[int] = Field(None, description="RNG seed for reproducibility")
    vs_ai: bool = Field(False, description="Play against AI opponent")
    ai_strategy: str = Field("greedy", description="AI strategy: 'greedy' or 'random'")


class PlayRequest(BaseModel):
    """Request to play tiles."""
    placements: List[PlacementModel] = Field(..., min_length=1, max_length=6)


class SwapRequest(BaseModel):
    """Request to swap tiles."""
    tile_indices: List[int] = Field(..., min_length=1, max_length=6,
                                     description="1-based tile indices to swap")


class ValidPositionsRequest(BaseModel):
    """Request for valid positions for a tile."""
    tile_index: int = Field(ge=1, le=6, description="1-based tile index in hand")


# Response Models

class GameStateResponse(BaseModel):
    """Full game state response."""
    game_id: str
    board: Dict[str, TileModel]  # "row,col" -> TileModel
    hand: List[TileModel]
    current_player: int = Field(ge=0, le=1)
    scores: List[int]
    bag_remaining: int
    game_over: bool
    winner: Optional[int]
    last_move_positions: List[List[int]]  # [[row, col], ...]
    message: str = ""


class NewGameResponse(BaseModel):
    """Response after creating a new game."""
    game_id: str
    state: GameStateResponse


class PlayResponse(BaseModel):
    """Response after playing tiles."""
    success: bool
    points: int = 0
    qwirkles: int = 0
    error: Optional[str] = None
    state: Optional[GameStateResponse] = None


class SwapResponse(BaseModel):
    """Response after swapping tiles."""
    success: bool
    error: Optional[str] = None
    state: Optional[GameStateResponse] = None


class UndoResponse(BaseModel):
    """Response after undo."""
    success: bool
    error: Optional[str] = None
    state: Optional[GameStateResponse] = None


class HintResponse(BaseModel):
    """Response with AI hint."""
    has_move: bool
    placements: List[PlacementModel] = []
    expected_score: int = 0
    message: str = ""


class ValidPositionsResponse(BaseModel):
    """Response with valid positions for a tile."""
    positions: List[List[int]]  # [[row, col], ...]
