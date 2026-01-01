"""Command parsing for Qwirkle terminal UI.

Parses user input into structured commands.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
from src.models.tile import Tile, Color, Shape
from src.models.board import Position


# Maps for parsing tile specifications
COLOR_MAP = {
    'R': Color.RED,
    'O': Color.ORANGE,
    'Y': Color.YELLOW,
    'G': Color.GREEN,
    'B': Color.BLUE,
    'P': Color.PURPLE,
}

SHAPE_MAP = {
    'O': Shape.CIRCLE,   # O for circle
    'S': Shape.SQUARE,
    'D': Shape.DIAMOND,
    'T': Shape.STAR,     # T for star
    'L': Shape.CLOVER,   # L for clover
    'X': Shape.CROSS,    # X for cross
}


@dataclass
class PlayCommand:
    """Command to play tiles on the board.

    Attributes:
        placements: List of (tile_index, position) pairs.
            tile_index is 1-based index into player's hand.
    """
    placements: List[Tuple[int, Position]]


@dataclass
class SwapCommand:
    """Command to swap tiles with the bag.

    Attributes:
        tile_indices: 1-based indices of tiles to swap.
    """
    tile_indices: List[int]


@dataclass
class QuitCommand:
    """Command to quit the game."""
    pass


@dataclass
class UndoCommand:
    """Command to undo the last move."""
    pass


@dataclass
class HintCommand:
    """Command to request a hint."""
    pass


@dataclass
class HelpCommand:
    """Command to show help."""
    pass


@dataclass
class ProbCommand:
    """Command to show win probability estimate.

    Attributes:
        n_simulations: Number of Monte Carlo simulations to run.
    """
    n_simulations: int = 50


Command = Union[PlayCommand, SwapCommand, QuitCommand, UndoCommand, HintCommand, HelpCommand, ProbCommand]


def parse_position(pos_str: str) -> Optional[Position]:
    """Parse a position string like '0,0' or '1,-2'.

    Args:
        pos_str: Position string in 'row,col' format.

    Returns:
        Position tuple or None if invalid.
    """
    match = re.match(r'^(-?\d+),(-?\d+)$', pos_str.strip())
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def parse_tile_spec(spec: str) -> Optional[Tile]:
    """Parse a tile specification like 'RO' (Red Circle) or 'BS' (Blue Square).

    Args:
        spec: Two-character tile spec (color letter + shape letter).

    Returns:
        Tile or None if invalid.
    """
    spec = spec.upper().strip()
    if len(spec) != 2:
        return None

    color = COLOR_MAP.get(spec[0])
    shape = SHAPE_MAP.get(spec[1])

    if color and shape:
        return Tile(shape, color)
    return None


def parse_command(input_str: str) -> Tuple[Optional[Command], str]:
    """Parse a command string into a Command object.

    Args:
        input_str: Raw user input.

    Returns:
        Tuple of (Command or None, error message).
        If parsing succeeds, error is empty string.
    """
    input_str = input_str.strip().lower()

    if not input_str:
        return None, "Please enter a command"

    parts = input_str.split()
    cmd = parts[0]
    args = parts[1:]

    # Quit
    if cmd in ('quit', 'q', 'exit'):
        return QuitCommand(), ""

    # Undo
    if cmd == 'undo':
        return UndoCommand(), ""

    # Hint
    if cmd == 'hint':
        return HintCommand(), ""

    # Help
    if cmd in ('help', '?'):
        return HelpCommand(), ""

    # Win probability
    if cmd in ('prob', 'winprob', 'probability'):
        n_sims = 50  # default
        if args:
            try:
                n_sims = int(args[0])
                if n_sims < 1:
                    return None, "Number of simulations must be at least 1"
                if n_sims > 1000:
                    return None, "Maximum 1000 simulations (for performance)"
            except ValueError:
                return None, f"Invalid number of simulations: {args[0]}"
        return ProbCommand(n_sims), ""

    # Play command
    if cmd == 'play':
        return _parse_play_command(args)

    # Swap command
    if cmd == 'swap':
        return _parse_swap_command(args)

    return None, f"Unknown command: {cmd}. Try 'help' for usage."


def _parse_play_command(args: List[str]) -> Tuple[Optional[PlayCommand], str]:
    """Parse arguments for play command.

    Formats supported:
        play 1 0,0              - Play hand tile 1 at position (0,0)
        play 1,2 0,0 0,1        - Play tiles 1,2 at positions (0,0), (0,1)
        play 1 2 0,0 0,1        - Same as above (space-separated indices)
    """
    if not args:
        return None, "Usage: play <tile_indices> <positions>\nExample: play 1 0,0  or  play 1,2 0,0 0,1"

    # Separate tile indices from positions
    # Strategy: positions always contain negative numbers or are the later args
    # Tile indices are small positive integers (1-6)
    tile_indices = []
    positions = []

    for arg in args:
        if ',' in arg:
            # Check if it looks like a position (has exactly one comma, could have negative)
            parts = arg.split(',')
            if len(parts) == 2:
                try:
                    row, col = int(parts[0]), int(parts[1])
                    # If either is negative or both are valid coords, it's a position
                    # If all values are 1-6, it could be tile indices
                    if row < 0 or col < 0 or row > 6 or col > 6:
                        # Definitely a position (outside tile index range)
                        positions.append((row, col))
                    elif len(positions) > 0:
                        # We've already seen positions, so this must be a position too
                        positions.append((row, col))
                    elif all(1 <= int(x) <= 6 for x in parts):
                        # Could be tile indices if we haven't seen positions yet
                        # Check if remaining args look like positions
                        remaining = args[args.index(arg)+1:]
                        if remaining and any(',' in r for r in remaining):
                            # More comma args follow, treat this as tile indices
                            tile_indices.extend([int(x) for x in parts])
                        else:
                            # No more comma args, ambiguous - treat as position
                            positions.append((row, col))
                    else:
                        # Values outside 1-6, must be position
                        positions.append((row, col))
                except ValueError:
                    return None, f"Invalid argument: {arg}"
            else:
                # More than one comma - must be tile indices
                try:
                    indices = [int(x) for x in parts]
                    tile_indices.extend(indices)
                except ValueError:
                    return None, f"Invalid argument: {arg}"
        else:
            # No comma - single tile index
            try:
                tile_indices.append(int(arg))
            except ValueError:
                return None, f"Invalid tile index: {arg}"

    if not tile_indices:
        return None, "No tile indices specified"

    if not positions:
        return None, "No positions specified"

    if len(tile_indices) != len(positions):
        return None, f"Mismatch: {len(tile_indices)} tiles but {len(positions)} positions"

    # Validate indices are positive
    for idx in tile_indices:
        if idx < 1 or idx > 6:
            return None, f"Tile index must be 1-6, got: {idx}"

    placements = list(zip(tile_indices, positions))
    return PlayCommand(placements), ""


def _parse_swap_command(args: List[str]) -> Tuple[Optional[SwapCommand], str]:
    """Parse arguments for swap command.

    Formats supported:
        swap 1              - Swap tile 1
        swap 1,2,3          - Swap tiles 1, 2, 3
        swap 1 2 3          - Same as above
    """
    if not args:
        return None, "Usage: swap <tile_indices>\nExample: swap 1  or  swap 1,2,3"

    tile_indices = []

    for arg in args:
        if ',' in arg:
            try:
                indices = [int(x) for x in arg.split(',')]
                tile_indices.extend(indices)
            except ValueError:
                return None, f"Invalid tile indices: {arg}"
        else:
            try:
                tile_indices.append(int(arg))
            except ValueError:
                return None, f"Invalid tile index: {arg}"

    if not tile_indices:
        return None, "No tile indices specified"

    for idx in tile_indices:
        if idx < 1 or idx > 6:
            return None, f"Tile index must be 1-6, got: {idx}"

    return SwapCommand(tile_indices), ""


def get_help_text() -> str:
    """Return help text for commands."""
    return """
QWIRKLE COMMANDS
================

play <tiles> <positions>
    Place tiles from your hand onto the board.
    Tiles are specified by their index (1-6) in your hand.
    Positions are row,column coordinates.

    Examples:
        play 1 0,0           Place tile 1 at row 0, column 0
        play 1,2 0,0 0,1     Place tiles 1,2 at (0,0) and (0,1)
        play 1 2 3 0,0 0,1 0,2   Place three tiles in a row

swap <tiles>
    Exchange tiles with the bag (counts as your turn).

    Examples:
        swap 1               Swap tile 1
        swap 1,2,3           Swap tiles 1, 2, and 3

undo
    Take back the last move.

hint
    Get a suggestion for your next move.

prob [n]
    Estimate win probability using Monte Carlo simulation.
    Optional: specify number of simulations (default: 50, max: 1000).

    Examples:
        prob             Run 50 simulations
        prob 100         Run 100 simulations

quit (or q)
    Exit the game.

TILE CODES
==========
Colors: R=Red, O=Orange, Y=Yellow, G=Green, B=Blue, P=Purple
Shapes: O=Circle, S=Square, D=Diamond, T=Star, L=Clover, X=Cross

Example: RO = Red Circle, BS = Blue Square
"""
