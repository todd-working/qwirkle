// Main Qwirkle App component

import { useState, useMemo } from 'react';
import { DndContext, DragOverlay } from '@dnd-kit/core';
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import { useGame } from './hooks/useGame';
import { Board } from './components/Board';
import { Hand } from './components/Hand';
import { Sidebar } from './components/Sidebar';
import { MiniMap } from './components/MiniMap';
import { TileDisplay } from './components/Tile';
import { calculatePendingScore } from './utils/scoring';
import type { TileData } from './types/game';

function App() {
  const {
    state,
    pendingPlacements,
    isLoading,
    error,
    hintMessage,
    hintPlacements,
    isAiVsAi,
    startGame,
    dropTile,
    confirmPlay,
    cancelPlay,
    swapSelected,
    undo,
    getHint,
    clearHint,
    stepAi,
  } = useGame();

  // Track which tile is being dragged
  const [draggingTile, setDraggingTile] = useState<TileData | undefined>(undefined);

  // Calculate pending score preview
  const pendingScore = useMemo(() => {
    if (!state || pendingPlacements.size === 0) {
      return { score: 0, qwirkles: 0 };
    }
    return calculatePendingScore(state.board, pendingPlacements);
  }, [state, pendingPlacements]);

  // Handle drag start - track which tile is being dragged
  const handleDragStart = (event: DragStartEvent) => {
    if (event.active.data.current) {
      setDraggingTile(event.active.data.current.tile as TileData);
      // Clear any hint highlighting when user starts dragging
      clearHint();
    }
  };

  // Handle drag end - place tile on board
  const handleDragEnd = (event: DragEndEvent) => {
    setDraggingTile(undefined);
    const { active, over } = event;

    if (over && active.data.current) {
      const { index } = active.data.current;
      const { row, col } = over.data.current as { row: number; col: number };

      // Directly drop the tile at the position
      dropTile(index, row, col);
    }
  };

  // Start screen
  if (!state) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
          <h1 className="text-4xl font-bold text-center text-gray-800 mb-2">
            Qwirkle
          </h1>
          <p className="text-center text-gray-500 mb-8">
            Match shapes and colors to score points
          </p>

          <div className="space-y-4">
            <button
              onClick={() => startGame(false)}
              disabled={isLoading}
              className="w-full py-3 px-6 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium text-lg transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Starting...' : 'Play Local (2 Players)'}
            </button>

            <button
              onClick={() => startGame(true, 'greedy')}
              disabled={isLoading}
              className="w-full py-3 px-6 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium text-lg transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Starting...' : 'Play vs AI'}
            </button>

            <button
              onClick={() => startGame(false, 'greedy', true)}
              disabled={isLoading}
              className="w-full py-3 px-6 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium text-lg transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Starting...' : 'Watch AI vs AI'}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-lg text-center">
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Game screen
  return (
    <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <div className="bg-white shadow-sm px-4 py-3">
          <div className="max-w-6xl mx-auto flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-800">Qwirkle</h1>
            <button
              onClick={() => window.location.reload()}
              className="py-2 px-4 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              New Game
            </button>
          </div>
        </div>

        {/* Main content */}
        <div className="max-w-6xl mx-auto p-4">
          <div className="flex gap-4">
            {/* Sidebar */}
            <Sidebar
              scores={state.scores}
              currentPlayer={state.current_player}
              bagRemaining={state.bag_remaining}
              gameOver={state.game_over}
              winner={state.winner}
              isAiVsAi={isAiVsAi}
              isLoading={isLoading}
              canSwap={state.bag_remaining > 0}
              onHint={getHint}
              onUndo={undo}
              onSwap={swapSelected}
            />

            {/* Main area */}
            <div className="flex-1 space-y-4">
              {/* Message */}
              {(state.message || hintMessage || error) && (
                <div
                  className={`
                    p-3 rounded-lg text-center font-medium
                    ${error ? 'bg-red-100 text-red-700' : ''}
                    ${hintMessage ? 'bg-blue-100 text-blue-700' : ''}
                    ${!error && !hintMessage ? 'bg-green-100 text-green-700' : ''}
                  `}
                >
                  {error || hintMessage || state.message}
                </div>
              )}

              {/* Board with Mini-map overlay */}
              <div className="relative">
                <Board
                  board={state.board}
                  pendingPlacements={pendingPlacements}
                  lastMovePositions={state.last_move_positions}
                  draggingTile={draggingTile}
                  hintPositions={hintPlacements}
                />

                {/* Mini-map overlay */}
                <div className="absolute top-2 right-2 opacity-90 hover:opacity-100 transition-opacity">
                  <MiniMap
                    board={state.board}
                    pendingPlacements={pendingPlacements}
                  />
                </div>
              </div>

              {/* Score Preview */}
              {!state.game_over && !isAiVsAi && pendingPlacements.size > 0 && (
                <div className="bg-white rounded-xl p-4 shadow-lg border-2 border-yellow-400">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🎯</span>
                      <div>
                        <div className="text-lg font-bold text-gray-800">
                          +{pendingScore.score} points
                        </div>
                        {pendingScore.qwirkles > 0 && (
                          <div className="text-sm text-purple-600 font-medium">
                            🌟 QWIRKLE! (+6 bonus)
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={confirmPlay}
                        disabled={isLoading}
                        className="py-2 px-6 bg-green-500 hover:bg-green-600 text-white rounded-lg font-bold transition-colors disabled:opacity-50"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={cancelPlay}
                        disabled={isLoading}
                        className="py-2 px-4 bg-gray-400 hover:bg-gray-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* AI vs AI Controls */}
              {!state.game_over && isAiVsAi && (
                <div className="flex justify-center gap-4">
                  <button
                    onClick={stepAi}
                    disabled={isLoading}
                    className="py-3 px-8 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium text-lg transition-colors disabled:opacity-50"
                  >
                    {isLoading ? 'Thinking...' : 'Next Move'}
                  </button>
                  <button
                    onClick={undo}
                    disabled={isLoading}
                    className="py-3 px-6 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    Undo
                  </button>
                </div>
              )}

              {/* Hand */}
              {!state.game_over && !isAiVsAi && (
                <Hand
                  tiles={state.hand}
                  usedIndices={new Set([...pendingPlacements.values()].map(p => p.index))}
                  disabled={isLoading}
                />
              )}

              {/* Game Over */}
              {state.game_over && (
                <div className="text-center py-8">
                  <button
                    onClick={() => window.location.reload()}
                    className="py-3 px-8 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium text-lg transition-colors"
                  >
                    Play Again
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      {/* Drag overlay - renders dragged tile smoothly */}
      <DragOverlay dropAnimation={null}>
        {draggingTile ? (
          <TileDisplay tile={draggingTile} size="lg" isDragOverlay />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default App;
