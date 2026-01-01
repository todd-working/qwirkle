"""Tests for game engine."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board
from src.models.bag import Bag
from src.models.hand import Hand
from src.engine.game import (
    GameState,
    new_game,
    apply_move,
    apply_swap,
    get_current_hand,
    get_current_score,
    can_play,
    can_swap,
)


class TestNewGame:
    """Test game initialization."""

    def test_new_game_creates_valid_state(self):
        state = new_game(seed=42)

        assert state.board.is_board_empty()
        assert state.current_player == 0
        assert state.turn_number == 1
        assert state.game_over is False
        assert state.winner is None
        assert state.scores == [0, 0]
        assert state.qwirkle_counts == [0, 0]

    def test_new_game_deals_hands(self):
        state = new_game(seed=42)

        assert len(state.hands[0]) == 6
        assert len(state.hands[1]) == 6

    def test_new_game_bag_has_remaining(self):
        state = new_game(seed=42)

        # 108 - 12 dealt = 96
        assert state.bag.remaining() == 96

    def test_new_game_seeded_is_deterministic(self):
        state1 = new_game(seed=123)
        state2 = new_game(seed=123)

        assert state1.hands[0].tiles() == state2.hands[0].tiles()
        assert state1.hands[1].tiles() == state2.hands[1].tiles()

    def test_new_game_different_seeds_different(self):
        state1 = new_game(seed=1)
        state2 = new_game(seed=2)

        # Very unlikely to be equal
        assert state1.hands[0].tiles() != state2.hands[0].tiles()


class TestGameStateClone:
    """Test game state cloning."""

    def test_clone_creates_copy(self):
        state = new_game(seed=42)
        clone = state.clone()

        assert clone.current_player == state.current_player
        assert clone.turn_number == state.turn_number
        assert clone.scores == state.scores
        assert clone.game_over == state.game_over

    def test_clone_is_independent(self):
        state = new_game(seed=42)
        clone = state.clone()

        # Modify original
        state.scores[0] = 100
        state.current_player = 1

        # Clone should be unchanged
        assert clone.scores[0] == 0
        assert clone.current_player == 0

    def test_clone_board_is_independent(self):
        state = new_game(seed=42)
        tile = Tile(Shape.CIRCLE, Color.RED)
        state.board.place((0, 0), tile)

        clone = state.clone()

        # Modify original board
        state.board.place((0, 1), Tile(Shape.SQUARE, Color.BLUE))

        # Clone board should not have new tile
        assert clone.board.get((0, 1)) is None
        assert clone.board.get((0, 0)) == tile

    def test_clone_hands_are_independent(self):
        state = new_game(seed=42)
        original_tiles = state.hands[0].tiles()

        clone = state.clone()

        # Draw from original's hand
        tile = state.hands[0].tiles()[0]
        state.hands[0].remove([tile])

        # Clone should still have all tiles
        assert clone.hands[0].tiles() == original_tiles


class TestApplyMove:
    """Test move application."""

    def test_first_move_valid(self):
        state = new_game(seed=42)
        hand = state.hands[0]
        tile = hand.tiles()[0]

        placements = [((0, 0), tile)]
        success, error, points = apply_move(state, placements)

        assert success is True
        assert error == ""
        assert points == 1  # Single tile first move
        assert state.board.get((0, 0)) == tile
        assert tile not in state.hands[0]

    def test_move_updates_score(self):
        state = new_game(seed=42)
        hand = state.hands[0]
        tiles = hand.tiles()

        # Find two tiles that form valid line (same color or same shape)
        tile1 = tiles[0]
        tile2 = None
        for t in tiles[1:]:
            if t.color == tile1.color or t.shape == tile1.shape:
                tile2 = t
                break

        if tile2:
            placements = [((0, 0), tile1), ((0, 1), tile2)]
            success, error, points = apply_move(state, placements)

            if success:
                assert state.scores[0] == points
                assert points >= 2

    def test_move_advances_turn(self):
        state = new_game(seed=42)
        tile = state.hands[0].tiles()[0]

        placements = [((0, 0), tile)]
        apply_move(state, placements)

        assert state.current_player == 1
        assert state.turn_number == 2

    def test_move_refills_hand(self):
        state = new_game(seed=42)
        tile = state.hands[0].tiles()[0]

        placements = [((0, 0), tile)]
        apply_move(state, placements)

        # Hand should be refilled to 6
        assert len(state.hands[0]) == 6

    def test_move_fails_without_tiles(self):
        state = new_game(seed=42)
        # Try to place a tile player doesn't have
        fake_tile = Tile(Shape.CROSS, Color.PURPLE)
        # Remove from hand if present
        if fake_tile in state.hands[0]:
            # This seed might have it - find one they don't have
            all_tiles = set(state.hands[0].tiles())
            for shape in Shape:
                for color in Color:
                    t = Tile(shape, color)
                    if t not in all_tiles:
                        fake_tile = t
                        break

        placements = [((0, 0), fake_tile)]
        success, error, points = apply_move(state, placements)

        assert success is False
        assert "does not have tile" in error

    def test_move_fails_on_game_over(self):
        state = new_game(seed=42)
        state.game_over = True
        tile = state.hands[0].tiles()[0]

        success, error, _ = apply_move(state, [((0, 0), tile)])

        assert success is False
        assert "already over" in error

    def test_move_fails_invalid_placement(self):
        state = new_game(seed=42)
        tile = state.hands[0].tiles()[0]

        # First move at (0, 0)
        apply_move(state, [((0, 0), tile)])

        # Second player tries disconnected placement
        tile2 = state.hands[1].tiles()[0]
        success, error, _ = apply_move(state, [((5, 5), tile2)])

        assert success is False
        assert "connect" in error.lower()


class TestApplySwap:
    """Test tile swapping."""

    def test_swap_valid(self):
        state = new_game(seed=42)
        old_tiles = state.hands[0].tiles()
        tile_to_swap = old_tiles[0]

        success, error = apply_swap(state, [tile_to_swap])

        assert success is True
        assert error == ""
        # Hand still has 6 tiles
        assert len(state.hands[0]) == 6
        # Turn advanced
        assert state.current_player == 1

    def test_swap_multiple_tiles(self):
        state = new_game(seed=42)
        tiles = state.hands[0].tiles()[:3]

        success, error = apply_swap(state, tiles)

        assert success is True
        assert len(state.hands[0]) == 6

    def test_swap_returns_to_bag(self):
        state = new_game(seed=42)
        initial_bag = state.bag.remaining()
        tiles = state.hands[0].tiles()[:2]

        apply_swap(state, tiles)

        # Bag should have same count (drew 2, returned 2)
        assert state.bag.remaining() == initial_bag

    def test_swap_fails_empty_bag(self):
        state = new_game(seed=42)
        # Empty the bag
        state.bag.draw(state.bag.remaining())

        tile = state.hands[0].tiles()[0]
        success, error = apply_swap(state, [tile])

        assert success is False
        assert "empty" in error.lower()

    def test_swap_fails_without_tile(self):
        state = new_game(seed=42)
        # Find a tile not in hand
        hand_tiles = set(state.hands[0].tiles())
        fake_tile = None
        for shape in Shape:
            for color in Color:
                t = Tile(shape, color)
                if t not in hand_tiles:
                    fake_tile = t
                    break
            if fake_tile:
                break

        success, error = apply_swap(state, [fake_tile])

        assert success is False
        assert "does not have tile" in error

    def test_swap_fails_on_game_over(self):
        state = new_game(seed=42)
        state.game_over = True

        success, error = apply_swap(state, state.hands[0].tiles()[:1])

        assert success is False
        assert "already over" in error


class TestTurnFlow:
    """Test turn advancement and game flow."""

    def test_turns_alternate(self):
        state = new_game(seed=42)
        assert state.current_player == 0

        # Player 0 moves
        apply_move(state, [((0, 0), state.hands[0].tiles()[0])])
        assert state.current_player == 1

        # Player 1 swaps
        apply_swap(state, state.hands[1].tiles()[:1])
        assert state.current_player == 0

    def test_turn_number_increments(self):
        state = new_game(seed=42)
        assert state.turn_number == 1

        apply_move(state, [((0, 0), state.hands[0].tiles()[0])])
        assert state.turn_number == 2

        apply_swap(state, state.hands[1].tiles()[:1])
        assert state.turn_number == 3


class TestEndGame:
    """Test end-game detection."""

    def test_game_ends_when_hand_empty_bag_empty(self):
        state = new_game(seed=42)

        # Empty the bag
        state.bag.draw(state.bag.remaining())

        # Make player 0's hand have just one tile
        hand = state.hands[0]
        tiles = hand.tiles()
        hand.remove(tiles[1:])  # Keep only first tile

        # Place the tile
        tile = hand.tiles()[0]
        apply_move(state, [((0, 0), tile)])

        assert state.game_over is True

    def test_winner_determined_by_score(self):
        state = new_game(seed=42)
        state.scores = [50, 30]
        state.bag.draw(state.bag.remaining())

        hand = state.hands[0]
        tiles = hand.tiles()
        hand.remove(tiles[1:])

        apply_move(state, [((0, 0), hand.tiles()[0])])

        assert state.game_over is True
        assert state.winner == 0  # Player 0 had higher score

    def test_end_game_bonus_applied(self):
        state = new_game(seed=42)
        state.bag.draw(state.bag.remaining())

        hand = state.hands[0]
        tiles = hand.tiles()
        hand.remove(tiles[1:])

        initial_score = state.scores[0]
        apply_move(state, [((0, 0), hand.tiles()[0])])

        # Should have move score + end game bonus (6)
        assert state.scores[0] > initial_score + 6  # 1 point + 6 bonus = 7


class TestHelperFunctions:
    """Test helper query functions."""

    def test_get_current_hand(self):
        state = new_game(seed=42)

        assert get_current_hand(state) is state.hands[0]

        state.current_player = 1
        assert get_current_hand(state) is state.hands[1]

    def test_get_current_score(self):
        state = new_game(seed=42)
        state.scores = [10, 20]

        assert get_current_score(state) == 10

        state.current_player = 1
        assert get_current_score(state) == 20

    def test_can_play(self):
        state = new_game(seed=42)

        assert can_play(state) is True

        state.game_over = True
        assert can_play(state) is False

    def test_can_swap(self):
        state = new_game(seed=42)

        assert can_swap(state) is True

        # Empty bag
        state.bag.draw(state.bag.remaining())
        assert can_swap(state) is False

    def test_can_swap_game_over(self):
        state = new_game(seed=42)
        state.game_over = True

        assert can_swap(state) is False


class TestQwirkleTracking:
    """Test Qwirkle count tracking."""

    def test_qwirkle_count_tracked(self):
        state = new_game(seed=42)

        # Manually set up a Qwirkle scenario
        # Place 5 tiles of same color, different shapes
        shapes = list(Shape)
        for i in range(5):
            state.board.place((0, i), Tile(shapes[i], Color.RED))

        # Give player the 6th tile to complete Qwirkle
        state.hands[0] = Hand([Tile(shapes[5], Color.RED)])

        apply_move(state, [((0, 5), Tile(shapes[5], Color.RED))])

        assert state.qwirkle_counts[0] == 1


class TestBagAndHandCopy:
    """Test copy methods added to Bag and Hand."""

    def test_bag_copy_independent(self):
        bag = Bag(seed=42)
        copy = bag.copy()

        # Draw from original
        bag.draw(10)

        # Copy should still have all tiles
        assert copy.remaining() == 108

    def test_hand_copy_independent(self):
        tile1 = Tile(Shape.CIRCLE, Color.RED)
        tile2 = Tile(Shape.SQUARE, Color.BLUE)
        hand = Hand([tile1, tile2])

        copy = hand.copy()

        # Modify original
        hand.remove([tile1])

        # Copy unchanged
        assert len(copy) == 2
        assert tile1 in copy
