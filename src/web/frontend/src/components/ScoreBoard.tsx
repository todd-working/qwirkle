// ScoreBoard component - displays player scores and current turn

interface ScoreBoardProps {
  scores: number[];
  currentPlayer: number;
  bagRemaining: number;
  gameOver: boolean;
  winner: number | null;
}

export function ScoreBoard({
  scores,
  currentPlayer,
  bagRemaining,
  gameOver,
  winner,
}: ScoreBoardProps) {
  return (
    <div className="bg-white rounded-xl shadow-md p-4">
      <div className="flex justify-around items-center">
        {/* Player 1 */}
        <div
          className={`
            text-center px-6 py-3 rounded-lg
            ${currentPlayer === 0 && !gameOver ? 'bg-blue-100 ring-2 ring-blue-500' : 'bg-gray-50'}
          `}
        >
          <div className="text-sm text-gray-500 font-medium">Player 1</div>
          <div className="text-3xl font-bold text-gray-800">{scores[0]}</div>
          {winner === 0 && (
            <div className="text-green-600 font-bold mt-1">Winner!</div>
          )}
        </div>

        {/* Center info */}
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-400">vs</div>
          <div className="text-sm text-gray-500 mt-2">
            {bagRemaining} tiles left
          </div>
        </div>

        {/* Player 2 */}
        <div
          className={`
            text-center px-6 py-3 rounded-lg
            ${currentPlayer === 1 && !gameOver ? 'bg-purple-100 ring-2 ring-purple-500' : 'bg-gray-50'}
          `}
        >
          <div className="text-sm text-gray-500 font-medium">Player 2</div>
          <div className="text-3xl font-bold text-gray-800">{scores[1]}</div>
          {winner === 1 && (
            <div className="text-green-600 font-bold mt-1">Winner!</div>
          )}
        </div>
      </div>

      {/* Tie message */}
      {gameOver && winner === null && (
        <div className="text-center mt-4 text-xl font-bold text-gray-600">
          It's a tie!
        </div>
      )}
    </div>
  );
}

export default ScoreBoard;
