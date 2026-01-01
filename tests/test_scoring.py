"""Tests for scoring engine."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board
from src.engine.scoring import (
    calculate_line_score,
    calculate_move_score,
    calculate_end_game_bonus,
    score_move,
    QWIRKLE_SIZE,
    QWIRKLE_BONUS,
    END_GAME_BONUS,
)


class TestCalculateLineScore:
    """Test individual line scoring."""

    def test_empty_line_zero(self):
        assert calculate_line_score(0) == 0

    def test_single_tile_zero(self):
        # Single tile doesn't form a scoring line
        assert calculate_line_score(1) == 0

    def test_two_tiles(self):
        assert calculate_line_score(2) == 2

    def test_three_tiles(self):
        assert calculate_line_score(3) == 3

    def test_five_tiles(self):
        assert calculate_line_score(5) == 5

    def test_qwirkle_six_tiles(self):
        # 6 tiles = 6 + 6 bonus = 12
        assert calculate_line_score(6) == 12

    def test_constants(self):
        assert QWIRKLE_SIZE == 6
        assert QWIRKLE_BONUS == 6
        assert END_GAME_BONUS == 6


class TestCalculateMoveScore:
    """Test scoring after tiles are placed on board."""

    def test_empty_placements(self):
        board = Board()
        score, qwirkles = calculate_move_score(board, [])
        assert score == 0
        assert qwirkles == 0

    def test_single_tile_first_move(self):
        board = Board()
        tile = Tile(Shape.CIRCLE, Color.RED)
        board.place((0, 0), tile)

        score, qwirkles = calculate_move_score(board, [((0, 0), tile)])
        # Single tile on empty board scores 1
        assert score == 1
        assert qwirkles == 0

    def test_two_tile_horizontal_line(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)
        board.place((0, 0), t1)
        board.place((0, 1), t2)

        placements = [((0, 0), t1), ((0, 1), t2)]
        score, qwirkles = calculate_move_score(board, placements)
        assert score == 2
        assert qwirkles == 0

    def test_extend_line(self):
        board = Board()
        t1 = Tile(Shape.CIRCLE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.RED)
        t3 = Tile(Shape.DIAMOND, Color.RED)
        board.place((0, 0), t1)
        board.place((0, 1), t2)
        board.place((0, 2), t3)

        # Only the third tile was just placed
        placements = [((0, 2), t3)]
        score, qwirkles = calculate_move_score(board, placements)
        # Line is now 3 tiles
        assert score == 3
        assert qwirkles == 0

    def test_cross_scores_both_lines(self):
        board = Board()
        # Horizontal line
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))
        # Vertical line from (0, 0)
        board.place((1, 0), Tile(Shape.CIRCLE, Color.BLUE))

        # The corner tile (0, 0) was placed
        placements = [((0, 0), Tile(Shape.CIRCLE, Color.RED))]
        score, qwirkles = calculate_move_score(board, placements)
        # Horizontal: 2 tiles, Vertical: 2 tiles = 4 total
        assert score == 4
        assert qwirkles == 0

    def test_qwirkle_horizontal(self):
        board = Board()
        placements = []
        # Create Qwirkle: 6 different shapes, same color
        for i, shape in enumerate(Shape):
            tile = Tile(shape, Color.RED)
            board.place((0, i), tile)
            placements.append(((0, i), tile))

        score, qwirkles = calculate_move_score(board, placements)
        assert score == 12  # 6 + 6 bonus
        assert qwirkles == 1

    def test_qwirkle_vertical(self):
        board = Board()
        placements = []
        # Create Qwirkle: 6 different colors, same shape
        for i, color in enumerate(Color):
            tile = Tile(Shape.CIRCLE, color)
            board.place((i, 0), tile)
            placements.append(((i, 0), tile))

        score, qwirkles = calculate_move_score(board, placements)
        assert score == 12
        assert qwirkles == 1

    def test_multiple_lines_single_placement(self):
        """Place one tile that extends two lines."""
        board = Board()
        # Set up horizontal line
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))
        # Set up vertical line
        board.place((1, 2), Tile(Shape.DIAMOND, Color.RED))
        board.place((2, 2), Tile(Shape.STAR, Color.RED))

        # Place tile at (0, 2) to connect both
        new_tile = Tile(Shape.CLOVER, Color.RED)
        board.place((0, 2), new_tile)

        placements = [((0, 2), new_tile)]
        score, qwirkles = calculate_move_score(board, placements)
        # Horizontal now 3 tiles, Vertical now 3 tiles = 6 total
        assert score == 6
        assert qwirkles == 0


class TestScoreMove:
    """Test scoring with board-before semantics."""

    def test_score_first_move(self):
        board = Board()
        placements = [
            ((0, 0), Tile(Shape.CIRCLE, Color.RED)),
            ((0, 1), Tile(Shape.SQUARE, Color.RED)),
        ]
        score, qwirkles = score_move(board, placements)
        assert score == 2
        assert qwirkles == 0

    def test_score_extension(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))

        placements = [((0, 2), Tile(Shape.DIAMOND, Color.RED))]
        score, qwirkles = score_move(board, placements)
        assert score == 3  # Line is now 3 tiles
        assert qwirkles == 0

    def test_score_empty_placements(self):
        board = Board()
        score, qwirkles = score_move(board, [])
        assert score == 0
        assert qwirkles == 0

    def test_original_board_unchanged(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        placements = [((0, 1), Tile(Shape.SQUARE, Color.RED))]
        score_move(board, placements)

        # Original board should not have the new tile
        assert board.get((0, 1)) is None
        assert board.tile_count() == 1


class TestEndGameBonus:
    """Test end-game bonus."""

    def test_end_game_bonus_value(self):
        assert calculate_end_game_bonus() == 6


class TestComplexScoring:
    """Test complex scoring scenarios."""

    def test_two_qwirkles_same_move(self):
        """Place tiles that complete two Qwirkles at once."""
        board = Board()
        shapes = list(Shape)
        colors = list(Color)

        # Set up almost-complete horizontal Qwirkle
        for i in range(5):
            board.place((0, i), Tile(shapes[i], Color.RED))

        # Set up almost-complete vertical Qwirkle at column 5
        for i in range(1, 6):
            board.place((i, 5), Tile(Shape.CLOVER, colors[i]))

        # Place tile at (0, 5) to complete both
        new_tile = Tile(Shape.CLOVER, Color.RED)
        board.place((0, 5), new_tile)

        placements = [((0, 5), new_tile)]
        score, qwirkles = calculate_move_score(board, placements)
        # Two Qwirkles: 12 + 12 = 24
        assert score == 24
        assert qwirkles == 2

    def test_multiple_tiles_multiple_lines(self):
        """Place multiple tiles that form multiple scoring lines."""
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        # Place two tiles forming L shape
        t1 = Tile(Shape.SQUARE, Color.RED)
        t2 = Tile(Shape.SQUARE, Color.BLUE)
        board.place((0, 1), t1)
        board.place((1, 1), t2)

        placements = [((0, 1), t1), ((1, 1), t2)]
        score, qwirkles = calculate_move_score(board, placements)
        # Horizontal at row 0: 2 tiles = 2
        # Vertical at col 1: 2 tiles = 2
        # Total = 4
        assert score == 4
        assert qwirkles == 0
