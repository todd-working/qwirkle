#!/usr/bin/env python3
"""Qwirkle - Terminal game with AI solver and Monte Carlo simulator.

Usage:
    python main.py              Run interactive game
    python main.py --seed 42    Run with specific random seed
    python main.py --no-clear   Don't clear screen between turns
"""

from src.ui.game_loop import main

if __name__ == "__main__":
    main()
