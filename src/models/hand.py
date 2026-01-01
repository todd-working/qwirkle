"""Hand model: a player's current tiles.

Each player holds up to 6 tiles in their hand.
"""

from typing import List, Optional

from src.models.tile import Tile
from src.models.bag import Bag


class Hand:
    """A player's hand of tiles.

    Holds up to MAX_SIZE tiles (default 6).
    """

    MAX_SIZE = 6

    def __init__(self, tiles: Optional[List[Tile]] = None):
        """Create a hand with optional initial tiles.

        Args:
            tiles: Initial tiles (must not exceed MAX_SIZE).

        Raises:
            ValueError: If initial tiles exceed MAX_SIZE.
        """
        self._tiles: List[Tile] = []
        if tiles:
            if len(tiles) > self.MAX_SIZE:
                raise ValueError(f"Hand cannot exceed {self.MAX_SIZE} tiles")
            self._tiles = list(tiles)

    def add(self, tiles: List[Tile]) -> None:
        """Add tiles to the hand.

        Args:
            tiles: Tiles to add.

        Raises:
            ValueError: If adding would exceed MAX_SIZE.
        """
        if len(self._tiles) + len(tiles) > self.MAX_SIZE:
            raise ValueError(f"Cannot exceed {self.MAX_SIZE} tiles in hand")
        self._tiles.extend(tiles)

    def remove(self, tiles: List[Tile]) -> None:
        """Remove specific tiles from the hand.

        Args:
            tiles: Tiles to remove (must all be present in hand).

        Raises:
            ValueError: If any tile is not in the hand.
        """
        # Work with a copy to validate all tiles exist first
        remaining = self._tiles.copy()
        for tile in tiles:
            try:
                remaining.remove(tile)
            except ValueError:
                raise ValueError(f"Tile {tile} not in hand")
        self._tiles = remaining

    def refill(self, bag: Bag) -> int:
        """Refill hand to MAX_SIZE from the bag.

        Args:
            bag: The bag to draw from.

        Returns:
            Number of tiles drawn.
        """
        needed = self.MAX_SIZE - len(self._tiles)
        if needed <= 0:
            return 0
        drawn = bag.draw(needed)
        self._tiles.extend(drawn)
        return len(drawn)

    def tiles(self) -> List[Tile]:
        """Return a copy of the tiles in hand."""
        return self._tiles.copy()

    def size(self) -> int:
        """Return the number of tiles in hand."""
        return len(self._tiles)

    def is_empty(self) -> bool:
        """Check if the hand is empty."""
        return len(self._tiles) == 0

    def contains(self, tile: Tile) -> bool:
        """Check if a specific tile is in the hand."""
        return tile in self._tiles

    def count(self, tile: Tile) -> int:
        """Count how many copies of a tile are in the hand."""
        return self._tiles.count(tile)

    def __len__(self) -> int:
        return len(self._tiles)

    def __contains__(self, tile: Tile) -> bool:
        return tile in self._tiles

    def __iter__(self):
        return iter(self._tiles)

    def copy(self) -> "Hand":
        """Create an independent copy of this hand."""
        return Hand(self._tiles.copy())
