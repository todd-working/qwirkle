"""Tests for command parser."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.ui.input import (
    parse_command,
    parse_position,
    parse_tile_spec,
    PlayCommand,
    SwapCommand,
    QuitCommand,
    UndoCommand,
    HintCommand,
    HelpCommand,
)


class TestParsePosition:
    """Test position parsing."""

    def test_parse_origin(self):
        assert parse_position("0,0") == (0, 0)

    def test_parse_positive(self):
        assert parse_position("5,10") == (5, 10)

    def test_parse_negative(self):
        assert parse_position("-3,-5") == (-3, -5)

    def test_parse_mixed(self):
        assert parse_position("2,-1") == (2, -1)

    def test_parse_with_spaces(self):
        assert parse_position(" 1,2 ") == (1, 2)

    def test_parse_invalid_format(self):
        assert parse_position("1.2") is None
        assert parse_position("abc") is None
        assert parse_position("1,2,3") is None
        assert parse_position("") is None


class TestParseTileSpec:
    """Test tile specification parsing."""

    def test_parse_red_circle(self):
        tile = parse_tile_spec("RO")
        assert tile == Tile(Shape.CIRCLE, Color.RED)

    def test_parse_blue_square(self):
        tile = parse_tile_spec("BS")
        assert tile == Tile(Shape.SQUARE, Color.BLUE)

    def test_parse_green_diamond(self):
        tile = parse_tile_spec("GD")
        assert tile == Tile(Shape.DIAMOND, Color.GREEN)

    def test_parse_yellow_star(self):
        tile = parse_tile_spec("YT")
        assert tile == Tile(Shape.STAR, Color.YELLOW)

    def test_parse_orange_clover(self):
        tile = parse_tile_spec("OL")
        assert tile == Tile(Shape.CLOVER, Color.ORANGE)

    def test_parse_purple_cross(self):
        tile = parse_tile_spec("PX")
        assert tile == Tile(Shape.CROSS, Color.PURPLE)

    def test_parse_lowercase(self):
        tile = parse_tile_spec("ro")
        assert tile == Tile(Shape.CIRCLE, Color.RED)

    def test_parse_invalid(self):
        assert parse_tile_spec("XX") is None  # Invalid color
        assert parse_tile_spec("R") is None   # Too short
        assert parse_tile_spec("ROO") is None # Too long
        assert parse_tile_spec("") is None


class TestParseQuitCommand:
    """Test quit command parsing."""

    def test_quit(self):
        cmd, error = parse_command("quit")
        assert isinstance(cmd, QuitCommand)
        assert error == ""

    def test_q_shorthand(self):
        cmd, error = parse_command("q")
        assert isinstance(cmd, QuitCommand)

    def test_exit(self):
        cmd, error = parse_command("exit")
        assert isinstance(cmd, QuitCommand)

    def test_case_insensitive(self):
        cmd, error = parse_command("QUIT")
        assert isinstance(cmd, QuitCommand)


class TestParseUndoCommand:
    """Test undo command parsing."""

    def test_undo(self):
        cmd, error = parse_command("undo")
        assert isinstance(cmd, UndoCommand)
        assert error == ""


class TestParseHintCommand:
    """Test hint command parsing."""

    def test_hint(self):
        cmd, error = parse_command("hint")
        assert isinstance(cmd, HintCommand)
        assert error == ""


class TestParseHelpCommand:
    """Test help command parsing."""

    def test_help(self):
        cmd, error = parse_command("help")
        assert isinstance(cmd, HelpCommand)
        assert error == ""

    def test_question_mark(self):
        cmd, error = parse_command("?")
        assert isinstance(cmd, HelpCommand)


class TestParsePlayCommand:
    """Test play command parsing."""

    def test_single_tile(self):
        cmd, error = parse_command("play 1 0,0")
        assert isinstance(cmd, PlayCommand)
        assert error == ""
        assert cmd.placements == [(1, (0, 0))]

    def test_multiple_tiles_comma_separated(self):
        cmd, error = parse_command("play 1,2 0,0 0,1")
        assert isinstance(cmd, PlayCommand)
        assert cmd.placements == [(1, (0, 0)), (2, (0, 1))]

    def test_multiple_tiles_space_separated(self):
        cmd, error = parse_command("play 1 2 0,0 0,1")
        assert isinstance(cmd, PlayCommand)
        assert cmd.placements == [(1, (0, 0)), (2, (0, 1))]

    def test_three_tiles(self):
        cmd, error = parse_command("play 1,2,3 0,0 0,1 0,2")
        assert isinstance(cmd, PlayCommand)
        assert len(cmd.placements) == 3

    def test_negative_position(self):
        cmd, error = parse_command("play 1 -1,-2")
        assert isinstance(cmd, PlayCommand)
        assert cmd.placements == [(1, (-1, -2))]

    def test_no_tiles_error(self):
        cmd, error = parse_command("play")
        assert cmd is None
        assert "Usage" in error

    def test_no_positions_error(self):
        cmd, error = parse_command("play 1")
        assert cmd is None
        assert "positions" in error.lower()

    def test_mismatch_count_error(self):
        cmd, error = parse_command("play 1,2 0,0")
        assert cmd is None
        assert "Mismatch" in error

    def test_invalid_index_error(self):
        cmd, error = parse_command("play 0 0,0")
        assert cmd is None
        assert "1-6" in error

    def test_index_too_high_error(self):
        cmd, error = parse_command("play 7 0,0")
        assert cmd is None
        assert "1-6" in error


class TestParseSwapCommand:
    """Test swap command parsing."""

    def test_single_tile(self):
        cmd, error = parse_command("swap 1")
        assert isinstance(cmd, SwapCommand)
        assert error == ""
        assert cmd.tile_indices == [1]

    def test_multiple_comma_separated(self):
        cmd, error = parse_command("swap 1,2,3")
        assert isinstance(cmd, SwapCommand)
        assert cmd.tile_indices == [1, 2, 3]

    def test_multiple_space_separated(self):
        cmd, error = parse_command("swap 1 2 3")
        assert isinstance(cmd, SwapCommand)
        assert cmd.tile_indices == [1, 2, 3]

    def test_no_tiles_error(self):
        cmd, error = parse_command("swap")
        assert cmd is None
        assert "Usage" in error

    def test_invalid_index_error(self):
        cmd, error = parse_command("swap 0")
        assert cmd is None
        assert "1-6" in error

    def test_index_too_high_error(self):
        cmd, error = parse_command("swap 7")
        assert cmd is None
        assert "1-6" in error


class TestParseInvalidCommand:
    """Test invalid command handling."""

    def test_unknown_command(self):
        cmd, error = parse_command("foo")
        assert cmd is None
        assert "Unknown command" in error

    def test_empty_input(self):
        cmd, error = parse_command("")
        assert cmd is None
        assert "enter a command" in error.lower()

    def test_whitespace_only(self):
        cmd, error = parse_command("   ")
        assert cmd is None
        assert "enter a command" in error.lower()
