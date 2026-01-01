// Tile component with SVG shapes for Qwirkle

import { useDraggable } from '@dnd-kit/core';
import type { TileData } from '../types/game';
import { COLORS } from '../types/game';

interface TileProps {
  tile: TileData;
  index?: number;        // 1-based index for dragging
  size?: 'sm' | 'md' | 'lg';
  isDraggable?: boolean;
  isGhost?: boolean;     // Preview/pending placement
  isHighlighted?: boolean;
}

// SVG shape paths (40x40 viewBox)
const ShapeSVG: Record<number, React.ReactNode> = {
  // Circle
  0: <circle cx="20" cy="20" r="14" />,
  // Square
  1: <rect x="6" y="6" width="28" height="28" />,
  // Diamond
  2: <polygon points="20,4 36,20 20,36 4,20" />,
  // Clover (four-leaf)
  3: (
    <g>
      <circle cx="20" cy="12" r="7" />
      <circle cx="12" cy="20" r="7" />
      <circle cx="28" cy="20" r="7" />
      <circle cx="20" cy="28" r="7" />
    </g>
  ),
  // Star (6-pointed)
  4: (
    <polygon points="20,4 24,14 36,14 27,22 30,34 20,27 10,34 13,22 4,14 16,14" />
  ),
  // Starburst (8-pointed)
  5: (
    <polygon points="20,2 24,13 35,8 28,17 38,20 28,23 35,32 24,27 20,38 16,27 5,32 12,23 2,20 12,17 5,8 16,13" />
  ),
};

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
};

// Pure display component (used in DragOverlay)
export function TileDisplay({
  tile,
  size = 'md',
  isGhost = false,
  isHighlighted = false,
  isDragOverlay = false,
}: {
  tile: TileData;
  size?: 'sm' | 'md' | 'lg';
  isGhost?: boolean;
  isHighlighted?: boolean;
  isDragOverlay?: boolean;
}) {
  const color = COLORS[tile.color].hex;
  const shape = ShapeSVG[tile.shape];

  const baseClasses = `
    ${sizeClasses[size]}
    rounded-lg
    flex items-center justify-center
    ${isGhost ? 'opacity-60 ring-2 ring-blue-400' : ''}
    ${isHighlighted ? 'ring-2 ring-yellow-400 ring-offset-2' : ''}
    ${isDragOverlay ? 'scale-110 shadow-2xl ring-4 ring-blue-500 cursor-grabbing' : ''}
  `;

  return (
    <div className={baseClasses}>
      <svg
        viewBox="0 0 40 40"
        className="w-full h-full"
        style={{ fill: color, stroke: '#1f2937', strokeWidth: 1.5 }}
      >
        <rect
          x="2"
          y="2"
          width="36"
          height="36"
          rx="4"
          fill="#f3f4f6"
          stroke="#d1d5db"
          strokeWidth="1"
        />
        {shape}
      </svg>
    </div>
  );
}

export function Tile({
  tile,
  index,
  size = 'md',
  isDraggable = false,
  isGhost = false,
  isHighlighted = false,
}: TileProps) {
  const color = COLORS[tile.color].hex;
  const shape = ShapeSVG[tile.shape];

  // Draggable setup (only if index provided)
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `tile-${index}`,
    data: { tile, index },
    disabled: !isDraggable || index === undefined,
  });

  // Style for draggable - no transform here, DragOverlay handles visual
  const style: React.CSSProperties = {
    touchAction: 'none', // Prevent browser touch handling
  };

  const baseClasses = `
    ${sizeClasses[size]}
    rounded-lg
    flex items-center justify-center
    transition-all duration-150
    ${isGhost ? 'opacity-60 ring-2 ring-blue-400' : ''}
    ${isHighlighted ? 'ring-2 ring-yellow-400 ring-offset-2' : ''}
    ${isDragging ? 'opacity-30' : ''}
    ${isDraggable && !isDragging ? 'cursor-grab hover:scale-110 hover:shadow-xl hover:-translate-y-1' : ''}
  `;

  return (
    <div
      ref={isDraggable ? setNodeRef : undefined}
      style={style}
      className={baseClasses}
      {...(isDraggable ? { ...listeners, ...attributes } : {})}
    >
      <svg
        viewBox="0 0 40 40"
        className="w-full h-full"
        style={{ fill: color, stroke: '#1f2937', strokeWidth: 1.5 }}
      >
        {/* Background */}
        <rect
          x="2"
          y="2"
          width="36"
          height="36"
          rx="4"
          fill="#f3f4f6"
          stroke="#d1d5db"
          strokeWidth="1"
        />
        {/* Shape */}
        {shape}
      </svg>
      {/* Index badge for hand tiles */}
      {index !== undefined && !isGhost && (
        <span className="absolute -top-1 -left-1 w-5 h-5 bg-gray-800 text-white text-xs rounded-full flex items-center justify-center font-bold">
          {index}
        </span>
      )}
    </div>
  );
}

// Empty cell placeholder for board
export function EmptyCell({
  isValidTarget = false,
  isHovered = false,
  isHint = false,
}: {
  isValidTarget?: boolean;
  isHovered?: boolean;
  isHint?: boolean;
}) {
  // Hint cells (blue pulsing)
  if (isHint) {
    return (
      <div
        className={`
          w-12 h-12 rounded-lg border-3 border-solid
          flex items-center justify-center
          cursor-pointer
          transition-all duration-150
          bg-blue-400 border-blue-600 animate-pulse shadow-lg
        `}
      >
        <span className="text-blue-900 font-bold text-lg">?</span>
      </div>
    );
  }

  // Valid drop target (green)
  if (isValidTarget) {
    return (
      <div
        className={`
          w-12 h-12 rounded-lg border-3 border-solid
          flex items-center justify-center
          cursor-pointer
          transition-all duration-150
          ${isHovered
            ? 'bg-green-400 border-green-600 scale-110 shadow-lg'
            : 'bg-green-300 border-green-500 animate-pulse hover:bg-green-400 hover:scale-105'
          }
        `}
      >
        <span className="text-green-800 font-bold text-xl">+</span>
      </div>
    );
  }

  return (
    <div
      className="w-12 h-12 rounded-lg border border-dashed border-gray-300 bg-gray-100"
    />
  );
}

export default Tile;
