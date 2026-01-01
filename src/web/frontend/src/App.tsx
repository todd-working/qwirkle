// Main Qwirkle App component

import { useState } from 'react';
import { DndContext } from '@dnd-kit/core';
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import { useGame } from './hooks/useGame';
import { Board } from './components/Board';
import { Hand } from './components/Hand';
import { ScoreBoard } from './components/ScoreBoard';
import { GameControls } from './components/GameControls';
import type { TileData } from './types/game';

function App() {
  const {
    state,
    pendingPlacements,
    isLoading,
    error,
    hintMessage,
    startGame,
    dropTile,
    confirmPlay,
    cancelPlay,
    swapSelected,
    undo,
    getHint,
  } = useGame();

  // Track which tile is being dragged
  const [draggingTile, setDraggingTile] = useState<TileData | undefined>(undefined);

  // Handle drag start - track which tile is being dragged
  const handleDragStart = (event: DragStartEvent) => {
    if (event.active.data.current) {
      setDraggingTile(event.active.data.current.tile as TileData);
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
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Header */}
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-800">Qwirkle</h1>
            <button
              onClick={() => window.location.reload()}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              New Game
            </button>
          </div>

          {/* Score Board */}
          <ScoreBoard
            scores={state.scores}
            currentPlayer={state.current_player}
            bagRemaining={state.bag_remaining}
            gameOver={state.game_over}
            winner={state.winner}
          />

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

          {/* Board */}
          <Board
            board={state.board}
            pendingPlacements={pendingPlacements}
            lastMovePositions={state.last_move_positions}
            draggingTile={draggingTile}
          />

          {/* Controls */}
          {!state.game_over && (
            <GameControls
              hasPendingPlacements={pendingPlacements.size > 0}
              canUndo={true}
              canSwap={state.bag_remaining > 0}
              isLoading={isLoading}
              onConfirm={confirmPlay}
              onCancel={cancelPlay}
              onUndo={undo}
              onHint={getHint}
              onSwap={swapSelected}
            />
          )}

          {/* Hand */}
          {!state.game_over && (
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
    </DndContext>
  );
}

export default App;
