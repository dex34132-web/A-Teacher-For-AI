/* School — compression stage.
 * A real School session runs in a real terminal, the window fills, the
 * transcript is compressed into four named blocks, and a liquid-glass wave
 * rises through the stage: everything it passes is blurred through the glass
 * and the lines at the crest are carried away with it. Then the wave and the
 * text slide up together and the loop restarts.
 */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const stage = $(".cx-stage");
  const linesEl = $("#cx-lines");
  if (!stage || !linesEl) return;

/* A real terminal scrolls. The transcript keeps only the last MAX_LINES
   entries so the window never grows, the loop ends where it started, and
   the context meter cannot creep upward across cycles. */
const MAX_LINES = 18;

  const winEl = $("#cx-window");
  const blocksEl = $("#cx-blocks");
  const fillEl = $("#cx-fill");
  const cutEl = $("#cx-cut");
  const tokensEl = $("#cx-tokens");
  const stampEl = $("#cx-stamp");
  const waveEl = $("#cx-wave");
  const waveGlass = $("#cx-wave-glass");
  const waveLine = $("#cx-wave-line");
  const waveFill = $("#cx-wave-fill");
  const kickerEl = $("#cx-kicker");
  const valueEl = $("#cx-value");
  const noteEl = $("#cx-note");
  const readout = $("#cx-readout");

  /* ------------------------------------------------------------------ *
   * liquid glass refraction filter (21st.dev liquid-glass lineage)
   * ------------------------------------------------------------------ */
  const LIQ = "cxLiquid";
  function ensureLiquid() {
    if (document.getElementById(LIQ)) return;
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("id", "cx-liquid-def");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    svg.setAttribute("aria-hidden", "true");
    svg.style.cssText = "position:absolute;width:0;height:0;pointer-events:none";
    svg.innerHTML =
      '<filter id="' + LIQ + '" x="-25%" y="-25%" width="150%" height="150%" color-interpolation-filters="sRGB">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.005 0.013" numOctaves="2" seed="11" result="n"/>' +
      '<feGaussianBlur in="n" stdDeviation="2.2" result="s"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="s" scale="16" xChannelSelector="R" yChannelSelector="G"/>' +
      "</filter>";
    document.body.appendChild(svg);
  }
  ensureLiquid();

  /* ------------------------------------------------------------------ *
   * the real session (verbatim output from School V2.6)
   * ------------------------------------------------------------------ */
  const SESSION = [
    { cmd: "school status" },
    {
      out: [
        "School V2.6 Component Status:",
        "  school: available      v2_5: available",
        "  v2_6: available        persistence: available",
        "  security: available",
        "  Plugin 2.6.0 · Bridge 2.6.0 · match: yes",
        "┌▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓████┐ 100% [HIGH]",
        "● school  ● v2_5  ● v2_6  ● persistence  ● security",
        "◉ 100%"
      ]
    },
    { cmd: 'school_remember({ content: "retry policy: 3 attempts, exponential backoff" })' },
    { out: ["stored 8f21c4 · project teach · 1 pattern"] },
    { cmd: 'school_remember({ content: "the job queue is FIFO, deduped by content hash" })' },
    { out: ["stored 3ac910 · project teach · 1 pattern"] },
    { cmd: 'school_remember({ content: "sandbox tests flake on the third retry, not the first" })' },
    { out: ["stored 77e0b2 · project teach · 1 pattern"] },
    { cmd: 'school_remember({ content: "the context window budget is 128k tokens, hard limit" })' },
    { out: ["stored 1a4ff6 · project teach · 1 pattern"] },
    { cmd: 'school_recall({ query: "retry" })' },
    { out: ["3 memories · 1 pattern · project teach"] },
    { cmd: "school_context_status()" },
    { out: ['{ "ok": true, "mode": "school", "blocks": 0, "restores": 0, "tokens_saved": 0 }'] }
  ];

  const BLOCKS = [
    { id: "b1", name: "retry policy", range: "0-12", msgs: 12, before: 43.1, after: 2.4, c: "orange" },
    { id: "b2", name: "queue semantics", range: "13-31", msgs: 19, before: 34.2, after: 3.1, c: "teal" },
    { id: "b3", name: "sandbox flake", range: "32-54", msgs: 23, before: 30.6, after: 3.9, c: "violet" },
    { id: "b4", name: "window budget", range: "55-78", msgs: 24, before: 20.1, after: 4.6, c: "amber" }
  ];
  const TOTAL_AFTER = 14.0;
  const TOTAL_BEFORE = 128.0;

  /* ------------------------------------------------------------------ *
   * wave geometry
   * ------------------------------------------------------------------ */
  const W = 1200;
  const H = 100;
  let rise = 0.14;
  let phase = 0;
  const taken = new Set();

  function crestPoints(y, ph) {
    const pts = [];
    for (let i = 0; i <= 44; i++) {
      const t = i / 44;
      const x = t * W;
      const yy =
        y -
        Math.sin(t * Math.PI * 2 + ph) * 2.5 -
        Math.sin(t * Math.PI * 5.4 + ph * 1.6) * 1.05 -
        Math.cos(t * Math.PI * 3.3 - ph * 0.9) * 0.65;
      pts.push([x, yy]);
    }
    return pts;
  }
  function pathOf(pts) {
    let d = "";
    for (let i = 0; i < pts.length; i++) {
      d += (i ? " L " : "M ") + pts[i][0].toFixed(1) + " " + pts[i][1].toFixed(1);
    }
    return d;
  }

  function paintWave() {
    const y = (1 - rise) * H;
    const pts = crestPoints(y, phase);
    const line = pathOf(pts);
    if (waveLine) waveLine.setAttribute("d", line);
    if (waveFill) waveFill.setAttribute("d", line + " L 1200 100 L 0 100 Z");
    if (waveGlass) {
      /* the glass region is clipped to the exact crest, so the blur follows
         the wave instead of a straight line */
      const poly = [];
      for (let i = 0; i < pts.length; i++) {
        poly.push(((pts[i][0] / W) * 100).toFixed(2) + "% " + ((pts[i][1] / H) * 100).toFixed(2) + "%");
      }
      poly.push("100% 100%", "0% 100%");
      waveGlass.style.clipPath = "polygon(" + poly.join(",") + ")";
    }

    /* the crest carries the transcript away with it */
    const sr = stage.getBoundingClientRect();
    if (!sr.height) return;
    const crestY = sr.top + (1 - rise) * sr.height;
    const band = Math.max(16, sr.height * 0.055);
    $$(".cx-line", linesEl).forEach((el) => {
      if (taken.has(el)) return;
      const r = el.getBoundingClientRect();
      if (!r.height) return;
      const c = r.top + r.height / 2;
      if (Math.abs(c - crestY) < band) {
        taken.add(el);
        el.classList.add("is-taken");
      }
    });
  }

  const timer = setInterval(() => {
    phase += 0.09;
    paintWave();
  }, 40);

  function animateRise(from, to, ms) {
    const t0 = performance.now();
    return new Promise((resolve) => {
      const step = () => {
        const t = Math.min(1, (performance.now() - t0) / ms);
        const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        rise = from + (to - from) * e;
        paintWave();
        if (t < 1) setTimeout(step, 30);
        else resolve();
      };
      step();
    });
  }

  /* ------------------------------------------------------------------ *
   * helpers
   * ------------------------------------------------------------------ */
  function setReadout(kicker, value, note, hot) {
    if (kickerEl) kickerEl.textContent = kicker;
    if (valueEl) valueEl.textContent = value;
    if (noteEl) noteEl.textContent = note;
    if (readout) readout.classList.toggle("is-hot", !!hot);
  }
  function countTo(el, from, to, ms, fmt) {
    if (!el) return Promise.resolve();
    const t0 = performance.now();
    return new Promise((resolve) => {
      const step = () => {
        const t = Math.min(1, (performance.now() - t0) / ms);
        const e = 1 - Math.pow(1 - t, 3);
        el.textContent = fmt(from + (to - from) * e);
        if (t < 1) setTimeout(step, 32);
        else resolve();
      };
      step();
    });
  }
  function addLine(cls, text, prompt) {
    const li = document.createElement("li");
    li.className = "cx-line " + cls;
    if (prompt) {
      const p = document.createElement("span");
      p.className = "cx-line__p";
      p.textContent = prompt;
      li.appendChild(p);
    }
    const t = document.createElement("span");
    t.className = "cx-line__t";
    t.textContent = text;
    li.appendChild(t);
    linesEl.appendChild(li);
    while (linesEl.children.length > MAX_LINES) linesEl.removeChild(linesEl.firstChild);
    return li;
  }
  async function typeCmd(text) {
    const li = addLine("cx-line--cmd", "", "❯");
    const t = li.querySelector(".cx-line__t");
    const cur = document.createElement("span");
    cur.className = "cx-line__cur";
    li.appendChild(cur);
    for (let i = 0; i < text.length; i++) {
      t.textContent += text[i];
      if (i % 3 === 0) await wait(14);
    }
    await wait(120);
    cur.remove();
    return li;
  }
  async function typeOut(text) {
    const li = addLine("cx-line--out", text);
    const t = li.querySelector(".cx-line__t");
    for (let i = 0; i < text.length; i++) {
      t.textContent = text.slice(0, i + 1);
      if (i % 6 === 0) await wait(8);
    }
    await wait(40);
    return li;
  }
  function addBlock(b, i) {
    const el = document.createElement("article");
    el.className = "cx-block cx-block--" + b.c;
    el.style.setProperty("--d", (i * 0.11).toFixed(2) + "s");
    el.innerHTML =
      '<div class="cxb-top"><span class="cxb-id mono">' + b.id + "</span>" +
      '<span class="cxb-name">' + b.name + "</span>" +
      '<span class="cxb-rng mono">' + b.range + "</span></div>" +
      '<div class="cxb-meta mono"><span>' + b.msgs + " msgs</span><span>" +
      b.before.toFixed(1) + "k → " + b.after.toFixed(1) + "k</span></div>";
    blocksEl.appendChild(el);
    return el;
  }

  let everFilled = false;

  async function reset() {
    if (everFilled) {
      stage.classList.add("is-lifting");
      await wait(1050);
    }
    stage.classList.remove("is-lifting");
    if (waveEl) waveEl.classList.remove("is-on");
    if (winEl) winEl.classList.remove("is-cutting");
    if (stampEl) stampEl.classList.remove("is-on");
    if (fillEl) fillEl.style.width = "0%";
    if (cutEl) cutEl.style.width = "0%";
    linesEl.innerHTML = "";
    blocksEl.innerHTML = "";
    taken.clear();
    await animateRise(rise, 0.14, 700);
    if (tokensEl) tokensEl.innerHTML = "<b>0k</b> / 128k";
    setReadout("compressed context", "0.0K", "waiting for the first block", false);
    await wait(340);
  }

  async function phaseFill() {
    let used = 0;
    for (const entry of SESSION) {
      if (entry.cmd) {
        await typeCmd(entry.cmd);
        used += 900;
      } else {
        for (const line of entry.out) {
          await typeOut(line);
          used += 1100;
        }
      }
      if (fillEl) fillEl.style.width = Math.min(92, (used / 128000) * 100 * 12).toFixed(1) + "%";
      const kn = Math.min(118, Math.round(used / 1000));
      if (tokensEl) tokensEl.innerHTML = "<b>" + kn + "k</b> / 128k";
      setReadout("context window", kn + "K", "of 128K - the transcript is still growing", false);
      if (!everFilled) {
        everFilled = true;
      }
    }
    if (fillEl) fillEl.style.width = "92%";
    if (tokensEl) tokensEl.innerHTML = "<b>118k</b> / 128k";
    setReadout("context window", "118K", "of 128K - the window is full, the next message will not fit", false);
    await wait(320);
  }

  async function phaseCompress() {
    if (winEl) winEl.classList.add("is-cutting");
    if (cutEl) cutEl.style.width = "92%";
    if (stampEl) {
      stampEl.innerHTML =
        "<b>CONTEXT TRUNCATED</b><span>78 messages → 4 blocks · originals kept</span>";
      stampEl.classList.add("is-on");
    }
    await wait(900);
  }

  async function phaseStack() {
    for (let i = 0; i < BLOCKS.length; i++) {
      addBlock(BLOCKS[i], i);
      await wait(340);
    }
    await wait(420);
  }

  async function phaseWave() {
    if (waveEl) waveEl.classList.add("is-on");
    setReadout("total compressed context", TOTAL_AFTER.toFixed(1) + "K", "of 128K — 89% of the window back", true);
    countTo(valueEl, TOTAL_AFTER - 5, TOTAL_AFTER, 1500, (v) => v.toFixed(1) + "K");
    await animateRise(rise, 1, 3200);
    await wait(1500);
  }

  async function phaseCounter() {
    setReadout("without compression", "128K", "the same 78 messages (128.0k) would have filled the window — and been dropped", true);
    countTo(valueEl, TOTAL_AFTER, 128, 1600, (v) => Math.round(v) + "K");
    await wait(1900);
  }

  async function run() {
    if (reduced) {
      for (const entry of SESSION) {
        if (entry.cmd) addLine("cx-line--cmd", entry.cmd, "❯");
        else for (const line of entry.out) addLine("cx-line--out", line);
      }
      BLOCKS.forEach((b, i) => addBlock(b, i));
      setReadout("total compressed context", "14.0K", "of 128K — 89% of the window back", true);
      paintWave();
      return;
    }
    for (;;) {
      await reset();
      await phaseFill();
      await phaseCompress();
      await phaseStack();
      await phaseWave();
      await phaseCounter();
    }
  }

  paintWave();
  run();
  window.addEventListener("beforeunload", () => clearInterval(timer));
})();
