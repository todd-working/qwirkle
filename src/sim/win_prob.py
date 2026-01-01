"""Win probability estimation using Monte Carlo simulation.

Estimates the probability of each player winning from a given game state.
"""

from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor
import random

from src.models.tile import Tile, Color, Shape
from src.models.hand import Hand
from src.models.bag import Bag
from src.engine.game import GameState, apply_move, apply_swap
from src.ai.solver import GreedySolver, RandomSolver, Solver


@dataclass
class WinProbability:
    """Win probability estimate for each player.

    Attributes:
        p0_prob: Probability player 0 wins (0.0 to 1.0).
        p1_prob: Probability player 1 wins (0.0 to 1.0).
        tie_prob: Probability of tie.
        n_simulations: Number of simulations run.
        confidence: Rough confidence estimate (based on sample size).
    """
    p0_prob: float
    p1_prob: float
    tie_prob: float
    n_simulations: int
    confidence: float = 0.0

    def __post_init__(self):
        # Confidence based on standard error of proportion
        # For p close to 0.5, SE = sqrt(0.25/n)
        if self.n_simulations > 0:
            self.confidence = min(0.99, 1.0 - (0.5 / (self.n_simulations ** 0.5)))


def get_unseen_tiles(state: GameState, viewer: int) -> List[Tile]:
    """Get all tiles not visible to a player.

    The viewer knows:
    - Their own hand
    - All tiles on the board

    They don't know:
    - Opponent's hand
    - Tiles remaining in bag

    Args:
        state: Current game state.
        viewer: Index of the viewing player (0 or 1).

    Returns:
        List of tiles the viewer cannot see (opponent's hand + bag).
    """
    # Start with all 108 tiles
    all_tiles: List[Tile] = []
    for shape in Shape:
        for color in Color:
            for _ in range(3):  # 3 copies of each
                all_tiles.append(Tile(shape, color))

    # Remove tiles on board
    for _, tile in state.board.all_tiles():
        all_tiles.remove(tile)

    # Remove viewer's hand
    for tile in state.hands[viewer].tiles():
        all_tiles.remove(tile)

    return all_tiles


def _simulate_game(
    state: GameState,
    unseen: List[Tile],
    current_player: int,
    solver: Solver,
    rng: random.Random,
    max_turns: int = 100
) -> Optional[int]:
    """Simulate a game to completion from current state.

    Args:
        state: Cloned game state to simulate from.
        unseen: Unseen tiles to distribute.
        current_player: Who is simulating (knows their hand).
        solver: Solver to use for both players.
        rng: Random number generator.
        max_turns: Maximum additional turns.

    Returns:
        Winner index (0 or 1), or None for tie.
    """
    # Shuffle unseen tiles
    shuffled = unseen.copy()
    rng.shuffle(shuffled)

    # Deal opponent's hand from unseen
    opponent = 1 - current_player
    opponent_hand_size = len(state.hands[opponent])

    # Replace opponent's hand with random unseen tiles
    new_opponent_hand = shuffled[:opponent_hand_size]
    shuffled = shuffled[opponent_hand_size:]

    # Replace bag with remaining unseen tiles
    state.hands[opponent] = Hand(new_opponent_hand)

    # Create new bag with remaining tiles
    new_bag = Bag.__new__(Bag)
    new_bag._tiles = shuffled
    new_bag._rng = rng
    state.bag = new_bag

    # Play out the game
    turns = 0
    while not state.game_over and turns < max_turns:
        turns += 1
        move = solver.get_move(state)

        if move is not None:
            success, _, _ = apply_move(state, move.placements)
            if not success:
                # Fallback: swap if possible
                hand = state.hands[state.current_player]
                if not state.bag.is_empty() and len(hand) > 0:
                    apply_swap(state, [hand.tiles()[0]])
                else:
                    break
        else:
            # No valid moves
            hand = state.hands[state.current_player]
            if not state.bag.is_empty() and len(hand) > 0:
                apply_swap(state, [hand.tiles()[0]])
            else:
                state.game_over = True
                break

    # Determine winner
    if state.scores[0] > state.scores[1]:
        return 0
    elif state.scores[1] > state.scores[0]:
        return 1
    return None


def estimate_win_probability(
    state: GameState,
    viewer: int,
    n_simulations: int = 100,
    solver_type: str = "greedy",
    seed: Optional[int] = None
) -> WinProbability:
    """Estimate win probability using Monte Carlo simulation.

    Runs multiple simulations from the current state, randomizing
    the unknown information (opponent's hand and bag contents).

    Args:
        state: Current game state.
        viewer: Index of the viewing player (whose perspective).
        n_simulations: Number of simulations to run.
        solver_type: "greedy" or "random" for simulation.
        seed: Random seed for reproducibility.

    Returns:
        WinProbability with estimates.
    """
    if state.game_over:
        # Game already over
        if state.winner == 0:
            return WinProbability(1.0, 0.0, 0.0, 1)
        elif state.winner == 1:
            return WinProbability(0.0, 1.0, 0.0, 1)
        else:
            return WinProbability(0.0, 0.0, 1.0, 1)

    rng = random.Random(seed)
    unseen = get_unseen_tiles(state, viewer)

    # Create solver
    if solver_type == "greedy":
        solver = GreedySolver()
    else:
        solver = RandomSolver(seed)

    # Run simulations
    p0_wins = 0
    p1_wins = 0
    ties = 0

    for i in range(n_simulations):
        # Clone state for this simulation
        sim_state = state.clone()
        sim_rng = random.Random(rng.randint(0, 2**31))

        winner = _simulate_game(sim_state, unseen, viewer, solver, sim_rng)

        if winner == 0:
            p0_wins += 1
        elif winner == 1:
            p1_wins += 1
        else:
            ties += 1

    return WinProbability(
        p0_prob=p0_wins / n_simulations,
        p1_prob=p1_wins / n_simulations,
        tie_prob=ties / n_simulations,
        n_simulations=n_simulations,
    )


def format_win_probability(prob: WinProbability, current_player: int) -> str:
    """Format win probability for display.

    Args:
        prob: WinProbability object.
        current_player: Current player (for highlighting).

    Returns:
        Formatted string.
    """
    p1_pct = prob.p0_prob * 100
    p2_pct = prob.p1_prob * 100

    marker0 = "→ " if current_player == 0 else "  "
    marker1 = "→ " if current_player == 1 else "  "

    return (
        f"Win Probability ({prob.n_simulations} sims):\n"
        f"{marker0}Player 1: {p1_pct:.1f}%\n"
        f"{marker1}Player 2: {p2_pct:.1f}%"
    )
