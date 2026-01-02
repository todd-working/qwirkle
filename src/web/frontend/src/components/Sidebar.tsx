// Sidebar component - scores and controls

import type { WinProbabilityResponse } from '../types/game';

type GameMode = 'beginner' | 'normal';

interface SidebarProps {
  scores: number[];
  currentPlayer: number;
  bagRemaining: number;
  gameOver: boolean;
  winner: number | null;
  isAiVsAi: boolean;
  isLoading: boolean;
  canSwap: boolean;
  gameMode: GameMode;
  winProbability: WinProbabilityResponse | null;
  isLoadingWinProb: boolean;
  onHint: () => void;
  onUndo: () => void;
  onSwap: () => void;
  onWinProb: () => void;
}

export function Sidebar({
  scores,
  currentPlayer,
  bagRemaining,
  gameOver,
  winner,
  isAiVsAi,
  isLoading,
  canSwap,
  gameMode,
  winProbability,
  isLoadingWinProb,
  onHint,
  onUndo,
  onSwap,
  onWinProb,
}: SidebarProps) {
  // Beginner mode shows hints
  const showHint = gameMode === 'beginner';
  return (
    <div className="w-44 flex-shrink-0 space-y-4">
      {/* Scores */}
      <div className="bg-white rounded-xl shadow-md p-4 space-y-3">
        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide">
          Scores
        </h3>

        {/* Player 1 */}
        <div
          className={`
            p-3 rounded-lg transition-all
            ${currentPlayer === 0 && !gameOver
              ? 'bg-blue-100 ring-2 ring-blue-500'
              : 'bg-gray-50'
            }
          `}
        >
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">
              {isAiVsAi ? 'AI 1' : 'Player 1'}
            </span>
            <span className="text-2xl font-bold text-gray-800">{scores[0]}</span>
          </div>
          {winner === 0 && (
            <div className="text-green-600 font-bold text-sm mt-1">Winner!</div>
          )}
        </div>

        {/* Player 2 */}
        <div
          className={`
            p-3 rounded-lg transition-all
            ${currentPlayer === 1 && !gameOver
              ? 'bg-purple-100 ring-2 ring-purple-500'
              : 'bg-gray-50'
            }
          `}
        >
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">
              {isAiVsAi ? 'AI 2' : 'Player 2'}
            </span>
            <span className="text-2xl font-bold text-gray-800">{scores[1]}</span>
          </div>
          {winner === 1 && (
            <div className="text-green-600 font-bold text-sm mt-1">Winner!</div>
          )}
        </div>

        {/* Tie */}
        {gameOver && winner === null && (
          <div className="text-center text-gray-600 font-bold">Tie!</div>
        )}
      </div>

      {/* Bag */}
      <div className="bg-white rounded-xl shadow-md p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-500">Bag</span>
          <span className="text-xl font-bold text-gray-700">{bagRemaining}</span>
        </div>
        <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${(bagRemaining / 108) * 100}%` }}
          />
        </div>
      </div>

      {/* Win Probability */}
      {!gameOver && (
        <div className="bg-white rounded-xl shadow-md p-4">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">
            Win Chance
          </h3>
          {isLoadingWinProb ? (
            <div className="flex flex-col items-center py-4">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-gray-500 mt-2">Simulating...</span>
            </div>
          ) : winProbability ? (
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-600">{isAiVsAi ? 'AI 1' : 'Player 1'}</span>
                  <span className="font-bold text-blue-600">
                    {Math.round(winProbability.p0_prob * 100)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${winProbability.p0_prob * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-600">{isAiVsAi ? 'AI 2' : 'Player 2'}</span>
                  <span className="font-bold text-purple-600">
                    {Math.round(winProbability.p1_prob * 100)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all"
                    style={{ width: `${winProbability.p1_prob * 100}%` }}
                  />
                </div>
              </div>
              <button
                onClick={onWinProb}
                className="w-full py-1 px-2 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
              >
                Refresh
              </button>
            </div>
          ) : (
            <button
              onClick={onWinProb}
              className="w-full py-2 px-4 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors text-sm"
            >
              Calculate
            </button>
          )}
        </div>
      )}

      {/* Controls */}
      {!gameOver && !isAiVsAi && (
        <div className="bg-white rounded-xl shadow-md p-4 space-y-2">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">
            Actions
          </h3>

          {/* Hint button only in beginner mode */}
          {showHint && (
            <button
              onClick={onHint}
              disabled={isLoading}
              className="w-full py-2 px-4 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 text-sm"
            >
              Hint
            </button>
          )}

          <button
            onClick={onUndo}
            disabled={isLoading}
            className="w-full py-2 px-4 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 text-sm"
          >
            Undo
          </button>

          <button
            onClick={onSwap}
            disabled={isLoading || !canSwap}
            className="w-full py-2 px-4 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 text-sm"
          >
            Swap Tile
          </button>
        </div>
      )}
    </div>
  );
}

export default Sidebar;
