"""Tests for Board."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board, Position


class TestBoardCreation:
    """Test board initialization."""

    def test_empty_board(self):
        board = Board()
        assert board.tile_count() == 0
        assert board.is_board_empty()


class TestBoardPlace:
    """Test placing tiles on board."""

    def test_place_single_tile(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        assert board.tile_count() == 1
        assert board.get((0, 0)) == tile

    def test_place_multiple_tiles(self):
        board = Board()
        tile1 = Tile(Shape.CIRCLE, Color.RED)
        tile2 = Tile(Shape.SQUARE, Color.BLUE)

        board.place((0, 0), tile1)
        board.place((0, 1), tile2)

        assert board.tile_count() == 2
        assert board.get((0, 0)) == tile1
        assert board.get((0, 1)) == tile2

    def test_place_at_occupied_position_raises(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        with pytest.raises(ValueError, match="already occupied"):
            board.place((0, 0), Tile(Shape.SQUARE, Color.BLUE))

    def test_place_at_negative_coords(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((-5, -3), tile)

        assert board.get((-5, -3)) == tile


class TestBoardGet:
    """Test getting tiles from board."""

    def test_get_existing_tile(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        assert board.get((0, 0)) == tile

    def test_get_empty_position(self):
        board = Board()
        assert board.get((0, 0)) is None

    def test_is_empty(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        assert board.is_empty((1, 1))
        assert not board.is_empty((0, 0))

    def test_is_occupied(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        assert board.is_occupied((0, 0))
        assert not board.is_occupied((1, 1))


class TestBoardRemove:
    """Test removing tiles from board."""

    def test_remove_existing_tile(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        removed = board.remove((0, 0))
        assert removed == tile
        assert board.is_empty((0, 0))
        assert board.tile_count() == 0

    def test_remove_from_empty_position(self):
        board = Board()
        removed = board.remove((0, 0))
        assert removed is None


class TestBoardNeighbors:
    """Test neighbor queries."""

    def test_neighbors_all_empty(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        neighbors = board.neighbors((0, 0))
        assert neighbors == {
            "up": None,
            "down": None,
            "left": None,
            "right": None,
        }

    def test_neighbors_with_tiles(self):
        board = Board()
        center = Tile(Shape.CIRCLE, Color.RED)
        up = Tile(Shape.SQUARE, Color.BLUE)
        right = Tile(Shape.DIAMOND, Color.GREEN)

        board.place((0, 0), center)
        board.place((-1, 0), up)
        board.place((0, 1), right)

        neighbors = board.neighbors((0, 0))
        assert neighbors["up"] == up
        assert neighbors["down"] is None
        assert neighbors["left"] is None
        assert neighbors["right"] == right

    def test_neighbor_positions(self):
        board = Board()
        positions = board.neighbor_positions((0, 0))

        assert (-1, 0) in positions  # up
        assert (1, 0) in positions   # down
        assert (0, -1) in positions  # left
        assert (0, 1) in positions   # right

    def test_has_neighbor_true(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.BLUE))

        assert board.has_neighbor((0, 0))

    def test_has_neighbor_false(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        assert not board.has_neighbor((5, 5))


class TestBoardBounds:
    """Test bounding box calculation."""

    def test_bounds_empty_board(self):
        board = Board()
        assert board.bounds() == (0, 0, 0, 0)

    def test_bounds_single_tile(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        assert board.bounds() == (0, 0, 0, 0)

    def test_bounds_multiple_tiles(self):
        board = Board()
        board.place((-2, 3), Tile(Shape.CIRCLE, Color.RED))
        board.place((5, -1), Tile(Shape.SQUARE, Color.BLUE))
        board.place((0, 0), Tile(Shape.DIAMOND, Color.GREEN))

        min_row, max_row, min_col, max_col = board.bounds()
        assert min_row == -2
        assert max_row == 5
        assert min_col == -1
        assert max_col == 3


class TestBoardLines:
    """Test row and column extraction."""

    def test_get_row(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.BLUE)
        t3 = Tile(Shape.DIAMOND, Color.GREEN)

        board.place((0, 0), t1)
        board.place((0, 2), t2)
        board.place((0, 5), t3)

        result = board.get_row(0, -1, 6)
        assert len(result) == 3
        assert result[0] == ((0, 0), t1)
        assert result[1] == ((0, 2), t2)
        assert result[2] == ((0, 5), t3)

    def test_get_col(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.BLUE)

        board.place((0, 0), t1)
        board.place((3, 0), t2)

        result = board.get_col(0, -1, 5)
        assert len(result) == 2
        assert result[0] == ((0, 0), t1)
        assert result[1] == ((3, 0), t2)

    def test_get_row_empty_range(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        result = board.get_row(5, 0, 10)  # Different row
        assert result == []


class TestBoardQueries:
    """Test board query methods."""

    def test_all_positions(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((1, 2), Tile(Shape.SQUARE, Color.BLUE))

        positions = board.all_positions()
        assert set(positions) == {(0, 0), (1, 2)}

    def test_all_tiles(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.BLUE)
        board.place((0, 0), t1)
        board.place((1, 2), t2)

        all_tiles = board.all_tiles()
        assert set(all_tiles) == {((0, 0), t1), ((1, 2), t2)}


class TestBoardCopy:
    """Test board copying."""

    def test_copy_is_independent(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        copy = board.copy()

        # Modify original
        board.place((1, 1), Tile(Shape.SQUARE, Color.BLUE))

        # Copy should be unchanged
        assert copy.tile_count() == 1
        assert copy.get((1, 1)) is None

    def test_copy_has_same_tiles(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        copy = board.copy()
        assert copy.get((0, 0)) == tile
