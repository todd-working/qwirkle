"""Terminal rendering for Qwirkle.

Renders tiles, board, hands, and game status using ANSI colors and Unicode symbols.
"""

from typing import Dict, List, Optional, Tuple
from src.models.tile import Tile, Color, Shape
from src.models.board import Board, Position
from src.models.hand import Hand
from src.engine.game import GameState


# Unicode symbols for shapes
SHAPE_SYMBOLS: Dict[Shape, str] = {
    Shape.CIRCLE: "●",
    Shape.SQUARE: "■",
    Shape.DIAMOND: "◆",
    Shape.STAR: "★",
    Shape.CLOVER: "✿",
    Shape.CROSS: "✚",
}

# ANSI color codes (foreground)
COLOR_CODES: Dict[Color, str] = {
    Color.RED: "\033[91m",      # Bright red
    Color.ORANGE: "\033[38;5;208m",  # Orange (256-color)
    Color.YELLOW: "\033[93m",   # Bright yellow
    Color.GREEN: "\033[92m",    # Bright green
    Color.BLUE: "\033[94m",     # Bright blue
    Color.PURPLE: "\033[95m",   # Bright magenta/purple
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def render_tile(tile: Tile, with_color: bool = True) -> str:
    """Render a single tile as a colored Unicode symbol.

    Args:
        tile: The tile to render.
        with_color: Whether to include ANSI color codes.

    Returns:
        String representation of the tile.
    """
    symbol = SHAPE_SYMBOLS[tile.shape]
    if with_color:
        color = COLOR_CODES[tile.color]
        return f"{color}{symbol}{RESET}"
    return symbol


def render_tile_label(tile: Tile) -> str:
    """Render a tile with its letter codes (e.g., 'RC' for Red Circle).

    Returns a 2-character code: first letter of color + first letter of shape.
    """
    color_letter = tile.color.name[0]  # R, O, Y, G, B, P
    shape_letter = tile.shape.name[0]  # C, S, D, T(star), L(clover), R(cross)
    # Handle conflicts: Star->T, Clover->L, Cross->X
    shape_map = {
        Shape.CIRCLE: "O",   # O for circle
        Shape.SQUARE: "S",
        Shape.DIAMOND: "D",
        Shape.STAR: "T",     # T for star
        Shape.CLOVER: "L",   # L for clover (flower)
        Shape.CROSS: "X",    # X for cross
    }
    return f"{color_letter}{shape_map[tile.shape]}"


def render_board(
    board: Board,
    highlight_positions: Optional[List[Position]] = None,
    padding: int = 1
) -> str:
    """Render the board as a grid with coordinates.

    Args:
        board: The game board.
        highlight_positions: Positions to highlight (last move).
        padding: Extra cells around the bounds.

    Returns:
        Multi-line string representation of the board.
    """
    if board.is_board_empty():
        return "  (empty board)\n"

    highlight = set(highlight_positions) if highlight_positions else set()

    min_row, max_row, min_col, max_col = board.bounds()

    # Add padding
    min_row -= padding
    max_row += padding
    min_col -= padding
    max_col += padding

    lines = []

    # Column headers
    header = "    "  # Space for row labels
    for col in range(min_col, max_col + 1):
        header += f"{col:^3}"
    lines.append(header)

    # Separator
    lines.append("   " + "─" * ((max_col - min_col + 1) * 3 + 1))

    # Rows
    for row in range(min_row, max_row + 1):
        row_str = f"{row:>2} │"
        for col in range(min_col, max_col + 1):
            tile = board.get((row, col))
            if tile:
                cell = f" {render_tile(tile)} "
                if (row, col) in highlight:
                    cell = f"{BOLD}{cell}{RESET}"
            else:
                cell = " · "
            row_str += cell
        lines.append(row_str)

    return "\n".join(lines) + "\n"


def render_hand(
    hand: Hand,
    player_num: int,
    is_current: bool = False,
    show_indices: bool = True
) -> str:
    """Render a player's hand.

    Args:
        hand: The hand to render.
        player_num: Player number (0 or 1).
        is_current: Whether this is the current player.
        show_indices: Whether to show tile indices.

    Returns:
        String representation of the hand.
    """
    tiles = hand.tiles()

    if is_current:
        header = f"{BOLD}Player {player_num + 1}'s hand (your turn):{RESET}"
    else:
        header = f"Player {player_num + 1}'s hand:"

    if not tiles:
        return f"{header} (empty)\n"

    # Render tiles with indices
    tile_strs = []
    for i, tile in enumerate(tiles):
        rendered = render_tile(tile)
        label = render_tile_label(tile)
        if show_indices:
            tile_strs.append(f"{i+1}:{rendered}({label})")
        else:
            tile_strs.append(f"{rendered}")

    return f"{header} {' '.join(tile_strs)}\n"


def render_status(state: GameState) -> str:
    """Render game status (scores, turn, bag count).

    Args:
        state: Current game state.

    Returns:
        String representation of game status.
    """
    lines = []

    # Scores
    lines.append(f"Scores: Player 1: {state.scores[0]}  |  Player 2: {state.scores[1]}")

    # Bag count
    remaining = state.bag.remaining()
    lines.append(f"Tiles in bag: {remaining}")

    # Turn info
    if state.game_over:
        if state.winner is not None:
            lines.append(f"{BOLD}Game Over! Player {state.winner + 1} wins!{RESET}")
        else:
            lines.append(f"{BOLD}Game Over! It's a tie!{RESET}")
    else:
        lines.append(f"Turn {state.turn_number}: Player {state.current_player + 1}'s turn")

    # Qwirkle counts if any
    if any(state.qwirkle_counts):
        q_str = f"Qwirkles: P1={state.qwirkle_counts[0]}, P2={state.qwirkle_counts[1]}"
        lines.append(q_str)

    return "\n".join(lines) + "\n"


def render_game(
    state: GameState,
    last_move_positions: Optional[List[Position]] = None,
    message: Optional[str] = None
) -> str:
    """Render the complete game view.

    Args:
        state: Current game state.
        last_move_positions: Positions from last move to highlight.
        message: Optional message to display.

    Returns:
        Complete game display string.
    """
    output = []

    # Header
    output.append("=" * 50)
    output.append(f"{BOLD}QWIRKLE{RESET}")
    output.append("=" * 50)
    output.append("")

    # Status
    output.append(render_status(state))

    # Board
    output.append(render_board(state.board, last_move_positions))

    # Hands
    for i, hand in enumerate(state.hands):
        is_current = (i == state.current_player) and not state.game_over
        output.append(render_hand(hand, i, is_current))

    # Message
    if message:
        output.append(f"\n{message}\n")

    # Help hint
    if not state.game_over:
        output.append(f"{DIM}Commands: play <tiles> <positions>, swap <tiles>, undo, hint, prob, quit{RESET}")
        output.append(f"{DIM}Example: play 1 0,0  or  play 1,2 0,0 0,1{RESET}")

    return "\n".join(output)


def clear_screen() -> str:
    """Return ANSI escape code to clear screen."""
    return "\033[2J\033[H"
