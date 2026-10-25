/* School — the pointer.
 * Owns the liquid glass lens (a perfect circle that follows the pointer and
 * inverts everything inside its radius) and the flower's lean + glow.
 */
(() => {
  "use strict";
  const flower = document.getElementById("flower");
  const lens = document.getElementById("glassLens");
  const stage = document.getElementById("stage") || document;
  if (!lens) return;

  let tx = 0;
  let ty = 0;
  let bx = 0;
  let by = 0;
  let glow = 0;
  let over = false;
  let last = performance.now();

  /* the lens is always there: it starts at the centre of the screen and
     never disappears, not even before the mouse has moved */
  const place = (x, y) => {
    lens.style.setProperty("--lx", x + "px");
    lens.style.setProperty("--ly", y + "px");
  };
  place(-600, -600);

  const setPointer = (e) => {
    const x = e.clientX;
    const y = e.clientY;
    place(x, y);
    lens.classList.add("is-on");

    if (!flower) return;
    const r = flower.getBoundingClientRect();
    const inside =
      x > r.left - 46 && x < r.right + 46 && y > r.top - 46 && y < r.bottom + 46;
    over = inside;
    flower.classList.toggle("is-lit", inside);
    if (inside) {
      const sr = stage.getBoundingClientRect();
      tx = sr.width ? (x - sr.left) / sr.width * 2 - 1 : 0;
      ty = sr.height ? (y - sr.top) / sr.height * 2 - 1 : 0;
    }
  };

  const leave = () => {
    over = false;
    tx = 0;
    ty = 0;
    if (flower) flower.classList.remove("is-lit");
  };

  const apply = (now) => {
    const k = Math.min(1, (now - last) / 16.67);
    last = now;
    bx += (tx - bx) * 0.11 * k;
    by += (ty - by) * 0.09 * k;
    const want = over ? 1 : 0;
    glow += (want - glow) * 0.08 * k;
    if (flower) {
      flower.style.setProperty("--bx", bx.toFixed(3));
      flower.style.setProperty("--by", by.toFixed(3));
      flower.style.setProperty("--glow", glow.toFixed(3));
    }
  };

  const loop = (now) => {
    apply(now);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  /* rAF is dead in a throttled or hidden tab — poll as well */
  setInterval(() => {
    if (performance.now() - last > 220) apply(performance.now());
  }, 70);

  stage.addEventListener("mousemove", setPointer, { passive: true });
  stage.addEventListener("touchmove", (e) => {
    const t = e.touches && e.touches[0];
    if (t) setPointer(t);
  }, { passive: true });
  stage.addEventListener("mouseleave", leave);
  window.addEventListener("blur", leave);

})();
