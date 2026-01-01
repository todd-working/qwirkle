"""Tile model: the fundamental game piece in Qwirkle.

Each tile has a shape and a color. There are 6 shapes and 6 colors,
giving 36 unique tile types. The game has 3 copies of each = 108 tiles total.
"""

from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    """The six tile colors in Qwirkle."""
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"


class Shape(Enum):
    """The six tile shapes in Qwirkle."""
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"
    STAR = "star"
    CLOVER = "clover"
    CROSS = "cross"


@dataclass(frozen=True)
class Tile:
    """A single Qwirkle tile with a shape and color.

    Frozen (immutable) so it can be used in sets and as dict keys.
    """
    shape: Shape
    color: Color

    def __str__(self) -> str:
        """Human-readable representation, e.g., 'red circle'."""
        return f"{self.color.value} {self.shape.value}"

    def __repr__(self) -> str:
        return f"Tile({self.shape.name}, {self.color.name})"
