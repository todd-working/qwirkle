// API client for Qwirkle backend

import axios from 'axios';
import type {
  GameState,
  NewGameResponse,
  PlayResponse,
  SwapResponse,
  UndoResponse,
  HintResponse,
  ValidPositionsResponse,
  Placement,
} from '../types/game';

// Base URL - proxied through Vite in development
const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface NewGameOptions {
  seed?: number;
  vs_ai?: boolean;
  ai_strategy?: 'greedy' | 'random';
}

export async function createGame(options: NewGameOptions = {}): Promise<NewGameResponse> {
  const response = await api.post<NewGameResponse>('/game/new', {
    seed: options.seed,
    vs_ai: options.vs_ai ?? false,
    ai_strategy: options.ai_strategy ?? 'greedy',
  });
  return response.data;
}

export async function getGameState(gameId: string): Promise<GameState> {
  const response = await api.get<GameState>(`/game/${gameId}`);
  return response.data;
}

export async function playTiles(
  gameId: string,
  placements: Placement[]
): Promise<PlayResponse> {
  const response = await api.post<PlayResponse>(`/game/${gameId}/play`, {
    placements,
  });
  return response.data;
}

export async function swapTiles(
  gameId: string,
  tileIndices: number[]
): Promise<SwapResponse> {
  const response = await api.post<SwapResponse>(`/game/${gameId}/swap`, {
    tile_indices: tileIndices,
  });
  return response.data;
}

export async function undoMove(gameId: string): Promise<UndoResponse> {
  const response = await api.post<UndoResponse>(`/game/${gameId}/undo`);
  return response.data;
}

export async function getHint(gameId: string): Promise<HintResponse> {
  const response = await api.get<HintResponse>(`/game/${gameId}/hint`);
  return response.data;
}

export async function getValidPositions(
  gameId: string,
  tileIndex: number
): Promise<ValidPositionsResponse> {
  const response = await api.post<ValidPositionsResponse>(
    `/game/${gameId}/valid-positions`,
    { tile_index: tileIndex }
  );
  return response.data;
}

export async function deleteGame(gameId: string): Promise<void> {
  await api.delete(`/game/${gameId}`);
}
