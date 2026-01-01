// Game controls - buttons for undo, hint, swap, confirm

interface GameControlsProps {
  hasPendingPlacements: boolean;
  canUndo: boolean;
  canSwap: boolean;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  onUndo: () => void;
  onHint: () => void;
  onSwap: () => void;
}

export function GameControls({
  hasPendingPlacements,
  canUndo,
  canSwap,
  isLoading,
  onConfirm,
  onCancel,
  onUndo,
  onHint,
  onSwap,
}: GameControlsProps) {
  const buttonBase = `
    px-4 py-2 rounded-lg font-medium
    transition-all duration-150
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {hasPendingPlacements ? (
        <>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`${buttonBase} bg-green-500 hover:bg-green-600 text-white`}
          >
            {isLoading ? 'Playing...' : 'Confirm Play'}
          </button>
          <button
            onClick={onCancel}
            disabled={isLoading}
            className={`${buttonBase} bg-gray-500 hover:bg-gray-600 text-white`}
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <button
            onClick={onUndo}
            disabled={!canUndo || isLoading}
            className={`${buttonBase} bg-gray-500 hover:bg-gray-600 text-white`}
          >
            Undo
          </button>
          <button
            onClick={onHint}
            disabled={isLoading}
            className={`${buttonBase} bg-blue-500 hover:bg-blue-600 text-white`}
          >
            Hint
          </button>
          <button
            onClick={onSwap}
            disabled={!canSwap || isLoading}
            className={`${buttonBase} bg-orange-500 hover:bg-orange-600 text-white`}
          >
            Swap Tiles
          </button>
        </>
      )}
    </div>
  );
}

export default GameControls;
