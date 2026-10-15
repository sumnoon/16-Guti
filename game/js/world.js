// Village Uthan environment: sky, ground (with the board carved into it), props,
// lighting, time of day and ambient life.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { POINTS, EDGES } from './rules.js';

export const SPACING = 0.085;            // metres between board points
export const BOARD_RECT = { minX: -0.3, minZ: -0.47, sx: 0.6, sz: 0.94 };
export const toWorld = (i) => new THREE.Vector3(POINTS[i].x * SPACING, 0, POINTS[i].z * SPACING);

const SUN_DIR = new THREE.Vector3(-0.8, 0, -0.6).normalize(); // sun sits left-front of the player

export const TIMES = {
  afternoon: { pano: 'afternoon', sun: 0xffd6a0, sunI: 3.4, elev: 33, sky: 0xc9d8ea, ground: 0x8a6a48, hemiI: 0.95, fog: 0xd8c39f, exp: 1.0, env: 0.55, lantern: 0, dust: 1, flies: 0, bright: 1.0 },
  sunset:    { pano: 'sunset',    sun: 0xff9550, sunI: 2.6, elev: 9,  sky: 0xf0a477, ground: 0x6b4632, hemiI: 0.7,  fog: 0xd99a70, exp: 1.08, env: 0.45, lantern: 1.2, dust: 0.7, flies: 0.25, bright: 1.0 },
  night:     { pano: 'night',     sun: 0x9db4ff, sunI: 1.1, elev: 38, sky: 0x3a5088, ground: 0x221d1a, hemiI: 0.6, fog: 0x141c30, exp: 1.25, env: 0.35, lantern: 1.3, dust: 0, flies: 1, bright: 0.9 },
};

// ---------------------------------------------------------------- textures
function radialTexture(size, stops) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, col] of stops) gr.addColorStop(o, col);
  g.fillStyle = gr; g.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export const makeSoftShadowTex = () => radialTexture(64, [[0, 'rgba(0,0,0,0.75)'], [0.45, 'rgba(0,0,0,0.35)'], [1, 'rgba(0,0,0,0)']]);
export const makeGlowTex = () => radialTexture(64, [[0, 'rgba(255,255,255,1)'], [0.25, 'rgba(255,255,255,0.55)'], [1, 'rgba(255,255,255,0)']]);

function seeded(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// Height map of the board scratched into mud. 0.5 = flat, darker = groove, lighter = rim.
function makeBoardHeight() {
  const W = 768, H = Math.round(W * BOARD_RECT.sz / BOARD_RECT.sx);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const rnd = seeded(16);
  const px = (x) => ((x - BOARD_RECT.minX) / BOARD_RECT.sx) * W;
  const pz = (z) => ((BOARD_RECT.minZ + BOARD_RECT.sz - z) / BOARD_RECT.sz) * H;
  const mm = W / (BOARD_RECT.sx * 1000); // pixels per millimetre
  g.fillStyle = 'rgb(128,128,128)'; g.fillRect(0, 0, W, H);
  // swept, slightly smoother patch (green channel = swept mask)
  const sw = g.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, H * 0.55);
  sw.addColorStop(0, 'rgba(128,190,128,1)'); sw.addColorStop(1, 'rgba(128,128,128,0)');
  g.fillStyle = sw; g.fillRect(0, 0, W, H);
  const paths = EDGES.map(([a, b]) => {
    const A = POINTS[a], B = POINTS[b];
    const pts = []; const n = 10;
    const ax = A.x * SPACING, az = A.z * SPACING, bx = B.x * SPACING, bz = B.z * SPACING;
    const len = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / len, nz = (bx - ax) / len;
    let off = 0;
    for (let k = 0; k <= n; k++) {
      const t = k / n;
      off = k === 0 || k === n ? 0 : off * 0.6 + (rnd() - 0.5) * 0.0012;
      pts.push([px(ax + (bx - ax) * t + nx * off), pz(az + (bz - az) * t + nz * off)]);
    }
    return pts;
  });
  const stroke = (col, width, alpha) => {
    g.strokeStyle = col; g.lineWidth = width; g.globalAlpha = alpha; g.lineCap = 'round'; g.lineJoin = 'round';
    for (const p of paths) { g.beginPath(); g.moveTo(p[0][0], p[0][1]); for (const q of p.slice(1)) g.lineTo(q[0], q[1]); g.stroke(); }
  };
  // rims of pushed-out soil (fake blur with layered strokes)
  for (let k = 0; k < 6; k++) stroke('rgb(175,128,128)', (16 - k * 1.6) * mm * 0.62, 0.12);
  // the groove itself
  for (let k = 0; k < 5; k++) stroke('rgb(40,128,128)', (8.5 - k * 1.3) * mm * 0.62, 0.22);
  stroke('rgb(18,128,128)', 2.2 * mm, 0.9);
  g.globalAlpha = 1;
  // pressed dimples where lines meet
  for (const p of POINTS) {
    const x = px(p.x * SPACING), y = pz(p.z * SPACING);
    const gr = g.createRadialGradient(x, y, 0, x, y, 9 * mm);
    gr.addColorStop(0, 'rgba(70,128,128,0.8)'); gr.addColorStop(0.7, 'rgba(110,128,128,0.4)'); gr.addColorStop(1, 'rgba(128,128,128,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, 9 * mm, 0, Math.PI * 2); g.fill();
  }
  // loose crumbs thrown up beside the grooves
  for (const p of paths) for (let k = 0; k < 5; k++) {
    const q = p[Math.floor(rnd() * p.length)];
    const r = (0.6 + rnd() * 1.4) * mm, a = rnd() * 6.28, d = (5 + rnd() * 6) * mm;
    g.fillStyle = `rgba(${165 + rnd() * 25},128,128,0.6)`;
    g.beginPath(); g.arc(q[0] + Math.cos(a) * d, q[1] + Math.sin(a) * d, r, 0, 6.28); g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.NoColorSpace; t.anisotropy = 8;
  return { tex: t, texel: new THREE.Vector2(1 / W, 1 / H) };
}

// ---------------------------------------------------------------- sky
function makeSky(panos) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { uA: { value: panos.afternoon }, uB: { value: panos.afternoon }, uMix: { value: 0 }, uYaw: { value: 0 }, uBright: { value: 1 } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position = p.xyww; }`,
    fragmentShader: `uniform sampler2D uA; uniform sampler2D uB; uniform float uMix; uniform float uYaw; uniform float uBright; varying vec3 vDir;
      void main(){ vec3 d = normalize(vDir); float a = atan(d.z, d.x) + uYaw;
        vec2 uv = vec2(fract(a / 6.2831853 + 0.5), asin(clamp(d.y,-1.0,1.0)) / 3.14159265 + 0.5);
        vec3 c = mix(texture2D(uA, uv).rgb, texture2D(uB, uv).rgb, uMix) * uBright;
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`,
    side: THREE.BackSide, depthWrite: false, depthTest: true, fog: false,
  });
  const m = new THREE.Mesh(new THREE.SphereGeometry(400, 48, 24), mat);
  m.frustumCulled = false; m.renderOrder = -10;
  // Rotate the panorama so its sun lines up with the scene's sun (pano sun at u≈0.14).
  const panoAngle = (0.14 - 0.5) * Math.PI * 2;
  const worldAngle = Math.atan2(SUN_DIR.z, SUN_DIR.x);
  mat.uniforms.uYaw.value = panoAngle - worldAngle;
  return m;
}

// ---------------------------------------------------------------- ground
function makeGround(tex, board) {
  const size = 80, tile = 1.6;
  const geo = new THREE.PlaneGeometry(size, size, 1, 1);
  geo.rotateX(-Math.PI / 2);
  const uv = geo.attributes.uv, pos = geo.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / tile, -pos.getZ(i) / tile);
  const mat = new THREE.MeshStandardMaterial({ map: tex.mud, normalMap: tex.mudN, normalScale: new THREE.Vector2(0.9, 0.9), roughness: 0.96, metalness: 0, transparent: true });
  const uniforms = {
    uBoardH: { value: board.tex }, uTexel: { value: board.texel },
    uRect: { value: new THREE.Vector4(BOARD_RECT.minX, BOARD_RECT.minZ, BOARD_RECT.sx, BOARD_RECT.sz) },
    uRough: { value: tex.rough }, uBump: { value: 7.0 },
  };
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = 'varying vec3 vWPos;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(position, 1.0)).xyz;');
    sh.fragmentShader = `uniform sampler2D uBoardH; uniform vec2 uTexel; uniform vec4 uRect; uniform sampler2D uRough; uniform float uBump; varying vec3 vWPos;
      float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
        return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
      ` + sh.fragmentShader
      .replace('#include <map_fragment>', `
        vec2 buv = (vWPos.xz - uRect.xy) / uRect.zw;
        float bmask = step(0.0, buv.x) * step(buv.x, 1.0) * step(0.0, buv.y) * step(buv.y, 1.0);
        vec4 bh4 = texture2D(uBoardH, buv);
        float bh = mix(0.5, bh4.r, bmask);
        float swept = clamp((bh4.g - 0.5) * 2.0, 0.0, 1.0) * bmask;
        float n = vnoise(vWPos.xz * 0.45) * 0.6 + vnoise(vWPos.xz * 2.1) * 0.4;
        vec3 c1 = texture2D(map, vMapUv).rgb;
        vec3 c2 = texture2D(map, vMapUv * 0.29 + vec2(0.37, 0.11)).rgb;
        vec3 mud = mix(c1, c2, 0.45);
        vec3 rough = texture2D(uRough, vMapUv * 0.75).rgb;
        float dist = length(vWPos.xz - vec2(0.0, -1.5));
        float rm = smoothstep(7.0, 13.0, dist + n * 3.0);
        rm = max(rm, (1.0 - smoothstep(2.5, 6.0, length(vWPos.xz - vec2(-7.5, -5.5)) + n * 1.5)) * 0.85);
        vec3 col = mix(mud, rough, rm) * (0.86 + 0.26 * n);
        col = mix(col, col * 1.04, swept);
        float groove = clamp((0.5 - bh) * 2.0, 0.0, 1.0);
        float rim = clamp((bh - 0.5) * 2.0, 0.0, 1.0);
        col *= mix(vec3(1.0), vec3(0.62, 0.52, 0.44), groove);
        col *= 1.0 + rim * 0.12;
        diffuseColor.rgb *= col;
        diffuseColor.a *= 1.0 - smoothstep(22.0, 36.0, length(vWPos.xz));
      `)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        if (bmask > 0.5) {
          float hx = texture2D(uBoardH, buv + vec2(uTexel.x, 0.0)).r - texture2D(uBoardH, buv - vec2(uTexel.x, 0.0)).r;
          float hz = texture2D(uBoardH, buv + vec2(0.0, uTexel.y)).r - texture2D(uBoardH, buv - vec2(0.0, uTexel.y)).r;
          vec3 wn = normalize(vec3(-hx * uBump, 1.0, -hz * uBump));
          vec3 up = normalize((viewMatrix * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
          vec3 vn = normalize((viewMatrix * vec4(wn, 0.0)).xyz);
          normal = normalize(mix(normal, normal + (vn - up) * 1.4, 1.0));
        }`);
  };
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.renderOrder = -5;
  return mesh;
}

// ---------------------------------------------------------------- particles
function makeSmoke(glow, count) {
  const mat = new THREE.SpriteMaterial({ map: glow, color: 0xcfc6bb, transparent: true, depthWrite: false, opacity: 0.0 });
  const group = new THREE.Group(); const parts = [];
  for (let i = 0; i < count; i++) {
    const s = new THREE.Sprite(mat.clone()); s.userData.life = Math.random(); group.add(s); parts.push(s);
  }
  group.update = (dt, wind) => {
    for (const s of parts) {
      s.userData.life += dt * 0.12;
      if (s.userData.life > 1) { s.userData.life = 0; s.userData.ox = (Math.random() - 0.5) * 0.1; }
      const L = s.userData.life;
      s.position.set((s.userData.ox || 0) + L * L * 1.6 * wind + Math.sin(L * 6 + s.id) * 0.08, 0.3 + L * 3.2, Math.cos(L * 5 + s.id) * 0.06);
      const sc = 0.25 + L * 1.6; s.scale.set(sc, sc, sc);
      s.material.opacity = Math.sin(Math.PI * Math.min(1, L * 1.2)) * 0.22 * (1 - L);
    }
  };
  return group;
}

function makePoints(count, color, size, spread, centre, glow, additive = true) {
  const geo = new THREE.BufferGeometry();
  const p = new Float32Array(count * 3), seed = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    p[i * 3] = centre.x + (Math.random() - 0.5) * spread.x;
    p[i * 3 + 1] = centre.y + Math.random() * spread.y;
    p[i * 3 + 2] = centre.z + (Math.random() - 0.5) * spread.z;
    seed[i] = Math.random() * 100;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(p, 3));
  geo.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
  const mat = new THREE.PointsMaterial({ color, size, map: glow, transparent: true, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, opacity: 0, sizeAttenuation: true });
  const pts = new THREE.Points(geo, mat);
  pts.frustumCulled = false;
  pts.userData.base = p.slice();
  return pts;
}

// ---------------------------------------------------------------- props
function placeProps(scene, M, rnd, quality) {
  const put = (name, x, z, ry = 0, s = 1, opt = {}) => {
    const src = M[name]; if (!src) return null;
    // Place a wrapper: quantized GLBs keep their dequantization transform on the picked node.
    const o = new THREE.Group(); o.add((opt.node ? src.getObjectByName(opt.node) : src).clone(true));
    o.position.set(x, opt.y || 0, z); o.rotation.y = ry; o.scale.setScalar(s);
    o.traverse((m) => { if (m.isMesh) { m.castShadow = opt.shadow !== false; m.receiveShadow = true; } });
    scene.add(o); return o;
  };
  const out = {};
  out.banyan = put('prop_banyan_tree', -7.8, -5.8, 0.6, 1);
  put('prop_house', 8.6, -6.2, -Math.PI / 2 + 0.25, 1);
  // fence: back, sides, front
  const fence = (x0, z0, x1, z1) => {
    const len = Math.hypot(x1 - x0, z1 - z0), n = Math.round(len / 2), ang = Math.atan2(-(z1 - z0), x1 - x0);
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      const f = put('prop_fence', x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, ang + (rnd() - 0.5) * 0.06, 1, { shadow: quality > 0 });
      if (f) { f.scale.y = 0.9 + rnd() * 0.18; f.rotation.z = (rnd() - 0.5) * 0.04; }
    }
  };
  fence(-14, -11.5, 13, -11.5); fence(-14, 9, -14, -11.5); fence(13, -11.5, 13, 9); fence(-14, 9, 13, 9);
  put('prop_haystack', 3.4, -14.2, 0.4, 1);
  put('prop_haystack', -2.2, -16, 1.4, 0.8);
  put('prop_banana_tree', -3.6, -12.6, 0.3, 1.05);
  put('prop_banana_tree', 6.4, -13.0, 2.1, 1.25);
  put('prop_banana_tree', 11.2, -12.4, 1.0, 0.95);
  put('prop_banana_tree', -12.4, 2.5, 0.5, 1.1);
  out.chula = put('prop_chula', 3.4, -5.0, -0.4, 1);
  put('prop_pots', 3.4, -5.0, 0.3, 1, { node: 'aluminium_handi', y: 0.2 });
  put('prop_pots', 4.2, -5.4, 0, 1, { node: 'clay_rice_pot' });
  put('prop_kolshi', -3.4, -3.0, 0.2, 1);
  put('prop_kolshi', -3.0, -3.25, 1.2, 0.85);
  put('prop_kolshi', 6.0, -3.0, 0, 1);
  put('prop_chouki', -5.2, -1.4, 0.9, 1);
  put('prop_dala', 5.4, -3.7, 0, 1);
  put('prop_kula', 5.9, -4.4, 0, 1, { y: 0.0 });
  put('prop_clothesline', 9.6, 0.2, Math.PI / 2 + 0.15, 1);
  const j = put('prop_jharu', 5.2, -2.6, 0.5, 1); if (j) j.rotation.z = 0.28;
  // around the board: the players' mats, a brass lota and the hurricane lantern
  put('prop_pati', 0, 0.86, 0, 1, { shadow: false });
  put('prop_pati', 0, -0.88, Math.PI, 1, { shadow: false });
  put('prop_pots', -0.62, -0.1, 0.4, 0.9, { node: 'brass_lota' });
  put('prop_piri', 0.85, -0.95, 0.3, 1);
  out.lantern = put('prop_lantern', 0.6, -0.12, 0.5, 1);
  return out;
}

// ---------------------------------------------------------------- chickens
// The rigged chicken (idle / walk / peck clips) is skinned, so each bird needs SkeletonUtils.clone
// and its own AnimationMixer. An unrigged model falls back to whole-body motion.
function makeChickens(scene, src, n) {
  const clip = (name) => (src.animations || []).find((c) => c.name === name);
  const rigged = !!(clip('idle') && clip('walk') && clip('peck'));
  const birds = [];
  for (let i = 0; i < n; i++) {
    const g = new THREE.Group();
    const body = rigged ? SkeletonUtils.clone(src) : src.clone(true);
    body.traverse((m) => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
    g.add(body); scene.add(g);
    const a = Math.random() * 6.28, r = 3 + Math.random() * 5;
    g.position.set(Math.cos(a) * r + 1, 0, Math.sin(a) * r - 3);
    g.scale.setScalar(0.9 + Math.random() * 0.2);
    const b = { g, body, target: null, wait: Math.random() * 3, speed: 0.3, peck: 0, step: Math.random() * 10, flee: 0, anim: null, nextPeck: 1 + Math.random() * 3 };
    if (rigged) {
      const mixer = new THREE.AnimationMixer(body);
      const acts = { idle: mixer.clipAction(clip('idle')), walk: mixer.clipAction(clip('walk')), peck: mixer.clipAction(clip('peck')) };
      acts.peck.setLoop(THREE.LoopOnce, 1);
      acts.idle.play(); acts.idle.time = Math.random() * clip('idle').duration;
      b.anim = { mixer, acts, cur: 'idle' };
      mixer.addEventListener('finished', (e) => { if (e.action === acts.peck) play(b, 'idle', 0.3); });
    }
    birds.push(b);
  }
  function play(b, name, fade = 0.25) {
    const A = b.anim; if (A.cur === name) return;
    const next = A.acts[name]; next.reset().play();
    A.acts[A.cur].crossFadeTo(next, fade, false); A.cur = name;
  }
  const pick = () => {
    for (let k = 0; k < 20; k++) {
      const x = -6 + Math.random() * 13, z = -10 + Math.random() * 14;
      if (Math.hypot(x, z) < 1.8) continue;                      // keep off the board and mats
      if (x > 6 && z < -3) continue;                             // house
      if (Math.hypot(x + 7.8, z + 5.8) < 1.6) continue;          // tree trunk
      return new THREE.Vector3(x, 0, z);
    }
    return new THREE.Vector3(3, 0, -6);
  };
  return {
    update(dt) {
      for (const b of birds) {
        b.flee = Math.max(0, b.flee - dt);
        if (b.anim) b.anim.mixer.update(dt);
        if (b.wait > 0) {
          b.wait -= dt; b.peck += dt;
          if (b.anim) {
            if (b.anim.cur === 'walk') play(b, 'idle');
            b.nextPeck -= dt;
            if (b.nextPeck <= 0 && b.anim.cur === 'idle') { play(b, 'peck', 0.15); b.nextPeck = 1.5 + Math.random() * 3; }
          } else {
            b.body.rotation.x = Math.max(0, Math.sin(b.peck * 9)) * 0.45 * (Math.sin(b.peck * 1.3) > 0.2 ? 1 : 0);
          }
          if (b.wait <= 0) b.target = pick();
          continue;
        }
        if (!b.target) b.target = pick();
        const d = b.target.clone().sub(b.g.position); d.y = 0;
        const dist = d.length();
        const sp = b.flee > 0 ? 1.6 : 0.42;
        if (dist < 0.1) { b.target = null; b.wait = 1 + Math.random() * 4; b.body.position.y = 0; continue; }
        const want = Math.atan2(d.x, d.z);
        let diff = want - b.g.rotation.y; diff = Math.atan2(Math.sin(diff), Math.cos(diff));
        b.g.rotation.y += diff * Math.min(1, dt * 6);
        b.g.position.addScaledVector(d.normalize(), Math.min(dist, sp * dt));
        b.step += dt * (b.flee > 0 ? 22 : 11);
        if (b.anim) {
          play(b, 'walk', 0.2);
          b.anim.acts.walk.timeScale = b.flee > 0 ? 2.4 : 1;           // legs keep up with running
          b.body.position.y = b.flee > 0 ? Math.abs(Math.sin(b.step)) * 0.025 : 0;   // short hops while fleeing
        } else {
          b.body.position.y = Math.abs(Math.sin(b.step)) * 0.02;
          b.body.rotation.z = Math.sin(b.step) * 0.06; b.body.rotation.x = 0.05;
        }
      }
    },
    scare(center, r = 4) {
      for (const b of birds) if (b.g.position.distanceTo(center) < r) {
        const away = b.g.position.clone().sub(center).setY(0).normalize().multiplyScalar(2.5 + Math.random() * 2);
        b.target = b.g.position.clone().add(away); b.target.x = THREE.MathUtils.clamp(b.target.x, -11, 11); b.target.z = THREE.MathUtils.clamp(b.target.z, -10, 7);
        b.wait = 0; b.flee = 1.4;
      }
    },
  };
}

// ---------------------------------------------------------------- build
export function buildWorld({ renderer, scene, tex, models, quality }) {
  const rnd = seeded(7);
  const glow = makeGlowTex();
  const board = makeBoardHeight();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envs = {};
  for (const k of Object.keys(tex.pano)) {
    const t = tex.pano[k]; t.mapping = THREE.EquirectangularReflectionMapping;
    envs[k] = pmrem.fromEquirectangular(t).texture;
  }

  const sky = makeSky(tex.pano); scene.add(sky);
  scene.environment = envs.afternoon;
  scene.environmentRotation.y = -sky.material.uniforms.uYaw.value;
  scene.fog = new THREE.Fog(0xd8c39f, 30, 120);

  const ground = makeGround(tex, board); scene.add(ground);

  const hemi = new THREE.HemisphereLight(0xc9d8ea, 0x8a6a48, 0.9); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffd6a0, 3.2);
  sun.castShadow = true;
  const sm = quality > 0 ? 4096 : 2048;
  sun.shadow.mapSize.set(sm, sm);
  const sc = sun.shadow.camera; sc.left = -10; sc.right = 10; sc.top = 10; sc.bottom = -10; sc.near = 1; sc.far = 80;
  sun.shadow.bias = -0.0002; sun.shadow.normalBias = 0.015; sun.shadow.radius = 3;
  sun.target.position.set(0, 0, -1.5);
  scene.add(sun, sun.target);

  const props = placeProps(scene, models, rnd, quality);

  // lantern glow
  const lanternLight = new THREE.PointLight(0xffa64a, 0, 3, 2);
  lanternLight.position.copy(props.lantern.position).add(new THREE.Vector3(0, 0.2, 0));
  lanternLight.castShadow = quality > 0; lanternLight.shadow.mapSize.set(512, 512); lanternLight.shadow.bias = -0.002;
  scene.add(lanternLight);
  const flame = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xffb060, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
  flame.position.copy(lanternLight.position); flame.scale.setScalar(0.18); scene.add(flame);

  // chula fire glow + smoke
  const fire = new THREE.PointLight(0xff7a2a, 0.6, 3, 2);
  fire.position.copy(props.chula.position).add(new THREE.Vector3(0, 0.12, 0.2)); scene.add(fire);
  const smoke = makeSmoke(glow, quality > 0 ? 26 : 14);
  smoke.position.copy(props.chula.position); scene.add(smoke);

  const dust = makePoints(quality > 0 ? 220 : 90, 0xfff0c8, 0.012, new THREE.Vector3(5, 2.2, 5), new THREE.Vector3(-0.5, 0.05, -1.5), glow);
  const flies = makePoints(quality > 0 ? 70 : 35, 0xd8ff7a, 0.07, new THREE.Vector3(22, 2.5, 18), new THREE.Vector3(-1, 0.3, -3), glow);
  scene.add(dust, flies);

  // falling leaves (pooled)
  const leafGeo = new THREE.PlaneGeometry(0.06, 0.035);
  const leafMat = new THREE.MeshStandardMaterial({ color: 0x9a7a2e, side: THREE.DoubleSide, roughness: 0.9 });
  const leaves = [];
  for (let i = 0; i < 24; i++) { const l = new THREE.Mesh(leafGeo, leafMat); l.visible = false; l.castShadow = true; scene.add(l); leaves.push({ m: l, v: new THREE.Vector3(), life: 0 }); }
  const dropLeaves = (n, near) => {
    for (const L of leaves) {
      if (n <= 0) break; if (L.m.visible) continue;
      L.m.visible = true; L.life = 0; n--;
      const c = near || new THREE.Vector3(-2 + Math.random() * 3, 0, -1.5 + Math.random() * 2.5);
      L.m.position.set(c.x + (Math.random() - 0.5) * 1.5, 2.2 + Math.random() * 2, c.z + (Math.random() - 0.5) * 1.5);
      L.m.rotation.set(Math.random() * 6, Math.random() * 6, 0);
      L.v.set((Math.random() - 0.3) * 0.25, -0.35 - Math.random() * 0.2, (Math.random() - 0.5) * 0.2);
    }
  };

  const chickens = makeChickens(scene, models.prop_chicken, quality > 0 ? 5 : 3);

  // ---- time of day blending
  const cur = { ...TIMES.afternoon };
  let from = { ...TIMES.afternoon }, to = TIMES.afternoon, tBlend = 1, timeName = 'afternoon';
  const cA = new THREE.Color(), cB = new THREE.Color();
  const lerpCol = (a, b, t) => cA.set(a).lerp(cB.set(b), t).getHex();
  function applyTime(t) {
    const L = (k) => from[k] + (to[k] - from[k]) * t;
    const elev = THREE.MathUtils.degToRad(L('elev'));
    const dir = new THREE.Vector3(SUN_DIR.x * Math.cos(elev), Math.sin(elev), SUN_DIR.z * Math.cos(elev));
    sun.position.copy(sun.target.position).addScaledVector(dir, 40);
    sun.color.set(lerpCol(from.sun, to.sun, t)); sun.intensity = L('sunI');
    hemi.color.set(lerpCol(from.sky, to.sky, t)); hemi.groundColor.set(lerpCol(from.ground, to.ground, t)); hemi.intensity = L('hemiI');
    scene.fog.color.set(lerpCol(from.fog, to.fog, t));
    renderer.toneMappingExposure = L('exp');
    scene.environmentIntensity = L('env');
    cur.lantern = L('lantern'); cur.dust = L('dust'); cur.flies = L('flies');
    sky.material.uniforms.uMix.value = t; sky.material.uniforms.uBright.value = L('bright');
  }
  function setTime(name, instant = false) {
    if (!TIMES[name]) return;
    timeName = name;
    from = instant ? { ...TIMES[name] } : snapshot();
    to = TIMES[name];
    sky.material.uniforms.uA.value = tex.pano[from.pano || to.pano];
    sky.material.uniforms.uB.value = tex.pano[to.pano];
    scene.environment = envs[to.pano];
    tBlend = instant ? 1 : 0;
    applyTime(instant ? 1 : 0);
  }
  function snapshot() {
    const s = { pano: sky.material.uniforms.uMix.value > 0.5 ? (to.pano) : (from.pano || to.pano) };
    const t = tBlend;
    for (const k of ['sunI', 'elev', 'hemiI', 'exp', 'env', 'lantern', 'dust', 'flies', 'bright']) s[k] = from[k] + (to[k] - from[k]) * t;
    for (const k of ['sun', 'sky', 'ground', 'fog']) s[k] = lerpCol(from[k], to[k], t);
    return s;
  }
  setTime('afternoon', true);

  let wind = 1;
  return {
    sun, ground, chickens, timeName: () => timeName, setTime,
    dropLeaves,
    update(dt, t) {
      if (tBlend < 1) { tBlend = Math.min(1, tBlend + dt / 2.5); applyTime(THREE.MathUtils.smootherstep(tBlend, 0, 1)); }
      wind = 0.8 + Math.sin(t * 0.13) * 0.3;
      if (props.banyan) props.banyan.rotation.z = Math.sin(t * 0.6) * 0.004 * wind;
      smoke.update(dt, wind);
      const fl = 0.85 + Math.sin(t * 13) * 0.06 + Math.sin(t * 7.3) * 0.05 + (Math.random() - 0.5) * 0.06;
      lanternLight.intensity = cur.lantern * fl;
      flame.material.opacity = Math.min(1, cur.lantern * 0.35) * fl;
      fire.intensity = (0.5 + cur.lantern * 0.25) * (0.8 + Math.sin(t * 9) * 0.1 + Math.random() * 0.1);
      chickens.update(dt);
      // dust motes drift; fireflies wander and blink
      const dp = dust.geometry.attributes.position, db = dust.userData.base;
      for (let i = 0; i < dp.count; i++) {
        dp.setXYZ(i, db[i * 3] + Math.sin(t * 0.21 + i) * 0.25, db[i * 3 + 1] + Math.sin(t * 0.17 + i * 1.7) * 0.2, db[i * 3 + 2] + Math.cos(t * 0.19 + i) * 0.25);
      }
      dp.needsUpdate = true;
      dust.material.opacity = 0.55 * cur.dust;
      const fp = flies.geometry.attributes.position, fb = flies.userData.base;
      for (let i = 0; i < fp.count; i++) {
        fp.setXYZ(i, fb[i * 3] + Math.sin(t * 0.3 + i * 2.1) * 0.8, fb[i * 3 + 1] + Math.sin(t * 0.5 + i) * 0.3, fb[i * 3 + 2] + Math.cos(t * 0.27 + i * 1.3) * 0.8);
      }
      fp.needsUpdate = true;
      flies.material.opacity = cur.flies * (0.75 + Math.sin(t * 3) * 0.25);
      flies.visible = cur.flies > 0.01; dust.visible = cur.dust > 0.01;
      for (const L of leaves) {
        if (!L.m.visible) continue;
        L.life += dt;
        if (L.m.position.y > 0.004) {
          L.m.position.addScaledVector(L.v, dt);
          L.m.position.x += Math.sin(L.life * 3 + L.m.id) * 0.004;
          L.m.rotation.x += dt * 2.2; L.m.rotation.y += dt * 1.4;
        } else { L.m.position.y = 0.003; L.m.rotation.x = -Math.PI / 2; if (L.life > 14) L.m.visible = false; }
      }
    },
  };
}
