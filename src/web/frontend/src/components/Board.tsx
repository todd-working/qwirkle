// Board component - displays the game board with tiles and drop zones

import { useMemo } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { Tile, EmptyCell, BOARD_CELL_SIZE } from './Tile';
import type { BoardData, TileData } from '../types/game';

interface PendingPlacement {
  tile: TileData;
  index: number;
}

type GameMode = 'beginner' | 'normal';

interface AnimatingTile {
  row: number;
  col: number;
  tile: TileData;
}

interface BoardProps {
  board: BoardData;
  pendingPlacements: Map<string, PendingPlacement>;
  lastMovePositions: number[][];
  draggingTile?: TileData;
  hintPositions?: { row: number; col: number }[];
  gameMode?: GameMode;
  animatingTiles?: AnimatingTile[];
}

// Get board bounds with padding for drop zones
function getBounds(
  board: BoardData,
  pending: Map<string, PendingPlacement>
): { minRow: number; maxRow: number; minCol: number; maxCol: number } {
  const keys = [...Object.keys(board), ...pending.keys()];

  if (keys.length === 0) {
    // Empty board - show small area around origin
    return { minRow: -2, maxRow: 2, minCol: -2, maxCol: 2 };
  }

  let minRow = Infinity, maxRow = -Infinity;
  let minCol = Infinity, maxCol = -Infinity;

  for (const key of keys) {
    const [row, col] = key.split(',').map(Number);
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
      className={BOARD_CELL_SIZE}
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
  pending: Map<string, PendingPlacement>
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
  pending: Map<string, PendingPlacement>
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
  pending: Map<string, PendingPlacement>,
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

      // Check left extension (adjacent empty cell)
      const leftKey = `${row},${minCol - 1}`;
      if (!board[leftKey] && !pending.has(leftKey)) {
        candidates.add(leftKey);
      }

      // Check right extension (adjacent empty cell)
      const rightKey = `${row},${maxCol + 1}`;
      if (!board[rightKey] && !pending.has(rightKey)) {
        candidates.add(rightKey);
      }

      // Check for gaps between pending tiles that can be filled
      for (let c = minCol + 1; c < maxCol; c++) {
        const gapKey = `${row},${c}`;
        if (!board[gapKey] && !pending.has(gapKey)) {
          candidates.add(gapKey);
        }
      }
    }

    if (allSameCol) {
      const col = positions[0].col;
      const rows = positions.map(p => p.row);
      const minRow = Math.min(...rows);
      const maxRow = Math.max(...rows);

      // Check top extension (adjacent empty cell)
      const topKey = `${minRow - 1},${col}`;
      if (!board[topKey] && !pending.has(topKey)) {
        candidates.add(topKey);
      }

      // Check bottom extension (adjacent empty cell)
      const bottomKey = `${maxRow + 1},${col}`;
      if (!board[bottomKey] && !pending.has(bottomKey)) {
        candidates.add(bottomKey);
      }

      // Check for gaps between pending tiles that can be filled
      for (let r = minRow + 1; r < maxRow; r++) {
        const gapKey = `${r},${col}`;
        if (!board[gapKey] && !pending.has(gapKey)) {
          candidates.add(gapKey);
        }
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
  gameMode = 'beginner',
  animatingTiles = [],
}: BoardProps) {
  // Beginner mode shows valid positions while dragging
  const showValidPositions = gameMode === 'beginner';

  // Memoize expensive calculations
  const bounds = useMemo(
    () => getBounds(board, pendingPlacements),
    [board, pendingPlacements]
  );

  const lastMoveSet = useMemo(
    () => new Set(lastMovePositions.map(([r, c]) => `${r},${c}`)),
    [lastMovePositions]
  );

  // Only calculate valid positions in beginner mode
  const validPositions = useMemo(
    () => showValidPositions ? getValidDropPositions(board, pendingPlacements, draggingTile) : new Set<string>(),
    [board, pendingPlacements, draggingTile, showValidPositions]
  );

  // Only show hints in beginner mode
  const hintSet = useMemo(
    () => showValidPositions ? new Set(hintPositions.map(p => `${p.row},${p.col}`)) : new Set<string>(),
    [hintPositions, showValidPositions]
  );

  // Create a map of animating tiles for quick lookup
  const animatingSet = useMemo(
    () => new Map(animatingTiles.map((t, i) => [`${t.row},${t.col}`, { tile: t.tile, index: i }])),
    [animatingTiles]
  );

  // Build grid
  const rows: React.ReactNode[] = [];

  for (let row = bounds.minRow; row <= bounds.maxRow; row++) {
    const cells: React.ReactNode[] = [];

    for (let col = bounds.minCol; col <= bounds.maxCol; col++) {
      const key = `${row},${col}`;
      const tile = board[key];
      const pending = pendingPlacements.get(key);
      const isLastMove = lastMoveSet.has(key);
      const animating = animatingSet.get(key);

      // Show as valid drop zone based on game rules
      const isDropZone = validPositions.has(key);

      // Check for animating tile first (AI move animation)
      if (animating) {
        // Animating tile - show with slide-in animation
        const delay = animating.index * 300; // Stagger by 300ms per tile
        cells.push(
          <div
            key={key}
            className={`${BOARD_CELL_SIZE} animate-tile-appear`}
            style={{ animationDelay: `${delay}ms` }}
          >
            <Tile tile={animating.tile} isHighlighted />
          </div>
        );
      } else if (tile) {
        // Placed tile
        cells.push(
          <div key={key} className={BOARD_CELL_SIZE}>
            <Tile tile={tile} isHighlighted={isLastMove} />
          </div>
        );
      } else if (pending) {
        // Pending placement (ghost)
        cells.push(
          <div key={key} className={BOARD_CELL_SIZE}>
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

  const isEmpty = Object.keys(board).length === 0;

  return (
    <div className="rounded-xl shadow-inner bg-gray-200 p-4">
      {isEmpty && (
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
