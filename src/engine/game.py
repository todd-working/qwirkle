"""Game engine: state management and turn flow for Qwirkle.

Handles game state, move application, swapping, and end-game detection.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from copy import deepcopy

from src.models.board import Board, Position
from src.models.bag import Bag
from src.models.hand import Hand
from src.models.tile import Tile
from src.engine.rules import validate_move
from src.engine.scoring import score_move, calculate_end_game_bonus


@dataclass
class GameState:
    """Complete state of a Qwirkle game.

    Attributes:
        board: The game board with placed tiles.
        bag: The tile bag for drawing.
        hands: List of player hands [player0, player1].
        scores: List of player scores [player0, player1].
        current_player: Index of current player (0 or 1).
        turn_number: Current turn number (starts at 1).
        game_over: Whether the game has ended.
        winner: Index of winning player, or None if tie/not over.
    """
    board: Board
    bag: Bag
    hands: List[Hand]
    scores: List[int]
    current_player: int = 0
    turn_number: int = 1
    game_over: bool = False
    winner: Optional[int] = None

    # Track stats for simulation/analysis
    qwirkle_counts: List[int] = field(default_factory=lambda: [0, 0])

    def clone(self) -> "GameState":
        """Create a deep copy of the game state.

        Used for simulations and AI lookahead.
        """
        return GameState(
            board=self.board.copy(),
            bag=self.bag.copy(),
            hands=[hand.copy() for hand in self.hands],
            scores=self.scores.copy(),
            current_player=self.current_player,
            turn_number=self.turn_number,
            game_over=self.game_over,
            winner=self.winner,
            qwirkle_counts=self.qwirkle_counts.copy(),
        )


def new_game(seed: Optional[int] = None) -> GameState:
    """Create a new game with shuffled bag and dealt hands.

    Args:
        seed: Optional RNG seed for reproducibility.

    Returns:
        A fresh GameState ready to play.
    """
    bag = Bag(seed=seed)
    hands = [Hand(), Hand()]

    # Deal 6 tiles to each player
    for hand in hands:
        hand.refill(bag)

    return GameState(
        board=Board(),
        bag=bag,
        hands=hands,
        scores=[0, 0],
        current_player=0,
        turn_number=1,
        game_over=False,
        winner=None,
        qwirkle_counts=[0, 0],
    )


def apply_move(
    state: GameState,
    placements: List[Tuple[Position, Tile]]
) -> Tuple[bool, str, int]:
    """Apply a move to the game state.

    Validates the move, updates the board, calculates score,
    refills hand, and advances to next turn.

    Args:
        state: Current game state (will be modified).
        placements: List of (position, tile) to place.

    Returns:
        Tuple of (success, error_message, points_scored).
        If success is False, state is unchanged.
    """
    if state.game_over:
        return False, "Game is already over", 0

    if not placements:
        return False, "Must place at least one tile", 0

    hand = state.hands[state.current_player]
    tiles = [t for _, t in placements]

    # Verify player has these tiles
    for tile in tiles:
        if tile not in hand:
            return False, f"Player does not have tile: {tile}", 0

    # Validate the move
    is_first_move = state.board.is_board_empty()
    valid, error = validate_move(state.board, placements, is_first_move)
    if not valid:
        return False, error, 0

    # Calculate score before modifying board
    points, qwirkles = score_move(state.board, placements)

    # Apply the move
    for pos, tile in placements:
        state.board.place(pos, tile)

    # Remove tiles from hand
    hand.remove(tiles)

    # Update score and stats
    state.scores[state.current_player] += points
    state.qwirkle_counts[state.current_player] += qwirkles

    # Check for end game (hand empty and bag empty)
    if len(hand) == 0 and state.bag.is_empty():
        # End game bonus
        state.scores[state.current_player] += calculate_end_game_bonus()
        _end_game(state)
    else:
        # Refill hand and advance turn
        hand.refill(state.bag)
        _advance_turn(state)

    return True, "", points


def apply_swap(
    state: GameState,
    tiles_to_swap: List[Tile]
) -> Tuple[bool, str]:
    """Swap tiles from hand with bag.

    Player returns tiles to bag and draws same number of new tiles.
    This counts as the player's turn.

    Args:
        state: Current game state (will be modified).
        tiles_to_swap: Tiles to return to bag.

    Returns:
        Tuple of (success, error_message).
    """
    if state.game_over:
        return False, "Game is already over"

    if not tiles_to_swap:
        return False, "Must swap at least one tile"

    if state.bag.is_empty():
        return False, "Cannot swap when bag is empty"

    hand = state.hands[state.current_player]

    # Verify player has these tiles
    for tile in tiles_to_swap:
        if tile not in hand:
            return False, f"Player does not have tile: {tile}"

    # Check bag has enough tiles
    swap_count = len(tiles_to_swap)
    if state.bag.remaining() < swap_count:
        return False, f"Bag only has {state.bag.remaining()} tiles, cannot swap {swap_count}"

    # Remove tiles from hand
    hand.remove(tiles_to_swap)

    # Draw new tiles first (before returning, per Qwirkle rules)
    new_tiles = state.bag.draw(swap_count)
    hand.add(new_tiles)

    # Return swapped tiles to bag
    state.bag.return_tiles(tiles_to_swap)

    # Advance turn
    _advance_turn(state)

    return True, ""


def _advance_turn(state: GameState) -> None:
    """Advance to the next player's turn."""
    state.current_player = 1 - state.current_player
    state.turn_number += 1

    # Check if next player can make any move
    # If bag is empty and hand is empty, game ends
    next_hand = state.hands[state.current_player]
    if len(next_hand) == 0 and state.bag.is_empty():
        _end_game(state)


def _end_game(state: GameState) -> None:
    """End the game and determine winner."""
    state.game_over = True

    if state.scores[0] > state.scores[1]:
        state.winner = 0
    elif state.scores[1] > state.scores[0]:
        state.winner = 1
    else:
        state.winner = None  # Tie


def get_current_hand(state: GameState) -> Hand:
    """Get the current player's hand."""
    return state.hands[state.current_player]


def get_current_score(state: GameState) -> int:
    """Get the current player's score."""
    return state.scores[state.current_player]


def can_play(state: GameState) -> bool:
    """Check if current player can make any move.

    Returns True if player has tiles and game is not over.
    Does not check if any valid moves exist (that's expensive).
    """
    if state.game_over:
        return False
    return len(state.hands[state.current_player]) > 0


def can_swap(state: GameState) -> bool:
    """Check if current player can swap tiles."""
    if state.game_over:
        return False
    if state.bag.is_empty():
        return False
    return len(state.hands[state.current_player]) > 0
