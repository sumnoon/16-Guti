// Old Dhaka Rooftop environment: Shakrain, the kite festival, on a cement roof in Puran Dhaka.
// The board is chalked on the floor between two jute mats; neighbours fly kites from the roofs around,
// string lights come on at dusk, fire-breathers and fireworks light up the night, sky lanterns drift up.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { POINTS, EDGES } from './rules.js';
import { SPACING, BOARD_RECT, seeded, makeGlowTex, makeSky, makeTimeline, makePut, instanced, disposeTree } from './world.js';

const SUN_DIR = new THREE.Vector3(-0.6, 0, -0.8).normalize();   // dusk glow ahead-left of player 1
const PANO_SUN_U = 0.67;                                          // where the dusk glow sits in the panorama
const ROOF = { x0: -4.6, x1: 4.6, z0: -5.2, z1: 4.4 };            // inner floor, parapet outside it
const WALL = 0.15;                                                // parapet thickness
const STREET = -9.5;                                              // lanes between the houses

export const ROOF_TIMES = {
  dusk:  { pano: 'dusk',  sun: 0xffb27a, sunI: 1.9, elev: 24, sky: 0xb2a4b6, ground: 0x6e5c4c, hemiI: 0.9, fog: 0x6d5a8c, exp: 1.05, env: 0.45, bulbs: 0.7, lantern: 0.5, windows: 0.3, fireworks: 0.25, fanush: 0.45, fire: 0.35, kites: 1.0, bright: 1.0 },
  night: { pano: 'night', sun: 0x8ea6ff, sunI: 0.4, elev: 52, sky: 0x2a3c70, ground: 0x15110e, hemiI: 0.35, fog: 0x121a33, exp: 1.1, env: 0.25, bulbs: 1.5, lantern: 1.4, windows: 1.0, fireworks: 1.0, fanush: 1.0, fire: 1.0, kites: 0.45, bright: 0.95 },
};

export const ROOFTOP = {
  id: 'rooftop', name: 'Old Dhaka Rooftop',
  models: ['bld_mosque', 'bld_oldhaka_block_1', 'bld_oldhaka_block_2', 'bld_oldhaka_block_3', 'bld_oldhaka_block_4', 'char_fire_breather',
    'char_kite_flyers', 'prop_chilekotha', 'prop_clothesline_roof', 'prop_fanush', 'prop_flower_pots', 'prop_kite_ghuri', 'prop_moa_plate',
    'prop_natai_spool', 'prop_paper_lantern', 'prop_parapet_segment', 'prop_plastic_chair', 'prop_speaker', 'prop_string_lights',
    'prop_water_tank', 'prop_wire_pole', 'prop_lantern'],
  textures: {
    cement: 'roof_cement.jpg', cementN: ['roof_cement_n.jpg', false], plaster: 'roof_plaster_old.jpg', plasterN: ['roof_plaster_old_n.jpg', false],
    jute: 'roof_jute_mat.jpg', juteN: ['roof_jute_mat_n.jpg', false], windows: 'roof_facade_emissive.jpg', kites: ['roof_kites.png', true, false],
    fxFireworks: ['fx_fireworks.jpg', true, false], fxFire: ['fx_fire_breath.jpg', true, false], fxSparks: ['fx_sparks.jpg', true, false],
  },
  panos: { dusk: 'pano_rooftop_dusk.jpg', night: 'pano_rooftop_night.jpg' },
  times: { dusk: 'Dusk', night: 'Night' }, defaultTime: 'dusk',
  opponent: { name: 'Rana', avatar: 'rival', praise: '“Darun khelecho!” says Rana.' },
  loading: 'assets/ui/loading_rooftop.jpg', loadMsg: 'Climbing up to the roof…',
  lede: 'Shakrain in Puran Dhaka. Kites fill the sky and Rana, champion of the next roof, wants a game. Capture all sixteen of his guti to win.',
  aria: '3D Sholo Guti board chalked on an Old Dhaka rooftop during the kite festival',
  orbit: { r: 3.0, y: 2.0, target: [0, 1.5, -1.0] },
  sound: 'rooftop',
  build: (o) => buildRooftop(o),
};

// ---------------------------------------------------------------- chalk board
// White chalk lines on the cement, slightly wobbly, grainy and dusty. Red channel = chalk amount.
function makeChalk() {
  const W = 1024, H = Math.round(W * BOARD_RECT.sz / BOARD_RECT.sx);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const rnd = seeded(23);
  const px = (x) => ((x - BOARD_RECT.minX) / BOARD_RECT.sx) * W;
  const pz = (z) => ((BOARD_RECT.minZ + BOARD_RECT.sz - z) / BOARD_RECT.sz) * H;
  const mm = W / (BOARD_RECT.sx * 1000);
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  g.lineCap = 'round'; g.lineJoin = 'round';
  const strokeEdge = (A, B, width, alpha, wobble) => {
    const n = 8;
    g.strokeStyle = '#fff'; g.globalAlpha = alpha; g.lineWidth = width;
    g.beginPath();
    for (let k = 0; k <= n; k++) {
      const t = k / n, j = k === 0 || k === n ? 0.3 : 1;
      const x = A.x + (B.x - A.x) * t + (rnd() - 0.5) * wobble * j, z = A.z + (B.z - A.z) * t + (rnd() - 0.5) * wobble * j;
      k ? g.lineTo(px(x), pz(z)) : g.moveTo(px(x), pz(z));
    }
    g.stroke();
  };
  const ends = EDGES.map(([a, b]) => [{ x: POINTS[a].x * SPACING, z: POINTS[a].z * SPACING }, { x: POINTS[b].x * SPACING, z: POINTS[b].z * SPACING }]);
  for (const [A, B] of ends) strokeEdge(A, B, 16 * mm, 0.07, 0.003);        // smudged dust either side
  for (const [A, B] of ends) for (let k = 0; k < 3; k++) strokeEdge(A, B, (3.2 + rnd() * 1.6) * mm, 0.5, 0.0016);
  g.globalAlpha = 1;
  // chalk grain: the stick skips over the rough cement
  const img = g.getImageData(0, 0, W, H), d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const v = d[i] / 255, grain = rnd();
    d[i] = d[i + 1] = d[i + 2] = Math.round(255 * Math.min(1, v * (grain < 0.12 ? 0.25 : 0.7 + grain * 0.5)));
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.NoColorSpace; t.anisotropy = 8;
  return t;
}

// ---------------------------------------------------------------- roof floor
function makeFloor(tex) {
  const w = ROOF.x1 - ROOF.x0, d = ROOF.z1 - ROOF.z0, tile = 2.0;
  const geo = new THREE.PlaneGeometry(w, d, 1, 1).rotateX(-Math.PI / 2).translate((ROOF.x0 + ROOF.x1) / 2, 0, (ROOF.z0 + ROOF.z1) / 2);
  const uv = geo.attributes.uv, pos = geo.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / tile, -pos.getZ(i) / tile);
  const mat = new THREE.MeshStandardMaterial({ map: tex.cement, normalMap: tex.cementN, normalScale: new THREE.Vector2(0.7, 0.7), roughness: 0.93, metalness: 0 });
  const uniforms = {
    uChalk: { value: makeChalk() },
    uRect: { value: new THREE.Vector4(BOARD_RECT.minX, BOARD_RECT.minZ, BOARD_RECT.sx, BOARD_RECT.sz) },
    uRoof: { value: new THREE.Vector4(ROOF.x0, ROOF.z0, ROOF.x1, ROOF.z1) },
  };
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = 'varying vec3 vWPos;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(position, 1.0)).xyz;');
    sh.fragmentShader = `uniform sampler2D uChalk; uniform vec4 uRect; uniform vec4 uRoof; varying vec3 vWPos;
      float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
        return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
      ` + sh.fragmentShader.replace('#include <map_fragment>', `
        vec2 buv = (vWPos.xz - uRect.xy) / uRect.zw;
        float bmask = step(0.0, buv.x) * step(buv.x, 1.0) * step(0.0, buv.y) * step(buv.y, 1.0);
        float chalk = texture2D(uChalk, buv).r * bmask;
        float n = vnoise(vWPos.xz * 0.35) * 0.6 + vnoise(vWPos.xz * 1.7) * 0.4;
        vec3 c1 = texture2D(map, vMapUv).rgb;
        vec3 c2 = texture2D(map, vMapUv * 0.37 + vec2(0.31, 0.17)).rgb;
        vec3 col = mix(c1, c2, 0.4) * (0.8 + 0.32 * n);
        // rain water collects along the parapet: a darker, damp band
        float edge = min(min(vWPos.x - uRoof.x, uRoof.z - vWPos.x), min(vWPos.z - uRoof.y, uRoof.w - vWPos.z));
        col *= mix(0.62, 1.0, smoothstep(0.0, 0.7, edge + n * 0.2));
        col = mix(col, vec3(0.9, 0.89, 0.85), chalk * 0.92);
        diffuseColor.rgb *= col;
      `);
  };
  const m = new THREE.Mesh(geo, mat); m.receiveShadow = true; m.renderOrder = -5;
  return m;
}

// The house under the roof (seen when looking over the parapet) and the lane far below.
function makeHouseAndStreet(tex) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ map: tex.plaster, normalMap: tex.plasterN, roughness: 0.95, color: 0xd8cbb6 });
  const ox0 = ROOF.x0 - WALL, ox1 = ROOF.x1 + WALL, oz0 = ROOF.z0 - WALL, oz1 = ROOF.z1 + WALL, h = -STREET + 0.02, tile = 2.6;
  const wall = (len, x, z, ry) => {
    const geo = new THREE.PlaneGeometry(len, h); const uv = geo.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * len / tile, uv.getY(i) * h / tile);
    const m = new THREE.Mesh(geo, mat); m.position.set(x, STREET / 2, z); m.rotation.y = ry; m.receiveShadow = true; g.add(m);
  };
  wall(ox1 - ox0, (ox0 + ox1) / 2, oz1, 0); wall(ox1 - ox0, (ox0 + ox1) / 2, oz0, Math.PI);
  wall(oz1 - oz0, ox1, (oz0 + oz1) / 2, Math.PI / 2); wall(oz1 - oz0, ox0, (oz0 + oz1) / 2, -Math.PI / 2);
  const street = new THREE.Mesh(new THREE.PlaneGeometry(200, 200).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x2c2723, roughness: 1 }));
  street.position.y = STREET; g.add(street);
  return g;
}

function makeMat(tex, w, d) {
  const geo = new THREE.BoxGeometry(w, 0.008, d); const uv = geo.attributes.uv, n = geo.attributes.normal;
  for (let i = 0; i < uv.count; i++) if (Math.abs(n.getY(i)) > 0.5) uv.setXY(i, uv.getX(i) * w / 0.5, uv.getY(i) * d / 0.5);
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: tex.jute, normalMap: tex.juteN, roughness: 0.97, color: 0xb8a690 }));
  m.receiveShadow = true; m.position.y = 0.004;
  return m;
}

// ---------------------------------------------------------------- sprite sheets (4 x 4 cells)
function sheetSprite(texture, color = 0xffffff) {
  const map = texture.clone(); map.repeat.set(0.25, 0.25); map.needsUpdate = true;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false, opacity: 0 }));
  s.frame = (f) => map.offset.set((f % 4) * 0.25, 0.75 - Math.floor(f / 4) * 0.25);
  s.visible = false;
  return s;
}

function glowPoints(positions, color, size, glow) {
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  const p = new THREE.Points(geo, new THREE.PointsMaterial({ color, size, map: glow, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true, fog: false, opacity: 0 }));
  p.frustumCulled = false;
  return p;
}

// Bulb centres of the string-light model, found by clustering the vertices of its emissive bulbs.
function bulbOffsets(src) {
  let amber = null; src.traverse((o) => { if (o.isMesh && o.material.name === 'amber') amber = o; });
  if (!amber) return [];
  src.updateMatrixWorld(true);
  const pos = amber.geometry.attributes.position, pts = [];
  for (let i = 0; i < pos.count; i++) pts.push(new THREE.Vector3().fromBufferAttribute(pos, i).applyMatrix4(amber.matrixWorld));
  pts.sort((a, b) => a.x - b.x);
  const out = []; let grp = [];
  const flush = () => { if (grp.length) out.push(grp.reduce((s, p) => s.add(p), new THREE.Vector3()).divideScalar(grp.length)); grp = []; };
  for (let i = 0; i < pts.length; i++) { if (i && pts[i].x - pts[i - 1].x > 0.03) flush(); grp.push(pts[i]); }
  flush();
  return out;
}

// A sagging cable as a thin tube.
function cable(a, b, sag, r = 0.011) {
  const mid = a.clone().lerp(b, 0.5); mid.y -= sag * 2;
  return new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(a, mid, b), 18, r, 3, false);
}

// ---------------------------------------------------------------- kites
// One instanced mesh: a paper diamond plus a short tail, each instance showing one of the 16 atlas designs.
function makeKiteMesh(tex, count) {
  const P = [0, 0.5, 0, -0.2, 0.29, 0, 0, 0.09, 0, 0.2, 0.29, 0, -0.012, 0.1, 0, 0.012, 0.1, 0, -0.02, -0.14, 0, 0.02, -0.14, 0];
  const U = [0.5, 0.94, 0.06, 0.5, 0.5, 0.07, 0.94, 0.5, 0.47, 0.28, 0.53, 0.28, 0.47, 0.22, 0.53, 0.22];
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2));
  geo.setIndex([0, 1, 2, 0, 2, 3, 4, 6, 5, 5, 6, 7]);
  geo.computeVertexNormals();
  const cell = new Float32Array(count);
  for (let i = 0; i < count; i++) cell[i] = i % 16;
  geo.setAttribute('aCell', new THREE.InstancedBufferAttribute(cell, 1));
  const mat = new THREE.MeshBasicMaterial({ map: tex.kites, alphaTest: 0.5, side: THREE.DoubleSide });
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = 'attribute float aCell;\n' + sh.vertexShader.replace('#include <uv_vertex>',
      '#include <uv_vertex>\nvMapUv = (vMapUv + vec2(mod(aCell, 4.0), 3.0 - floor(aCell / 4.0))) * 0.25;');
  };
  const mesh = new THREE.InstancedMesh(geo, mat, count);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  return mesh;
}

// ---------------------------------------------------------------- build
export function buildRooftop({ renderer, scene: realScene, tex, models: M, quality, sfx }) {
  const scene = new THREE.Group(); realScene.add(scene);
  const hi = quality > 0;
  const rnd = seeded(11);
  const glow = makeGlowTex();
  const put = makePut(scene, M);
  // Repeated static props are collected here and drawn as one instanced mesh per part at the end.
  const statics = {};
  const putS = (name, ...a) => { const o = put(name, ...a); if (o) (statics[name] = statics[name] || []).push(o); return o; };
  for (const k of ['windows']) { tex[k].flipY = false; tex[k].needsUpdate = true; }   // glTF UVs

  const pmrem = new THREE.PMREMGenerator(renderer);
  const envs = {};
  for (const k of Object.keys(tex.pano)) {
    const t = tex.pano[k]; t.mapping = THREE.EquirectangularReflectionMapping;
    envs[k] = pmrem.fromEquirectangular(t).texture;
  }
  const sky = makeSky(tex.pano.dusk, PANO_SUN_U, SUN_DIR); scene.add(sky);
  sky.material.uniforms.uHazeAmt.value = 1;
  realScene.environment = envs.dusk;
  realScene.environmentRotation.y = -sky.material.uniforms.uYaw.value;
  realScene.fog = new THREE.Fog(0x6d5a8c, 26, 150);

  scene.add(makeFloor(tex), makeHouseAndStreet(tex));

  const hemi = new THREE.HemisphereLight(0x9a86c8, 0x5e4c4a, 1); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffa36b, 1.5);
  sun.castShadow = true;
  sun.shadow.mapSize.setScalar(hi ? 2048 : 1024);
  const sc = sun.shadow.camera; sc.left = -7; sc.right = 7; sc.top = 7; sc.bottom = -7; sc.near = 1; sc.far = 60;
  sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.02; sun.shadow.radius = 3;
  sun.target.position.set(0, 0, -0.4);
  scene.add(sun, sun.target);

  // ---- parapet: one instanced mesh per side
  const parapet = (x0, z0, x1, z1) => {
    const len = Math.hypot(x1 - x0, z1 - z0), n = Math.max(1, Math.round(len / 2)), ang = Math.atan2(-(z1 - z0), x1 - x0), side = [];
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      const p = put('prop_parapet_segment', x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, ang);
      if (p) { p.scale.x = len / n / 2; side.push(p); }
    }
    instanced(scene, side);
  };
  const hw = WALL / 2;
  parapet(ROOF.x0 - WALL, ROOF.z0 - hw, ROOF.x1 + WALL, ROOF.z0 - hw);
  parapet(ROOF.x0 - WALL, ROOF.z1 + hw, ROOF.x1 + WALL, ROOF.z1 + hw);
  parapet(ROOF.x0 - hw, ROOF.z0, ROOF.x0 - hw, ROOF.z1);
  parapet(ROOF.x1 + hw, ROOF.z0, ROOF.x1 + hw, ROOF.z1);

  // ---- things on our roof
  put('prop_chilekotha', -3.35, -3.95, 0);
  putS('prop_water_tank', 3.7, -4.55, 0.2);
  putS('prop_water_tank', 2.45, -4.6, 1.1, 0.92);
  // Battery saver: small props cast no sun shadow (the shadow pass draws every caster again)
  const small = { shadow: hi };
  put('prop_clothesline_roof', 4.05, -1.2, Math.PI / 2, 1, small);
  putS('prop_plastic_chair', 3.0, 2.7, -2.4, 1, small);
  putS('prop_plastic_chair', 3.7, 1.8, -1.9, 1, small);
  put('prop_speaker', -4.1, 3.9, 2.4, 1, small);
  putS('prop_natai_spool', -3.6, 3.5, 0.6, 1, small);
  putS('prop_natai_spool', 0.8, 0.66, 0.4, 1, small);
  const lyingKite = (x, z, ry, s = 1) => { const k = putS('prop_kite_ghuri', x, z, ry, s, { y: 0.012, shadow: hi }); if (k) k.children[0].rotation.x = -Math.PI / 2; };
  lyingKite(-0.95, 0.6, 0.5); lyingKite(-3.3, 3.0, 2.2);
  // flower pots along the parapets and by the stair-room door (instanced per kind)
  const pots = { marigold_terracotta: [], tulsi_plastic: [], marigold_clay: [] }, kinds = Object.keys(pots);
  const pot = (x, z) => { const kind = kinds[Math.floor(rnd() * 3)]; const p = put('prop_flower_pots', x, z, rnd() * 6.28, 0.9 + rnd() * 0.25, { node: kind, center: true, shadow: hi }); if (p) pots[kind].push(p); };
  for (let z = -2.1; z < 3.0; z += 0.62 + rnd() * 0.3) pot(ROOF.x0 + 0.24, z);
  for (let x = -1.6; x < 2.0; x += 0.7 + rnd() * 0.4) pot(x, ROOF.z0 + 0.24);
  for (let x = -2.6; x < 1.5; x += 0.8 + rnd() * 0.5) pot(x, ROOF.z1 - 0.24);
  pot(-1.85, -2.5); pot(-1.5, -2.85); pot(ROOF.x1 - 0.25, 3.9); pot(ROOF.x1 - 0.25, 3.3);
  for (const k of kinds) instanced(scene, pots[k]);

  // around the board: the players' jute mats, murir moa and the hurricane lantern
  const mat1 = makeMat(tex, 1.1, 0.6); mat1.position.z = 0.82; mat1.rotation.y = 0.02;
  const mat2 = makeMat(tex, 1.1, 0.6); mat2.position.z = -0.84; mat2.rotation.y = -0.03;
  scene.add(mat1, mat2);
  put('prop_moa_plate', -0.66, 0.08, 0.4);
  const lantern = put('prop_lantern', 0.62, -0.12, 0.5);

  // ---- neighbouring houses. Facades face +z in the models; roofY is where their roof floor ends up.
  // Bases sink into the lane (STREET) so no building floats.
  const BLD = { b1: ['bld_oldhaka_block_1', 11.2], b2: ['bld_oldhaka_block_2', 8.4], b3: ['bld_oldhaka_block_3', 14], b4: ['bld_oldhaka_block_4', 5.6] };
  const FACE = { S: 0, N: Math.PI, E: Math.PI / 2, W: -Math.PI / 2 };
  const byType = {}, roofs = [];
  const bld = (type, x, z, face, roofY) => {
    const [name, roofLocal] = BLD[type];
    const base = Math.min(roofY - roofLocal, STREET);
    const o = put(name, x, z, typeof face === 'string' ? FACE[face] : face, 1, { y: base, shadow: false });
    if (!o) return null;
    (byType[name] = byType[name] || []).push(o);
    const r = { x, z, y: base + roofLocal, ry: o.rotation.y, type };
    roofs.push(r); return r;
  };
  // inner ring, 1.2-2 m lanes away from our house
  const F2 = bld('b1', -1.6, -10, 'S', 1.6);
  bld('b2', -8.0, -10, 'S', -1.1);
  bld('b4', 5.2, -10, 'S', -3.9);
  const R1 = bld('b3', 9.6, -3.4, 'W', 2.4);
  bld('b3', 9.6, 2.7, 'W', 4.5);              // tall: hides the roof foreground baked into the panoramas
  bld('b2', 9.6, 9.2, 'W', -1.1);
  bld('b2', -9.6, -2.6, 'E', -1.1);
  const L2 = bld('b3', -9.6, 4.6, 'E', 3.0);
  bld('b1', -9.6, 10.6, 'E', 0.6);
  bld('b4', -2.2, 9.4, 'N', -3.9);
  bld('b1', 3.75, 9.4, 'N', 1.0);
  // outer ring, scattered, mostly taller so they show over the first one
  const boxes = [];
  for (const r of roofs) boxes.push([r.x - 5, r.z - 5, r.x + 5, r.z + 5]);
  const types = ['b1', 'b2', 'b3', 'b1', 'b2', 'b4'];
  for (let a = 0; a < Math.PI * 2; a += 0.3 + rnd() * 0.12) {
    const d = 19 + rnd() * 6, x = Math.cos(a) * d, z = Math.sin(a) * d;
    const box = [x - 4.2, z - 4.2, x + 4.2, z + 4.2];
    if (boxes.some((b) => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3])) continue;
    if (Math.hypot(x - 6, z + 23) < 8) continue;                        // the mosque's spot
    boxes.push(box);
    const face = Math.round(Math.atan2(-x, -z) / (Math.PI / 2)) * (Math.PI / 2);
    bld(types[Math.floor(rnd() * types.length)], x, z, face, -1 + rnd() * 6);
  }
  for (const name in byType) instanced(scene, byType[name]);
  const mosque = put('bld_mosque', 6.0, -24, 0.15, 1.8, { y: STREET, shadow: false });
  // lit windows at night: the facade's own emission mask
  for (const name of Object.values(BLD).map((b) => b[0])) {
    M[name] && M[name].traverse((o) => { if (o.isMesh && o.material.name === 'facade') { const m = o.material; m.emissiveMap = tex.windows; m.emissive.set(0xffb45a); m.needsUpdate = true; } });
  }
  const facadeMats = [];
  for (const name of Object.values(BLD).map((b) => b[0])) M[name] && M[name].traverse((o) => { if (o.isMesh && o.material.name === 'facade') facadeMats.push(o.material); });

  // strings of light along the neighbours' parapets (glow sprites only, no geometry)
  const cityLights = [];
  for (const r of roofs) {
    const w = { b1: 5, b2: 7, b3: 6, b4: 8 }[r.type], front = { b1: 2.4, b2: 2.2, b3: 2.3, b4: 2.4 }[r.type];
    const c = Math.cos(r.ry), s = Math.sin(r.ry);
    const n = Math.round(w / 0.32);
    for (let i = 0; i <= n; i++) {
      const lx = -w / 2 + (w * i) / n, sag = 0.35 * (1 - Math.pow((2 * i) / n - 1, 2));
      cityLights.push(r.x + lx * c + front * s, r.y + 1.15 - sag, r.z - lx * s + front * c);
    }
  }
  const city = glowPoints(cityLights, 0xffbe6a, 0.32, glow); scene.add(city);

  // ---- people on the neighbouring roofs, turned to face our roof
  const face = (x, z) => Math.atan2(-x, -z);
  const person = (node, x, y, z, file = 'char_kite_flyers') => put(file, x, z, face(x, z), 1, { node, y, center: !!node, shadow: false });
  person(null, F2.x + 0.6, F2.y, F2.z + 1.7, 'char_fire_breather');
  const breather = { x: F2.x + 0.6, y: F2.y, z: F2.z + 1.7 };
  person('flyer_natai', R1.x - 1.6, R1.y, R1.z - 1.2);
  person('flyer_pointing', R1.x - 1.8, R1.y, R1.z + 0.2);
  person('flyer_cheering', R1.x - 1.5, R1.y, R1.z + 1.6);
  if (hi) {
    person('flyer_natai', L2.x + 1.7, L2.y, L2.z - 1.0);
    person('flyer_cheering', L2.x + 1.6, L2.y, L2.z + 0.6);
  }
  const hands = [new THREE.Vector3(R1.x - 1.45, R1.y + 1.15, R1.z - 1.2), new THREE.Vector3(L2.x + 1.85, L2.y + 1.15, L2.z - 1.0)];
  const sparklerAt = new THREE.Vector3(L2.x + 1.75, L2.y + 1.85, L2.z + 0.6);

  // ---- electric poles in the lanes and their tangle of cables
  putS('prop_wire_pole', 5.6, -5.95, 0.3, 1, { y: -6.2, shadow: false });
  putS('prop_wire_pole', -5.5, 5.2, 1.2, 1, { y: -6.4, shadow: false });
  const P1 = new THREE.Vector3(5.6, 1.5, -5.95), P2 = new THREE.Vector3(-5.5, 1.3, 5.2);
  const cables = [
    [P1, new THREE.Vector3(-2.1, 2.4, -5.2), 0.5], [P1, new THREE.Vector3(6.3, 0.6, -1.2), 0.3], [P1, new THREE.Vector3(3.0, -1.5, -6.7), 0.2],
    [P1, new THREE.Vector3(9.0, 0.2, -6.7), 0.3], [P1, new THREE.Vector3(-0.8, 0.9, -6.7), 0.4], [P1, new THREE.Vector3(5.8, -0.4, -12.0), 0.4],
    [P1, new THREE.Vector3(4.75, 0.9, 1.5), 0.6],
    [P2, new THREE.Vector3(6.3, 1.6, 3.0), 0.9], [P2, new THREE.Vector3(-6.3, 1.4, 1.0), 0.3], [P2, new THREE.Vector3(-2.0, -1.2, 6.1), 0.3],
    [P2, new THREE.Vector3(-6.3, 0.5, 9.0), 0.3], [P2, new THREE.Vector3(-4.75, 0.9, -2.0), 0.5], [P2, new THREE.Vector3(-5.6, -1.0, 12.0), 0.4],
  ];
  const cableMesh = new THREE.Mesh(mergeGeometries(cables.map(([a, b, s], i) => cable(a.clone().add(new THREE.Vector3(0, (i % 3) * 0.06, 0)), b, s))),
    new THREE.MeshStandardMaterial({ color: 0x1b1916, roughness: 0.7 }));
  cableMesh.castShadow = hi; scene.add(cableMesh);
  const stuck = put('prop_kite_ghuri', 2.2, -5.55, 0.2, 1.1, { y: 1.38, shadow: false });   // a kite caught on a wire
  if (stuck) stuck.rotation.z = 0.5;

  // ---- string lights: poles at the parapet, strands between them, paper lanterns hanging below
  const poleMat = new THREE.MeshStandardMaterial({ color: 0x3b3530, roughness: 0.8, metalness: 0.2 });
  const poleGeo = new THREE.CylinderGeometry(0.025, 0.03, 1, 6).translate(0, 0.5, 0);
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const L1 = V(-4.45, 2.3, -0.6), L2p = V(-4.45, 2.3, 2.6), Rp1 = V(4.45, 2.3, -2.9), Rp2 = V(4.45, 2.3, 0.2), Rp3 = V(4.45, 2.3, 3.2), CK = V(-2.1, 2.42, -2.7);
  const poleList = [L1, L2p, Rp1, Rp2, Rp3], poles = new THREE.InstancedMesh(poleGeo, poleMat, poleList.length);
  poleList.forEach((p, i) => poles.setMatrixAt(i, new THREE.Matrix4().compose(V(p.x, 0, p.z), new THREE.Quaternion(), V(1, p.y + 0.08, 1))));
  poles.castShadow = hi; poles.computeBoundingSphere(); scene.add(poles);
  const strands = [[CK, Rp1], [L1, Rp2], [L2p, Rp3], [CK, L1], [L1, L2p], [Rp1, Rp2], [Rp2, Rp3]];
  const bulbs = bulbOffsets(M.prop_string_lights), bulbPos = [], strandCopies = [], mids = [];
  for (const [A, B] of strands) {
    const len = Math.hypot(B.x - A.x, B.z - A.z), sy = 0.7 + len / 14;
    const o = putS('prop_string_lights', (A.x + B.x) / 2, (A.z + B.z) / 2, Math.atan2(-(B.z - A.z), B.x - A.x), 1, { y: (A.y + B.y) / 2 - 0.5 * sy, shadow: false });
    if (!o) continue;
    o.scale.set(len / 5, sy, 1); o.rotation.z = Math.atan2(B.y - A.y, len);
    o.updateMatrixWorld(true);
    for (const b of bulbs) { const w = b.clone().applyMatrix4(o.matrixWorld); bulbPos.push(w.x, w.y, w.z); }
    strandCopies.push(o);
    const lowest = (A.y + B.y) / 2 - 0.41 * sy;
    mids.push({ A, B, sag: 0.41 * sy, low: V((A.x + B.x) / 2, lowest, (A.z + B.z) / 2) });
  }
  const bulbGlow = glowPoints(bulbPos, 0xffb860, 0.11, glow); scene.add(bulbGlow);
  const amberMats = new Set();
  for (const name of ['prop_string_lights', 'prop_fanush']) M[name] && M[name].traverse((o) => { if (o.isMesh && o.material.name === 'amber') amberMats.add(o.material); });
  const stringLights = [];
  for (const k of hi ? [0, 1, 2] : [1]) {
    const l = new THREE.PointLight(0xffb052, 0, 8, 1.6); l.position.copy(mids[k].low).add(V(0, -0.35, 0)); scene.add(l); stringLights.push(l);
  }
  // paper lanterns on the strands
  const lanternGlowPos = [];
  const hang = (k, t) => {
    const { A, B, sag } = mids[k];
    const p = A.clone().lerp(B, t); p.y -= sag * 4 * t * (1 - t) + 0.42;
    putS('prop_paper_lantern', p.x, p.z, rnd() * 6, 0.85, { y: p.y, shadow: false });
    lanternGlowPos.push(p.x, p.y + 0.15, p.z);
  };
  hang(1, 0.32); hang(1, 0.68); hang(2, 0.5); hang(0, 0.55);
  const lanternGlow = glowPoints(lanternGlowPos, 0xff5a8a, 0.75, glow); scene.add(lanternGlow);
  const paperLanternMats = new Set();
  M.prop_paper_lantern && M.prop_paper_lantern.traverse((o) => { if (o.isMesh && o.material.name === 'magenta') paperLanternMats.add(o.material); });
  // a bulb over the stair-room door
  const doorLight = new THREE.PointLight(0xffc27a, 0, 5, 1.8); doorLight.position.set(-3.0, 2.1, -2.45); scene.add(doorLight);
  const doorGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xffd090, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
  doorGlow.position.set(-3.0, 2.15, -2.6); doorGlow.scale.setScalar(0.45); scene.add(doorGlow);

  // ---- hurricane lantern by the board
  const lanternLight = new THREE.PointLight(0xffa64a, 0, 3, 2);
  lanternLight.position.copy(lantern.position).add(V(0, 0.2, 0));
  lanternLight.castShadow = hi; lanternLight.shadow.mapSize.set(512, 512); lanternLight.shadow.bias = -0.002;
  scene.add(lanternLight);
  const flame = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xffb060, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
  flame.position.copy(lanternLight.position); flame.scale.setScalar(0.18); scene.add(flame);

  // ---- kites over the city
  const NK = hi ? 170 : 90;
  const kiteMesh = makeKiteMesh(tex, NK); scene.add(kiteMesh);
  const kites = [];
  const anchors = hands.map((h) => h.clone());
  const placeKite = (k, i) => {
    if (i < anchors.length) {                                        // the two flyers we can see
      const h = anchors[i], out = h.clone().setY(0).normalize();
      k.base = h.clone().addScaledVector(out, 14 + rnd() * 6).setY(h.y + 11 + rnd() * 5);
    } else {
      const a = rnd() * Math.PI * 2, d = 13 + Math.pow(rnd(), 0.7) * 85;
      k.base = V(Math.cos(a) * d, 7 + d * 0.32 + rnd() * 12, Math.sin(a) * d);
    }
    k.amp = 0.5 + rnd() * 1.6; k.f = 0.25 + rnd() * 0.5; k.ph = rnd() * 100; k.s = 1.0 + rnd() * 0.7; k.cut = 0;
    k.pos = k.base.clone();
  };
  for (let i = 0; i < NK; i++) { const k = {}; placeKite(k, i); kites.push(k); }
  // strings: from the visible flyers' hands, and from unseen roofs below for the nearer kites
  const stringed = [0, 1];
  for (let i = 2; i < NK && stringed.length < (hi ? 16 : 8); i++) if (kites[i].base.length() < 40) stringed.push(i);
  const stringGeo = new THREE.BufferGeometry(); stringGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(stringed.length * 6), 3));
  const strings = new THREE.LineSegments(stringGeo, new THREE.LineBasicMaterial({ color: 0xe8e0d0, transparent: true, opacity: 0.35 }));
  strings.frustumCulled = false; scene.add(strings);
  const stringFrom = stringed.map((i, n) => n < anchors.length ? anchors[n] : kites[i].base.clone().multiplyScalar(0.55).setY(1.5 + rnd() * 2));
  let nextCut = 6 + rnd() * 8;
  const kDummy = new THREE.Object3D(), wind = V(0.8, 0, 0.3).normalize();

  // ---- fireworks over the skyline
  const fwColors = [0xff5a48, 0x58ff8a, 0xffc24a, 0xff4ac8];
  const fireworks = [];
  for (let i = 0; i < (hi ? 6 : 4); i++) {
    const s = sheetSprite(tex.fxFireworks); scene.add(s);
    const trail = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xffe0a0, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false }));
    trail.scale.setScalar(1.2); trail.visible = false; scene.add(trail);
    fireworks.push({ s, trail, t: -1 });
  }
  let nextFw = 1.5, flash = 0;
  const flashCol = new THREE.Color(), hemiBase = new THREE.Color();
  const launch = (forward = false, big = false) => {
    const f = fireworks.find((x) => x.t < 0); if (!f) return;
    const a = forward ? -Math.PI / 2 + (rnd() - 0.5) * 1.6 : rnd() * Math.PI * 2, d = forward ? 38 + rnd() * 25 : 45 + rnd() * 65;
    f.pos = V(Math.cos(a) * d, 20 + rnd() * 28 + (forward ? -6 : 0), Math.sin(a) * d);
    f.clip = Math.floor(rnd() * 4); f.size = (14 + rnd() * 12) * (big ? 1.3 : 1); f.t = 0; f.dist = d; f.big = big;
    f.trail.visible = true; f.s.visible = false;
  };

  // ---- the fire-breather on the roof ahead
  const fire = sheetSprite(tex.fxFire); fire.center.set(0.1015625, 1 - 0.56640625); fire.material.rotation = 0.35; scene.add(fire);
  const fRot = face(breather.x, breather.z);
  const mouth = V(breather.x, breather.y + 1.6, breather.z).add(V(Math.sin(fRot), 0, Math.cos(fRot)).multiplyScalar(0.12));
  fire.position.copy(mouth); fire.scale.setScalar(2.8);
  const torch = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xff9a40, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false, opacity: 0 }));
  torch.position.copy(V(breather.x, breather.y + 2.0, breather.z).add(V(Math.cos(fRot), 0, -Math.sin(fRot)).multiplyScalar(-0.38)).add(V(Math.sin(fRot), 0, Math.cos(fRot)).multiplyScalar(0.25)));
  torch.scale.setScalar(0.5); scene.add(torch);
  const fireLight = hi ? new THREE.PointLight(0xff8a30, 0, 14, 1.5) : null;
  if (fireLight) { fireLight.position.copy(mouth).add(V(0.6, 0.4, 0.6)); scene.add(fireLight); }
  let fireT = -1, nextFire = 3;

  // ---- a sparkler on the roof to the left, and sparks where a guti is captured
  const sparkler = sheetSprite(tex.fxSparks); sparkler.position.copy(sparklerAt); sparkler.scale.setScalar(0.9); scene.add(sparkler);
  const bursts = [];
  for (let i = 0; i < 3; i++) { const s = sheetSprite(tex.fxSparks, 0xffe6b0); s.material.depthTest = false; s.renderOrder = 3; scene.add(s); bursts.push({ s, t: -1 }); }

  // ---- sky lanterns (fanush) rising from distant roofs: one instanced mesh per part, moved every frame
  const NF = hi ? 7 : 4, fanushParts = [], fanush = [];
  if (M.prop_fanush) {
    M.prop_fanush.updateMatrixWorld(true);
    M.prop_fanush.traverse((o) => {
      if (!o.isMesh) return;
      const im = new THREE.InstancedMesh(o.geometry, o.material, NF);
      im.userData.local = o.matrixWorld.clone(); im.instanceMatrix.setUsage(THREE.DynamicDrawUsage); im.frustumCulled = false;
      scene.add(im); fanushParts.push(im);
    });
  }
  const respawnFanush = (f, first) => {
    const a = -Math.PI / 2 + (rnd() - 0.5) * 3.2, d = 22 + rnd() * 40;
    f.pos.set(Math.cos(a) * d, first ? rnd() * 50 : 1 + rnd() * 3, Math.sin(a) * d);
  };
  for (let i = 0; i < NF; i++) { const f = { pos: V(0, 0, 0), v: 0.45 + rnd() * 0.35, ry: rnd() * 6 }; respawnFanush(f, true); fanush.push(f); }
  const fanushGlow = glowPoints(new Array(NF * 3).fill(0), 0xffa24a, 2.2, glow); scene.add(fanushGlow);
  const fDummy = new THREE.Object3D(), fMat = new THREE.Matrix4();
  const paperMats = new Set();
  M.prop_fanush && M.prop_fanush.traverse((o) => { if (o.isMesh && o.material.name === 'paper') paperMats.add(o.material); });

  for (const name in statics) instanced(scene, statics[name]);

  // ---- time of day
  const cur = {};
  const timeline = makeTimeline(ROOF_TIMES, ['sun', 'sky', 'ground', 'fog'], (v) => {
    const elev = THREE.MathUtils.degToRad(v.elev);
    const dir = V(SUN_DIR.x * Math.cos(elev), Math.sin(elev), SUN_DIR.z * Math.cos(elev));
    sun.position.copy(sun.target.position).addScaledVector(dir, 30);
    sun.color.set(v.sun); sun.intensity = v.sunI;
    hemiBase.set(v.sky); hemi.groundColor.set(v.ground); hemi.intensity = v.hemiI;
    realScene.fog.color.set(v.fog); sky.material.uniforms.uHaze.value.set(v.fog);
    renderer.toneMappingExposure = v.exp;
    realScene.environmentIntensity = v.env;
    realScene.environment = envs[v.panoB];
    const u = sky.material.uniforms;
    u.uA.value = tex.pano[v.panoA]; u.uB.value = tex.pano[v.panoB]; u.uMix.value = v.mix; u.uBright.value = v.bright;
    Object.assign(cur, v);
    for (const m of amberMats) m.emissiveIntensity = 0.6 + v.bulbs * 2.2;
    for (const m of facadeMats) m.emissiveIntensity = v.windows * 1.4;
    for (const m of paperLanternMats) { m.emissive.set(0xff2a5a); m.emissiveIntensity = v.bulbs * 0.25; }
    for (const m of paperMats) { m.emissive.set(0xff9a40); m.emissiveIntensity = v.fanush * 0.9; }
    kiteMesh.material.color.setScalar(v.kites);
    strings.material.opacity = 0.18 + v.kites * 0.22;
    doorGlow.material.opacity = Math.min(1, v.bulbs * 0.6);
    lanternGlow.material.opacity = Math.min(0.8, v.bulbs * 0.4);
    city.material.opacity = Math.min(1, v.bulbs * 0.55);
    bulbGlow.material.opacity = Math.min(1, v.bulbs * 0.6);
  });
  const setTime = (name, instant = false) => timeline.set(name, instant);
  setTime('dusk', true);

  // ---- per frame
  const tmp = V(0, 0, 0);
  function updateKites(dt, t) {
    nextCut -= dt;
    if (nextCut <= 0) {                                           // "bhokatta!" a kite is cut loose and drifts away
      nextCut = 7 + rnd() * 10;
      const i = stringed.length + Math.floor(rnd() * (NK - stringed.length));
      if (kites[i] && !kites[i].cut) kites[i].cut = 0.001;
    }
    for (let i = 0; i < NK; i++) {
      const k = kites[i];
      if (k.cut > 0) {
        k.cut += dt;
        k.pos.addScaledVector(wind, dt * 2.2); k.pos.y -= dt * (0.6 + Math.sin(k.cut * 3) * 0.4);
        if (k.cut > 14 || k.pos.y < 1) placeKite(k, i);
      } else {
        const w = t * k.f + k.ph;
        k.pos.set(k.base.x + Math.sin(w) * k.amp, k.base.y + Math.sin(w * 2.1) * k.amp * 0.4, k.base.z + Math.cos(w * 0.8) * k.amp * 0.6);
      }
      kDummy.position.copy(k.pos);
      tmp.set(0, k.pos.y * 0.35, 0);
      kDummy.lookAt(tmp);                                         // the face turns towards our roof
      kDummy.rotateZ(Math.sin(t * k.f * 3.1 + k.ph) * 0.35 + (k.cut > 0 ? k.cut * 4 : 0));
      kDummy.rotateX(-0.25);
      kDummy.scale.setScalar(k.s);
      kDummy.updateMatrix();
      kiteMesh.setMatrixAt(i, kDummy.matrix);
    }
    kiteMesh.instanceMatrix.needsUpdate = true;
    const sp = stringGeo.attributes.position;
    stringed.forEach((i, n) => {
      const a = stringFrom[n], k = kites[i];
      sp.setXYZ(n * 2, a.x, a.y, a.z);
      sp.setXYZ(n * 2 + 1, k.pos.x, k.pos.y + 0.1 * k.s, k.pos.z);
    });
    sp.needsUpdate = true;
  }

  function updateFireworks(dt) {
    nextFw -= dt * cur.fireworks;
    if (nextFw <= 0 && cur.fireworks > 0.05) { launch(rnd() < 0.5); nextFw = 1.1 + rnd() * 2.6; }
    for (const f of fireworks) {
      if (f.t < 0) continue;
      f.t += dt;
      if (f.t < 0.9) {                                             // the rocket climbing
        const e = f.t / 0.9;
        f.trail.position.set(f.pos.x, f.pos.y - 22 * (1 - e) * (1 - e), f.pos.z);
        f.trail.material.opacity = 0.9; f.trail.scale.setScalar(0.6 + f.dist * 0.012);
        continue;
      }
      if (f.trail.visible) {                                       // bang
        f.trail.visible = false; f.s.visible = true; f.s.position.copy(f.pos);
        flash = Math.min(1.5, flash + (f.big ? 1.2 : 0.7) * (40 / f.dist)); flashCol.set(fwColors[f.clip]);
        sfx && sfx.pop(f.dist, f.big);
      }
      const b = f.t - 0.9, frame = Math.min(3, Math.floor(b / 0.16));
      f.s.frame(f.clip * 4 + frame);
      f.s.scale.setScalar(f.size * (0.55 + Math.min(1, b / 0.6) * 0.5));
      f.s.material.opacity = b < 0.64 ? 1 : Math.max(0, 1 - (b - 0.64) / 1.1);
      f.s.position.y -= dt * 1.2;
      if (b > 1.8) { f.t = -1; f.s.visible = false; }
    }
  }

  function updateFire(dt) {
    if (fireT < 0) {
      nextFire -= dt * cur.fire;
      if (nextFire <= 0 && cur.fire > 0.05) { fireT = 0; fire.visible = true; sfx && sfx.whoosh(mouth.length()); }
    }
    if (fireT >= 0) {
      fireT += dt;
      const f = Math.floor(fireT * 13);
      if (f > 15) { fireT = -1; fire.visible = false; nextFire = 4 + rnd() * 6; if (fireLight) fireLight.intensity = 0; }
      else {
        fire.frame(f); fire.material.opacity = 1;
        if (fireLight) fireLight.intensity = Math.sin(Math.min(1, fireT / 1.2) * Math.PI) * 60 * (0.8 + rnd() * 0.4);
      }
    }
  }

  let wind0 = 1;
  return {
    sun, timeName: () => timeline.name, setTime,
    // sparks fly up where a guti is taken; long chains set off fireworks overhead
    react(at, slow) {
      const b = bursts.find((x) => x.t < 0) || bursts[0];
      b.t = 0; b.s.visible = true; b.s.position.copy(at).setY(0.05); b.s.scale.setScalar(slow ? 0.42 : 0.3);
      if (slow) { launch(true, true); launch(true, true); }
    },
    dispose() {
      realScene.remove(scene); disposeTree(scene);
      for (const k in envs) envs[k].dispose();
      pmrem.dispose(); realScene.environment = null; realScene.fog = null;
    },
    update(dt, t) {
      timeline.update(dt);
      wind0 = 0.8 + Math.sin(t * 0.13) * 0.3;
      const fl = 0.85 + Math.sin(t * 13) * 0.06 + Math.sin(t * 7.3) * 0.05 + (Math.random() - 0.5) * 0.06;
      lanternLight.intensity = cur.lantern * fl;
      flame.material.opacity = Math.min(1, cur.lantern * 0.35) * fl;
      for (const l of stringLights) l.intensity = cur.bulbs * (hi ? 0.9 : 1.8);
      doorLight.intensity = cur.bulbs * 1.6;
      bulbGlow.material.size = 0.11 * (0.95 + Math.sin(t * 2.3) * 0.05);
      updateKites(dt, t);
      updateFireworks(dt);
      updateFire(dt);
      torch.material.opacity = Math.min(1, cur.fire) * fl * 0.9;
      // fireworks briefly tint the whole scene
      flash *= Math.exp(-dt * 3.5);
      hemi.color.copy(hemiBase).lerp(flashCol, Math.min(0.6, flash * 0.35 * cur.fireworks));
      // sparkler loops while it is dark enough
      sparkler.visible = cur.fireworks > 0.4;
      if (sparkler.visible) { sparkler.frame(Math.floor(t * 12) % 16); sparkler.material.opacity = Math.min(1, (cur.fireworks - 0.4) * 2); }
      for (const b of bursts) {
        if (b.t < 0) continue;
        b.t += dt; const f = Math.floor(b.t * 22);
        if (f > 15) { b.t = -1; b.s.visible = false; } else { b.s.frame(f); b.s.material.opacity = 1; }
      }
      const gp = fanushGlow.geometry.attributes.position;
      fanush.forEach((f, i) => {
        f.pos.y += f.v * dt; f.pos.x += wind0 * 0.25 * dt; f.ry += dt * 0.2;
        if (f.pos.y > 75) respawnFanush(f, false);
        fDummy.position.copy(f.pos); fDummy.rotation.y = f.ry; fDummy.updateMatrix();
        for (const part of fanushParts) part.setMatrixAt(i, fMat.multiplyMatrices(fDummy.matrix, part.userData.local));
        gp.setXYZ(i, f.pos.x, f.pos.y + 0.3, f.pos.z);
      });
      gp.needsUpdate = true;
      for (const part of fanushParts) { part.instanceMatrix.needsUpdate = true; part.visible = cur.fanush > 0.05; }
      fanushGlow.material.opacity = cur.fanush * (0.55 + Math.sin(t * 5) * 0.06);
    },
  };
}
