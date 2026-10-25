/* ==========================================================================
   PERSPECTIVE TUNNEL — engine
   Port of the 21st.dev `perspective-tunnel-hero` React component:
   wheel-driven progress through a 3D corridor, pointer parallax, a spring on
   every value, and a golden-angle card layout. The photos are replaced by
   terminal panels running real School / OpenCode / Hermes commands.
   ========================================================================== */
(() => {
  "use strict";

  const CARDS = [
    { tag: "opencode", img: "assets/card-1.png", seed: "school-opencode", out: "the open source AI coding agent" },
    { tag: "hermes", img: "assets/card-2.png", seed: "school-hermes", out: "hermes agent" },
    { tag: "openclaw", img: "assets/card-3.png", seed: "school-openclaw", out: "openclaw" },
    { tag: "editor", img: "assets/card-4.png", seed: "school-editor", out: "syntax, all night" },
    { tag: "ide", img: "assets/card-5.png", seed: "school-ide", out: "components/header/header.jsx" },
    { tag: "auth", img: "assets/card-6.png", seed: "school-auth", out: "authenticateUser" },
    { tag: "terminal", img: "assets/card-7.png", seed: "school-terminal", out: "school install" },
    { tag: "ops", img: "assets/card-8.png", seed: "school-ops", out: "one engine, every agent" },
    { tag: "crew", img: "assets/card-9.png", seed: "school-crew", out: "agents that learn" },
  ];

  const $ = (s, r) => (r || document).querySelector(s);
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const hero = $("#hero");
  const tunnel = $("#tunnel");
  const layer = $("#tunnelCards");
  const copy = $(".hero__copy");
  if (!hero || !tunnel || !layer) return;

  /* ---- build the panels ------------------------------------------------ */
  const cards = CARDS.map((c, i) => {
    const el = document.createElement("div");
    el.className = "tunnel-card";
    el.innerHTML =
      '<div class="tunnel-card__fig">' +
      '<img class="tunnel-card__img" alt="' + c.tag + '" src="' + c.img + '" decoding="async">' +
      "</div>" +
      '<div class="tunnel-card__cap"><i></i><b>' + c.tag + "</b><span>" + c.out + "</span></div>";
    layer.appendChild(el);
    const img = $(".tunnel-card__img", el);
    if (img) {
      img.addEventListener("error", function () {
        if (img.dataset.fell) return;
        img.dataset.fell = "1";
        img.src = "https://picsum.photos/seed/" + c.seed + "/900/1125";
        img.addEventListener("error", function once() {
          img.removeEventListener("error", once);
          img.src = "data:image/svg+xml;utf8," + encodeURIComponent(
            "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='1125'>" +
            "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>" +
            "<stop offset='0' stop-color='#1b1b20'/><stop offset='1' stop-color='#0b0b0d'/>" +
            "</linearGradient></defs><rect width='900' height='1125' fill='url(#g)'/>" +
            "<text x='450' y='580' fill='#ff3d00' font-family='monospace' font-size='54'" +
            " text-anchor='middle'>" + c.tag.toUpperCase() + "</text></svg>"
          );
        }, { once: true });
      });
    }
    /* golden-angle placement — same spiral as the source component */
    const golden = i * 137.5 * (Math.PI / 180);
    return {
      el,
      cos: Math.cos(golden),
      sin: Math.sin(golden),
      rx: 0.26 + (i % 3) * 0.085,
      ry: 0.24 + (i % 2) * 0.095,
      rot: (i % 2 === 0 ? 1 : -1) * (3 + (i % 5) * 2),
      start: (i / CARDS.length) * 0.45,
      end: (i / CARDS.length) * 0.45 + 0.55,
    };
  });

  /* ---- state ----------------------------------------------------------- */
  let target = 0.16;      /* a couple of panels already waiting in the dark */
  let p = target;
  let tx = 0, ty = 0;    /* pointer target, -1..1 */
  let px = 0, py = 0;    /* pointer, smoothed */
  let w = window.innerWidth;
  let h = window.innerHeight;
  const mobile = () => w < 768;

  const onResize = () => {
    w = window.innerWidth;
    h = window.innerHeight;
  };
  window.addEventListener("resize", onResize);
  onResize();

  /* ---- the intro screen ----------------------------------------------
     The tunnel IS the entry. The page is locked while the flight runs; the
     first scroll flies the camera past the cards and hands the gesture on
     to the page, so you land inside the site instead of on it. */
  const rootEl = document.documentElement;
  let intro = true;
  let pending = 0;
  let introT0 = 0;   /* when the flight started, ms */
  let introFrom = 0; /* tunnel depth when it started */
  let copyOwned = true; /* the tunnel drives the hero copy until the flight ends */
  rootEl.classList.add("intro-lock");
  rootEl.classList.add("intro-quiet");
  /* ?skipintro=1 - deep link straight to the site, no intro gate */
  if (/skipintro/i.test(location.search)) {
    rootEl.classList.remove("intro-lock");
    rootEl.classList.remove("intro-quiet");
    intro = false;
    copyOwned = false;
    p = 1;
    target = 1;
  }
  if (scrollY > 0) window.scrollTo(0, 0);

  const unlock = (dy) => {
    if (!intro) return;
    intro = false;
    rootEl.classList.remove("intro-lock");
    rootEl.classList.remove("intro-quiet");
    rootEl.classList.remove("intro-flying");
    /* land on the hero: the copy, the see-pipeline button and the GitHub
       button are what the user scrolls INTO, so do not sail past them */
    /* hand the copy back to the page: drop the inline opacity and let the
       stylesheet transition fade it in */
    copyOwned = false;
    copy.style.setProperty("transform", "none", "important");
    copy.style.setProperty("filter", "none", "important");
    /* fade the copy in on a timer - CSS transitions do not advance in a
       throttled tab, and the copy is the one thing that must never be
       left invisible */
    const t0 = performance.now();
    const fade = function () {
      const el = clamp((performance.now() - t0) / 1300, 0, 1);
      copy.style.setProperty("opacity", (1 - Math.pow(1 - el, 3)).toFixed(3), "important");
      if (el < 1) setTimeout(fade, 32);
    };
    copy.style.setProperty("opacity", "0", "important");
    fade();
    /* safety net: after the entrance has had its window, nothing may stay
       hidden - including the per-character title reveal */
    setTimeout(function () {
      rootEl.classList.add("intro-done");
      /* drop every inline override on the copy: an inline "opacity: 0 !important"
         would beat the stylesheet forever, and a plain inline write CLEARS the
         important flag, which is how the intro's own opacity:0 rule kept
         winning. The stylesheet owns the copy once the flight is over. */
      copy.style.removeProperty("opacity");
      copy.style.removeProperty("transform");
      copy.style.removeProperty("filter");
      var hint = document.querySelector(".hero__scroll");
      if (hint) hint.style.opacity = "0";
    }, 1900);
    window.scrollTo(0, 0);
  };
  const enter = (dy) => {
    if (!intro) return;
    pending += dy || 0;
    /* stamp the clock once - a continuing scroll must not restart the flight */
    if (!introT0) {
      introT0 = performance.now();
      introFrom = p;
      /* the gate opens on a real timer - a throttled tab or a busy main
         thread must never be able to keep the site locked */
      setTimeout(function () {
        if (!intro) return;
        p = 1;
        unlock(pending);
      }, 2700);
    }
    target = 1;
    rootEl.classList.add("intro-flying");
  };

  if (!reduced) {
    window.addEventListener(
      "pointermove",
      (e) => {
        tx = (e.clientX / w - 0.5) * 2;
        ty = (e.clientY / h - 0.5) * 2;
      },
      { passive: true },
    );
  }

  /* ---- wheel drives the flight, the page takes over when it is done ---- */
  hero.addEventListener(
    "wheel",
    (e) => {
      if (reduced) return;
      const d = e.deltaY;
      if (intro) {
        e.preventDefault();
        /* enter() arms the flight clock and the unlock timer */
        enter(d);
        return;
      }
      /* release the wheel at either end so the page never feels trapped */
      if (d > 0 && target >= 0.999) return;
      if (d < 0 && target <= 0.001) return;
      e.preventDefault();
      target = clamp(target + d * 0.00085, 0, 1);
    },
    { passive: false },
  );

  /* keys and the scroll hint also enter the site */
  addEventListener("keydown", (e) => {
    if (!intro) return;
    if (e.key === " " || e.key === "PageDown" || e.key === "ArrowDown") {
      e.preventDefault();
      enter(innerHeight * 0.85);
    }
  });
  const scrollHint = $(".hero__scroll");
  if (scrollHint) scrollHint.addEventListener("click", () => enter(innerHeight * 0.85));
  hero.addEventListener(
    "touchmove",
    (e) => {
      if (!intro) return;
      e.preventDefault();
      enter(innerHeight * 0.6);
    },
    { passive: false },
  );

  /* if the hero leaves the viewport, finish the flight */
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) {
            target = 1;
            if (intro) unlock(pending || innerHeight * 0.85);
          }
        });
      },
      { threshold: 0.08 },
    ).observe(hero);
  }

  /* ---- frame loop ------------------------------------------------------ */
  let last = performance.now();
  const frame = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (intro) {
      /* the intro is timed, not frame-counted: it always takes the
         same 2.6s however fast the machine renders */
      const el = clamp((now - introT0) / 2600, 0, 1);
      p = lerp(introFrom, 1, 1 - Math.pow(1 - el, 3));
    } else {
      const k = 1 - Math.exp(-dt * 5.5);
      p += (target - p) * k;
    }
    if (intro && p >= 0.995) unlock(pending || innerHeight * 0.85);
    if (!intro && scrollY < innerHeight * 0.5) rootEl.classList.remove("intro-flying");
    px += (tx - px) * (1 - Math.exp(-dt * 4.5));
    py += (ty - py) * (1 - Math.exp(-dt * 4.5));

    const far = mobile() ? -1200 : -1700;
    const near = mobile() ? 350 : 500;
    const pan = mobile() ? 20 : 45;

    for (const c of cards) {
      const local = clamp((p - c.start) / (c.end - c.start), 0, 1);
      const z = lerp(far, near, local);
      /* distant panels stay faintly lit so the corridor never reads empty */
      let o;
      if (local <= 0.22) o = lerp(0.16, 1, local / 0.22);
      else if (local <= 0.8) o = 1;
      else o = lerp(1, 0, (local - 0.8) / 0.2);
      const ox = c.cos * (w * c.rx) - px * pan;
      const oy = c.sin * (h * c.ry) - py * pan;
      c.el.style.opacity = o.toFixed(3);
      c.el.style.zIndex = String(10 + Math.round(local * 20));
      c.el.style.transform =
        "translate3d(calc(-50% + " + ox.toFixed(1) + "px), calc(-50% + " + oy.toFixed(1) + "px), " + z.toFixed(1) + "px) rotateZ(" + c.rot + "deg)";
    }

    if (copy) {
      const s = p <= 0.5 ? lerp(0.72, 1, p / 0.5) : lerp(1, 1.28, (p - 0.5) / 0.5);
      let o;
      if (p <= 0.12) o = lerp(0.3, 1, p / 0.12);
      else if (p <= 0.85) o = 1;
      else o = lerp(1, 0, (p - 0.85) / 0.15);
      if (copyOwned) {
        copy.style.transform = "scale(" + s.toFixed(3) + ")";
        copy.style.opacity = o.toFixed(3);
      }
    }

    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  /* ---- intro safety net ------------------------------------------------ */
  /* The intro is a gate, not a cage. If the lock ever disappears without the
     flight (a script, a bookmark, a browser quirk) the copy has to come back,
     and if nobody ever touches the page the gate opens by itself. */
  try {
    const rootEl = document.documentElement
    const sync = () => {
      if (!rootEl.classList.contains("intro-lock") && rootEl.classList.contains("intro-quiet")) {
        rootEl.classList.remove("intro-quiet")
      }
    }
    if (typeof MutationObserver === "function") {
      new MutationObserver(sync).observe(rootEl, { attributes: true, attributeFilter: ["class"] })
    }
    setTimeout(() => {
      if (!rootEl.classList.contains("intro-lock")) return
      rootEl.classList.remove("intro-lock")
      rootEl.classList.remove("intro-quiet")
      window.scrollTo(0, Math.round(window.innerHeight * 0.85))
    }, 15000)
  } catch (err) {
    /* the gate is a nicety, never a blocker */
  }

})();
