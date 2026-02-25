import { createInitialState, makeMove, checkWinner, resetGame } from './src/game_logic.mjs';
const state = createInitialState();
const boardEl  = document.getElementById('board');
const statusEl = document.getElementById('status');
const resetBtn = document.getElementById('reset-btn');
function getWinningIndices(board) {
  const WIN_LINES = [
    [0,1,2],[3,4,5],[6,7,8],
    [0,3,6],[1,4,7],[2,5,8],
    [0,4,8],[2,4,6],
  ];
  for (const line of WIN_LINES) {
    const [a,b,c] = line;
    if (board[a] && board[a] === board[b] && board[a] === board[c]) return line;
  }
  return [];
}
function render() {
  const winLine = state.status === 'won' ? getWinningIndices(state.board) : [];
  boardEl.innerHTML = '';
  state.board.forEach((cell, i) => {
    const div = document.createElement('div');
    div.className = 'cell' +
      (cell ? ` taken ${cell.toLowerCase()}` : '') +
      (winLine.includes(i) ? ' winning' : '');
    div.textContent = cell ?? '';
    div.addEventListener('click', () => {
      makeMove(state, i);
      render();
    });
    boardEl.appendChild(div);
  });
  statusEl.className = 'status';
  if (state.status === 'won') {
    statusEl.textContent = `Player ${state.winner} wins!`;
    statusEl.classList.add('won');
  } else if (state.status === 'draw') {
    statusEl.textContent = "It's a draw!";
    statusEl.classList.add('draw');
  } else {
    statusEl.textContent = `Player ${state.currentPlayer}'s turn`;
  }
}
resetBtn.addEventListener('click', () => { resetGame(state); render(); });
// Playwright / test hook
window.render_game_to_text = () => {
  const b = state.board.map((c) => c ?? '.');
  return [
    `${b[0]}|${b[1]}|${b[2]}`,
    `-+-+-`,
    `${b[3]}|${b[4]}|${b[5]}`,
    `-+-+-`,
    `${b[6]}|${b[7]}|${b[8]}`,
    ``,
    `Status: ${state.status}  Player: ${state.currentPlayer}  Winner: ${state.winner ?? '-'}`,
  ].join('\n');
};
render();