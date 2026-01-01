"""Statistics collection and aggregation for simulations.

Collects game results and computes aggregate statistics.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from statistics import mean, stdev, median
from collections import Counter

from src.sim.runner import GameResult


@dataclass
class AggregateStats:
    """Aggregated statistics from multiple games.

    Attributes:
        n_games: Number of games played.
        p0_wins: Player 0 win count.
        p1_wins: Player 1 win count.
        ties: Number of ties.
        p0_win_rate: Player 0 win percentage.
        p1_win_rate: Player 1 win percentage.
        avg_score_p0: Average final score for player 0.
        avg_score_p1: Average final score for player 1.
        avg_turns: Average number of turns per game.
        avg_qwirkles_p0: Average Qwirkles for player 0.
        avg_qwirkles_p1: Average Qwirkles for player 1.
        max_score: Highest final score achieved.
        max_turn_score: Highest single-turn score.
        score_std_p0: Standard deviation of player 0 scores.
        score_std_p1: Standard deviation of player 1 scores.
    """
    n_games: int = 0
    p0_wins: int = 0
    p1_wins: int = 0
    ties: int = 0
    p0_win_rate: float = 0.0
    p1_win_rate: float = 0.0
    avg_score_p0: float = 0.0
    avg_score_p1: float = 0.0
    avg_turns: float = 0.0
    avg_qwirkles_p0: float = 0.0
    avg_qwirkles_p1: float = 0.0
    max_score: int = 0
    max_turn_score: int = 0
    score_std_p0: float = 0.0
    score_std_p1: float = 0.0
    median_score_p0: float = 0.0
    median_score_p1: float = 0.0


def compute_stats(results: List[GameResult]) -> AggregateStats:
    """Compute aggregate statistics from game results.

    Args:
        results: List of GameResult objects.

    Returns:
        AggregateStats with computed values.
    """
    if not results:
        return AggregateStats()

    n = len(results)

    # Win counts
    p0_wins = sum(1 for r in results if r.winner == 0)
    p1_wins = sum(1 for r in results if r.winner == 1)
    ties = sum(1 for r in results if r.winner is None)

    # Scores
    scores_p0 = [r.scores[0] for r in results]
    scores_p1 = [r.scores[1] for r in results]

    # Turns
    turns = [r.turns for r in results]

    # Qwirkles
    qwirkles_p0 = [r.qwirkles[0] for r in results]
    qwirkles_p1 = [r.qwirkles[1] for r in results]

    # Max scores
    max_score = max(max(r.scores) for r in results)
    max_turn = max(r.max_turn_score for r in results)

    return AggregateStats(
        n_games=n,
        p0_wins=p0_wins,
        p1_wins=p1_wins,
        ties=ties,
        p0_win_rate=p0_wins / n * 100,
        p1_win_rate=p1_wins / n * 100,
        avg_score_p0=mean(scores_p0),
        avg_score_p1=mean(scores_p1),
        avg_turns=mean(turns),
        avg_qwirkles_p0=mean(qwirkles_p0),
        avg_qwirkles_p1=mean(qwirkles_p1),
        max_score=max_score,
        max_turn_score=max_turn,
        score_std_p0=stdev(scores_p0) if n > 1 else 0.0,
        score_std_p1=stdev(scores_p1) if n > 1 else 0.0,
        median_score_p0=median(scores_p0),
        median_score_p1=median(scores_p1),
    )


def format_stats(stats: AggregateStats) -> str:
    """Format statistics for display.

    Args:
        stats: AggregateStats object.

    Returns:
        Formatted string.
    """
    lines = [
        f"Games Played: {stats.n_games}",
        "",
        "Win Rates:",
        f"  Player 1: {stats.p0_win_rate:.1f}% ({stats.p0_wins} wins)",
        f"  Player 2: {stats.p1_win_rate:.1f}% ({stats.p1_wins} wins)",
        f"  Ties: {stats.ties}",
        "",
        "Scores:",
        f"  Player 1: {stats.avg_score_p0:.1f} avg (±{stats.score_std_p0:.1f}), median {stats.median_score_p0:.0f}",
        f"  Player 2: {stats.avg_score_p1:.1f} avg (±{stats.score_std_p1:.1f}), median {stats.median_score_p1:.0f}",
        f"  Max Score: {stats.max_score}",
        f"  Max Turn Score: {stats.max_turn_score}",
        "",
        "Game Length:",
        f"  Average Turns: {stats.avg_turns:.1f}",
        "",
        "Qwirkles:",
        f"  Player 1: {stats.avg_qwirkles_p0:.2f} avg per game",
        f"  Player 2: {stats.avg_qwirkles_p1:.2f} avg per game",
    ]
    return "\n".join(lines)


def score_distribution(results: List[GameResult]) -> Dict[str, Counter]:
    """Get score distribution for analysis.

    Args:
        results: List of GameResult objects.

    Returns:
        Dict with 'p0' and 'p1' Counters of score ranges.
    """
    def bucket(score: int) -> str:
        """Put score into 10-point buckets."""
        bucket_start = (score // 10) * 10
        return f"{bucket_start}-{bucket_start + 9}"

    p0_dist = Counter(bucket(r.scores[0]) for r in results)
    p1_dist = Counter(bucket(r.scores[1]) for r in results)

    return {"p0": p0_dist, "p1": p1_dist}
