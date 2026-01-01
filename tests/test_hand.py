"""Tests for Hand."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.bag import Bag
from src.models.hand import Hand


class TestHandCreation:
    """Test hand initialization."""

    def test_empty_hand(self):
        hand = Hand()
        assert hand.size() == 0
        assert hand.is_empty()

    def test_hand_with_initial_tiles(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.BLUE),
        ]
        hand = Hand(tiles)
        assert hand.size() == 2
        assert not hand.is_empty()

    def test_hand_rejects_too_many_initial_tiles(self):
        tiles = [Tile(Shape.CIRCLE, Color.RED)] * 7
        with pytest.raises(ValueError, match="cannot exceed"):
            Hand(tiles)

    def test_hand_copies_initial_tiles(self):
        tiles = [Tile(Shape.CIRCLE, Color.RED)]
        hand = Hand(tiles)
        tiles.append(Tile(Shape.SQUARE, Color.BLUE))  # Modify original
        assert hand.size() == 1  # Hand unchanged


class TestHandAdd:
    """Test adding tiles to hand."""

    def test_add_tiles(self):
        hand = Hand()
        hand.add([Tile(Shape.CIRCLE, Color.RED)])
        assert hand.size() == 1

    def test_add_multiple_tiles(self):
        hand = Hand()
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.BLUE),
            Tile(Shape.DIAMOND, Color.GREEN),
        ]
        hand.add(tiles)
        assert hand.size() == 3

    def test_add_rejects_overflow(self):
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)] * 5)
        with pytest.raises(ValueError, match="Cannot exceed"):
            hand.add([Tile(Shape.SQUARE, Color.BLUE)] * 2)


class TestHandRemove:
    """Test removing tiles from hand."""

    def test_remove_tile(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        hand = Hand([tile, Tile(Shape.SQUARE, Color.BLUE)])
        hand.remove([tile])
        assert hand.size() == 1
        assert tile not in hand

    def test_remove_multiple_tiles(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.BLUE),
            Tile(Shape.DIAMOND, Color.GREEN),
        ]
        hand = Hand(tiles)
        hand.remove([tiles[0], tiles[2]])
        assert hand.size() == 1
        assert tiles[1] in hand

    def test_remove_duplicate_tiles(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        hand = Hand([tile, tile, Tile(Shape.SQUARE, Color.BLUE)])
        hand.remove([tile, tile])
        assert hand.size() == 1

    def test_remove_nonexistent_tile_raises(self):
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)])
        with pytest.raises(ValueError, match="not in hand"):
            hand.remove([Tile(Shape.SQUARE, Color.BLUE)])

    def test_remove_validates_all_before_removing(self):
        # If removing [A, B] and B doesn't exist, A should NOT be removed
        tile_a = Tile(Shape.CIRCLE, Color.RED)
        tile_b = Tile(Shape.SQUARE, Color.BLUE)
        hand = Hand([tile_a])

        with pytest.raises(ValueError):
            hand.remove([tile_a, tile_b])

        assert tile_a in hand  # A should still be there


class TestHandRefill:
    """Test refilling hand from bag."""

    def test_refill_empty_hand(self):
        bag = Bag(seed=42)
        hand = Hand()
        drawn = hand.refill(bag)

        assert drawn == 6
        assert hand.size() == 6
        assert bag.remaining() == 102

    def test_refill_partial_hand(self):
        bag = Bag(seed=42)
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)] * 4)
        drawn = hand.refill(bag)

        assert drawn == 2
        assert hand.size() == 6

    def test_refill_full_hand(self):
        bag = Bag(seed=42)
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)] * 6)
        drawn = hand.refill(bag)

        assert drawn == 0
        assert hand.size() == 6

    def test_refill_from_near_empty_bag(self):
        bag = Bag(seed=42)
        bag.draw(106)  # Only 2 left
        hand = Hand()
        drawn = hand.refill(bag)

        assert drawn == 2
        assert hand.size() == 2
        assert bag.remaining() == 0


class TestHandQueries:
    """Test hand query methods."""

    def test_tiles_returns_copy(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        hand = Hand([tile])
        tiles = hand.tiles()
        tiles.clear()
        assert hand.size() == 1

    def test_contains(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        other = Tile(Shape.SQUARE, Color.BLUE)
        hand = Hand([tile])

        assert hand.contains(tile)
        assert not hand.contains(other)

    def test_count(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        hand = Hand([tile, tile, Tile(Shape.SQUARE, Color.BLUE)])

        assert hand.count(tile) == 2
        assert hand.count(Tile(Shape.DIAMOND, Color.GREEN)) == 0

    def test_len_dunder(self):
        hand = Hand([Tile(Shape.CIRCLE, Color.RED)] * 3)
        assert len(hand) == 3

    def test_in_operator(self):
        tile = Tile(Shape.CIRCLE, Color.RED)
        hand = Hand([tile])
        assert tile in hand

    def test_iteration(self):
        tiles = [
            Tile(Shape.CIRCLE, Color.RED),
            Tile(Shape.SQUARE, Color.BLUE),
        ]
        hand = Hand(tiles)
        iterated = list(hand)
        assert iterated == tiles
