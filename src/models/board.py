"""Board model: the game grid where tiles are placed.

Uses a sparse dictionary representation for an infinite grid.
Positions are (row, col) tuples where (0, 0) is the center.
"""

from typing import Dict, List, Tuple, Optional

from src.models.tile import Tile


# Type alias for board positions
Position = Tuple[int, int]


class Board:
    """The game board using sparse representation.

    Tiles are stored in a dict mapping (row, col) -> Tile.
    The grid has no fixed bounds and grows as tiles are placed.
    """

    def __init__(self):
        """Create an empty board."""
        self._grid: Dict[Position, Tile] = {}

    def place(self, pos: Position, tile: Tile) -> None:
        """Place a tile at a position.

        Args:
            pos: The (row, col) position.
            tile: The tile to place.

        Raises:
            ValueError: If the position is already occupied.
        """
        if pos in self._grid:
            raise ValueError(f"Position {pos} is already occupied")
        self._grid[pos] = tile

    def get(self, pos: Position) -> Optional[Tile]:
        """Get the tile at a position, or None if empty.

        Args:
            pos: The (row, col) position.

        Returns:
            The tile at that position, or None.
        """
        return self._grid.get(pos)

    def is_empty(self, pos: Position) -> bool:
        """Check if a position is empty."""
        return pos not in self._grid

    def is_occupied(self, pos: Position) -> bool:
        """Check if a position has a tile."""
        return pos in self._grid

    def remove(self, pos: Position) -> Optional[Tile]:
        """Remove and return the tile at a position.

        Args:
            pos: The (row, col) position.

        Returns:
            The removed tile, or None if position was empty.
        """
        return self._grid.pop(pos, None)

    def neighbors(self, pos: Position) -> Dict[str, Optional[Tile]]:
        """Get the four orthogonal neighbors of a position.

        Args:
            pos: The (row, col) position.

        Returns:
            Dict with keys 'up', 'down', 'left', 'right' mapping to
            tiles (or None if that neighbor is empty).
        """
        row, col = pos
        return {
            "up": self.get((row - 1, col)),
            "down": self.get((row + 1, col)),
            "left": self.get((row, col - 1)),
            "right": self.get((row, col + 1)),
        }

    def neighbor_positions(self, pos: Position) -> List[Position]:
        """Get the four orthogonal neighbor positions.

        Args:
            pos: The (row, col) position.

        Returns:
            List of (row, col) tuples for up, down, left, right.
        """
        row, col = pos
        return [
            (row - 1, col),  # up
            (row + 1, col),  # down
            (row, col - 1),  # left
            (row, col + 1),  # right
        ]

    def has_neighbor(self, pos: Position) -> bool:
        """Check if a position has at least one adjacent tile."""
        return any(self.is_occupied(n) for n in self.neighbor_positions(pos))

    def bounds(self) -> Tuple[int, int, int, int]:
        """Get the bounding box of all placed tiles.

        Returns:
            Tuple of (min_row, max_row, min_col, max_col).
            Returns (0, 0, 0, 0) if board is empty.
        """
        if not self._grid:
            return (0, 0, 0, 0)

        rows = [pos[0] for pos in self._grid]
        cols = [pos[1] for pos in self._grid]
        return (min(rows), max(rows), min(cols), max(cols))

    def get_row(self, row: int, col_start: int, col_end: int) -> List[Tuple[Position, Tile]]:
        """Get all tiles in a row within a column range.

        Args:
            row: The row number.
            col_start: Starting column (inclusive).
            col_end: Ending column (inclusive).

        Returns:
            List of (position, tile) tuples, sorted by column.
        """
        result = []
        for col in range(col_start, col_end + 1):
            tile = self.get((row, col))
            if tile:
                result.append(((row, col), tile))
        return result

    def get_col(self, col: int, row_start: int, row_end: int) -> List[Tuple[Position, Tile]]:
        """Get all tiles in a column within a row range.

        Args:
            col: The column number.
            row_start: Starting row (inclusive).
            row_end: Ending row (inclusive).

        Returns:
            List of (position, tile) tuples, sorted by row.
        """
        result = []
        for row in range(row_start, row_end + 1):
            tile = self.get((row, col))
            if tile:
                result.append(((row, col), tile))
        return result

    def tile_count(self) -> int:
        """Return the number of tiles on the board."""
        return len(self._grid)

    def is_board_empty(self) -> bool:
        """Check if the board has no tiles."""
        return len(self._grid) == 0

    def all_positions(self) -> List[Position]:
        """Return all occupied positions."""
        return list(self._grid.keys())

    def all_tiles(self) -> List[Tuple[Position, Tile]]:
        """Return all (position, tile) pairs."""
        return list(self._grid.items())

    def copy(self) -> "Board":
        """Create a deep copy of the board."""
        new_board = Board()
        new_board._grid = self._grid.copy()
        return new_board
