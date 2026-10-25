/* School — the liquid glass lens.
 * A perfect circle of refracting glass that follows the pointer. Everything
 * inside its radius is inverted to its opposite; nothing outside it changes.
 * The 21st.dev liquid-glass lineage: a turbulence + displacement filter over
 * a blurred, saturated backdrop.
 */
(() => {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";

  function defs(id, scale, freq, seed) {
    if (document.getElementById(id)) return;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("id", "glass-defs");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    svg.setAttribute("aria-hidden", "true");
    svg.style.cssText = "position:absolute;width:0;height:0;pointer-events:none";
    const f = document.createElementNS(NS, "filter");
    f.setAttribute("id", id);
    f.setAttribute("x", "-35%");
    f.setAttribute("y", "-35%");
    f.setAttribute("width", "170%");
    f.setAttribute("height", "170%");
    f.setAttribute("color-interpolation-filters", "sRGB");
    f.innerHTML =
      '<feTurbulence type="fractalNoise" baseFrequency="' + freq + '" numOctaves="2" seed="' + seed + '" result="n"/>' +
      '<feGaussianBlur in="n" stdDeviation="2" result="s"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="s" scale="' + scale + '" xChannelSelector="R" yChannelSelector="G"/>';
    svg.appendChild(f);
    document.body.appendChild(svg);
  }

  /* the classic 21st.dev liquid-glass filter (kept for anything that wants
     the heavy refraction) + a gentler one for the lens itself */
  defs("glass-distortion", 64, "0.008 0.008", 92);
  defs("cxLens", 22, "0.012 0.012", 41);

  let lens = document.getElementById("glassLens");
  if (!lens) {
    lens = document.createElement("div");
    lens.id = "glassLens";
    lens.className = "glass-lens";
    lens.setAttribute("aria-hidden", "true");
    document.body.appendChild(lens);
  }
  window.__glassLens = lens;
})();
