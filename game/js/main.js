import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import * as R from './rules.js';
import { chooseTurn } from './ai.js';
import { VILLAGE, toWorld, SPACING, makeGlowTex, makeSoftShadowTex } from './world.js';
import { ROOFTOP } from './rooftop.js';
import { Pieces, PIECE_SETS } from './pieces.js';
import { Sfx } from './audio.js';

const $ = (id) => document.getElementById(id);
const store = {
  get(k, d) { try { const v = localStorage.getItem('sholo.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('sholo.' + k, JSON.stringify(v)); } catch {} },
};

// ------------------------------------------------------------------ settings
const isTouch = matchMedia('(pointer: coarse)').matches;
const ENVS = { village: VILLAGE, rooftop: ROOFTOP };
// Each place remembers its own time of day ('time' for the village, as before; 'time.rooftop' ...).
const timeKey = (env) => env === 'village' ? 'time' : 'time.' + env;
const savedTime = (env) => { const t = store.get(timeKey(env), ENVS[env].defaultTime); return ENVS[env].times[t] ? t : ENVS[env].defaultTime; };
const settings = {
  env: ENVS[store.get('env', 'village')] ? store.get('env', 'village') : 'village',
  level: store.get('level', 'medium'),
  pieces: PIECE_SETS[store.get('pieces', 'pebbles')] ? store.get('pieces', 'pebbles') : 'pebbles',
  forced: store.get('forced', false),
  quality: store.get('quality', isTouch || (navigator.hardwareConcurrency || 8) <= 4 ? 0 : 1),
  sound: store.get('sound', true),
};
settings.time = savedTime(settings.env);
const ENV = () => ENVS[settings.env];

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
// Assets load per environment, the first time it is shown, and stay cached for switching back.
const sfx = new Sfx(); sfx.on = settings.sound;
const progress = { total: 0, done: 0 };
function track(job) {
  progress.total++; showProgress();
  return job.finally(() => { progress.done++; showProgress(); });
}
function showProgress() {
  const f = progress.total ? progress.done / progress.total : 0;
  $('loadbar').style.transform = `scaleX(${f})`; $('loadpct').textContent = Math.round(f * 100) + '%';
}
const texLoader = new THREE.TextureLoader();
const gltf = new GLTFLoader();
const GUTI = ['guti_pebble_variations', 'guti_clay_shard', 'guti_tamarind_seed', 'guti_marble_glass', 'guti_bottle_cap'];
const shared = {};                // glow / soft shadow sprites, made once
const envTex = {};                // environment id -> its textures { pano: {...}, ... }
const models = {};                // every model loaded so far, by name
function loadTex(url, srgb = true, repeat = true) {
  return track(new Promise((res, rej) => texLoader.load(url, (t) => {
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); }
    res(t);
  }, undefined, rej)));
}
// Models ship as base64-wrapped GLB inside JSON so any static host can serve them.
function loadModel(name) {
  const url = `assets/models/${name}.json`;
  return track(fetch(url).then((r) => { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); })
    .then((o) => { const bin = atob(o.glb), buf = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i); return gltf.parseAsync(buf.buffer, ''); }));
}
// The glass marble's transmission would add a second full render pass every frame; a clear,
// slightly reflective transparent shell reads the same at board scale. Its three plain-coloured
// swirls become one vertex-coloured mesh: 16 marbles on the board, so every primitive counts.
function cheapGlass(root) {
  const swirls = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.material.transmission) { if (!o.material.map) swirls.push(o); return; }
    const m = o.material;
    m.transmission = 0; m.transparent = true; m.opacity = 0.55; m.roughness = 0.04; m.metalness = 0;
    m.envMapIntensity = 2.2; m.depthWrite = false; m.needsUpdate = true;
  });
  if (swirls.length < 2) return;
  const geos = swirls.map((o) => {
    const src = o.geometry, n = src.attributes.position.count, g = new THREE.BufferGeometry();
    const P = new Float32Array(n * 3), N = new Float32Array(n * 3), C = new Float32Array(n * 3), c = o.material.color;
    for (let i = 0; i < n; i++) {
      P.set([src.attributes.position.getX(i), src.attributes.position.getY(i), src.attributes.position.getZ(i)], i * 3);
      N.set([src.attributes.normal.getX(i), src.attributes.normal.getY(i), src.attributes.normal.getZ(i)], i * 3);
      C.set([c.r, c.g, c.b], i * 3);
    }
    g.setAttribute('position', new THREE.BufferAttribute(P, 3)); g.setAttribute('normal', new THREE.BufferAttribute(N, 3)); g.setAttribute('color', new THREE.BufferAttribute(C, 3));
    if (src.index) g.setIndex(Array.from(src.index.array));
    return g.applyMatrix4(o.matrix);
  });
  const merged = new THREE.Mesh(mergeGeometries(geos), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: swirls[0].material.roughness }));
  merged.userData.noShadow = true;                 // the glass shell already casts it
  const parent = swirls[0].parent;
  for (const o of swirls) o.removeFromParent();
  parent.add(merged);
}
const pendingModels = {};
function loadModels(names) {
  return Promise.all(names.filter((m) => !models[m]).map((m) => pendingModels[m] || (pendingModels[m] = loadModel(m).then((g) => {
    if (m === 'guti_marble_glass') cheapGlass(g.scene);
    // the bottle cap's liner is on its underside, out of sight while it lies flat: one draw call less per cap
    if (m === 'guti_bottle_cap') { const liner = []; g.scene.traverse((o) => { if (o.isMesh && o.material.name === 'cloth') liner.push(o); }); liner.forEach((o) => o.removeFromParent()); }
    models[m] = g.scene; g.scene.animations = g.animations;
  }).finally(() => { delete pendingModels[m]; }))));
}
function loadEnv(id) {
  const E = ENVS[id], jobs = [loadModels(E.models)];
  if (!envTex[id]) {
    const t = { pano: {} }, texJobs = [];
    for (const [k, v] of Object.entries(E.textures)) {
      const [file, srgb = true, repeat = true] = [].concat(v);
      texJobs.push(loadTex('assets/tex/' + file, srgb, repeat).then((x) => (t[k] = x)));
    }
    for (const [k, file] of Object.entries(E.panos)) {
      texJobs.push(loadTex('assets/tex/' + file, true, false).then((x) => { x.generateMipmaps = false; x.minFilter = THREE.LinearFilter; t.pano[k] = x; }));
    }
    jobs.push(Promise.all(texJobs).then(() => (envTex[id] = t)));
  }
  return Promise.all(jobs);
}
function showLoading(id) {
  const E = ENVS[id];
  progress.total = progress.done = 0; showProgress();
  $('loading').style.backgroundImage = `url("${E.loading}")`;
  $('loadmsg').firstChild.textContent = E.loadMsg + ' ';
  $('loading').hidden = false;
}
async function loadAll() {
  showLoading(settings.env);
  await Promise.all([loadModels(GUTI), loadEnv(settings.env)]);
  shared.glow = makeGlowTex(); shared.shadow = makeSoftShadowTex();
}
function makeEnvWorld() {
  const w = ENV().build({ renderer, scene, tex: { ...envTex[settings.env], glow: shared.glow, shadow: shared.shadow }, models, quality: settings.quality, sfx });
  w.env = settings.env;
  return w;
}

// ------------------------------------------------------------------ game state
let world, pieces;
let state = R.initialState({ forcedCapture: settings.forced });
let mode = 'ai';               // 'ai' | 'local'
let history = [];              // states at the start of each human turn
let phase = 'menu';            // menu | play | over
let thinking = false, chainCount = 0, view = 'seat';
const HUMAN = R.P1, AI = R.P2;

const opp = () => ENV().opponent;
const names = () => mode === 'ai' ? { [R.P1]: 'You', [R.P2]: opp().name } : { [R.P1]: 'Player 1', [R.P2]: 'Player 2' };
const colourName = (p) => PIECE_SETS[settings.pieces].colours[p === R.P1 ? 0 : 1];
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
  $('avatar2').classList.toggle('opp', mode === 'ai'); $('avatar2').dataset.opp = opp().avatar;
  document.body.dataset.pieces = settings.pieces;
  let s = msg;
  if (!s) {
    if (thinking) s = `${opp().name} is thinking…`;
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
  world.react(toWorld(a.over), slow);
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
    title = mode === 'ai' ? (youWon ? 'You win' : `${opp().name} wins`) : `${nm[o.winner]} wins`;
    sub = o.reason === 'blocked' ? `${nm[R.other(o.winner)]} has no legal move left.` : `Every one of ${mode === 'ai' && o.winner === HUMAN ? opp().name + "'s" : (mode === 'ai' ? 'your' : nm[R.other(o.winner)] + "'s")} 16 guti was captured.`;
    if (youWon) sub += ' ' + opp().praise;
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
seg('optEnv', 'env', (v) => switchEnv(v));
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
// Time of day: each place has its own presets, so the menu buttons are rebuilt when the place changes.
function setTime(v, instant = false) {
  settings.time = v; store.set(timeKey(settings.env), v);
  world && world.setTime(v, instant); sfx.setMode(v);
  $('timeBtn').querySelector('span').textContent = ENV().times[v];
  document.querySelectorAll('#optTime button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === v)));
}
function buildTimeButtons() {
  $('optTime').innerHTML = Object.entries(ENV().times).map(([k, label]) => `<button data-v="${k}">${label}</button>`).join('');
}
$('optTime').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { sfx.tick(); setTime(b.dataset.v); } });
$('timeBtn').onclick = () => {
  const order = Object.keys(ENV().times);
  setTime(order[(order.indexOf(settings.time) + 1) % order.length]);
};
// Menu text and the opponent follow the place.
function applyEnvText() {
  const E = ENV(), o = E.opponent;
  $('place').textContent = `${E.name} · 37 points · 16 guti each`;
  $('lede').textContent = E.lede;
  $('playAI').firstChild.textContent = `Play ${o.name} `;
  $('levelLegend').textContent = `${o.name}’s strength`;
  $('scene').setAttribute('aria-label', E.aria);
  buildTimeButtons();
  if (pieces) updateHud();
}
// Switch place: load what is missing behind the loading screen, then swap the world. A game in
// progress carries on (the board and guti are not part of the world).
let switching = false;
async function switchEnv(id) {
  if (!world || switching || world.env === id || !ENVS[id]) return;
  switching = true;
  settings.env = id; store.set('env', id);
  document.querySelectorAll('#optEnv button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === id)));
  showLoading(id);
  try { await loadEnv(id); } catch (err) {
    console.error(err);
    $('loadmsg').firstChild.textContent = 'Some game files did not load. Check your connection and try again. ';
    settings.env = world.env; store.set('env', world.env);
    document.querySelectorAll('#optEnv button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === world.env)));
    setTimeout(() => { $('loading').hidden = true; switching = false; }, 2500);
    return;
  }
  world.dispose();
  world = makeEnvWorld();
  applyEnvText();
  setTime(savedTime(id), true); sfx.setScene(ENV().sound);
  renderer.compile(scene, camera);
  $('loading').hidden = true;
  switching = false;
}
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
    const { r, y, target } = world ? ENVS[world.env].orbit : ENV().orbit;
    camera.position.set(Math.sin(orbitT + 0.4) * r, y + Math.sin(orbitT * 0.7) * 0.4, Math.cos(orbitT + 0.4) * r);
    controls.target.set(...target);
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
// Places load lazily, so once the service worker is in charge, fetch the other places' files in the
// background: the worker caches them and every place then works offline.
function precacheOtherPlaces() {
  if (!(navigator.serviceWorker && navigator.serviceWorker.controller)) return;
  for (const E of Object.values(ENVS)) {
    if (E.id === settings.env) continue;
    const files = [...E.models.map((m) => `assets/models/${m}.json`), ...[...Object.values(E.textures), ...Object.values(E.panos)].map((v) => 'assets/tex/' + [].concat(v)[0]),
      E.loading, `assets/ui/${E.opponent.avatar}.jpg`];
    files.forEach((f, i) => setTimeout(() => fetch(f).catch(() => {}), i * 150));
  }
}

// ------------------------------------------------------------------ boot
(async function boot() {
  try {
    await loadAll();
  } catch (err) {
    $('loadmsg').textContent = 'Some game files did not load. Check your connection and reload the page.';
    console.error(err); return;
  }
  world = makeEnvWorld();
  applyEnvText();
  setTime(settings.time, true); sfx.setScene(ENV().sound);
  pieces = new Pieces(scene, models, shared, sfx);
  pieces.setName = settings.pieces;
  pieces.build(state.board);
  renderer.compile(scene, camera);
  document.body.classList.add('ready');
  $('loading').hidden = true;
  $('playAI').disabled = false; $('playLocal').disabled = false;
  updateHud();
  frame();
  setTimeout(precacheOtherPlaces, 10000);
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
  window.__game = { loadPosition(cells, turn = 1) { const b = new Int8Array(37); for (const [x, z, p] of cells) b[R.pointAt(x, z)] = p; state = { ...R.initialState({ forcedCapture: settings.forced }), board: b, turn }; pieces.sync(Array.from(b)); history = []; updateHud(); prepareTurn(); }, THREE, camera, controls, scene, renderer, get state() { return state; }, get world() { return world; }, pieces, setEnv: switchEnv, newGame, tap, flyTo, seatPose, topPose, settings, R, setView: (v) => { view = v; homeView(0.01); } };
})();
