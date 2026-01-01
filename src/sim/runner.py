"""Game runner for simulations.

Runs games between AI players and collects results.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from src.engine.game import GameState, new_game, apply_move, apply_swap
from src.ai.solver import Solver, GreedySolver, RandomSolver


@dataclass
class GameResult:
    """Result of a single game.

    Attributes:
        winner: Winning player index (0 or 1), or None for tie.
        scores: Final scores [player0, player1].
        turns: Total number of turns played.
        qwirkles: Qwirkle counts [player0, player1].
        max_turn_score: Highest single-turn score achieved.
        max_turn_player: Player who achieved max turn score.
    """
    winner: Optional[int]
    scores: List[int]
    turns: int
    qwirkles: List[int]
    max_turn_score: int = 0
    max_turn_player: int = 0


def run_game(
    solver0: Optional[Solver] = None,
    solver1: Optional[Solver] = None,
    seed: Optional[int] = None,
    max_turns: int = 200
) -> GameResult:
    """Run a complete game between two AI players.

    Args:
        solver0: Solver for player 0 (default: GreedySolver).
        solver1: Solver for player 1 (default: GreedySolver).
        seed: Random seed for game initialization.
        max_turns: Maximum turns before forcing game end.

    Returns:
        GameResult with final stats.
    """
    if solver0 is None:
        solver0 = GreedySolver()
    if solver1 is None:
        solver1 = GreedySolver()

    solvers = [solver0, solver1]
    state = new_game(seed)

    max_turn_score = 0
    max_turn_player = 0

    while not state.game_over and state.turn_number <= max_turns:
        current = state.current_player
        solver = solvers[current]

        move = solver.get_move(state)

        if move is not None:
            success, _, points = apply_move(state, move.placements)
            if success and points > max_turn_score:
                max_turn_score = points
                max_turn_player = current
        else:
            # No valid moves - try to swap
            hand = state.hands[current]
            if not state.bag.is_empty() and len(hand) > 0:
                apply_swap(state, [hand.tiles()[0]])
            else:
                # Can't move or swap - force game end
                state.game_over = True
                break

    return GameResult(
        winner=state.winner,
        scores=state.scores.copy(),
        turns=state.turn_number,
        qwirkles=state.qwirkle_counts.copy(),
        max_turn_score=max_turn_score,
        max_turn_player=max_turn_player,
    )


def _run_game_worker(args: Tuple) -> GameResult:
    """Worker function for parallel game execution.

    Args:
        args: Tuple of (solver0_type, solver1_type, seed).

    Returns:
        GameResult.
    """
    solver0_type, solver1_type, seed = args

    # Recreate solvers in worker process
    if solver0_type == "greedy":
        solver0 = GreedySolver()
    else:
        solver0 = RandomSolver(seed)

    if solver1_type == "greedy":
        solver1 = GreedySolver()
    else:
        solver1 = RandomSolver(seed + 1 if seed else None)

    return run_game(solver0, solver1, seed)


def run_batch(
    n_games: int,
    solver0_type: str = "greedy",
    solver1_type: str = "greedy",
    base_seed: Optional[int] = None,
    parallel: bool = True,
    max_workers: Optional[int] = None
) -> List[GameResult]:
    """Run multiple games and collect results.

    Args:
        n_games: Number of games to run.
        solver0_type: "greedy" or "random" for player 0.
        solver1_type: "greedy" or "random" for player 1.
        base_seed: Base random seed (each game uses base_seed + i).
        parallel: Whether to run games in parallel.
        max_workers: Max parallel workers (default: CPU count).

    Returns:
        List of GameResult objects.
    """
    # Prepare arguments for each game
    args_list = []
    for i in range(n_games):
        seed = (base_seed + i) if base_seed is not None else None
        args_list.append((solver0_type, solver1_type, seed))

    if parallel and n_games > 1:
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), n_games)

        results = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_run_game_worker, args) for args in args_list]
            for future in as_completed(futures):
                results.append(future.result())
        return results
    else:
        # Sequential execution
        results = []
        for args in args_list:
            results.append(_run_game_worker(args))
        return results
