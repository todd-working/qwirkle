"""Rules engine: move validation for Qwirkle.

A valid move must:
1. Place tiles in a single row OR single column
2. Tiles must be contiguous (no gaps in the line)
3. Must connect to existing tiles (except first move)
4. Each resulting line must have ≤6 tiles with no duplicates
5. Each line must share exactly one attribute (all same color OR all same shape)
"""

from typing import List, Tuple, Set, Optional
from src.models.board import Board, Position
from src.models.tile import Tile, Color, Shape


def get_line_horizontal(board: Board, pos: Position) -> List[Tuple[Position, Tile]]:
    """Get the complete horizontal line containing a position.

    Extends left and right from pos until hitting empty cells.
    Includes the tile at pos if present.

    Args:
        board: The game board.
        pos: Starting position (row, col).

    Returns:
        List of (position, tile) tuples in left-to-right order.
    """
    row, col = pos
    tiles = []

    # Find leftmost tile in this line
    left = col
    while board.get((row, left - 1)) is not None:
        left -= 1

    # Collect all tiles from left to right
    current = left
    while True:
        tile = board.get((row, current))
        if tile is None:
            break
        tiles.append(((row, current), tile))
        current += 1

    return tiles


def get_line_vertical(board: Board, pos: Position) -> List[Tuple[Position, Tile]]:
    """Get the complete vertical line containing a position.

    Extends up and down from pos until hitting empty cells.
    Includes the tile at pos if present.

    Args:
        board: The game board.
        pos: Starting position (row, col).

    Returns:
        List of (position, tile) tuples in top-to-bottom order.
    """
    row, col = pos
    tiles = []

    # Find topmost tile in this line
    top = row
    while board.get((top - 1, col)) is not None:
        top -= 1

    # Collect all tiles from top to bottom
    current = top
    while True:
        tile = board.get((current, col))
        if tile is None:
            break
        tiles.append(((current, col), tile))
        current += 1

    return tiles


def is_valid_line(tiles: List[Tile]) -> bool:
    """Check if a line of tiles is valid.

    A valid line:
    - Has at most 6 tiles
    - Has no duplicate tiles
    - All tiles share exactly one attribute (all same color OR all same shape)

    Args:
        tiles: List of tiles in the line.

    Returns:
        True if the line is valid.
    """
    if len(tiles) == 0:
        return True  # Empty line is trivially valid

    if len(tiles) == 1:
        return True  # Single tile is always valid

    if len(tiles) > 6:
        return False  # Line too long

    # Check for duplicates
    if len(tiles) != len(set(tiles)):
        return False

    # Check shared attribute: all same color OR all same shape (not both, not neither)
    colors = {t.color for t in tiles}
    shapes = {t.shape for t in tiles}

    same_color = len(colors) == 1
    same_shape = len(shapes) == 1

    # Valid if exactly one attribute is shared
    # (same_color XOR same_shape, but also accept both for single tile which we already handled)
    if same_color and not same_shape:
        return True  # All same color, different shapes
    if same_shape and not same_color:
        return True  # All same shape, different colors

    return False


def are_positions_collinear(positions: List[Position]) -> Optional[str]:
    """Check if positions are all in the same row or column.

    Args:
        positions: List of (row, col) positions.

    Returns:
        'row' if all in same row, 'col' if all in same column,
        None if neither (or empty/single position returns 'row').
    """
    if len(positions) <= 1:
        return 'row'  # Trivially collinear

    rows = {p[0] for p in positions}
    cols = {p[1] for p in positions}

    if len(rows) == 1:
        return 'row'
    if len(cols) == 1:
        return 'col'
    return None


def are_positions_contiguous(positions: List[Position], direction: str) -> bool:
    """Check if positions form a contiguous line (no gaps).

    Args:
        positions: List of (row, col) positions.
        direction: 'row' (horizontal) or 'col' (vertical).

    Returns:
        True if positions are contiguous.
    """
    if len(positions) <= 1:
        return True

    if direction == 'row':
        # Same row, check columns are consecutive
        cols = sorted(p[1] for p in positions)
        for i in range(1, len(cols)):
            if cols[i] - cols[i-1] != 1:
                return False
    else:
        # Same column, check rows are consecutive
        rows = sorted(p[0] for p in positions)
        for i in range(1, len(rows)):
            if rows[i] - rows[i-1] != 1:
                return False

    return True


def get_affected_lines(board: Board, positions: List[Position]) -> List[List[Tuple[Position, Tile]]]:
    """Get all lines affected by placing tiles at the given positions.

    For each placed tile, we check its horizontal and vertical lines.
    Only returns lines with 2+ tiles (single tiles don't score).

    Args:
        board: The board with tiles already placed.
        positions: Positions where tiles were placed.

    Returns:
        List of lines, each line is a list of (position, tile) tuples.
    """
    seen_lines: Set[Tuple[Tuple[Position, Tile], ...]] = set()
    lines = []

    for pos in positions:
        # Check horizontal line
        h_line = get_line_horizontal(board, pos)
        if len(h_line) >= 2:
            key = tuple(h_line)
            if key not in seen_lines:
                seen_lines.add(key)
                lines.append(h_line)

        # Check vertical line
        v_line = get_line_vertical(board, pos)
        if len(v_line) >= 2:
            key = tuple(v_line)
            if key not in seen_lines:
                seen_lines.add(key)
                lines.append(v_line)

    return lines


def validate_move(
    board: Board,
    placements: List[Tuple[Position, Tile]],
    is_first_move: bool = False
) -> Tuple[bool, str]:
    """Validate a move before applying it.

    Args:
        board: Current board state (before placing tiles).
        placements: List of (position, tile) to place.
        is_first_move: True if this is the first move of the game.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not placements:
        return False, "Must place at least one tile"

    positions = [p[0] for p in placements]
    tiles = [p[1] for p in placements]

    # Check all positions are empty
    for pos in positions:
        if board.get(pos) is not None:
            return False, f"Position {pos} is already occupied"

    # Check positions are collinear
    direction = are_positions_collinear(positions)
    if direction is None:
        return False, "All tiles must be placed in the same row or column"

    # Create a temporary board to check the result
    temp_board = board.copy()
    for pos, tile in placements:
        temp_board.place(pos, tile)

    # Check tiles are contiguous (including existing tiles in the line)
    # Get the full line after placement - starting from any placed position
    if direction == 'row':
        full_line = get_line_horizontal(temp_board, positions[0])
    else:
        full_line = get_line_vertical(temp_board, positions[0])

    line_positions = [p[0] for p in full_line]

    # All placed positions must be in the same contiguous line
    # If any placement position is not in the line, there's a gap
    for pos in positions:
        if pos not in line_positions:
            return False, "Tiles must be placed in a contiguous line"

    if not are_positions_contiguous(line_positions, direction):
        return False, "Tiles must be placed in a contiguous line"

    # Check connection to existing tiles (except first move)
    if not is_first_move:
        has_connection = False
        for pos in positions:
            # Check if any neighbor was on the original board
            for neighbor in temp_board.neighbor_positions(pos):
                if neighbor not in positions and board.get(neighbor) is not None:
                    has_connection = True
                    break
            if has_connection:
                break

        if not has_connection:
            return False, "Tiles must connect to existing tiles on the board"

    # Check all affected lines are valid
    affected = get_affected_lines(temp_board, positions)

    # For single tile placements that don't form lines with existing tiles,
    # we still need to validate the tile itself connects properly
    if not affected and len(placements) == 1 and not is_first_move:
        # This case means a single tile was placed but doesn't form a 2+ tile line
        # This is actually valid - the tile just doesn't score
        pass

    for line in affected:
        line_tiles = [t for _, t in line]
        if not is_valid_line(line_tiles):
            return False, f"Invalid line: tiles must share exactly one attribute with no duplicates"

    # Also check the main placement line even if it's not in affected
    # (in case it's a single-tile first move)
    if is_first_move and len(placements) > 1:
        if not is_valid_line(tiles):
            return False, "Invalid line: tiles must share exactly one attribute with no duplicates"

    return True, ""
