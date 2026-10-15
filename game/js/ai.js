// Sholo Guti AI: negamax + alpha-beta over whole turns (chains expanded),
// iterative deepening, capture quiescence, small transposition table.
import { generateTurns, outcome, count, other, ADJ, JUMPS, POINTS, P1 } from './rules.js';

const LEVELS = {
  easy:   { depth: 1, time: 250,  noise: 60, blunder: 0.3 },
  medium: { depth: 3, time: 700,  noise: 12, blunder: 0.05 },
  hard:   { depth: 9, time: 1600, noise: 0,  blunder: 0 },
};

// Zobrist hashing
const Z = POINTS.map(() => [0, rnd32(), rnd32()]);
const ZTURN = rnd32();
function rnd32() { return (Math.random() * 0x100000000) >>> 0; }
function hash(s) {
  let h = s.turn === P1 ? 0 : ZTURN;
  for (let i = 0; i < s.board.length; i++) if (s.board[i]) h ^= Z[i][s.board[i]];
  return h >>> 0;
}

// Static evaluation from the point of view of the side to move.
function evaluate(s) {
  const me = s.turn, op = other(me), b = s.board;
  let score = 0, myMob = 0, opMob = 0, myHang = 0, opHang = 0;
  for (let i = 0; i < b.length; i++) {
    const v = b[i];
    if (!v) continue;
    const sign = v === me ? 1 : -1;
    score += 100 * sign;
    const p = POINTS[i];
    // centre control and gentle advancement
    score += sign * (4 - Math.abs(p.x) * 1.5 - Math.abs(p.z) * 0.8);
    for (const n of ADJ[i]) if (!b[n]) { if (v === me) myMob++; else opMob++; }
  }
  // count pieces that can be captured right now (by either side)
  for (let i = 0; i < b.length; i++) {
    const v = b[i];
    if (!v) continue;
    for (const j of JUMPS[i]) if (b[j.over] && b[j.over] !== v && !b[j.to]) { if (v === me) opHang++; else myHang++; }
  }
  score += 2 * (myMob - opMob);
  // side to move benefits from its own threats more than it suffers
  score += 18 * Math.min(opHang, 3) - 8 * Math.min(myHang, 3);
  return score;
}

const WIN = 100000;

export function chooseTurn(state, level = 'medium') {
  const cfg = LEVELS[level] || LEVELS.medium;
  const start = performance.now();
  const deadline = start + cfg.time;
  const tt = new Map();
  let nodes = 0, timeUp = false;

  function search(s, depth, alpha, beta, ply) {
    nodes++;
    if ((nodes & 1023) === 0 && performance.now() > deadline) timeUp = true;
    if (timeUp) return 0;
    const o = outcome(s);
    if (o) return o.winner === 0 ? 0 : (o.winner === s.turn ? WIN - ply : -WIN + ply);
    const h = hash(s);
    const e = tt.get(h);
    if (e && e.depth >= depth) {
      if (e.flag === 0) return e.val;
      if (e.flag === 1 && e.val >= beta) return e.val;
      if (e.flag === -1 && e.val <= alpha) return e.val;
    }
    let turns = generateTurns(s);
    if (depth <= 0) {
      // quiescence: only look at captures, limited depth
      const stand = evaluate(s);
      if (depth < -3) return stand;
      if (stand >= beta) return stand;
      if (stand > alpha) alpha = stand;
      turns = turns.filter((t) => t.caps > 0);
      if (!turns.length) return stand;
    }
    turns.sort((a, b) => b.caps - a.caps);
    const a0 = alpha;
    let best = -Infinity;
    for (let i = 0; i < turns.length; i++) {
      const t = turns[i];
      const v = -search(t.state, depth - 1, -beta, -alpha, ply + 1);
      if (timeUp) return 0;
      if (v > best) best = v;
      if (v > alpha) alpha = v;
      if (alpha >= beta) break;
    }
    if (depth > 0) tt.set(h, { depth, val: best, flag: best <= a0 ? -1 : best >= beta ? 1 : 0 });
    return best;
  }

  const root = generateTurns(state);
  if (root.length === 0) return null;
  if (root.length === 1) return root[0].actions;

  let scored = root.map((t) => ({ t, v: t.caps * 100 }));
  for (let d = 1; d <= cfg.depth; d++) {
    const res = [];
    let alpha = -Infinity;
    scored.sort((a, b) => b.v - a.v);
    for (const { t } of scored) {
      const v = -search(t.state, d - 1, -Infinity, -(alpha - 2 * cfg.noise - 1), 1);
      if (timeUp) break;
      res.push({ t, v });
      if (v > alpha) alpha = v;
    }
    if (timeUp) { if (res.length) { const done = new Set(res.map((r) => r.t)); scored = res.concat(scored.filter((r) => !done.has(r.t))); } break; }
    scored = res;
    if (Math.abs(alpha) > WIN - 100) break;
  }
  // difficulty noise
  scored.forEach((r) => (r.v += (Math.random() * 2 - 1) * cfg.noise));
  scored.sort((a, b) => b.v - a.v);
  if (cfg.blunder && Math.random() < cfg.blunder && scored.length > 2) {
    return scored[1 + Math.floor(Math.random() * Math.min(3, scored.length - 1))].t.actions;
  }
  return scored[0].t.actions;
}
