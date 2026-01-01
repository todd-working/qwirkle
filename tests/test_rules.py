"""Tests for rules engine."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board
from src.engine.rules import (
    get_line_horizontal,
    get_line_vertical,
    is_valid_line,
    are_positions_collinear,
    are_positions_contiguous,
    get_affected_lines,
    validate_move,
)


class TestGetLineHorizontal:
    """Test horizontal line extraction."""

    def test_single_tile(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        line = get_line_horizontal(board, (0, 0))
        assert len(line) == 1
        assert line[0] == ((0, 0), tile)

    def test_multiple_tiles_contiguous(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.CIRCLE, Color.BLUE)
        t3 = Tile(Shape.CIRCLE, Color.GREEN)

        board.place((0, 0), t1)
        board.place((0, 1), t2)
        board.place((0, 2), t3)

        # Query from middle
        line = get_line_horizontal(board, (0, 1))
        assert len(line) == 3
        assert line[0] == ((0, 0), t1)
        assert line[1] == ((0, 1), t2)
        assert line[2] == ((0, 2), t3)

    def test_gap_splits_line(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.CIRCLE, Color.BLUE)

        board.place((0, 0), t1)
        board.place((0, 3), t2)  # Gap at columns 1-2

        line = get_line_horizontal(board, (0, 0))
        assert len(line) == 1
        assert line[0] == ((0, 0), t1)

    def test_empty_position(self):
        board = Board()
        line = get_line_horizontal(board, (0, 0))
        assert line == []


class TestGetLineVertical:
    """Test vertical line extraction."""

    def test_single_tile(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        line = get_line_vertical(board, (0, 0))
        assert len(line) == 1
        assert line[0] == ((0, 0), tile)

    def test_multiple_tiles_contiguous(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)
        t3 = Tile(Shape.DIAMOND, Color.RED)

        board.place((0, 0), t1)
        board.place((1, 0), t2)
        board.place((2, 0), t3)

        # Query from middle
        line = get_line_vertical(board, (1, 0))
        assert len(line) == 3
        assert line[0] == ((0, 0), t1)
        assert line[1] == ((1, 0), t2)
        assert line[2] == ((2, 0), t3)

    def test_gap_splits_line(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)

        board.place((0, 0), t1)
        board.place((3, 0), t2)  # Gap at rows 1-2

        line = get_line_vertical(board, (0, 0))
        assert len(line) == 1

    def test_empty_position(self):
        board = Board()
        line = get_line_vertical(board, (0, 0))
        assert line == []


class TestIsValidLine:
    """Test line validation logic."""

    def test_empty_line_valid(self):
        assert is_valid_line([]) is True

    def test_single_tile_valid(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        assert is_valid_line([tile]) is True

    def test_same_color_different_shapes_valid(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
            Tile(Shape.DIAMOND, Color.RED),
        ]
        assert is_valid_line(tiles) is True

    def test_same_shape_different_colors_valid(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.CIRCLE, Color.BLUE),
            Tile(Shape.CIRCLE, Color.GREEN),
        ]
        assert is_valid_line(tiles) is True

    def test_qwirkle_same_color_valid(self):
        # All 6 shapes in red
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
            Tile(Shape.DIAMOND, Color.RED),
            Tile(Shape.STAR, Color.RED),
            Tile(Shape.CLOVER, Color.RED),
            Tile(Shape.CROSS, Color.RED),
        ]
        assert is_valid_line(tiles) is True

    def test_qwirkle_same_shape_valid(self):
        # All 6 colors with circle
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.CIRCLE, Color.ORANGE),
            Tile(Shape.CIRCLE, Color.YELLOW),
            Tile(Shape.CIRCLE, Color.GREEN),
            Tile(Shape.CIRCLE, Color.BLUE),
            Tile(Shape.CIRCLE, Color.PURPLE),
        ]
        assert is_valid_line(tiles) is True

    def test_too_long_invalid(self):
        # 7 tiles is too many
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.CIRCLE, Color.ORANGE),
            Tile(Shape.CIRCLE, Color.YELLOW),
            Tile(Shape.CIRCLE, Color.GREEN),
            Tile(Shape.CIRCLE, Color.BLUE),
            Tile(Shape.CIRCLE, Color.PURPLE),
            Tile(Shape.SQUARE, Color.RED),  # Would need 7th color
        ]
        assert is_valid_line(tiles) is False

    def test_duplicate_tile_invalid(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
            Tile(Shape.CIRCLE, Color.RED),  # Duplicate
        ]
        assert is_valid_line(tiles) is False

    def test_neither_attribute_shared_invalid(self):
        # Different colors AND different shapes
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.BLUE),
        ]
        assert is_valid_line(tiles) is False

    def test_both_attributes_same_invalid(self):
        # This would be a duplicate, but testing the logic
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.CIRCLE, Color.RED),
        ]
        assert is_valid_line(tiles) is False  # Fails duplicate check


class TestArePositionsCollinear:
    """Test collinearity checking."""

    def test_empty_positions(self):
        assert are_positions_collinear([]) == 'row'

    def test_single_position(self):
        assert are_positions_collinear([(0, 0)]) == 'row'

    def test_same_row(self):
        positions = [(0, 0), (0, 1), (0, 5)]
        assert are_positions_collinear(positions) == 'row'

    def test_same_column(self):
        positions = [(0, 0), (1, 0), (5, 0)]
        assert are_positions_collinear(positions) == 'col'

    def test_not_collinear(self):
        positions = [(0, 0), (1, 1), (2, 2)]  # Diagonal
        assert are_positions_collinear(positions) is None

    def test_l_shape_not_collinear(self):
        positions = [(0, 0), (0, 1), (1, 1)]  # L shape
        assert are_positions_collinear(positions) is None


class TestArePositionsContiguous:
    """Test contiguity checking."""

    def test_empty_contiguous(self):
        assert are_positions_contiguous([], 'row') is True

    def test_single_contiguous(self):
        assert are_positions_contiguous([(0, 0)], 'row') is True

    def test_horizontal_contiguous(self):
        positions = [(0, 0), (0, 1), (0, 2)]
        assert are_positions_contiguous(positions, 'row') is True

    def test_horizontal_not_contiguous(self):
        positions = [(0, 0), (0, 2)]  # Gap at column 1
        assert are_positions_contiguous(positions, 'row') is False

    def test_vertical_contiguous(self):
        positions = [(0, 0), (1, 0), (2, 0)]
        assert are_positions_contiguous(positions, 'col') is True

    def test_vertical_not_contiguous(self):
        positions = [(0, 0), (2, 0)]  # Gap at row 1
        assert are_positions_contiguous(positions, 'col') is False

    def test_unordered_still_contiguous(self):
        # Positions don't need to be in order
        positions = [(0, 2), (0, 0), (0, 1)]
        assert are_positions_contiguous(positions, 'row') is True


class TestGetAffectedLines:
    """Test finding all lines affected by a move."""

    def test_single_tile_no_neighbors(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        # Single tile doesn't form a 2+ tile line
        lines = get_affected_lines(board, [(0, 0)])
        assert lines == []

    def test_horizontal_line(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)
        board.place((0, 0), t1)
        board.place((0, 1), t2)

        lines = get_affected_lines(board, [(0, 0), (0, 1)])
        assert len(lines) == 1
        assert len(lines[0]) == 2

    def test_cross_creates_two_lines(self):
        board = Board()
        # Create a cross pattern
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))
        board.place((1, 0), Tile(Shape.DIAMOND, Color.RED))

        # Placing at (0, 0) affects horizontal and vertical lines
        lines = get_affected_lines(board, [(0, 0)])
        assert len(lines) == 2

    def test_no_duplicate_lines(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)
        t3 = Tile(Shape.DIAMOND, Color.RED)
        board.place((0, 0), t1)
        board.place((0, 1), t2)
        board.place((0, 2), t3)

        # Multiple positions in same line shouldn't duplicate
        lines = get_affected_lines(board, [(0, 0), (0, 1), (0, 2)])
        assert len(lines) == 1


class TestValidateMove:
    """Test complete move validation."""

    def test_empty_move_invalid(self):
        board = Board()
        valid, msg = validate_move(board, [])
        assert valid is False
        assert "at least one tile" in msg.lower()

    def test_first_move_single_tile_valid(self):
        board = Board()
        placements = [((0, 0), Tile(Shape.CIRCLE, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=True)
        assert valid is True

    def test_first_move_line_valid(self):
        board = Board()
        placements = [
            ((0, 0), Tile(Shape.CIRCLE, Color.RED)),
            ((0, 1), Tile(Shape.SQUARE, Color.RED)),
            ((0, 2), Tile(Shape.DIAMOND, Color.RED)),
        ]
        valid, msg = validate_move(board, placements, is_first_move=True)
        assert valid is True

    def test_first_move_invalid_line(self):
        board = Board()
        # Different colors AND different shapes
        placements = [
            ((0, 0), Tile(Shape.CIRCLE, Color.RED)),
            ((0, 1), Tile(Shape.SQUARE, Color.BLUE)),
        ]
        valid, msg = validate_move(board, placements, is_first_move=True)
        assert valid is False

    def test_occupied_position_invalid(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        placements = [((0, 0), Tile(Shape.SQUARE, Color.BLUE))]
        valid, msg = validate_move(board, placements)
        assert valid is False
        assert "occupied" in msg.lower()

    def test_not_collinear_invalid(self):
        board = Board()
        placements = [
            ((0, 0), Tile(Shape.CIRCLE, Color.RED)),
            ((1, 1), Tile(Shape.SQUARE, Color.RED)),  # Diagonal
        ]
        valid, msg = validate_move(board, placements, is_first_move=True)
        assert valid is False
        assert "same row or column" in msg.lower()

    def test_must_connect_to_existing(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        # Place tile not connected to existing
        placements = [((5, 5), Tile(Shape.SQUARE, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is False
        assert "connect" in msg.lower()

    def test_connects_to_existing_valid(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        # Place tile next to existing
        placements = [((0, 1), Tile(Shape.SQUARE, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is True

    def test_extends_line_valid(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))

        # Extend the line
        placements = [((0, 2), Tile(Shape.DIAMOND, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is True

    def test_creates_invalid_line(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        # This would create an invalid line (different color AND shape)
        placements = [((0, 1), Tile(Shape.SQUARE, Color.BLUE))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is False

    def test_gap_in_placement_invalid(self):
        board = Board()
        # Try to place with gap
        placements = [
            ((0, 0), Tile(Shape.CIRCLE, Color.RED)),
            ((0, 2), Tile(Shape.SQUARE, Color.RED)),  # Gap at column 1
        ]
        valid, msg = validate_move(board, placements, is_first_move=True)
        assert valid is False
        assert "contiguous" in msg.lower()

    def test_fills_gap_between_existing_valid(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 2), Tile(Shape.DIAMOND, Color.RED))

        # Fill the gap
        placements = [((0, 1), Tile(Shape.SQUARE, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is True

    def test_perpendicular_placement_valid(self):
        board = Board()
        # Existing horizontal line
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))

        # Place vertically, connecting at (0, 0)
        placements = [((1, 0), Tile(Shape.CIRCLE, Color.BLUE))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is True

    def test_duplicate_in_resulting_line_invalid(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        # Would create duplicate
        placements = [((0, 1), Tile(Shape.CIRCLE, Color.RED))]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is False

    def test_line_exceeds_six_invalid(self):
        board = Board()
        # Create a line of 5 tiles
        shapes = list(Shape)
        for i in range(5):
            board.place((0, i), Tile(shapes[i], Color.RED))

        # Try to add two more (would make 7)
        placements = [
            ((0, 5), Tile(Shape.CLOVER, Color.RED)),
            ((0, 6), Tile(Shape.CROSS, Color.RED)),  # This would be 7th
        ]
        valid, msg = validate_move(board, placements, is_first_move=False)
        assert valid is False
