const TRACK_WIDTH = 900;
const TRACK_HEIGHT = 650;
const PLAYER_RADIUS = 16;
const PLAYER_ACCEL = 450;
const PLAYER_DRAG = 0.9;
const BULLET_SPEED = 620;
const BULLET_RADIUS = 4;
const FIRE_COOLDOWN_MS = 130;
const ENEMY_RADIUS = 18;
const ENEMY_HP = 2;

const CHECKPOINTS = [
  { x: 120, y: 120, radius: 40 },
  { x: 780, y: 120, radius: 40 },
  { x: 780, y: 530, radius: 40 },
  { x: 120, y: 530, radius: 40 },
];

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function distanceSq(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return dx * dx + dy * dy;
}

export function createInitialState(overrides = {}) {
  return {
    mode: overrides.mode ?? 'menu',
    track: { width: TRACK_WIDTH, height: TRACK_HEIGHT, checkpoints: CHECKPOINTS },
    lap: 1,
    nextCheckpointIndex: 0,
    score: 0,
    elapsedMs: 0,
    player: {
      x: 120,
      y: 120,
      vx: 0,
      vy: 0,
      radius: PLAYER_RADIUS,
      angle: 0,
      hp: 100,
      heroClass: 'Vanguard',
      input: { up: false, down: false, left: false, right: false },
    },
    enemies: [
      { id: 'enemy-1', x: 260, y: 120, radius: ENEMY_RADIUS, hp: ENEMY_HP },
      { id: 'enemy-2', x: 620, y: 340, radius: ENEMY_RADIUS, hp: ENEMY_HP },
    ],
    bullets: [],
    fireCooldownMs: 0,
    lastShotAtMs: -Infinity,
  };
}

export function applyInput(state, input) {
  state.player.input = {
    up: Boolean(input.up),
    down: Boolean(input.down),
    left: Boolean(input.left),
    right: Boolean(input.right),
  };
}

export function firePrimary(state) {
  if (state.mode !== 'playing') return false;
  if (state.fireCooldownMs > 0) return false;

  const aimX = Math.cos(state.player.angle);
  const aimY = Math.sin(state.player.angle);

  state.bullets.push({
    x: state.player.x + aimX * (state.player.radius + 8),
    y: state.player.y + aimY * (state.player.radius + 8),
    vx: aimX * BULLET_SPEED,
    vy: aimY * BULLET_SPEED,
    radius: BULLET_RADIUS,
    ttlMs: 1400,
  });

  state.fireCooldownMs = FIRE_COOLDOWN_MS;
  state.lastShotAtMs = state.elapsedMs;
  return true;
}

function updatePlayer(state, dtSeconds) {
  const { input } = state.player;
  const axisX = (input.right ? 1 : 0) - (input.left ? 1 : 0);
  const axisY = (input.down ? 1 : 0) - (input.up ? 1 : 0);

  if (axisX !== 0 || axisY !== 0) {
    const len = Math.hypot(axisX, axisY);
    const normX = axisX / len;
    const normY = axisY / len;
    state.player.vx += normX * PLAYER_ACCEL * dtSeconds;
    state.player.vy += normY * PLAYER_ACCEL * dtSeconds;
    state.player.angle = Math.atan2(normY, normX);
  }

  state.player.vx *= PLAYER_DRAG;
  state.player.vy *= PLAYER_DRAG;
  state.player.x = clamp(state.player.x + state.player.vx * dtSeconds, PLAYER_RADIUS, TRACK_WIDTH - PLAYER_RADIUS);
  state.player.y = clamp(state.player.y + state.player.vy * dtSeconds, PLAYER_RADIUS, TRACK_HEIGHT - PLAYER_RADIUS);
}

function updateCheckpoints(state) {
  const checkpoint = CHECKPOINTS[state.nextCheckpointIndex];
  const reachDistance = checkpoint.radius + state.player.radius;
  if (distanceSq(state.player, checkpoint) <= reachDistance * reachDistance) {
    state.nextCheckpointIndex += 1;
    if (state.nextCheckpointIndex >= CHECKPOINTS.length) {
      state.nextCheckpointIndex = 0;
      state.lap += 1;
      state.score += 50;
    }
  }
}

function updateBulletsAndEnemies(state, dtMs, dtSeconds) {
  for (const bullet of state.bullets) {
    bullet.x += bullet.vx * dtSeconds;
    bullet.y += bullet.vy * dtSeconds;
    bullet.ttlMs -= dtMs;
  }

  const liveBullets = [];
  for (const bullet of state.bullets) {
    let hitEnemy = false;
    for (const enemy of state.enemies) {
      const hitRange = bullet.radius + enemy.radius;
      if (distanceSq(bullet, enemy) <= hitRange * hitRange) {
        enemy.hp -= 1;
        hitEnemy = true;
        if (enemy.hp <= 0) {
          state.score += 100;
        }
        break;
      }
    }

    const inBounds =
      bullet.x >= 0 && bullet.x <= TRACK_WIDTH && bullet.y >= 0 && bullet.y <= TRACK_HEIGHT && bullet.ttlMs > 0;
    if (!hitEnemy && inBounds) {
      liveBullets.push(bullet);
    }
  }

  state.bullets = liveBullets;
  state.enemies = state.enemies.filter((enemy) => enemy.hp > 0);
}

export function stepGame(state, dtMs) {
  if (state.mode !== 'playing') return;

  const dtSeconds = dtMs / 1000;
  state.elapsedMs += dtMs;
  state.fireCooldownMs = Math.max(0, state.fireCooldownMs - dtMs);

  updatePlayer(state, dtSeconds);
  updateCheckpoints(state);
  updateBulletsAndEnemies(state, dtMs, dtSeconds);
}

export function advanceTime(state, totalMs) {
  const stepMs = 1000 / 60;
  let remaining = totalMs;
  while (remaining > 0) {
    const dt = Math.min(stepMs, remaining);
    stepGame(state, dt);
    remaining -= dt;
  }
}
