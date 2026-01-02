// useGame hook - manages game state and API interactions

import { useState, useCallback } from 'react';
import type { GameState, TileData, Placement } from '../types/game';
import * as api from '../api/gameApi';

interface PendingPlacement {
  tile: TileData;
  index: number;  // 1-based hand index
}

// Game mode types
export type GameMode = 'beginner' | 'normal';

// Animation state for AI moves
export interface AnimatingTile {
  row: number;
  col: number;
  tile: TileData;
}

interface UseGameReturn {
  // State
  gameId: string | null;
  state: GameState | null;
  pendingPlacements: Map<string, PendingPlacement>;
  selectedTileIndex: number | undefined;
  validPositions: Set<string>;
  isLoading: boolean;
  error: string | null;
  hintMessage: string | null;
  hintPlacements: Placement[];
  isAiVsAi: boolean;
  gameMode: GameMode;
  animatingTiles: AnimatingTile[];  // Tiles currently animating onto board
  isAnimating: boolean;

  // Actions
  startGame: (vsAI?: boolean, aiStrategy?: 'greedy' | 'random', aiVsAi?: boolean, mode?: GameMode) => Promise<void>;
  selectTile: (index: number) => void;
  placeTile: (row: number, col: number) => void;
  dropTile: (tileIndex: number, row: number, col: number) => void;
  confirmPlay: () => Promise<void>;
  cancelPlay: () => void;
  swapSelected: () => Promise<void>;
  undo: () => Promise<void>;
  getHint: () => Promise<void>;
  clearHint: () => void;
  stepAi: () => Promise<void>;
}

export function useGame(): UseGameReturn {
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [pendingPlacements, setPending] = useState<Map<string, PendingPlacement>>(new Map());
  const [selectedTileIndex, setSelected] = useState<number | undefined>(undefined);
  const [validPositions, setValidPositions] = useState<Set<string>>(new Set());
  const [isLoading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hintMessage, setHintMessage] = useState<string | null>(null);
  const [hintPlacements, setHintPlacements] = useState<Placement[]>([]);
  const [isAiVsAi, setIsAiVsAi] = useState(false);
  const [vsAi, setVsAi] = useState(false);  // Human vs AI mode
  const [gameMode, setGameMode] = useState<GameMode>('beginner');
  const [animatingTiles, setAnimatingTiles] = useState<AnimatingTile[]>([]);
  const [isAnimating, setIsAnimating] = useState(false);

  // Start a new game
  const startGame = useCallback(async (
    vsAI = false,
    aiStrategy: 'greedy' | 'random' = 'greedy',
    aiVsAi = false,
    mode: GameMode = 'beginner'
  ) => {
    console.log('startGame called with vsAI:', vsAI, 'aiVsAi:', aiVsAi, 'mode:', mode);
    setLoading(true);
    setError(null);
    try {
      const response = await api.createGame({ vs_ai: vsAI, ai_strategy: aiStrategy, ai_vs_ai: aiVsAi });
      setGameId(response.game_id);
      setState(response.state);
      setPending(new Map());
      setSelected(undefined);
      setValidPositions(new Set());
      setHintMessage(null);
      setIsAiVsAi(aiVsAi);
      setVsAi(vsAI);
      setGameMode(mode);
      console.log('Game started, vsAi set to:', vsAI);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }, []);

  // Select a tile from hand
  const selectTile = useCallback(async (index: number) => {
    if (!gameId || !state) return;

    // Toggle selection
    if (selectedTileIndex === index) {
      setSelected(undefined);
      setValidPositions(new Set());
      return;
    }

    setSelected(index);

    // Get valid positions for this tile
    try {
      const response = await api.getValidPositions(gameId, index);
      const positions = new Set(response.positions.map(([r, c]) => `${r},${c}`));
      setValidPositions(positions);
    } catch {
      setValidPositions(new Set());
    }
  }, [gameId, state, selectedTileIndex]);

  // Place selected tile at position (click-based)
  const placeTile = useCallback((row: number, col: number) => {
    if (!state || selectedTileIndex === undefined) return;

    const key = `${row},${col}`;

    // Check if position is valid
    if (!validPositions.has(key)) return;

    // Get tile from hand
    const tile = state.hand[selectedTileIndex - 1];
    if (!tile) return;

    // Add to pending placements
    setPending(prev => {
      const next = new Map(prev);
      next.set(key, { tile, index: selectedTileIndex });
      return next;
    });

    // Clear selection
    setSelected(undefined);
    setValidPositions(new Set());
  }, [state, selectedTileIndex, validPositions]);

  // Drop tile at position (drag-based) - directly adds to pending
  const dropTile = useCallback((tileIndex: number, row: number, col: number) => {
    if (!state) return;

    const key = `${row},${col}`;

    // Get tile from hand
    const tile = state.hand[tileIndex - 1];
    if (!tile) return;

    // Add to pending placements
    setPending(prev => {
      const next = new Map(prev);
      next.set(key, { tile, index: tileIndex });
      return next;
    });

    // Clear any selection
    setSelected(undefined);
    setValidPositions(new Set());
  }, [state]);

  // Helper to animate tiles onto board
  const animateTiles = useCallback((
    newState: GameState,
    onComplete: () => void
  ) => {
    const lastMovePositions = newState.last_move_positions;

    console.log('animateTiles called, positions:', lastMovePositions);
    console.log('board keys:', Object.keys(newState.board));

    if (lastMovePositions && lastMovePositions.length > 0) {
      const tilesToAnimate: AnimatingTile[] = lastMovePositions.map((pos) => {
        // pos is [row, col] array
        const row = pos[0];
        const col = pos[1];
        const key = `${row},${col}`;
        const tile = newState.board[key];
        console.log(`Position ${key}, tile:`, tile);
        return { row, col, tile };
      }).filter(t => t.tile);

      console.log('tilesToAnimate:', tilesToAnimate);

      if (tilesToAnimate.length > 0) {
        setIsAnimating(true);
        setAnimatingTiles(tilesToAnimate);

        const animationDuration = 600;
        const staggerDelay = 400;
        const totalDuration = animationDuration + (tilesToAnimate.length - 1) * staggerDelay;

        setTimeout(() => {
          setAnimatingTiles([]);
          setIsAnimating(false);
          onComplete();
        }, totalDuration);

        return true; // Animation started
      }
    }

    return false; // No animation
  }, []);

  // Confirm pending placements
  const confirmPlay = useCallback(async () => {
    console.log('confirmPlay called, vsAi:', vsAi, 'gameId:', gameId);
    if (!gameId || pendingPlacements.size === 0) return;

    setLoading(true);
    setError(null);
    setHintMessage(null);
    setPending(new Map()); // Clear pending immediately for visual feedback

    try {
      const placements: Placement[] = [];
      for (const [key, { index }] of pendingPlacements) {
        const [row, col] = key.split(',').map(Number);
        placements.push({ row, col, tile_index: index });
      }

      const response = await api.playTiles(gameId, placements);
      console.log('playTiles response:', response);

      if (response.success && response.state) {
        const newState = response.state;
        console.log('newState.game_over:', newState.game_over, 'last_move_positions:', newState.last_move_positions);

        // If vs AI, animate the AI's response tiles
        // The backend auto-plays AI after human, so last_move_positions = AI's move
        if (vsAi && !newState.game_over) {
          console.log('Attempting to animate AI tiles');
          const animated = animateTiles(newState, () => {
            setState(newState);
            setLoading(false);
          });

          if (animated) return; // Don't set loading false yet
        }

        setState(newState);
      } else {
        setError(response.error || 'Invalid move');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to play');
    } finally {
      if (!isAnimating) {
        setLoading(false);
      }
    }
  }, [gameId, pendingPlacements, vsAi, animateTiles, isAnimating]);

  // Cancel pending placements
  const cancelPlay = useCallback(() => {
    setPending(new Map());
    setSelected(undefined);
    setValidPositions(new Set());
  }, []);

  // Swap selected tile(s)
  const swapSelected = useCallback(async () => {
    if (!gameId || !state) return;

    // For now, swap the first tile if none selected
    const indices = selectedTileIndex ? [selectedTileIndex] : [1];

    setLoading(true);
    setError(null);

    try {
      const response = await api.swapTiles(gameId, indices);

      if (response.success && response.state) {
        setState(response.state);
        setSelected(undefined);
        setValidPositions(new Set());
      } else {
        setError(response.error || 'Cannot swap');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to swap');
    } finally {
      setLoading(false);
    }
  }, [gameId, state, selectedTileIndex]);

  // Undo last move
  const undo = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.undoMove(gameId);

      if (response.success && response.state) {
        setState(response.state);
        setPending(new Map());
        setSelected(undefined);
        setValidPositions(new Set());
      } else {
        setError(response.error || 'Cannot undo');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to undo');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Get hint
  const getHint = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.getHint(gameId);
      setHintMessage(response.message);

      if (response.has_move && response.placements.length > 0) {
        // Store hint placements for board highlighting
        setHintPlacements(response.placements);
        // Highlight first placement's tile
        setSelected(response.placements[0].tile_index);
      } else {
        setHintPlacements([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get hint');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Clear hint highlighting
  const clearHint = useCallback(() => {
    setHintMessage(null);
    setHintPlacements([]);
  }, []);

  // Step AI (for AI vs AI mode) - with animation
  const stepAi = useCallback(async () => {
    if (!gameId || !state) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.aiStep(gameId);

      if (response.success && response.state) {
        const newState = response.state;

        // Animate the AI's tiles
        const animated = animateTiles(newState, () => {
          setState(newState);
          setLoading(false);
        });

        if (animated) return; // Don't set loading false yet

        // No animation needed, just update state
        setState(newState);
      } else {
        setError(response.error || 'AI move failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to step AI');
    } finally {
      if (!isAnimating) {
        setLoading(false);
      }
    }
  }, [gameId, state, animateTiles, isAnimating]);

  return {
    gameId,
    state,
    pendingPlacements,
    selectedTileIndex,
    validPositions,
    isLoading,
    error,
    hintMessage,
    hintPlacements,
    isAiVsAi,
    gameMode,
    animatingTiles,
    isAnimating,
    startGame,
    selectTile,
    placeTile,
    dropTile,
    confirmPlay,
    cancelPlay,
    swapSelected,
    undo,
    getHint,
    clearHint,
    stepAi,
  };
}

export default useGame;
