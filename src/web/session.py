"""Game session management for Qwirkle Web API.

Manages in-memory game sessions with undo support.
"""

import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.models.board import Position
from src.models.tile import Tile, Shape, Color
from src.engine.game import GameState, new_game, apply_move, apply_swap
from src.ai.solver import GreedySolver, RandomSolver, get_hint
from src.ai.move_gen import Move


@dataclass
class GameSession:
    """A game session with undo history.

    Attributes:
        game_id: Unique session identifier.
        state: Current game state.
        history: Stack of previous states for undo.
        last_move_positions: Positions from last move (for highlighting).
        message: Status message.
        vs_ai: Whether playing against AI.
        ai_vs_ai: Whether both players are AI (watch mode).
        ai_strategy: AI strategy type.
    """
    game_id: str
    state: GameState
    history: List[GameState] = field(default_factory=list)
    last_move_positions: List[Position] = field(default_factory=list)
    message: str = ""
    vs_ai: bool = False
    ai_vs_ai: bool = False
    ai_strategy: str = "greedy"

    MAX_UNDO_HISTORY = 50

    def save_state(self) -> None:
        """Save current state for undo."""
        if len(self.history) >= self.MAX_UNDO_HISTORY:
            self.history.pop(0)
        self.history.append(self.state.clone())

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.history) > 0


class SessionManager:
    """Manages active game sessions.

    Thread-safe for basic operations (dict access is atomic in CPython).
    For production, use Redis or database storage.
    """

    def __init__(self):
        self._sessions: Dict[str, GameSession] = {}

    def create_game(
        self,
        seed: Optional[int] = None,
        vs_ai: bool = False,
        ai_vs_ai: bool = False,
        ai_strategy: str = "greedy"
    ) -> GameSession:
        """Create a new game session.

        Args:
            seed: Optional RNG seed.
            vs_ai: Whether player 2 is AI.
            ai_vs_ai: Whether both players are AI (watch mode).
            ai_strategy: "greedy" or "random".

        Returns:
            New GameSession.
        """
        game_id = str(uuid.uuid4())
        state = new_game(seed)

        if ai_vs_ai:
            message = "AI vs AI mode - click 'Next Move' to advance"
        else:
            message = "Welcome to Qwirkle! Player 1 goes first."

        session = GameSession(
            game_id=game_id,
            state=state,
            vs_ai=vs_ai,
            ai_vs_ai=ai_vs_ai,
            ai_strategy=ai_strategy,
            message=message
        )

        self._sessions[game_id] = session
        return session

    def get_session(self, game_id: str) -> Optional[GameSession]:
        """Get a session by ID."""
        return self._sessions.get(game_id)

    def delete_session(self, game_id: str) -> bool:
        """Delete a session."""
        if game_id in self._sessions:
            del self._sessions[game_id]
            return True
        return False

    def play_tiles(
        self,
        session: GameSession,
        placements: List[Tuple[int, Position]]
    ) -> Tuple[bool, int, int, str]:
        """Play tiles on the board.

        Args:
            session: The game session.
            placements: List of (tile_index, position) where tile_index is 1-based.

        Returns:
            Tuple of (success, points, qwirkles, error_message).
        """
        hand = session.state.hands[session.state.current_player]
        tiles = hand.tiles()

        # Convert 1-based indices to tile placements
        try:
            tile_placements: List[Tuple[Position, Tile]] = []
            for idx, pos in placements:
                if idx < 1 or idx > len(tiles):
                    return False, 0, 0, f"Invalid tile index: {idx}"
                tile_placements.append((pos, tiles[idx - 1]))
        except (IndexError, TypeError) as e:
            return False, 0, 0, f"Invalid placement: {e}"

        # Save state for undo
        session.save_state()

        # Apply move
        success, error, points = apply_move(session.state, tile_placements)

        if success:
            session.last_move_positions = [p for p, _ in tile_placements]
            # Count qwirkles from the move's score (6 = qwirkle bonus per line)
            qwirkles = 0
            if points >= 12:
                # Rough estimate - actual counting would need move analysis
                qwirkles = points // 12
            session.message = f"Scored {points} points!"

            if session.state.game_over:
                if session.state.winner is not None:
                    session.message = (
                        f"Game Over! Player {session.state.winner + 1} wins "
                        f"with {session.state.scores[session.state.winner]} points!"
                    )
                else:
                    session.message = f"Game Over! It's a tie at {session.state.scores[0]} points!"

            return True, points, qwirkles, ""
        else:
            # Restore state on failure
            session.history.pop()
            return False, 0, 0, error or "Invalid move"

    def swap_tiles(
        self,
        session: GameSession,
        tile_indices: List[int]
    ) -> Tuple[bool, str]:
        """Swap tiles with the bag.

        Args:
            session: The game session.
            tile_indices: 1-based indices of tiles to swap.

        Returns:
            Tuple of (success, error_message).
        """
        hand = session.state.hands[session.state.current_player]
        tiles = hand.tiles()

        # Convert indices to tiles
        try:
            tiles_to_swap: List[Tile] = []
            for idx in tile_indices:
                if idx < 1 or idx > len(tiles):
                    return False, f"Invalid tile index: {idx}"
                tiles_to_swap.append(tiles[idx - 1])
        except (IndexError, TypeError) as e:
            return False, f"Invalid swap: {e}"

        # Save state for undo
        session.save_state()

        # Apply swap
        success, error = apply_swap(session.state, tiles_to_swap)

        if success:
            session.last_move_positions = []
            session.message = f"Swapped {len(tiles_to_swap)} tile(s)"
            return True, ""
        else:
            session.history.pop()
            return False, error or "Cannot swap"

    def undo(self, session: GameSession) -> Tuple[bool, str]:
        """Undo the last move.

        Returns:
            Tuple of (success, error_message).
        """
        if not session.can_undo():
            return False, "Nothing to undo"

        session.state = session.history.pop()
        session.last_move_positions = []
        session.message = "Move undone"
        return True, ""

    def get_hint(self, session: GameSession) -> Optional[Move]:
        """Get AI hint for current player.

        Returns:
            Best move or None if no moves available.
        """
        return get_hint(session.state)

    def play_ai_turn(self, session: GameSession, player: Optional[int] = None) -> Tuple[bool, int, str]:
        """Execute AI's turn.

        Args:
            session: The game session.
            player: Which player's turn to play (None = current player in ai_vs_ai mode).

        Returns:
            Tuple of (success, points, message).
        """
        if session.state.game_over:
            return False, 0, "Game is over"

        current = session.state.current_player

        # In regular vs_ai mode, only player 1 is AI
        if not session.ai_vs_ai and current != 1:
            return False, 0, "Not AI's turn"

        # Create solver based on strategy
        if session.ai_strategy == "random":
            solver = RandomSolver()
        else:
            solver = GreedySolver()

        move = solver.get_move(session.state)
        player_name = f"AI {current + 1}" if session.ai_vs_ai else "AI"

        if move is None:
            # No valid moves - swap a tile
            hand = session.state.hands[current]
            if not session.state.bag.is_empty() and len(hand) > 0:
                session.save_state()
                success, error = apply_swap(session.state, [hand.tiles()[0]])
                if success:
                    session.last_move_positions = []
                    session.message = f"{player_name} swapped a tile"
                    return True, 0, session.message
            return False, 0, f"{player_name} has no valid moves"

        # Save state and apply move
        session.save_state()
        success, error, points = apply_move(session.state, move.placements)

        if success:
            session.last_move_positions = [p for p, _ in move.placements]
            session.message = f"{player_name} scored {points} points!"

            if session.state.game_over:
                if session.state.winner is not None:
                    winner_name = f"AI {session.state.winner + 1}" if session.ai_vs_ai else f"Player {session.state.winner + 1}"
                    session.message = (
                        f"Game Over! {winner_name} wins "
                        f"with {session.state.scores[session.state.winner]} points!"
                    )
                else:
                    session.message = f"Game Over! It's a tie!"

            return True, points, session.message
        else:
            session.history.pop()
            return False, 0, f"{player_name} move failed: {error}"


# Global session manager instance
session_manager = SessionManager()
