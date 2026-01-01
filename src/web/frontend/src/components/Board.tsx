// Board component - displays the game board with tiles and drop zones

import { useDroppable } from '@dnd-kit/core';
import { Tile, EmptyCell } from './Tile';
import type { BoardData, TileData, Position } from '../types/game';

interface BoardProps {
  board: BoardData;
  pendingPlacements: Map<string, { tile: TileData; index: number }>;
  lastMovePositions: number[][];
  draggingTile?: TileData;  // The tile currently being dragged
  hintPositions?: { row: number; col: number }[];  // Positions to highlight as hints
}

// Parse "row,col" key to Position
function parseKey(key: string): Position {
  const [row, col] = key.split(',').map(Number);
  return { row, col };
}

// Get board bounds with padding
function getBounds(
  board: BoardData,
  pending: Map<string, unknown>
): { minRow: number; maxRow: number; minCol: number; maxCol: number } {
  const keys = [...Object.keys(board), ...pending.keys()];

  if (keys.length === 0) {
    // Empty board - show small area around origin
    return { minRow: -2, maxRow: 2, minCol: -2, maxCol: 2 };
  }

  let minRow = Infinity, maxRow = -Infinity;
  let minCol = Infinity, maxCol = -Infinity;

  for (const key of keys) {
    const { row, col } = parseKey(key);
    minRow = Math.min(minRow, row);
    maxRow = Math.max(maxRow, row);
    minCol = Math.min(minCol, col);
    maxCol = Math.max(maxCol, col);
  }

  // Add padding for drop zones
  return {
    minRow: minRow - 2,
    maxRow: maxRow + 2,
    minCol: minCol - 2,
    maxCol: maxCol + 2,
  };
}

// Droppable cell wrapper
function DroppableCell({
  row,
  col,
  isValid,
  isHint,
  children,
}: {
  row: number;
  col: number;
  isValid: boolean;
  isHint?: boolean;
  children?: React.ReactNode;
}) {
  const id = `cell-${row}-${col}`;
  const { isOver, setNodeRef } = useDroppable({
    id,
    data: { row, col },
  });

  return (
    <div
      ref={setNodeRef}
      className="w-12 h-12"
    >
      {children || (
        <EmptyCell
          isValidTarget={isValid}
          isHovered={isOver && isValid}
          isHint={isHint}
        />
      )}
    </div>
  );
}

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

// Check if a tile can legally be placed at a position
function isValidPlacement(
  tile: TileData,
  row: number,
  col: number,
  board: BoardData,
  pending: Map<string, { tile: TileData; index: number }>
): boolean {
  // Get horizontal and vertical lines
  const hLine = getLine(row, col, 'horizontal', board, pending);
  const vLine = getLine(row, col, 'vertical', board, pending);

  // Check horizontal line (if any neighbors)
  if (hLine.length > 0) {
    const allTiles = [...hLine, tile];
    if (!isValidLine(allTiles)) return false;
  }

  // Check vertical line (if any neighbors)
  if (vLine.length > 0) {
    const allTiles = [...vLine, tile];
    if (!isValidLine(allTiles)) return false;
  }

  return true;
}

// Check if a line of tiles is valid (all same color OR all same shape, no duplicates)
function isValidLine(tiles: TileData[]): boolean {
  if (tiles.length <= 1) return true;
  if (tiles.length > 6) return false;

  // Check for duplicates
  const seen = new Set<string>();
  for (const t of tiles) {
    const key = `${t.shape},${t.color}`;
    if (seen.has(key)) return false;
    seen.add(key);
  }

  // Check if all same color (different shapes) OR all same shape (different colors)
  const allSameColor = tiles.every(t => t.color === tiles[0].color);
  const allSameShape = tiles.every(t => t.shape === tiles[0].shape);

  return allSameColor || allSameShape;
}

// Get valid drop positions based on current state and the tile being dragged
function getValidDropPositions(
  board: BoardData,
  pending: Map<string, { tile: TileData; index: number }>,
  draggingTile?: TileData
): Set<string> {
  const validPositions = new Set<string>();
  const boardIsEmpty = Object.keys(board).length === 0;
  const pendingKeys = [...pending.keys()];

  // If no tile being dragged, show no valid positions
  if (!draggingTile) {
    return validPositions;
  }

  if (boardIsEmpty && pendingKeys.length === 0) {
    // First tile must go at origin
    validPositions.add('0,0');
    return validPositions;
  }

  // Get candidate positions
  const candidates = new Set<string>();

  if (pendingKeys.length > 0) {
    // Must extend the current line of pending placements
    const positions = pendingKeys.map(k => {
      const [r, c] = k.split(',').map(Number);
      return { row: r, col: c };
    });

    const allSameRow = positions.every(p => p.row === positions[0].row);
    const allSameCol = positions.every(p => p.col === positions[0].col);

    if (allSameRow) {
      const row = positions[0].row;
      const cols = positions.map(p => p.col);
      const minCol = Math.min(...cols);
      const maxCol = Math.max(...cols);

      // Check left extension
      for (let c = minCol - 1; c >= minCol - 5; c--) {
        const key = `${row},${c}`;
        if (board[key] || pending.has(key)) break;
        candidates.add(key);
        break;
      }

      // Check right extension
      for (let c = maxCol + 1; c <= maxCol + 5; c++) {
        const key = `${row},${c}`;
        if (board[key] || pending.has(key)) break;
        candidates.add(key);
        break;
      }
    }

    if (allSameCol) {
      const col = positions[0].col;
      const rows = positions.map(p => p.row);
      const minRow = Math.min(...rows);
      const maxRow = Math.max(...rows);

      for (let r = minRow - 1; r >= minRow - 5; r--) {
        const key = `${r},${col}`;
        if (board[key] || pending.has(key)) break;
        candidates.add(key);
        break;
      }

      for (let r = maxRow + 1; r <= maxRow + 5; r++) {
        const key = `${r},${col}`;
        if (board[key] || pending.has(key)) break;
        candidates.add(key);
        break;
      }
    }
  } else {
    // No pending - get all adjacent to existing board tiles
    for (const key of Object.keys(board)) {
      const [row, col] = key.split(',').map(Number);
      const neighbors = [
        `${row - 1},${col}`,
        `${row + 1},${col}`,
        `${row},${col - 1}`,
        `${row},${col + 1}`,
      ];
      for (const neighbor of neighbors) {
        if (!board[neighbor] && !pending.has(neighbor)) {
          candidates.add(neighbor);
        }
      }
    }
  }

  // Filter candidates by Qwirkle rules
  for (const key of candidates) {
    const [row, col] = key.split(',').map(Number);
    if (isValidPlacement(draggingTile, row, col, board, pending)) {
      validPositions.add(key);
    }
  }

  return validPositions;
}

export function Board({
  board,
  pendingPlacements,
  lastMovePositions,
  draggingTile,
  hintPositions = [],
}: BoardProps) {
  const bounds = getBounds(board, pendingPlacements);
  const lastMoveSet = new Set(lastMovePositions.map(([r, c]) => `${r},${c}`));
  const validPositions = getValidDropPositions(board, pendingPlacements, draggingTile);
  const hintSet = new Set(hintPositions.map(p => `${p.row},${p.col}`));

  // Build grid
  const rows: React.ReactNode[] = [];

  for (let row = bounds.minRow; row <= bounds.maxRow; row++) {
    const cells: React.ReactNode[] = [];

    for (let col = bounds.minCol; col <= bounds.maxCol; col++) {
      const key = `${row},${col}`;
      const tile = board[key];
      const pending = pendingPlacements.get(key);
      const isLastMove = lastMoveSet.has(key);

      // Show as valid drop zone based on game rules
      const isDropZone = validPositions.has(key);

      if (tile) {
        // Placed tile
        cells.push(
          <div key={key} className="w-12 h-12">
            <Tile tile={tile} isHighlighted={isLastMove} />
          </div>
        );
      } else if (pending) {
        // Pending placement (ghost)
        cells.push(
          <div key={key} className="w-12 h-12">
            <Tile tile={pending.tile} isGhost />
          </div>
        );
      } else {
        // Empty cell (potential drop zone or hint)
        const isHint = hintSet.has(key);
        cells.push(
          <DroppableCell
            key={key}
            row={row}
            col={col}
            isValid={isDropZone}
            isHint={isHint}
          />
        );
      }
    }

    rows.push(
      <div key={row} className="flex">
        {cells}
      </div>
    );
  }

  // Show drop zones on empty cells adjacent to tiles
  const boardHasTiles = Object.keys(board).length > 0;

  return (
    <div className="overflow-auto p-4 rounded-xl shadow-inner bg-gray-200">
      {!boardHasTiles && (
        <div className="text-center mb-2 text-blue-700 font-bold">
          Drop your first tile in the center!
        </div>
      )}
      <div className="inline-block min-w-fit">
        {rows}
      </div>
    </div>
  );
}

export default Board;
