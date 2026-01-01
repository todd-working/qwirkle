"""Game recorder for ML training data generation.

Records complete game trajectories with state/action/reward for training.
"""

import json
import pickle
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from src.models.tile import Tile, Color, Shape
from src.models.board import Board, Position
from src.models.hand import Hand
from src.engine.game import GameState, new_game, apply_move, apply_swap
from src.ai.solver import GreedySolver, RandomSolver, Solver
import random as stdlib_random
from src.ai.move_gen import Move, generate_all_moves


class EpsilonGreedySolver(Solver):
    """Wrapper that adds exploration noise to any solver.

    With probability epsilon, picks a random move instead of the base solver's choice.
    """

    def __init__(self, base_solver: Solver, epsilon: float, seed: Optional[int] = None):
        self.base = base_solver
        self.epsilon = epsilon
        self._rng = stdlib_random.Random(seed)

    def select_move(self, state: GameState, moves: Optional[List[Move]] = None) -> Optional[Move]:
        if moves is None:
            hand = state.hands[state.current_player]
            is_first = state.board.is_board_empty()
            moves = generate_all_moves(state.board, hand, is_first)

        if not moves:
            return None

        # Epsilon chance of random move
        if self._rng.random() < self.epsilon:
            return self._rng.choice(moves)

        return self.base.select_move(state, moves)

    def get_move(self, state: GameState) -> Optional[Move]:
        hand = state.hands[state.current_player]
        is_first = state.board.is_board_empty()
        moves = generate_all_moves(state.board, hand, is_first)
        return self.select_move(state, moves)


@dataclass
class StateSnapshot:
    """Snapshot of game state for ML training.

    Attributes:
        turn: Turn number.
        player: Current player (0 or 1).
        board: Board as dict of {(row,col): (shape_idx, color_idx)}.
        hand: Current player's hand as list of (shape_idx, color_idx).
        scores: [player0_score, player1_score].
        bag_remaining: Number of tiles left in bag.
    """
    turn: int
    player: int
    board: Dict[str, Tuple[int, int]]  # "(row,col)" -> (shape, color)
    hand: List[Tuple[int, int]]  # [(shape, color), ...]
    scores: List[int]
    bag_remaining: int


@dataclass
class ActionRecord:
    """Record of action taken.

    Attributes:
        action_type: "play" or "swap".
        placements: For play: list of ((row,col), (shape,color)).
        tiles_swapped: For swap: number of tiles swapped.
        score: Points earned (0 for swap).
        qwirkles: Number of qwirkles made.
    """
    action_type: str
    placements: List[Tuple[Tuple[int, int], Tuple[int, int]]] = field(default_factory=list)
    tiles_swapped: int = 0
    score: int = 0
    qwirkles: int = 0


@dataclass
class Transition:
    """Single state transition for training."""
    state: StateSnapshot
    action: ActionRecord
    reward: float  # Normalized score or win signal


@dataclass
class GameTrajectory:
    """Complete game trajectory for training.

    Attributes:
        seed: Random seed used.
        transitions: List of state transitions.
        winner: Winning player (0, 1, or None for tie).
        final_scores: Final scores [p0, p1].
        p0_strategy: Strategy used by player 0.
        p1_strategy: Strategy used by player 1.
    """
    seed: int
    transitions: List[Transition]
    winner: Optional[int]
    final_scores: List[int]
    p0_strategy: str
    p1_strategy: str


def _tile_to_indices(tile: Tile) -> Tuple[int, int]:
    """Convert tile to (shape_index, color_index)."""
    shapes = list(Shape)
    colors = list(Color)
    return (shapes.index(tile.shape), colors.index(tile.color))


def _board_to_dict(board: Board) -> Dict[str, Tuple[int, int]]:
    """Convert board to serializable dict."""
    result = {}
    for pos, tile in board.all_tiles():
        key = f"{pos[0]},{pos[1]}"
        result[key] = _tile_to_indices(tile)
    return result


def _hand_to_list(hand: Hand) -> List[Tuple[int, int]]:
    """Convert hand to list of tile indices."""
    return [_tile_to_indices(t) for t in hand.tiles()]


def _snapshot_state(state: GameState) -> StateSnapshot:
    """Create a snapshot of current game state."""
    return StateSnapshot(
        turn=state.turn_number,
        player=state.current_player,
        board=_board_to_dict(state.board),
        hand=_hand_to_list(state.hands[state.current_player]),
        scores=state.scores.copy(),
        bag_remaining=state.bag.remaining()
    )


def _get_strategy_name(solver: Solver) -> str:
    """Get the base strategy name of a solver."""
    if isinstance(solver, EpsilonGreedySolver):
        return _get_strategy_name(solver.base)
    if isinstance(solver, GreedySolver):
        return "greedy"
    return "random"


def record_game(
    seed: int,
    solver0: Optional[Solver] = None,
    solver1: Optional[Solver] = None,
    max_turns: int = 200
) -> GameTrajectory:
    """Play and record a complete game.

    Args:
        seed: Random seed for reproducibility.
        solver0: Solver for player 0 (default: GreedySolver).
        solver1: Solver for player 1 (default: GreedySolver).
        max_turns: Maximum turns before forcing end.

    Returns:
        GameTrajectory with all state transitions.
    """
    if solver0 is None:
        solver0 = GreedySolver()
    if solver1 is None:
        solver1 = GreedySolver()

    solvers = [solver0, solver1]
    state = new_game(seed)
    transitions: List[Transition] = []

    # Determine strategy names
    p0_strategy = _get_strategy_name(solver0)
    p1_strategy = _get_strategy_name(solver1)

    while not state.game_over and state.turn_number <= max_turns:
        current = state.current_player
        solver = solvers[current]

        # Snapshot state before action
        snapshot = _snapshot_state(state)

        # Get and apply move
        move = solver.get_move(state)

        if move is not None:
            # Record action
            placements = [
                ((pos[0], pos[1]), _tile_to_indices(tile))
                for pos, tile in move.placements
            ]
            action = ActionRecord(
                action_type="play",
                placements=placements,
                score=move.score,
                qwirkles=move.qwirkles
            )

            # Apply move
            success, _, points = apply_move(state, move.placements)
            reward = points / 12.0  # Normalize by max single-tile score (qwirkle)

        else:
            # No valid moves - swap
            hand = state.hands[current]
            if not state.bag.is_empty() and len(hand) > 0:
                apply_swap(state, [hand.tiles()[0]])
                action = ActionRecord(action_type="swap", tiles_swapped=1)
                reward = -0.1  # Small penalty for swapping
            else:
                state.game_over = True
                action = ActionRecord(action_type="pass")
                reward = 0.0

        transitions.append(Transition(
            state=snapshot,
            action=action,
            reward=reward
        ))

    # Add terminal reward based on game outcome
    if transitions:
        for i, trans in enumerate(transitions):
            player = trans.state.player
            if state.winner == player:
                # Won - add bonus to final transitions
                if i >= len(transitions) - 10:
                    transitions[i].reward += 1.0
            elif state.winner is not None and state.winner != player:
                # Lost - add penalty to final transitions
                if i >= len(transitions) - 10:
                    transitions[i].reward -= 0.5

    return GameTrajectory(
        seed=seed,
        transitions=transitions,
        winner=state.winner,
        final_scores=state.scores.copy(),
        p0_strategy=p0_strategy,
        p1_strategy=p1_strategy
    )


def _make_solver(solver_type: str, seed: int, epsilon: float = 0.0) -> Solver:
    """Create a solver with optional exploration noise."""
    if solver_type == "greedy":
        base = GreedySolver()
    else:
        base = RandomSolver(seed)

    if epsilon > 0:
        return EpsilonGreedySolver(base, epsilon, seed)
    return base


def _record_single_worker(args: Tuple) -> GameTrajectory:
    """Worker function for parallel recording."""
    seed, s0_type, s1_type, epsilon = args
    s0 = _make_solver(s0_type, seed, epsilon)
    s1 = _make_solver(s1_type, seed + 1, epsilon)
    return record_game(seed, s0, s1)


def record_batch(
    n_games: int,
    base_seed: int = 0,
    solver0_type: str = "greedy",
    solver1_type: str = "greedy",
    parallel: bool = True,
    max_workers: Optional[int] = None,
    epsilon: float = 0.0,
    mix_strategies: bool = False
) -> List[GameTrajectory]:
    """Record multiple games.

    Args:
        n_games: Number of games to record.
        base_seed: Starting seed (each game uses base_seed + i).
        solver0_type: "greedy" or "random" (ignored if mix_strategies=True).
        solver1_type: "greedy" or "random" (ignored if mix_strategies=True).
        parallel: Whether to run in parallel.
        max_workers: Max parallel workers.
        epsilon: Exploration rate (0-1). With this probability, pick random move.
        mix_strategies: If True, randomly vary strategies each game:
            - 25% greedy vs greedy
            - 25% greedy vs random
            - 25% random vs greedy
            - 25% random vs random

    Returns:
        List of GameTrajectory objects.
    """
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing

    args_list = []
    strategy_combos = [
        ("greedy", "greedy"),
        ("greedy", "random"),
        ("random", "greedy"),
        ("random", "random"),
    ]

    for i in range(n_games):
        seed = base_seed + i

        if mix_strategies:
            # Cycle through strategy combinations evenly
            s0_type, s1_type = strategy_combos[i % 4]
        else:
            s0_type = solver0_type
            s1_type = solver1_type

        args_list.append((seed, s0_type, s1_type, epsilon))

    if parallel and n_games > 1:
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), n_games)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_record_single_worker, args_list))
        return results
    else:
        return [_record_single_worker(args) for args in args_list]


def save_trajectories(
    trajectories: List[GameTrajectory],
    filepath: str,
    format: str = "pickle"
) -> None:
    """Save trajectories to file.

    Args:
        trajectories: List of game trajectories.
        filepath: Output file path.
        format: "pickle" or "json".
    """
    path = Path(filepath)

    if format == "pickle":
        with open(path, 'wb') as f:
            pickle.dump(trajectories, f)
    elif format == "json":
        # Convert to JSON-serializable format
        data = []
        for traj in trajectories:
            traj_dict = {
                'seed': traj.seed,
                'winner': traj.winner,
                'final_scores': traj.final_scores,
                'p0_strategy': traj.p0_strategy,
                'p1_strategy': traj.p1_strategy,
                'transitions': []
            }
            for trans in traj.transitions:
                traj_dict['transitions'].append({
                    'state': asdict(trans.state),
                    'action': asdict(trans.action),
                    'reward': trans.reward
                })
            data.append(traj_dict)

        with open(path, 'w') as f:
            json.dump(data, f)
    else:
        raise ValueError(f"Unknown format: {format}")


def load_trajectories(filepath: str, format: str = "pickle") -> List[GameTrajectory]:
    """Load trajectories from file.

    Args:
        filepath: Input file path.
        format: "pickle" or "json".

    Returns:
        List of GameTrajectory objects.
    """
    path = Path(filepath)

    if format == "pickle":
        with open(path, 'rb') as f:
            return pickle.load(f)
    elif format == "json":
        with open(path, 'r') as f:
            data = json.load(f)

        trajectories = []
        for traj_dict in data:
            transitions = []
            for trans_dict in traj_dict['transitions']:
                state = StateSnapshot(**trans_dict['state'])
                action = ActionRecord(**trans_dict['action'])
                transitions.append(Transition(
                    state=state,
                    action=action,
                    reward=trans_dict['reward']
                ))
            trajectories.append(GameTrajectory(
                seed=traj_dict['seed'],
                transitions=transitions,
                winner=traj_dict['winner'],
                final_scores=traj_dict['final_scores'],
                p0_strategy=traj_dict['p0_strategy'],
                p1_strategy=traj_dict['p1_strategy']
            ))
        return trajectories
    else:
        raise ValueError(f"Unknown format: {format}")


def trajectories_to_numpy(trajectories: List[GameTrajectory]):
    """Convert trajectories to numpy arrays for training.

    Returns:
        Dict with:
        - 'boards': (N, 21, 21, 2) - board states (shape, color channels)
        - 'hands': (N, 6, 2) - hand tiles
        - 'meta': (N, 4) - [turn, player, score0, score1]
        - 'actions': (N,) - action indices or embeddings
        - 'rewards': (N,) - reward values
        - 'players': (N,) - which player took action
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("numpy required for trajectories_to_numpy")

    all_boards = []
    all_hands = []
    all_meta = []
    all_rewards = []
    all_players = []

    for traj in trajectories:
        for trans in traj.transitions:
            # Board: 21x21 grid centered at origin, 2 channels (shape, color)
            # Using -10 to 10 range
            board = np.zeros((21, 21, 2), dtype=np.int8)
            for pos_str, (shape_idx, color_idx) in trans.state.board.items():
                row, col = map(int, pos_str.split(','))
                # Offset to center at (10, 10)
                r, c = row + 10, col + 10
                if 0 <= r < 21 and 0 <= c < 21:
                    board[r, c, 0] = shape_idx + 1  # +1 so 0 = empty
                    board[r, c, 1] = color_idx + 1
            all_boards.append(board)

            # Hand: up to 6 tiles, each with (shape, color)
            hand = np.zeros((6, 2), dtype=np.int8)
            for i, (shape_idx, color_idx) in enumerate(trans.state.hand[:6]):
                hand[i, 0] = shape_idx + 1
                hand[i, 1] = color_idx + 1
            all_hands.append(hand)

            # Meta: turn, player, scores
            meta = np.array([
                trans.state.turn,
                trans.state.player,
                trans.state.scores[0],
                trans.state.scores[1]
            ], dtype=np.int16)
            all_meta.append(meta)

            all_rewards.append(trans.reward)
            all_players.append(trans.state.player)

    return {
        'boards': np.array(all_boards),
        'hands': np.array(all_hands),
        'meta': np.array(all_meta),
        'rewards': np.array(all_rewards, dtype=np.float32),
        'players': np.array(all_players, dtype=np.int8)
    }
