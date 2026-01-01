"""
Training script for Qwirkle neural network AI.

Reads game data from Go simulator output (JSONL format) and trains
a neural network to predict good moves.

Uses MLX for Apple Metal GPU acceleration.
"""

import json
import sys
from pathlib import Path
from typing import Iterator

# Placeholder for MLX/PyTorch imports
# import mlx.core as mx
# import mlx.nn as nn


def load_games(path: Path) -> Iterator[dict]:
    """Load games from JSONL file."""
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def extract_training_data(games: Iterator[dict]) -> list[tuple]:
    """
    Extract (board_state, move, outcome) tuples from games.

    For each move in winning games:
    - board_state: current board as tensor
    - move: the move that was played
    - outcome: 1 if player won, 0 if lost, 0.5 if tie
    """
    data = []

    for game in games:
        winner = game["winner"]

        # TODO: Reconstruct board state at each move
        # For now, just count games
        data.append(game)

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python train.py <games.jsonl>")
        sys.exit(1)

    games_path = Path(sys.argv[1])

    if not games_path.exists():
        print(f"File not found: {games_path}")
        sys.exit(1)

    print(f"Loading games from {games_path}...")
    games = list(load_games(games_path))
    print(f"Loaded {len(games)} games")

    # Count outcomes
    p1_wins = sum(1 for g in games if g["winner"] == 0)
    p2_wins = sum(1 for g in games if g["winner"] == 1)
    ties = sum(1 for g in games if g["winner"] == -1)

    print(f"\nResults:")
    print(f"  Player 1 wins: {p1_wins} ({100*p1_wins/len(games):.1f}%)")
    print(f"  Player 2 wins: {p2_wins} ({100*p2_wins/len(games):.1f}%)")
    print(f"  Ties: {ties} ({100*ties/len(games):.1f}%)")

    # TODO: Implement actual training
    print("\n[Training not yet implemented - scaffold only]")


if __name__ == "__main__":
    main()
