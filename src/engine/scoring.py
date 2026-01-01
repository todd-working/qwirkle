"""Scoring engine for Qwirkle.

Scoring rules:
- Each line formed/extended: score = number of tiles in line
- Qwirkle bonus: if line has exactly 6 tiles, add 6 bonus points (total 12)
- End-game bonus: +6 for player who empties hand first when bag is empty
"""

from typing import List, Tuple
from src.models.board import Board, Position
from src.models.tile import Tile
from src.engine.rules import get_affected_lines

# Qwirkle = 6 tiles in a line
QWIRKLE_SIZE = 6
QWIRKLE_BONUS = 6
END_GAME_BONUS = 6


def calculate_line_score(line_length: int) -> int:
    """Calculate score for a single line.

    Args:
        line_length: Number of tiles in the line.

    Returns:
        Score for the line (includes Qwirkle bonus if applicable).
    """
    if line_length < 2:
        return 0  # Lines of 1 don't score

    score = line_length
    if line_length == QWIRKLE_SIZE:
        score += QWIRKLE_BONUS  # Qwirkle bonus

    return score


def calculate_move_score(
    board: Board,
    placements: List[Tuple[Position, Tile]]
) -> Tuple[int, int]:
    """Calculate the score for a move.

    The board should already have the tiles placed on it.

    Args:
        board: Board with tiles already placed.
        placements: List of (position, tile) that were just placed.

    Returns:
        Tuple of (total_score, qwirkle_count).
    """
    if not placements:
        return 0, 0

    positions = [p[0] for p in placements]
    affected = get_affected_lines(board, positions)

    total_score = 0
    qwirkle_count = 0

    for line in affected:
        line_len = len(line)
        total_score += calculate_line_score(line_len)
        if line_len == QWIRKLE_SIZE:
            qwirkle_count += 1

    # Special case: single tile placed with no 2+ tile lines
    # This can happen on first move with single tile - scores 1 point
    if not affected and len(placements) == 1:
        total_score = 1

    return total_score, qwirkle_count


def calculate_end_game_bonus() -> int:
    """Get the end-game bonus for emptying hand first.

    Returns:
        The bonus points (6).
    """
    return END_GAME_BONUS


def score_move(
    board_before: Board,
    placements: List[Tuple[Position, Tile]]
) -> Tuple[int, int]:
    """Calculate score for a move given the board state before the move.

    Creates a temporary board with the move applied to calculate scoring.

    Args:
        board_before: Board state before tiles are placed.
        placements: List of (position, tile) to place.

    Returns:
        Tuple of (total_score, qwirkle_count).
    """
    if not placements:
        return 0, 0

    # Create temp board with tiles placed
    temp_board = board_before.copy()
    for pos, tile in placements:
        temp_board.place(pos, tile)

    return calculate_move_score(temp_board, placements)
