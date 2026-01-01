"""AI solvers for Qwirkle.

Provides different strategies for selecting moves.
"""

import random
from abc import ABC, abstractmethod
from typing import Optional, List

from src.models.board import Board
from src.models.hand import Hand
from src.engine.game import GameState
from src.ai.move_gen import Move, generate_all_moves


class Solver(ABC):
    """Abstract base class for Qwirkle solvers."""

    @abstractmethod
    def select_move(
        self,
        state: GameState,
        moves: Optional[List[Move]] = None
    ) -> Optional[Move]:
        """Select a move to play.

        Args:
            state: Current game state.
            moves: Optional pre-computed list of valid moves.

        Returns:
            The selected Move, or None if no valid moves.
        """
        pass

    def get_move(self, state: GameState) -> Optional[Move]:
        """Convenience method to get a move for current player.

        Args:
            state: Current game state.

        Returns:
            The selected Move, or None if no valid moves.
        """
        hand = state.hands[state.current_player]
        is_first = state.board.is_board_empty()
        moves = generate_all_moves(state.board, hand, is_first)

        if not moves:
            return None

        return self.select_move(state, moves)


class GreedySolver(Solver):
    """Greedy solver that picks the highest-scoring move.

    Simple but effective strategy: always maximize immediate points.
    """

    def select_move(
        self,
        state: GameState,
        moves: Optional[List[Move]] = None
    ) -> Optional[Move]:
        """Select the highest-scoring move.

        Args:
            state: Current game state.
            moves: Optional pre-computed list of valid moves.

        Returns:
            The highest-scoring Move, or None if no valid moves.
        """
        if moves is None:
            hand = state.hands[state.current_player]
            is_first = state.board.is_board_empty()
            moves = generate_all_moves(state.board, hand, is_first)

        if not moves:
            return None

        # Moves are already sorted by score, return the first
        return moves[0]


class RandomSolver(Solver):
    """Random solver that picks a random valid move.

    Useful for Monte Carlo simulations and as a baseline.
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize with optional random seed.

        Args:
            seed: Random seed for reproducibility.
        """
        self._rng = random.Random(seed)

    def select_move(
        self,
        state: GameState,
        moves: Optional[List[Move]] = None
    ) -> Optional[Move]:
        """Select a random valid move.

        Args:
            state: Current game state.
            moves: Optional pre-computed list of valid moves.

        Returns:
            A random Move, or None if no valid moves.
        """
        if moves is None:
            hand = state.hands[state.current_player]
            is_first = state.board.is_board_empty()
            moves = generate_all_moves(state.board, hand, is_first)

        if not moves:
            return None

        return self._rng.choice(moves)


class WeightedRandomSolver(Solver):
    """Weighted random solver that favors higher-scoring moves.

    Probability of selecting a move is proportional to its score.
    Good for Monte Carlo simulations that need variety but
    still favor reasonable moves.
    """

    def __init__(self, seed: Optional[int] = None, temperature: float = 1.0):
        """Initialize with optional random seed and temperature.

        Args:
            seed: Random seed for reproducibility.
            temperature: Higher = more random, lower = more greedy.
        """
        self._rng = random.Random(seed)
        self._temperature = temperature

    def select_move(
        self,
        state: GameState,
        moves: Optional[List[Move]] = None
    ) -> Optional[Move]:
        """Select a move weighted by score.

        Args:
            state: Current game state.
            moves: Optional pre-computed list of valid moves.

        Returns:
            A weighted-random Move, or None if no valid moves.
        """
        if moves is None:
            hand = state.hands[state.current_player]
            is_first = state.board.is_board_empty()
            moves = generate_all_moves(state.board, hand, is_first)

        if not moves:
            return None

        if len(moves) == 1:
            return moves[0]

        # Calculate weights based on score
        # Add 1 to avoid zero weights
        weights = [(m.score + 1) ** (1 / self._temperature) for m in moves]
        total = sum(weights)
        probabilities = [w / total for w in weights]

        # Weighted random choice
        r = self._rng.random()
        cumulative = 0.0
        for move, prob in zip(moves, probabilities):
            cumulative += prob
            if r <= cumulative:
                return move

        return moves[-1]  # Fallback


# Convenience functions

def get_best_move(state: GameState) -> Optional[Move]:
    """Get the best (highest-scoring) move for current player.

    Args:
        state: Current game state.

    Returns:
        The best Move, or None if no valid moves.
    """
    solver = GreedySolver()
    return solver.get_move(state)


def get_random_move(
    state: GameState,
    seed: Optional[int] = None
) -> Optional[Move]:
    """Get a random valid move for current player.

    Args:
        state: Current game state.
        seed: Optional random seed.

    Returns:
        A random Move, or None if no valid moves.
    """
    solver = RandomSolver(seed)
    return solver.get_move(state)


def get_hint(state: GameState) -> Optional[Move]:
    """Get a hint (best move) for the current player.

    Alias for get_best_move, used by the UI.

    Args:
        state: Current game state.

    Returns:
        The recommended Move, or None if no valid moves.
    """
    return get_best_move(state)
