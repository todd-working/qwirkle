"""Bag model: the pool of tiles to draw from.

The bag starts with 108 tiles (3 copies of each of the 36 unique tiles).
Players draw from the bag to fill their hands.
"""

import random
from typing import List, Optional

from src.models.tile import Color, Shape, Tile


class Bag:
    """The tile bag containing all undrawn tiles.

    Starts with 108 tiles: 3 copies of each shape/color combination.
    """

    COPIES_PER_TILE = 3

    def __init__(self, seed: Optional[int] = None):
        """Create a new bag with all 108 tiles, shuffled.

        Args:
            seed: Optional random seed for reproducible shuffling.
        """
        self._tiles: List[Tile] = []
        self._rng = random.Random(seed)

        # Create 3 copies of each unique tile (6 shapes x 6 colors x 3 = 108)
        for shape in Shape:
            for color in Color:
                for _ in range(self.COPIES_PER_TILE):
                    self._tiles.append(Tile(shape, color))

        self._rng.shuffle(self._tiles)

    def draw(self, n: int = 1) -> List[Tile]:
        """Draw n tiles from the bag.

        Args:
            n: Number of tiles to draw (draws fewer if bag has less).

        Returns:
            List of drawn tiles (may be shorter than n if bag is low).
        """
        n = min(n, len(self._tiles))
        drawn = self._tiles[:n]
        self._tiles = self._tiles[n:]
        return drawn

    def return_tiles(self, tiles: List[Tile]) -> None:
        """Return tiles to the bag and reshuffle.

        Used when a player swaps tiles.

        Args:
            tiles: Tiles to return to the bag.
        """
        self._tiles.extend(tiles)
        self._rng.shuffle(self._tiles)

    def remaining(self) -> int:
        """Return the number of tiles left in the bag."""
        return len(self._tiles)

    def is_empty(self) -> bool:
        """Check if the bag is empty."""
        return len(self._tiles) == 0

    def peek(self) -> List[Tile]:
        """Return a copy of all tiles in the bag (for debugging/testing)."""
        return self._tiles.copy()

    def copy(self) -> "Bag":
        """Create an independent copy of this bag.

        The copy has the same tiles in the same order but independent RNG.
        """
        new_bag = Bag.__new__(Bag)
        new_bag._tiles = self._tiles.copy()
        new_bag._rng = random.Random()
        # Sync RNG state for reproducibility
        new_bag._rng.setstate(self._rng.getstate())
        return new_bag
