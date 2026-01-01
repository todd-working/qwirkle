// Hand component - displays player's draggable tiles

import { Tile } from './Tile';
import type { TileData } from '../types/game';

interface HandProps {
  tiles: TileData[];
  usedIndices: Set<number>;  // Indices of tiles already placed (pending)
  disabled?: boolean;
}

// Desktop-optimized hand slot size (matches lg tile size)
const HAND_SLOT_SIZE = 'w-20 h-20';

export function Hand({ tiles, usedIndices, disabled = false }: HandProps) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-lg border-2 border-blue-200">
      {/* Drag instruction */}
      <div className="text-center mb-4 py-3 px-6 rounded-lg font-bold text-xl bg-blue-100 text-blue-700">
        Drag a tile to the board
      </div>

      <div className="flex gap-6 justify-center">
        {tiles.map((tile, i) => {
          const index = i + 1; // 1-based
          const isUsed = usedIndices.has(index);

          if (isUsed) {
            // Show empty slot for used tile
            return (
              <div
                key={i}
                className={`${HAND_SLOT_SIZE} rounded-lg border-2 border-dashed border-blue-300 bg-blue-50 flex items-center justify-center`}
              >
                <span className="text-blue-400 text-sm">Placed</span>
              </div>
            );
          }

          return (
            <div
              key={i}
              className={`relative ${disabled ? 'opacity-50' : ''}`}
            >
              <Tile
                tile={tile}
                index={index}
                size="lg"
                isDraggable={!disabled}
              />
            </div>
          );
        })}
        {/* Empty slots for missing tiles */}
        {Array.from({ length: 6 - tiles.length }).map((_, i) => (
          <div
            key={`empty-${i}`}
            className={`${HAND_SLOT_SIZE} rounded-lg border-2 border-dashed border-gray-300 bg-gray-50`}
          />
        ))}
      </div>
    </div>
  );
}

export default Hand;
