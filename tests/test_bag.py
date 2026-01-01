"""Tests for Bag."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.bag import Bag


class TestBagCreation:
    """Test bag initialization."""

    def test_bag_starts_with_108_tiles(self):
        bag = Bag(seed=42)
        assert bag.remaining() == 108

    def test_bag_has_3_copies_of_each_tile(self):
        bag = Bag(seed=42)
        tiles = bag.peek()

        # Count each unique tile
        for shape in Shape:
            for color in Color:
                tile = Tile(shape, color)
                count = tiles.count(tile)
                assert count == 3, f"Expected 3 of {tile}, got {count}"

    def test_bag_is_shuffled(self):
        # Two bags with different seeds should have different orders
        bag1 = Bag(seed=1)
        bag2 = Bag(seed=2)
        assert bag1.peek() != bag2.peek()

    def test_bag_with_same_seed_is_deterministic(self):
        bag1 = Bag(seed=42)
        bag2 = Bag(seed=42)
        assert bag1.peek() == bag2.peek()


class TestBagDraw:
    """Test drawing tiles from bag."""

    def test_draw_one(self):
        bag = Bag(seed=42)
        tiles = bag.draw(1)
        assert len(tiles) == 1
        assert bag.remaining() == 107

    def test_draw_multiple(self):
        bag = Bag(seed=42)
        tiles = bag.draw(6)
        assert len(tiles) == 6
        assert bag.remaining() == 102

    def test_draw_more_than_available(self):
        bag = Bag(seed=42)
        # Draw most tiles
        bag.draw(100)
        assert bag.remaining() == 8

        # Try to draw more than remaining
        tiles = bag.draw(20)
        assert len(tiles) == 8  # Only got what was left
        assert bag.remaining() == 0

    def test_draw_from_empty_bag(self):
        bag = Bag(seed=42)
        bag.draw(108)
        tiles = bag.draw(1)
        assert tiles == []
        assert bag.remaining() == 0

    def test_draw_zero(self):
        bag = Bag(seed=42)
        tiles = bag.draw(0)
        assert tiles == []
        assert bag.remaining() == 108


class TestBagReturn:
    """Test returning tiles to bag."""

    def test_return_tiles(self):
        bag = Bag(seed=42)
        drawn = bag.draw(6)
        assert bag.remaining() == 102

        bag.return_tiles(drawn)
        assert bag.remaining() == 108

    def test_return_reshuffles(self):
        bag = Bag(seed=42)
        original_order = bag.peek()

        drawn = bag.draw(6)
        bag.return_tiles(drawn)

        # After return, bag should be reshuffled (very unlikely to match)
        # This could theoretically fail but probability is astronomically low
        new_order = bag.peek()
        assert new_order != original_order


class TestBagState:
    """Test bag state queries."""

    def test_is_empty_false_initially(self):
        bag = Bag(seed=42)
        assert not bag.is_empty()

    def test_is_empty_true_after_all_drawn(self):
        bag = Bag(seed=42)
        bag.draw(108)
        assert bag.is_empty()

    def test_peek_returns_copy(self):
        bag = Bag(seed=42)
        peeked = bag.peek()
        peeked.clear()  # Modify the peeked list
        assert bag.remaining() == 108  # Bag unchanged
