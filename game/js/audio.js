// Synthesised sound: pebble clacks, captures, and a quiet village ambience.
export class Sfx {
  constructor() { this.ctx = null; this.on = true; this.mode = 'day'; this.nextBird = 0; this.nextCricket = 0; }

  start() {
    if (this.ctx) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const c = this.ctx = new AC();
    this.master = c.createGain(); this.master.gain.value = this.on ? 0.9 : 0; this.master.connect(c.destination);
    // noise buffer
    const len = c.sampleRate * 2, buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) { const w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = w; }
    this.noise = buf;
    // brown-ish wind bed
    const brown = c.createBuffer(1, len, c.sampleRate), bd = brown.getChannelData(0);
    for (let i = 0; i < len; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; bd[i] = last * 3.2; }
    const src = c.createBufferSource(); src.buffer = brown; src.loop = true;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 500;
    this.windGain = c.createGain(); this.windGain.gain.value = 0.05;
    src.connect(lp).connect(this.windGain).connect(this.master); src.start();
    this.loop();
  }

  setOn(v) { this.on = v; if (this.master) this.master.gain.setTargetAtTime(v ? 0.9 : 0, this.ctx.currentTime, 0.1); }
  setMode(m) { this.mode = m; }

  env(g, t, a, peak, dec) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + dec); }

  clack(v = 0.7) {
    const c = this.ctx; if (!c) return; const t = c.currentTime;
    const n = c.createBufferSource(); n.buffer = this.noise;
    const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1800 + Math.random() * 1400; bp.Q.value = 3;
    const g = c.createGain(); this.env(g, t, 0.002, 0.5 * v, 0.07);
    n.connect(bp).connect(g).connect(this.master); n.start(t, Math.random()); n.stop(t + 0.1);
    const o = c.createOscillator(); o.type = 'sine'; o.frequency.value = 2400 + Math.random() * 900;
    const g2 = c.createGain(); this.env(g2, t, 0.001, 0.12 * v, 0.04);
    o.connect(g2).connect(this.master); o.start(t); o.stop(t + 0.06);
    // dull thump of soil
    const o2 = c.createOscillator(); o2.type = 'sine'; o2.frequency.setValueAtTime(180, t); o2.frequency.exponentialRampToValueAtTime(70, t + 0.08);
    const g3 = c.createGain(); this.env(g3, t, 0.002, 0.35 * v, 0.09);
    o2.connect(g3).connect(this.master); o2.start(t); o2.stop(t + 0.12);
  }

  capture() {
    const c = this.ctx; if (!c) return; const t = c.currentTime;
    this.clack(1);
    const o = c.createOscillator(); o.type = 'triangle'; o.frequency.setValueAtTime(520, t + 0.02); o.frequency.exponentialRampToValueAtTime(260, t + 0.25);
    const g = c.createGain(); this.env(g, t + 0.02, 0.01, 0.12, 0.3);
    o.connect(g).connect(this.master); o.start(t); o.stop(t + 0.4);
  }

  tick() {
    const c = this.ctx; if (!c) return; const t = c.currentTime;
    const o = c.createOscillator(); o.frequency.value = 1300; const g = c.createGain(); this.env(g, t, 0.002, 0.05, 0.05);
    o.connect(g).connect(this.master); o.start(t); o.stop(t + 0.08);
  }

  chord(happy = true) {
    const c = this.ctx; if (!c) return; const t = c.currentTime;
    const notes = happy ? [392, 494, 587, 784] : [330, 392, 466];
    notes.forEach((f, i) => {
      const o = c.createOscillator(); o.type = 'triangle'; o.frequency.value = f;
      const g = c.createGain(); this.env(g, t + i * 0.12, 0.02, 0.09, 1.4);
      o.connect(g).connect(this.master); o.start(t + i * 0.12); o.stop(t + i * 0.12 + 1.6);
    });
  }

  bird(t) {
    const c = this.ctx;
    const n = 2 + Math.floor(Math.random() * 4), base = 2800 + Math.random() * 1800;
    for (let i = 0; i < n; i++) {
      const s = t + i * (0.09 + Math.random() * 0.05);
      const o = c.createOscillator(); o.type = 'sine';
      o.frequency.setValueAtTime(base, s); o.frequency.exponentialRampToValueAtTime(base * (1.2 + Math.random() * 0.4), s + 0.06);
      const g = c.createGain(); this.env(g, s, 0.01, 0.018, 0.07);
      const pan = c.createStereoPanner ? c.createStereoPanner() : null;
      if (pan) { pan.pan.value = Math.random() * 2 - 1; o.connect(g).connect(pan).connect(this.master); } else o.connect(g).connect(this.master);
      o.start(s); o.stop(s + 0.12);
    }
  }

  cricket(t) {
    const c = this.ctx;
    const o = c.createOscillator(); o.frequency.value = 4400 + Math.random() * 400;
    const am = c.createOscillator(); am.frequency.value = 28; const amg = c.createGain(); amg.gain.value = 0.5;
    const g = c.createGain(); g.gain.value = 0;
    am.connect(amg).connect(g.gain);
    const out = c.createGain(); this.env(out, t, 0.05, 0.012, 0.6);
    o.connect(g).connect(out).connect(this.master);
    o.start(t); am.start(t); o.stop(t + 0.8); am.stop(t + 0.8);
  }

  loop() {
    const c = this.ctx; if (!c) return;
    const t = c.currentTime;
    if (this.on) {
      if (this.mode !== 'night' && t > this.nextBird) { this.bird(t + 0.05); this.nextBird = t + 2.5 + Math.random() * 7; }
      if (this.mode !== 'afternoon' && t > this.nextCricket) { this.cricket(t + 0.05); this.nextCricket = t + (this.mode === 'night' ? 0.7 + Math.random() * 1.2 : 3 + Math.random() * 5); }
    }
    setTimeout(() => this.loop(), 250);
  }
}
