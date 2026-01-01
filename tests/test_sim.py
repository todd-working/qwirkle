"""Tests for simulation module."""

import pytest
from src.models.tile import Color, Shape, Tile
from src.models.board import Board
from src.models.hand import Hand
from src.engine.game import new_game
from src.ai.solver import GreedySolver, RandomSolver
from src.sim.runner import (
    GameResult,
    run_game,
    run_batch,
)
from src.sim.stats import (
    AggregateStats,
    compute_stats,
    format_stats,
)
from src.sim.win_prob import (
    WinProbability,
    get_unseen_tiles,
    estimate_win_probability,
)


class TestRunGame:
    """Test single game runner."""

    def test_run_game_completes(self):
        result = run_game(seed=42)

        assert isinstance(result, GameResult)
        assert result.winner in [0, 1, None]
        assert len(result.scores) == 2
        assert result.turns > 0

    def test_run_game_with_different_solvers(self):
        result = run_game(
            solver0=GreedySolver(),
            solver1=RandomSolver(seed=123),
            seed=42
        )

        assert result.winner in [0, 1, None]
        # Greedy usually beats random
        # (but not guaranteed in all cases)

    def test_run_game_deterministic(self):
        result1 = run_game(seed=42)
        result2 = run_game(seed=42)

        assert result1.winner == result2.winner
        assert result1.scores == result2.scores

    def test_game_result_has_stats(self):
        result = run_game(seed=42)

        assert len(result.qwirkles) == 2
        assert result.max_turn_score >= 0


class TestRunBatch:
    """Test batch game runner."""

    def test_run_batch_returns_correct_count(self):
        results = run_batch(n_games=5, base_seed=42, parallel=False)

        assert len(results) == 5
        assert all(isinstance(r, GameResult) for r in results)

    def test_run_batch_parallel(self):
        # Just verify it doesn't crash
        results = run_batch(n_games=2, base_seed=42, parallel=True)

        assert len(results) == 2

    def test_run_batch_with_different_strategies(self):
        results = run_batch(
            n_games=3,
            solver0_type="greedy",
            solver1_type="random",
            base_seed=42,
            parallel=False
        )

        assert len(results) == 3


class TestComputeStats:
    """Test statistics computation."""

    def test_compute_stats_empty(self):
        stats = compute_stats([])

        assert stats.n_games == 0
        assert stats.p0_wins == 0

    def test_compute_stats_single_game(self):
        result = run_game(seed=42)
        stats = compute_stats([result])

        assert stats.n_games == 1
        assert stats.p0_wins + stats.p1_wins + stats.ties == 1

    def test_compute_stats_multiple_games(self):
        results = run_batch(n_games=5, base_seed=42, parallel=False)
        stats = compute_stats(results)

        assert stats.n_games == 5
        assert stats.avg_score_p0 > 0
        assert stats.avg_score_p1 > 0
        assert stats.p0_win_rate + stats.p1_win_rate <= 100

    def test_stats_win_rates_valid(self):
        results = run_batch(n_games=10, base_seed=123, parallel=False)
        stats = compute_stats(results)

        assert 0 <= stats.p0_win_rate <= 100
        assert 0 <= stats.p1_win_rate <= 100


class TestFormatStats:
    """Test stats formatting."""

    def test_format_stats_returns_string(self):
        results = run_batch(n_games=3, base_seed=42, parallel=False)
        stats = compute_stats(results)
        formatted = format_stats(stats)

        assert isinstance(formatted, str)
        assert "Games Played" in formatted
        assert "Win Rates" in formatted


class TestGetUnseenTiles:
    """Test unseen tile calculation."""

    def test_unseen_tiles_initial_state(self):
        state = new_game(seed=42)
        unseen = get_unseen_tiles(state, viewer=0)

        # 108 total - 6 in viewer's hand = 102 unseen
        # But board is empty, so all 102 are unseen
        assert len(unseen) == 102

    def test_unseen_tiles_after_play(self):
        state = new_game(seed=42)
        # Place a tile from player 0's hand
        tile = state.hands[0].tiles()[0]
        state.board.place((0, 0), tile)
        state.hands[0].remove([tile])

        unseen = get_unseen_tiles(state, viewer=0)

        # 108 - 5 (viewer hand) - 1 (board) = 102
        assert len(unseen) == 102


class TestEstimateWinProbability:
    """Test win probability estimation."""

    def test_probability_sums_to_one(self):
        state = new_game(seed=42)
        prob = estimate_win_probability(state, viewer=0, n_simulations=10, seed=123)

        total = prob.p0_prob + prob.p1_prob + prob.tie_prob
        assert abs(total - 1.0) < 0.01

    def test_probability_game_over(self):
        state = new_game(seed=42)
        state.game_over = True
        state.winner = 0

        prob = estimate_win_probability(state, viewer=0, n_simulations=10)

        assert prob.p0_prob == 1.0
        assert prob.p1_prob == 0.0

    def test_probability_returns_valid_range(self):
        state = new_game(seed=42)
        prob = estimate_win_probability(state, viewer=0, n_simulations=10, seed=123)

        assert 0.0 <= prob.p0_prob <= 1.0
        assert 0.0 <= prob.p1_prob <= 1.0
        assert prob.n_simulations == 10

    def test_probability_confidence(self):
        state = new_game(seed=42)
        prob = estimate_win_probability(state, viewer=0, n_simulations=100, seed=123)

        assert prob.confidence > 0
        assert prob.confidence < 1


class TestWinProbabilityDataclass:
    """Test WinProbability dataclass."""

    def test_creation(self):
        prob = WinProbability(
            p0_prob=0.6,
            p1_prob=0.35,
            tie_prob=0.05,
            n_simulations=100
        )

        assert prob.p0_prob == 0.6
        assert prob.confidence > 0


class TestGameResultDataclass:
    """Test GameResult dataclass."""

    def test_creation(self):
        result = GameResult(
            winner=0,
            scores=[50, 40],
            turns=30,
            qwirkles=[1, 0],
            max_turn_score=12,
            max_turn_player=0
        )

        assert result.winner == 0
        assert result.scores == [50, 40]
