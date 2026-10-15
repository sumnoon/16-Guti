// Sholo Guti rules engine — pure logic, no graphics.
// Board: 37 points. A 5×5 Alquerque-style grid (x -2..2, z -2..2) plus a
// 6-point triangle on each end (z -3,-4 and z 3,4). Player 1 sits at +z
// (near the camera), player 2 at -z.

export const P1 = 1, P2 = 2;
export const other = (p) => (p === P1 ? P2 : P1);

// ---- Geometry -------------------------------------------------------------
export const POINTS = [];
const idx = new Map();
const key = (x, z) => x + ',' + z;
function addPoint(x, z) { idx.set(key(x, z), POINTS.length); POINTS.push({ x, z }); }

for (let z = -4; z <= 4; z++) {
  if (Math.abs(z) <= 2) for (let x = -2; x <= 2; x++) addPoint(x, z);
  else if (Math.abs(z) === 3) for (const x of [-1, 0, 1]) addPoint(x, z);
  else for (const x of [-2, 0, 2]) addPoint(x, z);
}
export const pointAt = (x, z) => idx.get(key(x, z));

// Lines as ordered point sequences. Adjacency = consecutive points on a line;
// a jump = three consecutive points on one line.
const raw = [];
for (let z = -2; z <= 2; z++) raw.push([-2, -1, 0, 1, 2].map((x) => [x, z]));       // rows
for (let x = -2; x <= 2; x++) {
  const zs = x === 0 ? [-4, -3, -2, -1, 0, 1, 2, 3, 4] : [-2, -1, 0, 1, 2];
  raw.push(zs.map((z) => [x, z]));                                                     // columns
}
for (const s of [-1, 1]) {
  raw.push([-1, 0, 1].map((x) => [x, 3 * s]));                                         // triangle bars
  raw.push([-2, 0, 2].map((x) => [x, 4 * s]));
}
// Diagonals through points where x+z is even, extended through the triangles.
for (let c = -2; c <= 2; c += 2) {
  const a = [], b = [];
  for (let x = -2; x <= 2; x++) {
    for (let z = -4; z <= 4; z++) {
      if (x - z === c && idx.has(key(x, z))) a.push([x, z]);
      if (x + z === c && idx.has(key(x, z))) b.push([x, z]);
    }
  }
  a.sort((p, q) => p[0] - q[0]); b.sort((p, q) => p[0] - q[0]);
  raw.push(a, b);
}
export const LINES = raw.map((l) => l.map(([x, z]) => pointAt(x, z)));

export const ADJ = POINTS.map(() => []);
export const JUMPS = POINTS.map(() => []); // {over, to}
for (const line of LINES) {
  for (let i = 0; i < line.length; i++) {
    if (i + 1 < line.length) { ADJ[line[i]].push(line[i + 1]); ADJ[line[i + 1]].push(line[i]); }
    if (i + 2 < line.length) {
      JUMPS[line[i]].push({ over: line[i + 1], to: line[i + 2] });
      JUMPS[line[i + 2]].push({ over: line[i + 1], to: line[i] });
    }
  }
}
// Edges for drawing the board.
export const EDGES = [];
for (const line of LINES) for (let i = 0; i + 1 < line.length; i++) EDGES.push([line[i], line[i + 1]]);

// ---- State ------------------------------------------------------------------
export const DEFAULT_OPTIONS = { forcedCapture: false, drawPlies: 60 };

export function initialState(options = {}) {
  const board = new Int8Array(POINTS.length);
  POINTS.forEach((p, i) => { if (p.z >= 1) board[i] = P1; else if (p.z <= -1) board[i] = P2; });
  return { board, turn: P1, chain: -1, quiet: 0, ply: 0, options: { ...DEFAULT_OPTIONS, ...options } };
}

export function cloneState(s) {
  return { board: s.board.slice(), turn: s.turn, chain: s.chain, quiet: s.quiet, ply: s.ply, options: s.options };
}

export const count = (s, p) => { let n = 0; for (const v of s.board) if (v === p) n++; return n; };

function jumpsFrom(board, i, p) {
  const out = [];
  for (const j of JUMPS[i]) if (board[j.over] === other(p) && board[j.to] === 0) out.push({ from: i, to: j.to, over: j.over });
  return out;
}

// Legal actions for the side to move. {from,to,over?} or {end:true}
export function legalActions(s) {
  const { board, turn: p } = s;
  if (s.chain >= 0) {
    const js = jumpsFrom(board, s.chain, p);
    if (!s.options.forcedCapture) js.push({ end: true });
    return js;
  }
  const jumps = [], steps = [];
  for (let i = 0; i < board.length; i++) {
    if (board[i] !== p) continue;
    for (const j of jumpsFrom(board, i, p)) jumps.push(j);
    for (const n of ADJ[i]) if (board[n] === 0) steps.push({ from: i, to: n });
  }
  return s.options.forcedCapture && jumps.length ? jumps : jumps.concat(steps);
}

export function applyAction(s, a) {
  const n = cloneState(s);
  n.ply++;
  if (a.end) { n.chain = -1; n.turn = other(s.turn); return n; }
  n.board[a.to] = n.board[a.from];
  n.board[a.from] = 0;
  if (a.over !== undefined) {
    n.board[a.over] = 0;
    n.quiet = 0;
    if (jumpsFrom(n.board, a.to, s.turn).length) { n.chain = a.to; return n; } // may keep jumping
  } else n.quiet++;
  n.chain = -1;
  n.turn = other(s.turn);
  return n;
}

// Returns {winner, reason} or null.
export function outcome(s) {
  const c1 = count(s, P1), c2 = count(s, P2);
  if (c1 === 0) return { winner: P2, reason: 'all-captured' };
  if (c2 === 0) return { winner: P1, reason: 'all-captured' };
  if (s.chain < 0 && legalActions(s).length === 0) return { winner: other(s.turn), reason: 'blocked' };
  if (s.quiet >= s.options.drawPlies) return { winner: 0, reason: 'draw' };
  return null;
}

// ---- Turn generation (chains expanded) for the AI ------------------------------
// Each turn = { actions:[...], state, caps }
export function generateTurns(s) {
  const out = [];
  const rec = (st, acts, caps) => {
    const as = legalActions(st);
    for (const a of as) {
      const ns = applyAction(st, a);
      const nacts = acts.concat([a]);
      const ncaps = caps + (a.over !== undefined ? 1 : 0);
      if (ns.turn === st.turn && ns.chain >= 0) rec(ns, nacts, ncaps);
      else out.push({ actions: nacts, state: ns, caps: ncaps });
    }
  };
  rec(s, [], 0);
  return out;
}
