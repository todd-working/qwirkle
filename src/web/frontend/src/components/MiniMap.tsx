// MiniMap component - shows overview of entire board

import type { BoardData, TileData } from '../types/game';
import { COLORS } from '../types/game';

interface MiniMapProps {
  board: BoardData;
  pendingPlacements: Map<string, { tile: TileData; index: number }>;
}

export function MiniMap({ board, pendingPlacements }: MiniMapProps) {
  // Get all tile positions
  const allKeys = [...Object.keys(board), ...pendingPlacements.keys()];

  if (allKeys.length === 0) {
    return (
      <div className="w-24 h-24 bg-gray-200 rounded-lg flex items-center justify-center">
        <span className="text-gray-400 text-xs">Empty</span>
      </div>
    );
  }

  // Calculate bounds
  let minRow = Infinity, maxRow = -Infinity;
  let minCol = Infinity, maxCol = -Infinity;

  for (const key of allKeys) {
    const [row, col] = key.split(',').map(Number);
    minRow = Math.min(minRow, row);
    maxRow = Math.max(maxRow, row);
    minCol = Math.min(minCol, col);
    maxCol = Math.max(maxCol, col);
  }

  const rows = maxRow - minRow + 1;
  const cols = maxCol - minCol + 1;

  // Calculate cell size to fit in 96x96 container
  const maxDim = Math.max(rows, cols);
  const cellSize = Math.max(4, Math.floor(88 / maxDim));

  // Build mini tiles
  const tiles: React.ReactNode[] = [];

  for (const key of Object.keys(board)) {
    const [row, col] = key.split(',').map(Number);
    const tile = board[key];
    const color = COLORS[tile.color].hex;

    tiles.push(
      <div
        key={key}
        className="absolute rounded-sm"
        style={{
          left: (col - minCol) * cellSize + 4,
          top: (row - minRow) * cellSize + 4,
          width: cellSize - 1,
          height: cellSize - 1,
          backgroundColor: color,
        }}
      />
    );
  }

  // Add pending placements with pulsing effect
  for (const [key] of pendingPlacements) {
    const [row, col] = key.split(',').map(Number);
    const placement = pendingPlacements.get(key)!;
    const color = COLORS[placement.tile.color].hex;

    tiles.push(
      <div
        key={`pending-${key}`}
        className="absolute rounded-sm animate-pulse ring-1 ring-white"
        style={{
          left: (col - minCol) * cellSize + 4,
          top: (row - minRow) * cellSize + 4,
          width: cellSize - 1,
          height: cellSize - 1,
          backgroundColor: color,
        }}
      />
    );
  }

  return (
    <div
      className="w-24 h-24 bg-gray-700 rounded-lg relative overflow-hidden"
      title="Board Overview"
    >
      {tiles}
    </div>
  );
}

export default MiniMap;
