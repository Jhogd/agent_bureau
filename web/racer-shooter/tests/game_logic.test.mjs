import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialState,
  advanceTime,
  firePrimary,
  applyInput,
} from '../src/game_logic.mjs';

test('completes a lap only after all checkpoints are reached in order', () => {
  const state = createInitialState({ mode: 'playing' });

  applyInput(state, { right: true, up: false, left: false, down: false });
  advanceTime(state, 2000);
  applyInput(state, { right: false, up: true, left: false, down: false });
  advanceTime(state, 2200);
  applyInput(state, { right: false, up: false, left: true, down: false });
  advanceTime(state, 2200);
  applyInput(state, { right: false, up: false, left: false, down: true });
  advanceTime(state, 2200);

  assert.equal(state.lap, 2);
  assert.equal(state.nextCheckpointIndex, 0);
});

test('primary fire damages and removes enemy then awards score', () => {
  const state = createInitialState({ mode: 'playing' });
  const enemyId = state.enemies[0].id;

  firePrimary(state);
  advanceTime(state, 200);

  firePrimary(state);
  advanceTime(state, 400);

  assert.equal(state.enemies.find((enemy) => enemy.id === enemyId), undefined);
  assert.equal(state.score, 100);
});
