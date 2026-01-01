// Scoring calculation for preview

import type { TileData, BoardData } from '../types/game';

const QWIRKLE_SIZE = 6;
const QWIRKLE_BONUS = 6;

// Get all tiles in a line (horizontal or vertical) from a position
function getLine(
  row: number,
  col: number,
  direction: 'horizontal' | 'vertical',
  board: BoardData,
  pending: Map<string, { tile: TileData; index: number }>
): TileData[] {
  const tiles: TileData[] = [];
  const dr = direction === 'vertical' ? 1 : 0;
  const dc = direction === 'horizontal' ? 1 : 0;

  // Include the tile at the position itself
  const centerKey = `${row},${col}`;
  const centerTile = board[centerKey] || pending.get(centerKey)?.tile;
  if (centerTile) {
    tiles.push(centerTile);
  }

  // Go negative direction
  let r = row - dr, c = col - dc;
  while (true) {
    const key = `${r},${c}`;
    const boardTile = board[key];
    const pendingTile = pending.get(key);
    if (boardTile) {
      tiles.unshift(boardTile);
    } else if (pendingTile) {
      tiles.unshift(pendingTile.tile);
    } else {
      break;
    }
    r -= dr;
    c -= dc;
  }

  // Go positive direction
  r = row + dr;
  c = col + dc;
  while (true) {
    const key = `${r},${c}`;
    const boardTile = board[key];
    const pendingTile = pending.get(key);
    if (boardTile) {
      tiles.push(boardTile);
    } else if (pendingTile) {
      tiles.push(pendingTile.tile);
    } else {
      break;
    }
    r += dr;
    c += dc;
  }

  return tiles;
}

// Calculate score for pending placements
export function calculatePendingScore(
  board: BoardData,
  pending: Map<string, { tile: TileData; index: number }>
): { score: number; qwirkles: number } {
  if (pending.size === 0) {
    return { score: 0, qwirkles: 0 };
  }

  const pendingPositions = [...pending.keys()].map(key => {
    const [row, col] = key.split(',').map(Number);
    return { row, col, key };
  });

  // Track which lines we've already counted
  const countedLines = new Set<string>();
  let totalScore = 0;
  let qwirkles = 0;

  for (const { row, col } of pendingPositions) {
    // Check horizontal line
    const hLine = getLine(row, col, 'horizontal', board, pending);
    if (hLine.length >= 2) {
      // Create a key for this line to avoid double counting
      const hLineKey = `h:${row}`;
      if (!countedLines.has(hLineKey)) {
        countedLines.add(hLineKey);
        totalScore += hLine.length;
        if (hLine.length === QWIRKLE_SIZE) {
          totalScore += QWIRKLE_BONUS;
          qwirkles++;
        }
      }
    }

    // Check vertical line
    const vLine = getLine(row, col, 'vertical', board, pending);
    if (vLine.length >= 2) {
      const vLineKey = `v:${col}`;
      if (!countedLines.has(vLineKey)) {
        countedLines.add(vLineKey);
        totalScore += vLine.length;
        if (vLine.length === QWIRKLE_SIZE) {
          totalScore += QWIRKLE_BONUS;
          qwirkles++;
        }
      }
    }
  }

  // Special case: single tile with no lines (first move)
  if (totalScore === 0 && pending.size === 1) {
    totalScore = 1;
  }

  return { score: totalScore, qwirkles };
}
