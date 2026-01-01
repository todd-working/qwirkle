// useGame hook - manages game state and API interactions

import { useState, useCallback } from 'react';
import type { GameState, TileData, Placement } from '../types/game';
import * as api from '../api/gameApi';

interface PendingPlacement {
  tile: TileData;
  index: number;  // 1-based hand index
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

  // Actions
  startGame: (vsAI?: boolean, aiStrategy?: 'greedy' | 'random') => Promise<void>;
  selectTile: (index: number) => void;
  placeTile: (row: number, col: number) => void;
  dropTile: (tileIndex: number, row: number, col: number) => void;
  confirmPlay: () => Promise<void>;
  cancelPlay: () => void;
  swapSelected: () => Promise<void>;
  undo: () => Promise<void>;
  getHint: () => Promise<void>;
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

  // Start a new game
  const startGame = useCallback(async (vsAI = false, aiStrategy: 'greedy' | 'random' = 'greedy') => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.createGame({ vs_ai: vsAI, ai_strategy: aiStrategy });
      setGameId(response.game_id);
      setState(response.state);
      setPending(new Map());
      setSelected(undefined);
      setValidPositions(new Set());
      setHintMessage(null);
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

  // Confirm pending placements
  const confirmPlay = useCallback(async () => {
    if (!gameId || pendingPlacements.size === 0) return;

    setLoading(true);
    setError(null);
    setHintMessage(null);

    try {
      const placements: Placement[] = [];
      for (const [key, { index }] of pendingPlacements) {
        const [row, col] = key.split(',').map(Number);
        placements.push({ row, col, tile_index: index });
      }

      const response = await api.playTiles(gameId, placements);

      if (response.success && response.state) {
        setState(response.state);
        setPending(new Map());
      } else {
        setError(response.error || 'Invalid move');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to play');
    } finally {
      setLoading(false);
    }
  }, [gameId, pendingPlacements]);

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
        // Highlight first placement's tile
        setSelected(response.placements[0].tile_index);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get hint');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  return {
    gameId,
    state,
    pendingPlacements,
    selectedTileIndex,
    validPositions,
    isLoading,
    error,
    hintMessage,
    startGame,
    selectTile,
    placeTile,
    dropTile,
    confirmPlay,
    cancelPlay,
    swapSelected,
    undo,
    getHint,
  };
}

export default useGame;
