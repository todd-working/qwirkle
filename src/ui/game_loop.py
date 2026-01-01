"""Main game loop for Qwirkle terminal UI.

Handles the play-render-input cycle with undo support and AI players.
"""

import sys
import time
from typing import List, Optional, Tuple

from src.models.board import Position
from src.models.tile import Tile
from src.engine.game import (
    GameState,
    new_game,
    apply_move,
    apply_swap,
)
from src.ui.terminal import render_game, render_tile, clear_screen
from src.ui.input import (
    parse_command,
    get_help_text,
    PlayCommand,
    SwapCommand,
    QuitCommand,
    UndoCommand,
    HintCommand,
    HelpCommand,
    ProbCommand,
)
from src.ai.solver import get_hint, GreedySolver, RandomSolver
from src.sim.win_prob import estimate_win_probability, format_win_probability


class GameSession:
    """Manages a game session with undo history.

    Attributes:
        state: Current game state.
        history: Stack of previous states for undo.
        last_move_positions: Positions from last move (for highlighting).
        message: Status message to display.
    """

    MAX_UNDO_HISTORY = 50

    def __init__(
        self,
        seed: Optional[int] = None,
        ai_player: Optional[int] = None,
        ai_strategy: str = "greedy",
        ai_vs_ai: bool = False,
        ai_strategy_p2: Optional[str] = None
    ):
        """Initialize a new game session.

        Args:
            seed: Optional RNG seed for reproducibility.
            ai_player: Player index for AI (0 or 1), or None for human vs human.
            ai_strategy: "greedy" or "random" for AI player(s).
            ai_vs_ai: If True, both players are AI.
            ai_strategy_p2: Strategy for player 2 in AI vs AI mode (defaults to ai_strategy).
        """
        self.state = new_game(seed)
        self.history: List[GameState] = []
        self.last_move_positions: List[Position] = []
        self.message: str = "Welcome to Qwirkle! Player 1 goes first."

        # AI setup
        self.ai_player = ai_player
        self.ai_vs_ai = ai_vs_ai

        # Create solvers
        if ai_strategy == "random":
            self.ai_solver = RandomSolver(seed)
        else:
            self.ai_solver = GreedySolver()

        # Second solver for AI vs AI mode
        p2_strategy = ai_strategy_p2 or ai_strategy
        if p2_strategy == "random":
            self.ai_solver_p2 = RandomSolver((seed + 1) if seed else None)
        else:
            self.ai_solver_p2 = GreedySolver()

    def _save_state(self) -> None:
        """Save current state to history for undo."""
        if len(self.history) >= self.MAX_UNDO_HISTORY:
            self.history.pop(0)
        self.history.append(self.state.clone())

    def play_tiles(self, placements: List[Tuple[int, Position]]) -> bool:
        """Execute a play command.

        Args:
            placements: List of (tile_index, position) pairs.
                tile_index is 1-based.

        Returns:
            True if move was successful.
        """
        hand = self.state.hands[self.state.current_player]
        tiles = hand.tiles()

        # Convert 1-based indices to tiles
        try:
            tile_placements = []
            for idx, pos in placements:
                if idx < 1 or idx > len(tiles):
                    self.message = f"Invalid tile index: {idx}. Hand has {len(tiles)} tiles."
                    return False
                tile_placements.append((pos, tiles[idx - 1]))
        except IndexError:
            self.message = "Invalid tile index"
            return False

        # Save state for undo
        self._save_state()

        # Apply the move
        success, error, points = apply_move(self.state, tile_placements)

        if success:
            self.last_move_positions = [p for p, _ in tile_placements]
            if points > 0:
                self.message = f"Scored {points} points!"
                if self.state.game_over:
                    self._announce_winner()
            else:
                self.message = ""
            return True
        else:
            # Restore state on failure
            self.history.pop()
            self.message = f"Invalid move: {error}"
            return False

    def swap_tiles(self, tile_indices: List[int]) -> bool:
        """Execute a swap command.

        Args:
            tile_indices: 1-based indices of tiles to swap.

        Returns:
            True if swap was successful.
        """
        hand = self.state.hands[self.state.current_player]
        tiles = hand.tiles()

        # Convert indices to tiles
        try:
            tiles_to_swap = []
            for idx in tile_indices:
                if idx < 1 or idx > len(tiles):
                    self.message = f"Invalid tile index: {idx}"
                    return False
                tiles_to_swap.append(tiles[idx - 1])
        except IndexError:
            self.message = "Invalid tile index"
            return False

        # Save state for undo
        self._save_state()

        # Apply the swap
        success, error = apply_swap(self.state, tiles_to_swap)

        if success:
            self.last_move_positions = []
            self.message = f"Swapped {len(tiles_to_swap)} tile(s)"
            return True
        else:
            self.history.pop()
            self.message = f"Cannot swap: {error}"
            return False

    def undo(self) -> bool:
        """Undo the last move.

        Returns:
            True if undo was successful.
        """
        if not self.history:
            self.message = "Nothing to undo"
            return False

        self.state = self.history.pop()
        self.last_move_positions = []
        self.message = "Move undone"
        return True

    def _announce_winner(self) -> None:
        """Set message for game over."""
        if self.state.winner is not None:
            self.message = f"Game Over! Player {self.state.winner + 1} wins with {self.state.scores[self.state.winner]} points!"
        else:
            self.message = f"Game Over! It's a tie at {self.state.scores[0]} points!"

    def get_hint_message(self) -> str:
        """Get a hint for the current player.

        Returns:
            String describing the recommended move.
        """
        move = get_hint(self.state)
        if move is None:
            return "No valid moves available. Try swapping tiles."

        # Format the hint
        placements_str = []
        hand = self.state.hands[self.state.current_player].tiles()
        for pos, tile in move.placements:
            # Find tile index in hand
            try:
                idx = hand.index(tile) + 1
                tile_str = render_tile(tile)
                placements_str.append(f"tile {idx} ({tile_str}) at {pos}")
            except ValueError:
                placements_str.append(f"{tile} at {pos}")

        return f"Hint: Play {', '.join(placements_str)} for {move.score} points"

    def get_win_probability_message(self, n_simulations: int = 50) -> str:
        """Estimate win probability using Monte Carlo simulation.

        Args:
            n_simulations: Number of simulations to run.

        Returns:
            Formatted win probability string.
        """
        if self.state.game_over:
            return "Game is already over."

        prob = estimate_win_probability(
            self.state,
            viewer=self.state.current_player,
            n_simulations=n_simulations,
            solver_type="greedy"
        )
        return format_win_probability(prob, self.state.current_player)

    def is_ai_turn(self) -> bool:
        """Check if it's the AI's turn.

        Returns:
            True if current player is AI.
        """
        if self.ai_vs_ai:
            return True
        return self.ai_player is not None and self.state.current_player == self.ai_player

    def play_ai_turn(self) -> bool:
        """Execute the AI's turn.

        Returns:
            True if AI made a move successfully.
        """
        if not self.is_ai_turn():
            return False

        # Select the appropriate solver for AI vs AI mode
        if self.ai_vs_ai:
            solver = self.ai_solver if self.state.current_player == 0 else self.ai_solver_p2
        else:
            solver = self.ai_solver

        move = solver.get_move(self.state)

        if move is None:
            # AI has no valid moves - try to swap
            hand = self.state.hands[self.state.current_player]
            if not self.state.bag.is_empty() and len(hand) > 0:
                # Swap first tile
                self._save_state()
                success, error = apply_swap(self.state, [hand.tiles()[0]])
                if success:
                    self.last_move_positions = []
                    self.message = f"AI swapped a tile"
                    return True
            self.message = "AI has no valid moves"
            return False

        # Save state and apply move
        self._save_state()
        success, error, points = apply_move(self.state, move.placements)

        if success:
            self.last_move_positions = [p for p, _ in move.placements]
            self.message = f"AI scored {points} points!"
            if self.state.game_over:
                self._announce_winner()
            return True
        else:
            self.history.pop()
            self.message = f"AI move failed: {error}"
            return False

    def render(self) -> str:
        """Render the current game view.

        Returns:
            String to display.
        """
        return render_game(self.state, self.last_move_positions, self.message)


def run_game(
    seed: Optional[int] = None,
    clear: bool = True,
    ai_player: Optional[int] = None,
    ai_strategy: str = "greedy",
    ai_vs_ai: bool = False,
    ai_strategy_p2: Optional[str] = None,
    delay: float = 0.5
) -> None:
    """Run the main game loop.

    Args:
        seed: Optional RNG seed.
        clear: Whether to clear screen between turns.
        ai_player: Player index for AI (0 or 1), or None for human vs human.
        ai_strategy: "greedy" or "random".
        ai_vs_ai: If True, both players are AI.
        ai_strategy_p2: Strategy for player 2 in AI vs AI mode.
        delay: Delay between AI moves in seconds (for watching).
    """
    session = GameSession(seed, ai_player, ai_strategy, ai_vs_ai, ai_strategy_p2)

    while True:
        # Render
        if clear:
            print(clear_screen(), end="")
        print(session.render())

        # Check if game over
        if session.state.game_over:
            print("\nThanks for playing!")
            break

        # Handle AI turn
        if session.is_ai_turn():
            if ai_vs_ai:
                player = session.state.current_player + 1
                print(f"\nPlayer {player} (AI) is thinking...")
            else:
                print("\nAI is thinking...")
            time.sleep(delay)
            session.play_ai_turn()
            continue

        # Get human input
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        # Parse and execute
        cmd, error = parse_command(user_input)

        if error:
            session.message = error
            continue

        if isinstance(cmd, QuitCommand):
            print("\nGoodbye!")
            break

        elif isinstance(cmd, HelpCommand):
            print(get_help_text())
            input("Press Enter to continue...")

        elif isinstance(cmd, UndoCommand):
            session.undo()

        elif isinstance(cmd, HintCommand):
            session.message = session.get_hint_message()

        elif isinstance(cmd, ProbCommand):
            print("\nCalculating win probability...")
            session.message = session.get_win_probability_message(cmd.n_simulations)

        elif isinstance(cmd, PlayCommand):
            session.play_tiles(cmd.placements)

        elif isinstance(cmd, SwapCommand):
            session.swap_tiles(cmd.tile_indices)


def main() -> None:
    """Entry point for the game."""
    import argparse

    parser = argparse.ArgumentParser(description="Play Qwirkle in the terminal")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear screen between turns")
    parser.add_argument("--vs-ai", action="store_true", help="Play against AI (you are Player 1)")
    parser.add_argument("--ai-first", action="store_true", help="AI plays as Player 1 (you are Player 2)")
    parser.add_argument("--ai-vs-ai", action="store_true", help="Watch AI vs AI game")
    parser.add_argument("--ai-strategy", choices=["greedy", "random"], default="greedy",
                        help="AI strategy for Player 1 (default: greedy)")
    parser.add_argument("--ai-strategy-p2", choices=["greedy", "random"],
                        help="AI strategy for Player 2 in AI vs AI mode (default: same as --ai-strategy)")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Delay between AI moves in seconds (default: 0.5)")

    args = parser.parse_args()

    # Determine AI player
    ai_player = None
    ai_vs_ai = args.ai_vs_ai
    if args.vs_ai:
        ai_player = 1  # AI is Player 2
    elif args.ai_first:
        ai_player = 0  # AI is Player 1

    run_game(
        seed=args.seed,
        clear=not args.no_clear,
        ai_player=ai_player,
        ai_strategy=args.ai_strategy,
        ai_vs_ai=ai_vs_ai,
        ai_strategy_p2=args.ai_strategy_p2,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
