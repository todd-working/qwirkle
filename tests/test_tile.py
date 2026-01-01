"""Tests for Tile, Color, and Shape."""

import pytest
from src.models.tile import Color, Shape, Tile


class TestEnums:
    """Test Color and Shape enums."""

    def test_color_has_six_values(self):
        assert len(Color) == 6

    def test_shape_has_six_values(self):
        assert len(Shape) == 6

    def test_color_values(self):
        expected = {"red", "orange", "yellow", "green", "blue", "purple"}
        actual = {c.value for c in Color}
        assert actual == expected

    def test_shape_values(self):
        expected = {"circle", "square", "diamond", "star", "clover", "cross"}
        actual = {s.value for s in Shape}
        assert actual == expected


class TestTile:
    """Test Tile dataclass."""

    def test_tile_creation(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        assert tile.shape == Shape.CIRCLE
        assert tile.color == Color.RED

    def test_tile_equality(self):
        tile1 = Tile(Shape.STAR, Color.BLUE)
        tile2 = Tile(Shape.STAR, Color.BLUE)
        tile3 = Tile(Shape.STAR, Color.GREEN)
        assert tile1 == tile2
        assert tile1 != tile3

    def test_tile_is_hashable(self):
        # Tiles must be hashable to use in sets and as dict keys
        tile1 = Tile(Shape.DIAMOND, Color.PURPLE)
        tile2 = Tile(Shape.DIAMOND, Color.PURPLE)
        tile3 = Tile(Shape.SQUARE, Color.ORANGE)

        # Can add to set
        tile_set = {tile1, tile2, tile3}
        assert len(tile_set) == 2  # tile1 and tile2 are equal

        # Can use as dict key
        tile_dict = {tile1: "first", tile3: "second"}
        assert tile_dict[tile2] == "first"  # tile2 equals tile1

    def test_tile_is_immutable(self):
        tile = Tile(Shape.CLOVER, Color.YELLOW)
        with pytest.raises(AttributeError):
            tile.shape = Shape.CROSS  # type: ignore

    def test_tile_str(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        assert str(tile) == "red circle"

    def test_tile_repr(self):
        tile = Tile(Shape.STAR, Color.BLUE)
        assert repr(tile) == "Tile(STAR, BLUE)"

    def test_all_unique_tiles(self):
        # 6 shapes x 6 colors = 36 unique tiles
        all_tiles = {Tile(shape, color) for shape in Shape for color in Color}
        assert len(all_tiles) == 36
