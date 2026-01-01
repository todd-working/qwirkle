// Game types matching the FastAPI backend models

export interface TileData {
  shape: number;  // 0-5: Circle, Square, Diamond, Clover, Star, Starburst
  color: number;  // 0-5: Red, Orange, Yellow, Green, Blue, Purple
}

export interface Position {
  row: number;
  col: number;
}

export interface Placement {
  row: number;
  col: number;
  tile_index: number;  // 1-based index in hand
}

// Board is a sparse map: "row,col" -> TileData
export type BoardData = Record<string, TileData>;

export interface GameState {
  game_id: string;
  board: BoardData;
  hand: TileData[];
  current_player: number;
  scores: number[];
  bag_remaining: number;
  game_over: boolean;
  winner: number | null;
  last_move_positions: number[][];  // [[row, col], ...]
  message: string;
}

export interface NewGameResponse {
  game_id: string;
  state: GameState;
}

export interface PlayResponse {
  success: boolean;
  points?: number;
  qwirkles?: number;
  error?: string;
  state?: GameState;
  // For AI moves, we include the tiles placed for animation
  ai_placements?: Array<{ row: number; col: number; tile: TileData }>;
}

export interface SwapResponse {
  success: boolean;
  error?: string;
  state?: GameState;
}

export interface UndoResponse {
  success: boolean;
  error?: string;
  state?: GameState;
}

export interface HintResponse {
  has_move: boolean;
  placements: Placement[];
  expected_score: number;
  message: string;
}

export interface ValidPositionsResponse {
  positions: number[][];  // [[row, col], ...]
}

// Shape names for display
export const SHAPE_NAMES = [
  'Circle',
  'Square',
  'Diamond',
  'Clover',
  'Star',
  'Starburst',
] as const;

// Color names and hex values
export const COLORS = [
  { name: 'Red', hex: '#ef4444' },
  { name: 'Orange', hex: '#f97316' },
  { name: 'Yellow', hex: '#eab308' },
  { name: 'Green', hex: '#22c55e' },
  { name: 'Blue', hex: '#3b82f6' },
  { name: 'Purple', hex: '#a855f7' },
] as const;
