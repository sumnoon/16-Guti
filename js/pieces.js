// Guti meshes, move/capture animation, selection and move hints.
// Every guti is drawn by instancing: one InstancedMesh per part of each model in use, plus one for
// all the contact shadows. A piece only keeps plain Object3Ds (obj = place, mesh = tilt / spin / lift,
// sh = shadow) that the animations move; draw() turns them into instance matrices every frame.
import * as THREE from 'three';
import { P1, P2, POINTS } from './rules.js';
import { toWorld, SPACING } from './world.js';

const SCALE = 1.6;
const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
const _m = new THREE.Matrix4(), _n = new THREE.Matrix4();
const capacity = (n) => Math.max(16, 2 ** Math.ceil(Math.log2(Math.max(n, 1))));

export const PIECE_SETS = {
  pebbles: { name: 'River pebbles', colours: ['cream', 'slate'], p1: (k) => ['guti_pebble_variations', 'cream_variation_' + (1 + (k % 3))], p2: (k) => ['guti_pebble_variations', 'dark_variation_' + (1 + (k % 3))] },
  village: { name: 'Clay & tamarind', colours: ['clay', 'tamarind'], p1: () => ['guti_clay_shard'], p2: () => ['guti_tamarind_seed'] },
  rooftop: { name: 'Marbles & caps', colours: ['marbles', 'bottle caps'], p1: () => ['guti_marble_glass'], p2: () => ['guti_bottle_cap'] },
};

export class Pieces {
  constructor(scene, models, tex, sfx) {
    this.scene = scene; this.models = models; this.sfx = sfx;
    this.group = new THREE.Group(); scene.add(this.group);
    this.byPoint = new Map();        // point index -> piece
    this.all = [];
    this.anims = [];
    this.setName = 'pebbles';
    this.batches = new Map();        // model file/node -> { parts, list, meshes }
    // Contact shadows: per-instance opacity (aShade) multiplies the soft shadow sprite's alpha.
    this.shadowMat = new THREE.MeshBasicMaterial({ map: tex.shadow, transparent: true, depthWrite: false });
    this.shadowMat.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aShade;\nvarying float vShade;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvShade = aShade;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vShade;')
        .replace('#include <alphamap_fragment>', '#include <alphamap_fragment>\ndiffuseColor.a *= vShade;');
    };
    this.shadows = null;
    this.markGeo = new THREE.PlaneGeometry(0.05, 0.05).rotateX(-Math.PI / 2);
    this.glow = tex.glow;
    this.markers = new THREE.Group(); scene.add(this.markers);
    this.selRing = this.mark(0xfff1c4, 0.075, 0.9); this.selRing.visible = false; scene.add(this.selRing);
    this.lastFrom = this.mark(0xffffff, 0.05, 0.25); this.lastTo = this.mark(0xffffff, 0.06, 0.35);
    this.lastFrom.visible = this.lastTo.visible = false; scene.add(this.lastFrom, this.lastTo);
    this.selected = -1; this.time = 0; this.captured = { [P1]: 0, [P2]: 0 };
  }

  mark(color, size, opacity) {
    const m = new THREE.Mesh(this.markGeo, new THREE.MeshBasicMaterial({ map: this.glow, color, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity }));
    m.scale.setScalar(size / 0.05); m.renderOrder = 2; m.userData.base = opacity; return m;
  }

  // The model a guti uses, as a batch of instanced parts shared by every guti using that model.
  batchFor(player, k) {
    const set = PIECE_SETS[this.setName];
    const [file, node] = (player === P1 ? set.p1 : set.p2)(k);
    const key = file + '/' + (node || '');
    let b = this.batches.get(key);
    if (b) return b;
    const src = node ? this.models[file].getObjectByName(node) : this.models[file];
    // Each part keeps its transform relative to the model as a local matrix, src's own node transform
    // included: quantized GLBs carry their dequantization scale / offset there.
    const parts = [];
    src.traverse((o) => {
      if (!o.isMesh) return;
      const local = new THREE.Matrix4();
      for (let n = o; ; n = n.parent) { local.premultiply(_m.compose(n.position, n.quaternion, n.scale)); if (n === src) break; }
      parts.push({ geometry: o.geometry, material: o.material, local, cast: !o.userData.noShadow });
    });
    b = { parts, list: [], meshes: [] };
    this.batches.set(key, b);
    return b;
  }

  newPiece(player, k, point) {
    const obj = new THREE.Object3D(), mesh = new THREE.Object3D(), sh = new THREE.Object3D();
    sh.position.y = 0.0015;
    const piece = { obj, mesh, sh, shade: 0.8, player, point, k, lift: 0, batch: this.batchFor(player, k) };
    this.all.push(piece);
    return piece;
  }

  // (Re)assign instance slots after the set of pieces changed.
  rebatch() {
    for (const b of this.batches.values()) b.list = [];
    for (const p of this.all) { p.slot = p.batch.list.length; p.batch.list.push(p); }
    for (const b of this.batches.values()) {
      const n = b.list.length;
      if (n > (b.meshes[0]?.instanceMatrix.count ?? 0)) {
        for (const m of b.meshes) { this.group.remove(m); m.dispose(); }
        b.meshes = b.parts.map((part) => {
          const m = new THREE.InstancedMesh(part.geometry, part.material, capacity(n));
          m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
          m.castShadow = part.cast; m.receiveShadow = true; m.frustumCulled = false;
          return m;
        });
      }
      for (const m of b.meshes) { m.count = n; if (n) this.group.add(m); else this.group.remove(m); }
    }
    const n = this.all.length;
    if (!this.shadows || n > this.shadows.instanceMatrix.count) {
      if (this.shadows) { this.group.remove(this.shadows); this.shadows.geometry.dispose(); this.shadows.dispose(); }
      const geo = new THREE.PlaneGeometry(0.06, 0.06).rotateX(-Math.PI / 2), cap = capacity(n);
      geo.setAttribute('aShade', new THREE.InstancedBufferAttribute(new Float32Array(cap), 1).setUsage(THREE.DynamicDrawUsage));
      this.shadows = new THREE.InstancedMesh(geo, this.shadowMat, cap);
      this.shadows.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      this.shadows.renderOrder = 1; this.shadows.frustumCulled = false;
      this.group.add(this.shadows);
    }
    this.shadows.count = n;
    this.dirty = false;
    this.draw();
  }

  // Copy every piece's transforms into the instance buffers.
  draw() {
    const shade = this.shadows.geometry.attributes.aShade;
    this.all.forEach((p, i) => {
      p.obj.updateMatrix(); p.mesh.updateMatrix(); p.sh.updateMatrix();
      _m.multiplyMatrices(p.obj.matrix, p.mesh.matrix);
      p.batch.meshes.forEach((m, j) => m.setMatrixAt(p.slot, _n.multiplyMatrices(_m, p.batch.parts[j].local)));
      this.shadows.setMatrixAt(i, _n.multiplyMatrices(p.obj.matrix, p.sh.matrix));
      shade.array[i] = p.shade;
    });
    for (const b of this.batches.values()) if (b.list.length) for (const m of b.meshes) m.instanceMatrix.needsUpdate = true;
    this.shadows.instanceMatrix.needsUpdate = true; shade.needsUpdate = true;
  }

  build(board) { this.place(board); this.rebatch(); }

  place(board) {
    this.all = []; this.byPoint.clear(); this.anims = [];
    this.captured = { [P1]: 0, [P2]: 0 };
    let k1 = 0, k2 = 0;
    board.forEach((v, i) => {
      if (!v) return;
      const k = v === P1 ? k1++ : k2++;
      const piece = this.newPiece(v, k, i);
      piece.mesh.scale.setScalar(SCALE * (0.94 + ((k * 37) % 11) / 100));
      piece.mesh.rotation.y = (k * 2.399) % (Math.PI * 2);
      piece.obj.position.copy(toWorld(i));
      this.byPoint.set(i, piece);
    });
    this.selected = -1; this.selRing.visible = false; this.clearHints();
    this.lastFrom.visible = this.lastTo.visible = false;
  }

  setSet(name, board) { this.setName = name; this.build(board); }

  // Snap visuals to a board (after undo / restore). Captured pieces go to the piles.
  sync(board) {
    this.place(board);
    const c1 = 16 - board.filter((v) => v === P1).length, c2 = 16 - board.filter((v) => v === P2).length;
    for (let i = 0; i < c2; i++) this.addToPile(P1, P2, true);
    for (let i = 0; i < c1; i++) this.addToPile(P2, P1, true);
    this.rebatch();
  }

  pilePos(owner, n) {
    // capturer's pile sits to their right-hand side
    const side = owner === P1 ? 1 : -1;
    const row = Math.floor(n / 4), col = n % 4;
    return new THREE.Vector3(side * (0.33 + col * 0.045 + (row % 2) * 0.02), 0, side * (0.36 - row * 0.05));
  }

  addToPile(owner, victimPlayer, instant) {
    const n = this.captured[owner]++;
    if (!instant) return this.pilePos(owner, n);
    const p = this.newPiece(victimPlayer, n, -1); p.dead = true;
    p.mesh.scale.setScalar(SCALE); p.mesh.rotation.y = n * 1.7;
    p.obj.position.copy(this.pilePos(owner, n));
    this.dirty = true;
  }

  pieceAt(i) { return this.byPoint.get(i); }

  select(i) {
    if (this.selected >= 0 && this.byPoint.get(this.selected)) this.byPoint.get(this.selected).lift = 0;
    this.selected = i;
    const p = this.byPoint.get(i);
    if (p) { p.lift = 1; this.selRing.visible = true; this.selRing.position.copy(toWorld(i)).setY(0.002); }
    else this.selRing.visible = false;
  }

  clearHints() {
    for (const c of [...this.markers.children]) { this.markers.remove(c); c.geometry !== this.markGeo && c.geometry.dispose(); }
  }

  showHints(actions) {
    this.clearHints();
    for (const a of actions) {
      if (a.end) continue;
      const cap = a.over !== undefined;
      const m = this.mark(cap ? 0xff7a4a : 0xffd27a, cap ? 0.085 : 0.07, 1.0);
      m.position.copy(toWorld(a.to)).setY(0.002); m.userData.phase = Math.random() * 6; m.userData.to = a.to;
      this.markers.add(m);
      if (cap) {
        const A = toWorld(a.from), B = toWorld(a.to), C = toWorld(a.over).setY(0.07);
        const curve = new THREE.QuadraticBezierCurve3(A.setY(0.025), C, B.setY(0.006));
        const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.0016, 6), new THREE.MeshBasicMaterial({ color: 0xff9a5a, transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false }));
        tube.userData.base = 0.75; this.markers.add(tube);
        const v = this.mark(0xff4a2a, 0.07, 0.6); v.position.copy(toWorld(a.over)).setY(0.003); v.userData.phase = 0; this.markers.add(v);
      }
    }
  }

  markLast(from, to) {
    this.lastFrom.visible = this.lastTo.visible = true;
    this.lastFrom.position.copy(toWorld(from)).setY(0.0018);
    this.lastTo.position.copy(toWorld(to)).setY(0.0019);
  }

  // Animate one action. Resolves when the piece has landed.
  play(action, opts = {}) {
    const p = this.byPoint.get(action.from);
    if (!p) return Promise.resolve();
    this.select(-1); this.clearHints();
    const A = toWorld(action.from), B = toWorld(action.to);
    const isCap = action.over !== undefined;
    const dur = (isCap ? 0.55 : 0.38) * (opts.slow ? 1.6 : 1);
    const height = isCap ? 0.07 : 0.028;
    this.byPoint.delete(action.from); this.byPoint.set(action.to, p); p.point = action.to; p.lift = 0;
    let victim = null;
    if (isCap) { victim = this.byPoint.get(action.over); this.byPoint.delete(action.over); }
    return new Promise((resolve) => {
      let hitDone = false;
      this.anims.push({
        t: 0, dur,
        step: (t) => {
          const e = ease(t);
          p.obj.position.lerpVectors(A, B, e);
          p.obj.position.y = Math.sin(Math.PI * e) * height;
          p.mesh.rotation.z = Math.sin(Math.PI * e) * 0.25 * (B.x - A.x > 0 ? -1 : 1);
          p.sh.position.y = 0.0015 - p.obj.position.y; p.shade = 0.8 - p.obj.position.y * 6;
          if (victim && !hitDone && e > 0.5) { hitDone = true; this.knock(victim, p.player, opts); }
        },
        done: () => {
          p.obj.position.copy(B); p.mesh.rotation.z = 0; p.sh.position.y = 0.0015; p.shade = 0.8;
          this.bounce(p);
          this.sfx && this.sfx.clack(isCap ? 0.9 : 0.7);
          this.markLast(action.from, action.to);
          resolve();
        },
      });
    });
  }

  knock(v, capturer, opts) {
    this.sfx && this.sfx.capture();
    const start = v.obj.position.clone();
    const end = this.addToPile(capturer, v.player, false);
    const spin = (Math.random() - 0.5) * 12;
    v.point = -1; v.dead = true;
    this.anims.push({
      bg: true, t: 0, dur: 0.75 * (opts.slow ? 1.4 : 1),
      step: (t) => {
        const e = 1 - Math.pow(1 - t, 2);
        v.obj.position.lerpVectors(start, end, e);
        v.obj.position.y = Math.sin(Math.PI * t) * 0.12;
        v.mesh.rotation.x = e * spin; v.mesh.rotation.z = e * spin * 0.5;
        v.sh.position.y = 0.0015 - v.obj.position.y; v.shade = 0.8 - v.obj.position.y * 5;
      },
      done: () => { v.obj.position.copy(end); v.mesh.rotation.x = Math.PI * Math.round(spin / Math.PI) ; v.mesh.rotation.z = 0; v.sh.position.y = 0.0015; v.shade = 0.8; this.bounce(v); this.sfx && this.sfx.clack(0.4); },
    });
  }

  bounce(p) {
    this.anims.push({ bg: true, t: 0, dur: 0.22, step: (t) => { p.obj.position.y = Math.abs(Math.sin(t * Math.PI * 2)) * 0.004 * (1 - t); }, done: () => { p.obj.position.y = 0; } });
  }

  get busy() { return this.anims.some((a) => !a.bg); }

  update(dt) {
    this.time += dt;
    for (let i = this.anims.length - 1; i >= 0; i--) {
      const a = this.anims[i];
      a.t += dt / a.dur;
      if (a.t >= 1) { this.anims.splice(i, 1); a.done(); } else a.step(a.t);
    }
    // lifted (selected) piece bobs gently
    for (const p of this.all) {
      if (p.dead) continue;
      const target = p.lift ? 0.016 + Math.sin(this.time * 4) * 0.003 : 0;
      if (!this.busy || p.lift) {
        p.mesh.position.y += (target - p.mesh.position.y) * Math.min(1, dt * 12);
        p.shade = 0.8 - p.mesh.position.y * 14;
        p.sh.scale.setScalar(1 + p.mesh.position.y * 18);
      }
    }
    if (this.dirty) this.rebatch(); else this.draw();
    const pulse = 0.75 + Math.sin(this.time * 4) * 0.25;
    this.selRing.material.opacity = 0.7 * pulse;
    for (const m of this.markers.children) m.material.opacity = (m.userData.base ?? 0.8) * (0.65 + Math.sin(this.time * 4 + (m.userData.phase || 0)) * 0.35);
  }
}

export { SPACING, POINTS };
