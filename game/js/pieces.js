// Guti meshes, move/capture animation, selection and move hints.
import * as THREE from 'three';
import { P1, P2, POINTS } from './rules.js';
import { toWorld, SPACING } from './world.js';

const SCALE = 1.6;
const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

export const PIECE_SETS = {
  pebbles: { name: 'River pebbles', p1: (k) => ['guti_pebble_variations', 'cream_variation_' + (1 + (k % 3))], p2: (k) => ['guti_pebble_variations', 'dark_variation_' + (1 + (k % 3))] },
  village: { name: 'Clay & tamarind', p1: () => ['guti_clay_shard'], p2: () => ['guti_tamarind_seed'] },
};

export class Pieces {
  constructor(scene, models, tex, sfx) {
    this.scene = scene; this.models = models; this.sfx = sfx;
    this.group = new THREE.Group(); scene.add(this.group);
    this.byPoint = new Map();        // point index -> piece
    this.all = [];
    this.anims = [];
    this.setName = 'pebbles';
    this.shadowMat = new THREE.MeshBasicMaterial({ map: tex.shadow, transparent: true, depthWrite: false, opacity: 0.8 });
    this.shadowGeo = new THREE.PlaneGeometry(0.06, 0.06).rotateX(-Math.PI / 2);
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

  makeMesh(player, k) {
    const set = PIECE_SETS[this.setName];
    const [file, node] = (player === P1 ? set.p1 : set.p2)(k);
    const src = node ? this.models[file].getObjectByName(node) : this.models[file];
    // Wrap rather than reset the clone: quantized GLBs keep their dequantization transform on the node.
    const m = new THREE.Group(); m.add(src.clone(true));
    m.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return m;
  }

  build(board) {
    for (const p of this.all) this.group.remove(p.obj);
    this.all = []; this.byPoint.clear(); this.anims = [];
    this.captured = { [P1]: 0, [P2]: 0 };
    let k1 = 0, k2 = 0;
    board.forEach((v, i) => {
      if (!v) return;
      const k = v === P1 ? k1++ : k2++;
      const obj = new THREE.Group();
      const mesh = this.makeMesh(v, k);
      mesh.scale.setScalar(SCALE * (0.94 + ((k * 37) % 11) / 100));
      mesh.rotation.y = (k * 2.399) % (Math.PI * 2);
      const sh = new THREE.Mesh(this.shadowGeo, this.shadowMat.clone()); sh.position.y = 0.0015; sh.renderOrder = 1;
      obj.add(mesh, sh);
      obj.position.copy(toWorld(i));
      this.group.add(obj);
      const piece = { obj, mesh, sh, player: v, point: i, k, lift: 0 };
      this.all.push(piece); this.byPoint.set(i, piece);
    });
    this.selected = -1; this.selRing.visible = false; this.clearHints();
    this.lastFrom.visible = this.lastTo.visible = false;
  }

  setSet(name, board) { this.setName = name; this.build(board); }

  // Snap visuals to a board (after undo / restore). Captured pieces go to the piles.
  sync(board) {
    this.build(board);
    const c1 = 16 - board.filter((v) => v === P1).length, c2 = 16 - board.filter((v) => v === P2).length;
    for (let i = 0; i < c2; i++) this.addToPile(P1, P2, true);
    for (let i = 0; i < c1; i++) this.addToPile(P2, P1, true);
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
    const obj = new THREE.Group();
    const mesh = this.makeMesh(victimPlayer, n); mesh.scale.setScalar(SCALE); mesh.rotation.y = n * 1.7;
    const sh = new THREE.Mesh(this.shadowGeo, this.shadowMat.clone()); sh.position.y = 0.0015;
    obj.add(mesh, sh); obj.position.copy(this.pilePos(owner, n)); this.group.add(obj);
    this.all.push({ obj, mesh, sh, player: victimPlayer, point: -1, k: n, lift: 0, dead: true });
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
          p.sh.position.y = 0.0015 - p.obj.position.y; p.sh.material.opacity = 0.8 - p.obj.position.y * 6;
          if (victim && !hitDone && e > 0.5) { hitDone = true; this.knock(victim, p.player, opts); }
        },
        done: () => {
          p.obj.position.copy(B); p.mesh.rotation.z = 0; p.sh.position.y = 0.0015; p.sh.material.opacity = 0.8;
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
        v.sh.position.y = 0.0015 - v.obj.position.y; v.sh.material.opacity = 0.8 - v.obj.position.y * 5;
      },
      done: () => { v.obj.position.copy(end); v.mesh.rotation.x = Math.PI * Math.round(spin / Math.PI) ; v.mesh.rotation.z = 0; v.sh.position.y = 0.0015; v.sh.material.opacity = 0.8; this.bounce(v); this.sfx && this.sfx.clack(0.4); },
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
        p.sh.material.opacity = 0.8 - p.mesh.position.y * 14;
        p.sh.scale.setScalar(1 + p.mesh.position.y * 18);
      }
    }
    const pulse = 0.75 + Math.sin(this.time * 4) * 0.25;
    this.selRing.material.opacity = 0.7 * pulse;
    for (const m of this.markers.children) m.material.opacity = (m.userData.base ?? 0.8) * (0.65 + Math.sin(this.time * 4 + (m.userData.phase || 0)) * 0.35);
  }
}

export { SPACING, POINTS };
