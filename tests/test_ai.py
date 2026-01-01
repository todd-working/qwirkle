"""Tests for AI module."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board
from src.models.hand import Hand
from src.engine.game import GameState, new_game
from src.ai.move_gen import (
    find_valid_positions,
    generate_single_tile_moves,
    generate_multi_tile_moves,
    generate_all_moves,
    Move,
)
from src.ai.solver import (
    GreedySolver,
    RandomSolver,
    WeightedRandomSolver,
    get_best_move,
    get_random_move,
    get_hint,
)


class TestFindValidPositions:
    """Test position finding."""

    def test_empty_board_returns_origin(self):
        board = Board()
        positions = find_valid_positions(board)
        assert positions == {(0, 0)}

    def test_single_tile_returns_neighbors(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        positions = find_valid_positions(board)

        # Should be 4 neighbors
        assert (-1, 0) in positions  # up
        assert (1, 0) in positions   # down
        assert (0, -1) in positions  # left
        assert (0, 1) in positions   # right
        assert (0, 0) not in positions  # not the occupied cell

    def test_line_returns_all_neighbors(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))
        board.place((0, 1), Tile(Shape.SQUARE, Color.RED))

        positions = find_valid_positions(board)

        # All empty neighbors of both tiles
        assert (0, -1) in positions  # left of first
        assert (0, 2) in positions   # right of second
        assert (-1, 0) in positions  # above first
        assert (-1, 1) in positions  # above second
        assert len(positions) >= 6


class TestGenerateSingleTileMoves:
    """Test single-tile move generation."""

    def test_first_move_generates_moves(self):
        board = Board()
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)])

        moves = generate_single_tile_moves(board, hand, is_first_move=True)

        assert len(moves) == 1
        assert moves[0].placements == [((0, 0), Tile(Shape.CIRCLE, Color.RED))]
        assert moves[0].score == 1

    def test_extension_generates_valid_moves(self):
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        hand = Hand([
            Tile(Shape.SQUARE, Color.RED),   # Valid - same color
            Tile(Shape.CIRCLE, Color.BLUE),  # Valid - same shape
            Tile(Shape.SQUARE, Color.BLUE),  # Invalid - neither matches
        ])

        moves = generate_single_tile_moves(board, hand, is_first_move=False)

        # Should have valid moves for matching tiles
        valid_tiles = {m.placements[0][1] for m in moves}
        assert Tile(Shape.SQUARE, Color.RED) in valid_tiles
        assert Tile(Shape.CIRCLE, Color.BLUE) in valid_tiles

    def test_no_duplicates_for_same_tile_type(self):
        board = Board()
        # Hand with duplicate tiles
        hand = Hand([
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.CIRCLE, Color.RED),  # Duplicate
        ])

        moves = generate_single_tile_moves(board, hand, is_first_move=True)

        # Should only generate one move, not two
        assert len(moves) == 1


class TestGenerateMultiTileMoves:
    """Test multi-tile move generation."""

    def test_first_move_line(self):
        board = Board()
        hand = Hand([
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
        ])

        moves = generate_multi_tile_moves(board, hand, is_first_move=True)

        # Should find horizontal line at origin
        assert len(moves) >= 1
        # Find the 2-tile move
        two_tile_moves = [m for m in moves if len(m.placements) == 2]
        assert len(two_tile_moves) >= 1
        assert two_tile_moves[0].score == 2

    def test_extension_returns_list(self):
        # Just verify the function returns without crashing
        board = Board()
        board.place((0, 0), Tile(Shape.CIRCLE, Color.RED))

        hand = Hand([Tile(Shape.SQUARE, Color.RED)])

        # Single tile in hand - should return empty list
        moves = generate_multi_tile_moves(board, hand, is_first_move=False)
        assert moves == []  # Need 2+ tiles for multi-tile moves


class TestGenerateAllMoves:
    """Test combined move generation."""

    def test_includes_single_and_multi(self):
        board = Board()
        hand = Hand([
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
        ])

        moves = generate_all_moves(board, hand, is_first_move=True)

        # Should have both single-tile and multi-tile moves
        single_tile = [m for m in moves if len(m.placements) == 1]
        multi_tile = [m for m in moves if len(m.placements) > 1]

        assert len(single_tile) >= 1
        assert len(multi_tile) >= 1

    def test_sorted_by_score(self):
        board = Board()
        hand = Hand([
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.RED),
            Tile(Shape.DIAMOND, Color.RED),
        ])

        moves = generate_all_moves(board, hand, is_first_move=True)

        # Verify sorted by score (highest first)
        for i in range(len(moves) - 1):
            assert moves[i].score >= moves[i + 1].score


class TestGreedySolver:
    """Test greedy solver."""

    def test_selects_highest_score(self):
        # Use simple state for speed
        board = Board()
        hand = Hand([Tile(Shape.CIRCLE, Color.RED), Tile(Shape.SQUARE, Color.RED)])
        moves = generate_all_moves(board, hand, is_first_move=True)

        solver = GreedySolver()
        move = solver.select_move(None, moves)

        # Should return the highest-scoring move
        assert move is not None
        assert move.score == max(m.score for m in moves)

    def test_returns_none_when_no_moves(self):
        solver = GreedySolver()
        move = solver.select_move(None, [])

        assert move is None


class TestRandomSolver:
    """Test random solver."""

    def test_returns_valid_move(self):
        board = Board()
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)])
        moves = generate_all_moves(board, hand, is_first_move=True)

        solver = RandomSolver(seed=123)
        move = solver.select_move(None, moves)

        assert move is not None
        assert move in moves

    def test_deterministic_with_seed(self):
        board = Board()
        hand = Hand([Tile(Shape.CIRCLE, Color.RED), Tile(Shape.SQUARE, Color.RED)])
        moves = generate_all_moves(board, hand, is_first_move=True)

        solver1 = RandomSolver(seed=123)
        solver2 = RandomSolver(seed=123)

        move1 = solver1.select_move(None, moves)
        move2 = solver2.select_move(None, moves)

        assert move1.placements == move2.placements

    def test_returns_none_when_no_moves(self):
        solver = RandomSolver(seed=123)
        move = solver.select_move(None, [])

        assert move is None


class TestWeightedRandomSolver:
    """Test weighted random solver."""

    def test_returns_valid_move(self):
        board = Board()
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)])
        moves = generate_all_moves(board, hand, is_first_move=True)

        solver = WeightedRandomSolver(seed=123)
        move = solver.select_move(None, moves)

        assert move is not None

    def test_returns_none_when_no_moves(self):
        solver = WeightedRandomSolver(seed=123)
        move = solver.select_move(None, [])

        assert move is None


class TestConvenienceFunctions:
    """Test convenience functions with simple states."""

    def test_get_best_move_simple(self):
        # Create a simple game state
        state = new_game(seed=42)
        # Simplify the hand to make it fast
        state.hands[0] = Hand([Tile(Shape.CIRCLE, Color.RED)])

        move = get_best_move(state)

        assert move is not None
        assert isinstance(move, Move)

    def test_get_random_move_simple(self):
        state = new_game(seed=42)
        state.hands[0] = Hand([Tile(Shape.CIRCLE, Color.RED)])

        move = get_random_move(state, seed=123)

        assert move is not None
        assert isinstance(move, Move)

    def test_get_hint_simple(self):
        state = new_game(seed=42)
        state.hands[0] = Hand([Tile(Shape.CIRCLE, Color.RED)])

        move = get_hint(state)

        assert move is not None


class TestMoveDataclass:
    """Test Move dataclass."""

    def test_move_creation(self):
        placements = [((0, 0), Tile(Shape.CIRCLE, Color.RED))]
        move = Move(placements, score=5, qwirkles=0)

        assert move.placements == placements
        assert move.score == 5
        assert move.qwirkles == 0

    def test_move_repr(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        placements = [((0, 0), tile)]
        move = Move(placements, score=5, qwirkles=0)

        repr_str = repr(move)
        assert "Move" in repr_str
        assert "score=5" in repr_str
