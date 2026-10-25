// Dot Field — plain-JS island (no React/Tailwind).
// Draws the headline as a dot grid that flies in, repels from the cursor,
// and scatters back into the grid on scroll. Port of components/ui/dot-field.tsx.
(function () {
  "use strict";
  const mount = document.getElementById("dotField");
  if (!mount) return;

  const headline = mount.getAttribute("data-headline") || "SCHOOL";
  const accent = mount.getAttribute("data-accent") || "#ff3d00";
  const gridX = 16, gridY = 11;

  const stage = mount;
  const cv = document.createElement("canvas");
  const gl = document.createElement("canvas");
  stage.appendChild(cv);
  stage.appendChild(gl);
  const ctx = cv.getContext("2d");
  const gtx = gl.getContext("2d");
  if (!ctx || !gtx) return;

  let W = 0, H = 0, N = 0;
  let P = new Float32Array(0);
  let t0 = 0, raf = 0, alive = true, visible = true;
  let fg = "#17171c";
  let scrollP = 0, btnP = 0, btnT = 0, kick = 0, last = 0;
  let mouse = { x: -9999, y: -9999, on: false };
  let reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  function readFg() { try { fg = getComputedStyle(stage).color || fg; } catch (e) {} }

  function sample() {
    const c = document.createElement("canvas"), g = c.getContext("2d", { willReadFrequently: true });
    c.width = W; c.height = H;
    const size = Math.min(W * 0.13, H * 0.22, 150);
    g.font = "600 " + size + "px Pusab, Silkscreen, Pixelify Sans, monospace";
    g.textAlign = "center"; g.textBaseline = "middle";
    try { g.letterSpacing = (-size * 0.05) + "px"; } catch (e) {}
    const words = headline.split(/\s+/);
    let lines = [], cur = "";
    for (const w of words) { const t = cur ? cur + " " + w : w; if (g.measureText(t).width > W * 0.9 && cur) { lines.push(cur); cur = w; } else cur = t; }
    lines.push(cur);
    const lh = size * 0.98, top = H * 0.46 - ((lines.length - 1) * lh) / 2;
    lines.forEach((l, i) => g.fillText(l, W / 2, top + i * lh));
    const d = g.getImageData(0, 0, W, H).data, pts = [], step = Math.max(3, Math.round(size / 30));
    for (let y = 0; y < H; y += step) for (let x = 0; x < W; x += step) if (d[(y * W + x) * 4 + 3] > 128) pts.push(x, y);
    return pts;
  }

  function build() {
    const r = stage.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, Math.round(r.width)); H = Math.max(1, Math.round(r.height));
    for (const c of [cv, gl]) { c.width = W * dpr; c.height = H * dpr; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); gtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const [GX, GY] = [gridX, gridY], tgt = sample();
    const cols = Math.ceil(W / GX) + 1, rows = Math.ceil(H / GY) + 1, cells = cols * rows, nText = tgt.length / 2;
    N = Math.max(cells, nText);
    const P = new Float32Array(N * 10);
    for (let i = 0; i < N; i++) {
      const cell = i < cells ? i : ((Math.random() * cells) | 0);
      const hx = (cell % cols) * GX - 6, hy = Math.floor(cell / cols) * GY - 1, o = i * 10;
      P[o] = hx; P[o + 1] = hy; P[o + 4] = hx; P[o + 5] = hy;
    }
    const ids = Array.from({ length: N }, (_, i) => i);
    for (let i = ids.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [ids[i], ids[j]] = [ids[j], ids[i]]; }
    const diag = Math.hypot(W, H);
    for (let k = 0; k < nText; k++) {
      const o = ids[k] * 10, tx = tgt[k * 2], ty = tgt[k * 2 + 1];
      P[o + 6] = tx; P[o + 7] = ty; P[o + 9] = 1;
      P[o + 8] = 0.15 + Math.min(0.9, Math.hypot(tx - W / 2, ty - H * 0.46) / diag) * 1.1 + Math.random() * 0.25;
    }
    P = PP;
  }

  function buildReal() {
    const r = stage.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, Math.round(r.width)); H = Math.max(1, Math.round(r.height));
    for (const c of [cv, gl]) { c.width = W * dpr; c.height = H * dpr; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); gtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const [GX, GY] = [gridX, gridY], tgt = sample();
    const cols = Math.ceil(W / GX) + 1, rows = Math.ceil(H / GY) + 1, cells = cols * rows, nText = tgt.length / 2;
    N = Math.max(cells, nText);
    const PP = new Float32Array(N * 10);
    for (let i = 0; i < N; i++) {
      const cell = i < cells ? i : ((Math.random() * cells) | 0);
      const hx = (cell % cols) * GX - 6, hy = Math.floor(cell / cols) * GY - 1, o = i * 10;
      PP[o] = hx; PP[o + 1] = hy; PP[o + 4] = hx; PP[o + 5] = hy;
    }
    const ids = Array.from({ length: N }, (_, i) => i);
    for (let i = ids.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [ids[i], ids[j]] = [ids[j], ids[i]]; }
    const diag = Math.hypot(W, H);
    for (let k = 0; k < nText; k++) {
      const o = ids[k] * 10, tx = tgt[k * 2], ty = tgt[k * 2 + 1];
      PP[o + 6] = tx; PP[o + 7] = ty; PP[o + 9] = 1;
      PP[o + 8] = 0.15 + Math.min(0.9, Math.hypot(tx - W / 2, ty - H * 0.46) / diag) * 1.1 + Math.random() * 0.25;
    }
    P = PP;
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (!alive || !visible) return;
    const t = (now - t0) / 1000;
    const R = 120, R2 = R * R;
    ctx.clearRect(0, 0, W, H); gtx.clearRect(0, 0, W, H);
    ctx.fillStyle = fg; gtx.fillStyle = accent;
    for (let i = 0; i < N; i++) {
      const o = i * 10, isT = P[o + 9] === 1;
      let tx = P[o + 4], ty = P[o + 5], k = 0.06, fl = 0;
      const local = t - P[o + 8];
      if (isT) {
        if (local > 0) { const d = Math.min(1, scrollP * (0.8 + P[o + 8] * 0.6)); tx = P[o + 6] + (P[o + 4] - P[o + 6]) * d; ty = P[o + 7] + (P[o + 5] - P[o + 7]) * d; k = Math.min(0.09, 0.02 + local * 0.08); }
        fl = local > -1 ? Math.max(0, 1 - Math.max(0, local) * 1.4) : 0;
      }
      if (kick > 0.01) fl = Math.max(fl, Math.min(1, kick) * 0.9);
      let ax = (tx - P[o]) * k, ay = (ty - P[o + 1]) * k;
      if (fl > 0) { const a = (Math.sin(P[o] * 0.004 + t * 0.7) + Math.cos(P[o + 1] * 0.005 - t * 0.5)) * Math.PI; ax += Math.cos(a) * 2.2 * fl; ay += Math.sin(a) * 2.2 * fl; }
      if (mouse.on && R > 0) {
        const dx = P[o] - mouse.x, dy = P[o + 1] - mouse.y, d2 = dx * dx + dy * dy;
        if (d2 < R2) { const d = Math.sqrt(d2) || 1, f = (1 - d / R) * 6; ax += (dx / d) * f; ay += (dy / d) * f; }
      }
      P[o + 2] = (P[o + 2] + ax) * 0.82; P[o + 3] = (P[o + 3] + ay) * 0.82;
      P[o] += P[o + 2]; P[o + 1] += P[o + 3];
      const x = P[o], y = P[o + 1], sp = Math.abs(P[o + 2]) + Math.abs(P[o + 3]);
      const gridA = Math.min(0.5, 0.12 + sp * 0.05);
      if (isT) {
        const q = Math.min(1, scrollP);
        const settle = Math.min(1, Math.max(0, (t - P[o + 8]) * 1.2)) * (1 - q);
        const a = (0.34 + settle * 0.6) * (1 - q) + gridA * q, r = 1 - q * 0.25;
        ctx.globalAlpha = a; ctx.fillRect(x - r, y - r, r * 2, r * 2);
      } else {
        ctx.globalAlpha = gridA; ctx.fillRect(x - 0.75, y - 0.75, 1.5, 1.5);
      }
    }
    ctx.globalAlpha = 1;
    kick = kick * 0.93;
  }

  function onScroll() {
    const r = stage.getBoundingClientRect();
    scrollP = Math.min(1, Math.max(0, -r.top / (window.innerHeight * 0.7)));
  }

  function move(e) {
    const r = stage.getBoundingClientRect();
    mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; mouse.on = true;
  }
  function leave() { mouse.on = false; }

  const ro = new ResizeObserver(() => { buildReal(); t0 = performance.now() - 3000; });
  const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0 });

  stage.addEventListener("pointermove", move);
  stage.addEventListener("pointerleave", leave);
  window.addEventListener("scroll", onScroll, { passive: true });

  document.fonts.ready.then(() => {
    buildReal(); t0 = performance.now();
    ro.observe(stage); io.observe(stage);
    raf = requestAnimationFrame(frame);
  });

  const style = document.createElement("style");
  style.textContent = `
    #dotField { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
    #dotField canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
    .df-h1 { position: relative; z-index: 2; }
  `;
  document.head.appendChild(style);

  // h1 fallback for screen readers
  const h1 = document.createElement("h1");
  h1.className = "sr-only";
  h1.textContent = headline;
  mount.appendChild(h1);
})();
