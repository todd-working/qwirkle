"""Move generation for Qwirkle AI.

Enumerates all valid moves for a given game state.
"""

from dataclasses import dataclass
from typing import List, Set, Tuple, Iterator, Optional
from itertools import combinations, permutations

from src.models.board import Board, Position
from src.models.tile import Tile
from src.models.hand import Hand
from src.engine.rules import validate_move
from src.engine.scoring import score_move


@dataclass
class Move:
    """Represents a validated move with its score.

    Attributes:
        placements: List of (position, tile) tuples.
        score: Points this move would earn.
        qwirkles: Number of Qwirkles this move creates.
    """
    placements: List[Tuple[Position, Tile]]
    score: int
    qwirkles: int

    def __repr__(self) -> str:
        tiles = ", ".join(f"{t}@{p}" for p, t in self.placements)
        return f"Move({tiles}, score={self.score})"


def find_valid_positions(board: Board) -> Set[Position]:
    """Find all positions where a tile could potentially be placed.

    For an empty board, returns just the origin (0, 0).
    Otherwise, returns all empty positions adjacent to existing tiles.

    Args:
        board: The current board state.

    Returns:
        Set of positions that are candidates for placement.
    """
    if board.is_board_empty():
        return {(0, 0)}

    candidates: Set[Position] = set()

    for pos in board.all_positions():
        for neighbor in board.neighbor_positions(pos):
            if board.is_empty(neighbor):
                candidates.add(neighbor)

    return candidates


def _get_line_positions(
    start: Position,
    direction: str,
    length: int
) -> List[Position]:
    """Generate positions in a line from start position.

    Args:
        start: Starting position.
        direction: 'row' for horizontal, 'col' for vertical.
        length: Number of positions to generate.

    Returns:
        List of positions.
    """
    row, col = start
    positions = []
    for i in range(length):
        if direction == 'row':
            positions.append((row, col + i))
        else:
            positions.append((row + i, col))
    return positions


def generate_single_tile_moves(
    board: Board,
    hand: Hand,
    is_first_move: bool = False
) -> List[Move]:
    """Generate all valid single-tile moves.

    Args:
        board: Current board state.
        hand: Current player's hand.
        is_first_move: Whether this is the first move of the game.

    Returns:
        List of valid Move objects.
    """
    valid_positions = find_valid_positions(board)
    tiles = hand.tiles()
    seen_tiles: Set[Tile] = set()  # Avoid duplicate moves for same tile type
    moves: List[Move] = []

    for tile in tiles:
        if tile in seen_tiles:
            continue
        seen_tiles.add(tile)

        for pos in valid_positions:
            placements = [(pos, tile)]
            valid, _ = validate_move(board, placements, is_first_move)

            if valid:
                points, qwirkles = score_move(board, placements)
                moves.append(Move(placements, points, qwirkles))

    return moves


def _find_extension_positions(
    board: Board,
    start_pos: Position,
    direction: str,
    max_extend: int = 5
) -> List[Position]:
    """Find empty positions that extend a line in one direction.

    Args:
        board: Current board state.
        start_pos: Position to extend from.
        direction: 'left', 'right', 'up', or 'down'.
        max_extend: Maximum positions to extend (lines can be at most 6).

    Returns:
        List of empty positions in order of distance from start.
    """
    row, col = start_pos
    positions = []

    # Limit extension to max_extend positions (lines can only be 6 tiles)
    if direction == 'left':
        c = col - 1
        while board.is_empty((row, c)) and len(positions) < max_extend:
            positions.append((row, c))
            c -= 1
    elif direction == 'right':
        c = col + 1
        while board.is_empty((row, c)) and len(positions) < max_extend:
            positions.append((row, c))
            c += 1
    elif direction == 'up':
        r = row - 1
        while board.is_empty((r, col)) and len(positions) < max_extend:
            positions.append((r, col))
            r -= 1
    elif direction == 'down':
        r = row + 1
        while board.is_empty((r, col)) and len(positions) < max_extend:
            positions.append((r, col))
            r += 1

    return positions


def generate_multi_tile_moves(
    board: Board,
    hand: Hand,
    is_first_move: bool = False,
    max_tiles: int = 6,
    max_moves: int = 100
) -> List[Move]:
    """Generate valid multi-tile moves (2+ tiles).

    Strategy: For each valid single-tile placement, try extending
    the line with additional tiles from hand.

    Args:
        board: Current board state.
        hand: Current player's hand.
        is_first_move: Whether this is the first move.
        max_tiles: Maximum tiles to place (default 6).
        max_moves: Maximum moves to generate (for performance).

    Returns:
        List of valid Move objects.
    """
    moves: List[Move] = []
    tiles = hand.tiles()

    if len(tiles) < 2:
        return moves

    valid_positions = find_valid_positions(board)

    # For first move, generate lines of tiles at origin
    if is_first_move:
        moves.extend(_generate_first_move_lines(tiles, max_tiles))
        return moves

    # For subsequent moves, find positions that connect to existing tiles
    # and try to build lines from there
    # Limit to positions with neighbors (more likely to be valid)
    connected_positions = [p for p in valid_positions if board.has_neighbor(p)]

    for start_pos in connected_positions:
        if len(moves) >= max_moves:
            break

        # Try horizontal lines (extending left and right)
        moves.extend(_generate_lines_from_position(
            board, tiles, start_pos, 'row', max_tiles, is_first_move
        ))

        if len(moves) >= max_moves:
            break

        # Try vertical lines (extending up and down)
        moves.extend(_generate_lines_from_position(
            board, tiles, start_pos, 'col', max_tiles, is_first_move
        ))

    # Deduplicate moves with same placements
    return _deduplicate_moves(moves[:max_moves])


def _generate_first_move_lines(
    tiles: List[Tile],
    max_tiles: int
) -> List[Move]:
    """Generate all valid first-move lines (at origin).

    Args:
        tiles: Tiles in hand.
        max_tiles: Maximum tiles to place.

    Returns:
        List of valid moves.
    """
    moves: List[Move] = []
    board = Board()  # Empty board for validation

    # Try all subsets of tiles (2 to max_tiles)
    for size in range(2, min(len(tiles), max_tiles) + 1):
        for tile_combo in combinations(range(len(tiles)), size):
            selected = [tiles[i] for i in tile_combo]

            # Try horizontal placement at origin
            placements = [((0, i), t) for i, t in enumerate(selected)]
            valid, _ = validate_move(board, placements, is_first_move=True)
            if valid:
                points, qwirkles = score_move(board, placements)
                moves.append(Move(placements, points, qwirkles))

    return moves


def _generate_lines_from_position(
    board: Board,
    tiles: List[Tile],
    start_pos: Position,
    direction: str,
    max_tiles: int,
    is_first_move: bool,
    max_combinations: int = 20
) -> List[Move]:
    """Generate line moves starting from a position.

    Args:
        board: Current board state.
        tiles: Tiles in hand.
        start_pos: Starting position (must be empty).
        direction: 'row' or 'col'.
        max_tiles: Maximum tiles to place.
        is_first_move: Whether this is the first move.
        max_combinations: Max combinations to try per position (for speed).

    Returns:
        List of valid moves.
    """
    moves: List[Move] = []

    if not board.is_empty(start_pos):
        return moves

    # Find extension positions in both directions
    if direction == 'row':
        left_positions = _find_extension_positions(board, start_pos, 'left')
        right_positions = _find_extension_positions(board, start_pos, 'right')
        # Include start position
        all_positions = left_positions[::-1] + [start_pos] + right_positions
    else:
        up_positions = _find_extension_positions(board, start_pos, 'up')
        down_positions = _find_extension_positions(board, start_pos, 'down')
        all_positions = up_positions[::-1] + [start_pos] + down_positions

    # Limit positions to max_tiles
    if len(all_positions) > max_tiles:
        # Find the center (start_pos) and limit around it
        start_idx = all_positions.index(start_pos)
        # Take positions around start_pos
        left_take = min(start_idx, max_tiles // 2)
        right_take = min(len(all_positions) - start_idx - 1, max_tiles - left_take - 1)
        all_positions = all_positions[start_idx - left_take:start_idx + right_take + 1]

    # Track combinations tried
    combo_count = 0

    # Try placing 2 to max_tiles tiles in contiguous subsets
    for size in range(2, min(len(tiles), len(all_positions), max_tiles) + 1):
        for tile_combo in combinations(range(len(tiles)), size):
            if combo_count >= max_combinations:
                return moves

            selected = [tiles[i] for i in tile_combo]

            # Find contiguous position subsets that include start_pos
            for pos_start in range(len(all_positions)):
                if pos_start + size > len(all_positions):
                    break
                pos_subset = all_positions[pos_start:pos_start + size]

                # Must include at least one position adjacent to existing tile
                if not any(board.has_neighbor(p) for p in pos_subset):
                    continue

                combo_count += 1
                if combo_count > max_combinations:
                    return moves

                # Try this placement
                placements = list(zip(pos_subset, selected))
                valid, _ = validate_move(board, placements, is_first_move)
                if valid:
                    points, qwirkles = score_move(board, placements)
                    moves.append(Move(placements, points, qwirkles))

    return moves


def _deduplicate_moves(moves: List[Move]) -> List[Move]:
    """Remove duplicate moves (same placements, different order).

    Args:
        moves: List of moves.

    Returns:
        Deduplicated list.
    """
    seen: Set[frozenset] = set()
    unique: List[Move] = []

    for move in moves:
        key = frozenset(move.placements)
        if key not in seen:
            seen.add(key)
            unique.append(move)

    return unique


def generate_all_moves(
    board: Board,
    hand: Hand,
    is_first_move: bool = False
) -> List[Move]:
    """Generate all valid moves for the current state.

    Combines single and multi-tile moves.

    Args:
        board: Current board state.
        hand: Current player's hand.
        is_first_move: Whether this is the first move.

    Returns:
        List of all valid Move objects, sorted by score (descending).
    """
    moves = []

    # Single tile moves
    moves.extend(generate_single_tile_moves(board, hand, is_first_move))

    # Multi-tile moves
    moves.extend(generate_multi_tile_moves(board, hand, is_first_move))

    # Sort by score (highest first)
    moves.sort(key=lambda m: (m.score, m.qwirkles), reverse=True)

    return moves
