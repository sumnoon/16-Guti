import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as R from './rules.js';
import { chooseTurn } from './ai.js';
import { buildWorld, toWorld, SPACING, makeGlowTex, makeSoftShadowTex } from './world.js';
import { Pieces, PIECE_SETS } from './pieces.js';
import { Sfx } from './audio.js';

const $ = (id) => document.getElementById(id);
const store = {
  get(k, d) { try { const v = localStorage.getItem('sholo.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('sholo.' + k, JSON.stringify(v)); } catch {} },
};

// ------------------------------------------------------------------ settings
const isTouch = matchMedia('(pointer: coarse)').matches;
const settings = {
  level: store.get('level', 'medium'),
  pieces: store.get('pieces', 'pebbles'),
  time: store.get('time', 'afternoon'),
  forced: store.get('forced', false),
  quality: store.get('quality', isTouch || (navigator.hardwareConcurrency || 8) <= 4 ? 0 : 1),
  sound: store.get('sound', true),
};

// ------------------------------------------------------------------ renderer
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
// Battery saver renders at CSS-pixel resolution: on phones (devicePixelRatio 2.5-3) that is the biggest single saving.
renderer.setPixelRatio(Math.min(devicePixelRatio, settings.quality ? 2 : 1));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.02, 900);
camera.position.set(9, 4.5, 9);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08;
controls.minDistance = 0.35; controls.maxDistance = 4.5;
controls.maxPolarAngle = THREE.MathUtils.degToRad(84);
controls.target.set(0, 0, -0.02);
controls.enabled = false;
controls.enablePan = false;

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.fov = w / h < 0.8 ? 60 : 50; // portrait phones need a wider lens
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

// ------------------------------------------------------------------ loading
const sfx = new Sfx(); sfx.on = settings.sound;
const manager = new THREE.LoadingManager();
manager.onProgress = (_u, done, total) => { $('loadbar').style.transform = `scaleX(${done / total})`; $('loadpct').textContent = Math.round((done / total) * 100) + '%'; };
const texLoader = new THREE.TextureLoader(manager);
const gltf = new GLTFLoader(manager);
const MODELS = ['guti_pebble_variations', 'guti_clay_shard', 'guti_tamarind_seed', 'prop_banyan_tree', 'prop_house', 'prop_fence', 'prop_haystack',
  'prop_banana_tree', 'prop_chula', 'prop_pots', 'prop_kolshi', 'prop_chouki', 'prop_dala', 'prop_kula', 'prop_clothesline', 'prop_jharu',
  'prop_pati', 'prop_piri', 'prop_lantern', 'prop_chicken'];
const tex = { pano: {} };
const models = {};
function loadTex(url, srgb = true, repeat = true) {
  return new Promise((res, rej) => texLoader.load(url, (t) => {
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); }
    res(t);
  }, undefined, rej));
}
// Models ship as base64-wrapped GLB inside JSON so any static host can serve them.
function loadModel(name) {
  const url = `assets/models/${name}.json`;
  manager.itemStart(url);
  return fetch(url).then((r) => { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); })
    .then((o) => { const bin = atob(o.glb), buf = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i); return gltf.parseAsync(buf.buffer, ''); })
    .finally(() => manager.itemEnd(url));
}
async function loadAll() {
  const jobs = [
    loadTex('assets/tex/ground_mud.jpg').then((t) => (tex.mud = t)),
    loadTex('assets/tex/ground_mud_n.jpg', false).then((t) => (tex.mudN = t)),
    loadTex('assets/tex/ground_rough.jpg').then((t) => (tex.rough = t)),
    ...['afternoon', 'sunset', 'night'].map((k) => loadTex(`assets/tex/pano_${k}.jpg`, true, false).then((t) => { t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; tex.pano[k] = t; })),
    ...MODELS.map((m) => loadModel(m).then((g) => { models[m] = g.scene; g.scene.animations = g.animations; })),
  ];
  await Promise.all(jobs);
  tex.glow = makeGlowTex(); tex.shadow = makeSoftShadowTex();
}

// ------------------------------------------------------------------ game state
let world, pieces;
let state = R.initialState({ forcedCapture: settings.forced });
let mode = 'ai';               // 'ai' | 'local'
let history = [];              // states at the start of each human turn
let phase = 'menu';            // menu | play | over
let thinking = false, chainCount = 0, view = 'seat';
const HUMAN = R.P1, AI = R.P2;

const names = () => mode === 'ai' ? { [R.P1]: 'You', [R.P2]: 'Dadu' } : { [R.P1]: 'Player 1', [R.P2]: 'Player 2' };
const colourName = (p) => settings.pieces === 'pebbles' ? (p === R.P1 ? 'cream' : 'slate') : (p === R.P1 ? 'clay' : 'tamarind');
const isHumanTurn = () => phase === 'play' && (mode === 'local' || state.turn === HUMAN);

// AI worker (falls back to the main thread)
let worker = null, reqId = 0; const pending = new Map();
try {
  worker = new Worker(new URL('./ai-worker.js', import.meta.url), { type: 'module' });
  worker.onmessage = (e) => { const r = pending.get(e.data.id); if (r) { pending.delete(e.data.id); r(e.data.actions); } };
  worker.onerror = () => { worker = null; };
} catch { worker = null; }
function askAI(s) {
  const plain = { ...s, board: Array.from(s.board) };
  if (worker) return new Promise((res) => { const id = ++reqId; pending.set(id, res); worker.postMessage({ id, state: plain, level: settings.level }); setTimeout(() => { if (pending.has(id)) { pending.delete(id); res(chooseTurn(s, settings.level)); } }, 6000); });
  return new Promise((res) => setTimeout(() => res(chooseTurn(s, settings.level)), 30));
}

// ------------------------------------------------------------------ camera moves
let camAnim = null;
function seatPose(player) {
  const s = player === R.P2 ? -1 : 1;
  const portrait = innerWidth / innerHeight < 0.8;
  return { pos: new THREE.Vector3(0, portrait ? 1.0 : 0.5, s * (portrait ? 0.9 : 1.0)), target: new THREE.Vector3(0, portrait ? 0.0 : 0.16, s * (portrait ? -0.1 : -0.14)) };
}
function topPose(player) { const s = player === R.P2 ? -1 : 1; const portrait = innerWidth / innerHeight < 0.8; return { pos: new THREE.Vector3(0, portrait ? 1.5 : 1.12, s * 0.012), target: new THREE.Vector3(0, 0, s * -0.005) }; }
function flyTo(pose, dur = 1.2) {
  camAnim = { t: 0, dur, p0: camera.position.clone(), t0: controls.target.clone(), p1: pose.pos, t1: pose.target };
  controls.enabled = false;
}
function facing() { return mode === 'local' && store.get('rotate', true) ? state.turn : HUMAN; }
function homeView(dur) { flyTo(view === 'top' ? topPose(facing()) : seatPose(facing()), dur); }

// ------------------------------------------------------------------ HUD
function pips(el, n, player) {
  el.innerHTML = '';
  for (let i = 0; i < 16; i++) { const d = document.createElement('i'); if (i >= n) d.className = 'gone'; el.appendChild(d); }
  el.dataset.player = player;
}
function updateHud(msg) {
  const nm = names();
  $('name1').textContent = nm[R.P1]; $('name2').textContent = nm[R.P2];
  const c1 = R.count(state, R.P1), c2 = R.count(state, R.P2);
  pips($('pips1'), c1, 1); pips($('pips2'), c2, 2);
  $('card1').classList.toggle('active', state.turn === R.P1 && phase === 'play');
  $('card2').classList.toggle('active', state.turn === R.P2 && phase === 'play');
  $('avatar2').classList.toggle('dadu', mode === 'ai');
  document.body.dataset.pieces = settings.pieces;
  let s = msg;
  if (!s) {
    if (thinking) s = 'Dadu is thinking…';
    else if (state.chain >= 0) s = settings.forced ? 'Keep jumping' : 'Jump again, or end your turn';
    else s = mode === 'ai' ? 'Your move' : `${nm[state.turn]} to move (${colourName(state.turn)})`;
  }
  $('status').textContent = s;
  const left = state.options.drawPlies - state.quiet;
  $('drawnote').hidden = !(left <= 20 && phase === 'play');
  $('drawnote').textContent = `Draw in ${left} moves without a capture`;
  $('endturn').hidden = !(state.chain >= 0 && !settings.forced && isHumanTurn());
  $('undo').disabled = !history.length || thinking || pieces?.busy;
}

// ------------------------------------------------------------------ turn flow
function newGame(m) {
  mode = m;
  state = R.initialState({ forcedCapture: settings.forced });
  history = []; chainCount = 0; thinking = false;
  pieces.build(state.board);
  phase = 'play';
  document.body.classList.add('playing');
  $('menu').hidden = true; $('result').hidden = true;
  view = 'seat';
  flyTo(seatPose(HUMAN), 2.4);
  updateHud();
  setTimeout(() => prepareTurn(), 2400);
}

function prepareTurn() {
  if (phase !== 'play') return;
  const o = R.outcome(state);
  if (o) return finish(o);
  updateHud();
  if (mode === 'ai' && state.turn === AI) return aiTurn();
  if (state.chain >= 0) { pieces.select(state.chain); pieces.showHints(R.legalActions(state)); }
}

async function aiTurn() {
  thinking = true; updateHud();
  const t0 = performance.now();
  const acts = await askAI(state);
  const wait = 650 - (performance.now() - t0);
  if (wait > 0) await new Promise((r) => setTimeout(r, wait));
  thinking = false;
  if (phase !== 'play' || !acts) { updateHud(); return; }
  for (let i = 0; i < acts.length; i++) {
    const a = acts[i];
    if (a.end) { state = R.applyAction(state, a); break; }
    pieces.select(a.from); await new Promise((r) => setTimeout(r, i ? 180 : 320));
    await perform(a, true);
  }
  prepareTurn();
}

async function perform(a, byAI = false) {
  const isCap = a.over !== undefined;
  chainCount = state.chain >= 0 ? chainCount + 1 : (isCap ? 1 : 0);
  const slow = isCap && chainCount >= 2;
  const anim = pieces.play(a, { slow });
  if (isCap) reactToCapture(a, slow);
  await anim;
  state = R.applyAction(state, a);
  updateHud();
}

function reactToCapture(a, slow) {
  const at = toWorld(a.over);
  world.chickens.scare(at, 6);
  world.dropLeaves(slow ? 7 : 3, at);
  if (slow && view === 'seat') {
    // a small cinematic push-in on chains
    const p = toWorld(a.to);
    const pos = camera.position.clone().lerp(new THREE.Vector3(p.x, 0.32, p.z + Math.sign(camera.position.z || 1) * 0.42), 0.35);
    camAnim = { t: 0, dur: 0.9, p0: camera.position.clone(), t0: controls.target.clone(), p1: pos, t1: p.clone(), back: true };
    controls.enabled = false;
  }
  const c1 = R.count(state, R.P1), c2 = R.count(state, R.P2);
  if (Math.min(c1, c2) <= 4) sfx.windGain && sfx.windGain.gain.setTargetAtTime(0.09, sfx.ctx.currentTime, 2);
}

function finish(o) {
  phase = 'over'; document.body.classList.remove('playing');
  pieces.select(-1); pieces.clearHints();
  const nm = names();
  let title, sub;
  if (o.winner === 0) { title = 'Draw'; sub = `${state.options.drawPlies} moves passed without a capture.`; }
  else {
    const youWon = mode === 'ai' && o.winner === HUMAN;
    title = mode === 'ai' ? (youWon ? 'You win' : 'Dadu wins') : `${nm[o.winner]} wins`;
    sub = o.reason === 'blocked' ? `${nm[R.other(o.winner)]} has no legal move left.` : `Every one of ${mode === 'ai' && o.winner === HUMAN ? "Dadu's" : (mode === 'ai' ? 'your' : nm[R.other(o.winner)] + "'s")} 16 guti was captured.`;
    if (youWon) sub += ' “Shabash!” says Dadu.';
  }
  $('rtitle').textContent = title; $('rsub').textContent = sub;
  $('rstats').textContent = `${R.count(state, R.P1)} – ${R.count(state, R.P2)} guti left · ${Math.ceil(state.ply / 2)} ${Math.ceil(state.ply / 2) === 1 ? 'turn' : 'turns'}`;
  sfx.chord(o.winner !== AI || mode !== 'ai');
  setTimeout(() => { $('result').hidden = false; }, 900);
  updateHud(title);
  view = 'seat';
  flyTo({ pos: new THREE.Vector3(1.1, 0.75, 1.15), target: new THREE.Vector3(0, 0.0, -0.05) }, 3);
}

function undo() {
  if (!history.length || thinking || pieces.busy) return;
  state = history.pop();
  chainCount = 0;
  pieces.sync(Array.from(state.board));
  sfx.tick(); updateHud('Move taken back');
  prepareTurn();
}

// ------------------------------------------------------------------ input
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
function pointAtScreen(x, y) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  if (!ray.ray.intersectPlane(plane, hit)) return -1;
  let best = -1, bd = SPACING * 0.55;
  R.POINTS.forEach((p, i) => { const d = Math.hypot(p.x * SPACING - hit.x, p.z * SPACING - hit.z); if (d < bd) { bd = d; best = i; } });
  return best;
}

let down = null;
canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
canvas.addEventListener('pointerup', (e) => {
  if (!down) return;
  const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t; down = null;
  if (moved > 8 || dt > 600) return;
  tap(pointAtScreen(e.clientX, e.clientY));
});
canvas.addEventListener('pointermove', (e) => {
  if (e.pointerType !== 'mouse' || !isHumanTurn() || !pieces) return;
  const i = pointAtScreen(e.clientX, e.clientY);
  const legal = i >= 0 && (R.legalActions(state).some((a) => a.from === i || a.to === i));
  canvas.style.cursor = legal ? 'pointer' : '';
});

function tap(i) {
  if (!isHumanTurn() || thinking || pieces.busy) return;
  const legal = R.legalActions(state);
  if (state.chain >= 0) {
    const a = legal.find((x) => x.to === i && !x.end);
    if (a) return humanAct(a);
    if (i === state.chain && !settings.forced) return endChain();
    return;
  }
  const sel = pieces.selected;
  if (sel >= 0) {
    const a = legal.find((x) => x.from === sel && x.to === i);
    if (a) return humanAct(a);
  }
  if (i >= 0 && state.board[i] === state.turn) {
    const mine = legal.filter((x) => x.from === i);
    if (!mine.length) {
      const anyJump = legal.some((x) => x.over !== undefined);
      pieces.select(-1); pieces.clearHints();
      return updateHud(settings.forced && anyJump ? 'A capture is available, so you must jump' : 'That guti has nowhere to go');
    }
    sfx.tick(); pieces.select(i); pieces.showHints(mine); updateHud();
    return;
  }
  pieces.select(-1); pieces.clearHints(); updateHud();
}

async function humanAct(a) {
  if (state.chain < 0) history.push(R.cloneState(state));
  if (history.length > 200) history.shift();
  const before = state.turn;
  await perform(a);
  if (mode === 'local' && state.turn !== before && store.get('rotate', true)) homeView(1.4);
  prepareTurn();
}
function endChain() {
  if (state.chain < 0) return;
  state = R.applyAction(state, { end: true });
  pieces.select(-1); pieces.clearHints();
  if (mode === 'local' && store.get('rotate', true)) homeView(1.4);
  prepareTurn();
}

// ------------------------------------------------------------------ UI wiring
function seg(id, key, onChange) {
  const el = $(id);
  const sync = () => el.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(String(settings[key]) === b.dataset.v)));
  el.addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    let v = b.dataset.v; if (v === 'true' || v === 'false') v = v === 'true'; else if (/^\d+$/.test(v)) v = +v;
    settings[key] = v; store.set(key, v); sync(); sfx.tick(); onChange && onChange(v);
  });
  sync();
}
seg('optLevel', 'level');
seg('optPieces', 'pieces', (v) => { if (pieces) { pieces.setName = v; pieces.sync(Array.from(state.board)); } updateHud(); });
seg('optTime', 'time', (v) => { world && world.setTime(v); sfx.setMode(v); });
seg('optForced', 'forced');
seg('optQuality', 'quality', () => { $('qnote').hidden = false; });

$('playAI').onclick = () => { sfx.start(); newGame('ai'); };
$('playLocal').onclick = () => { sfx.start(); newGame('local'); };
$('again').onclick = () => newGame(mode);
$('tomenu').onclick = () => openMenu();
$('menuBtn').onclick = () => openMenu();
$('resume').onclick = () => { $('menu').hidden = true; document.body.classList.add('playing'); homeView(1); };
$('undo').onclick = undo;
$('endturn').onclick = endChain;
$('viewBtn').onclick = () => { view = view === 'seat' ? 'top' : 'seat'; $('viewBtn').querySelector('span').textContent = view === 'seat' ? 'Top view' : 'Seat view'; homeView(0.9); };
$('timeBtn').onclick = () => {
  const order = ['afternoon', 'sunset', 'night'];
  settings.time = order[(order.indexOf(settings.time) + 1) % 3]; store.set('time', settings.time);
  world.setTime(settings.time); sfx.setMode(settings.time);
  $('timeBtn').querySelector('span').textContent = { afternoon: 'Afternoon', sunset: 'Sunset', night: 'Night' }[settings.time];
  document.querySelectorAll('#optTime button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === settings.time)));
};
$('soundBtn').onclick = () => { settings.sound = !settings.sound; store.set('sound', settings.sound); sfx.start(); sfx.setOn(settings.sound); $('soundBtn').setAttribute('aria-pressed', String(settings.sound)); };
$('soundBtn').setAttribute('aria-pressed', String(settings.sound));
$('rotateOpt').checked = store.get('rotate', true);
$('rotateOpt').onchange = (e) => store.set('rotate', e.target.checked);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && phase === 'play') openMenu();
  if ((e.key === 'z' || e.key === 'Z') && (e.ctrlKey || e.metaKey)) undo();
  if (e.key === 'Enter' && !$('endturn').hidden) endChain();
});

function openMenu() {
  $('menu').hidden = false; $('result').hidden = true;
  $('resume').hidden = phase !== 'play';
  document.body.classList.remove('playing');
}

// ------------------------------------------------------------------ main loop
const clock = new THREE.Clock();
let orbitT = 0;
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  if (camAnim) {
    camAnim.t += dt / camAnim.dur;
    const e = THREE.MathUtils.smootherstep(Math.min(camAnim.t, 1), 0, 1);
    camera.position.lerpVectors(camAnim.p0, camAnim.p1, e);
    controls.target.lerpVectors(camAnim.t0, camAnim.t1, e);
    camera.lookAt(controls.target);
    if (camAnim.t >= 1) {
      const back = camAnim.back; camAnim = null;
      if (back) homeView(1.1); else controls.enabled = phase !== 'menu';
    }
  } else if (phase === 'menu' || !$('menu').hidden) {
    orbitT += dt * 0.035;
    const r = 6.2;
    camera.position.set(Math.sin(orbitT + 0.4) * r, 2.1 + Math.sin(orbitT * 0.7) * 0.4, Math.cos(orbitT + 0.4) * r);
    controls.target.set(0, 0.6, -2.5);
    camera.lookAt(controls.target);
  } else controls.update();
  if (world) world.update(dt, t);
  if (pieces) pieces.update(dt);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

// ------------------------------------------------------------------ app lifecycle
// Silence the ambience while the tab or Android app is in the background.
document.addEventListener('visibilitychange', () => { if (sfx.ctx) document.hidden ? sfx.ctx.suspend() : (sfx.on && sfx.ctx.resume()); });
// Offline play for the installed web app. Skipped on localhost (keeps the edit-refresh loop fresh)
// and inside the Capacitor Android app, which already ships every file.
if ('serviceWorker' in navigator && location.protocol === 'https:' && !/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && !(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform())) {
  addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
}

// ------------------------------------------------------------------ boot
(async function boot() {
  try {
    await loadAll();
  } catch (err) {
    $('loadmsg').textContent = 'Some game files did not load. Check your connection and reload the page.';
    console.error(err); return;
  }
  world = buildWorld({ renderer, scene, tex, models, quality: settings.quality });
  world.setTime(settings.time, true); sfx.setMode(settings.time);
  $('timeBtn').querySelector('span').textContent = { afternoon: 'Afternoon', sunset: 'Sunset', night: 'Night' }[settings.time];
  pieces = new Pieces(scene, models, tex, sfx);
  pieces.setName = settings.pieces;
  pieces.build(state.board);
  renderer.compile(scene, camera);
  document.body.classList.add('ready');
  $('loading').hidden = true;
  $('playAI').disabled = false; $('playLocal').disabled = false;
  updateHud();
  frame();
  // keep a game in progress across live page updates
  try {
    const hot = window.claude && window.claude.hot;
    const data = hot ? await new Promise((res) => (hot.ready ? hot.ready(res) : res(hot.data || {}))) : {};
    if (hot && typeof hot.snapshot === 'function') hot.snapshot(() => ({ board: Array.from(state.board), turn: state.turn, quiet: state.quiet, ply: state.ply, mode, playing: phase === 'play' }));
    if (data && data.playing && data.board) {
      mode = data.mode; phase = 'play'; $('menu').hidden = true; document.body.classList.add('playing');
      state = { ...R.initialState({ forcedCapture: settings.forced }), board: Int8Array.from(data.board), turn: data.turn, quiet: data.quiet, ply: data.ply };
      pieces.sync(Array.from(state.board)); flyTo(seatPose(HUMAN), 0.01); prepareTurn();
    }
  } catch {}
  window.__game = { loadPosition(cells, turn = 1) { const b = new Int8Array(37); for (const [x, z, p] of cells) b[R.pointAt(x, z)] = p; state = { ...R.initialState({ forcedCapture: settings.forced }), board: b, turn }; pieces.sync(Array.from(b)); history = []; updateHud(); prepareTurn(); }, THREE, camera, controls, scene, renderer, get state() { return state; }, world, pieces, newGame, tap, flyTo, seatPose, topPose, settings, R, setView: (v) => { view = v; homeView(0.01); } };
})();
