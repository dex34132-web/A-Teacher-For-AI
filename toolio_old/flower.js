/* flower.js — keep the interactive lily alive, and keep it WHOLE.

   The poster's script points #imgFront / #imgReveal at the Higgsfield lily.
   The old guard watched each image separately and replaced it on its own
   with a procedural fallback — front got the dim teal lily, reveal got the
   hot orange one. If only one of the two remote images failed, the morph
   trail punched a hole in the purple lily and revealed a completely
   different flower underneath, so the subject looked like it was deleting
   itself under the cursor.

   Now there is ONE decision for all three images: either the remote lily
   loads everywhere, or the procedural pair loads everywhere. The front and
   the reveal are always a matching pair, so a reveal can never be a
   different picture than the one it is revealing. */
(() => {
  const svgURI = (hot) => {
    const cx = 500, cy = 500, R = 320, petals = 14;
    const stroke = hot ? "#ff3d00" : "rgba(127,208,198,.62)";
    const fill = hot ? "rgba(255,61,0,.18)" : "rgba(127,208,198,.12)";
    let g = "";
    for (let i = 0; i < petals; i++) {
      const a = (i * 2 * Math.PI) / petals - Math.PI / 2;
      const x = cx + Math.cos(a) * R * 0.55;
      const y = cy + Math.sin(a) * R * 0.55;
      const rot = (a * 180) / Math.PI + 90;
      g +=
        '<ellipse cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" rx="' +
        (R * 0.46).toFixed(1) + '" ry="' + (R * 0.15).toFixed(1) +
        '" fill="' + fill + '" stroke="' + stroke + '" stroke-width="3" transform="rotate(' +
        rot.toFixed(1) + " " + x.toFixed(1) + " " + y.toFixed(1) + ')"/>';
    }
    const core = hot ? "#ffb27a" : "#7fd0c6";
    const svg =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">' +
      '<defs><radialGradient id="g" cx="50%" cy="50%" r="50%">' +
      '<stop offset="0" stop-color="' + (hot ? "rgba(255,61,0,.34)" : "rgba(127,208,198,.20)") + '"/>' +
      '<stop offset="1" stop-color="rgba(0,0,0,0)"/></radialGradient></defs>' +
      '<circle cx="500" cy="500" r="430" fill="url(#g)"/>' +
      '<circle cx="500" cy="500" r="430" fill="none" stroke="' +
      (hot ? "rgba(255,61,0,.26)" : "rgba(127,208,198,.14)") +
      '" stroke-width="2" stroke-dasharray="10 14"/>' + g +
      '<circle cx="500" cy="500" r="' + (hot ? 26 : 20) + '" fill="' + core + '"/>' +
      "</svg>";
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  };

  const FRONT = svgURI(false);
  const REVEAL = svgURI(true);
  const IDS = ["imgFront", "imgReveal", "flowerSizer"];

  let swapped = false;
  const swapAll = () => {
    if (swapped) return;
    swapped = true;
    document.documentElement.setAttribute("data-flower", "procedural");
    const set = (id, uri) => {
      const el = document.getElementById(id);
      if (el && el.getAttribute("src") !== uri) el.src = uri;
    };
    set("imgFront", FRONT);
    set("imgReveal", REVEAL);
    set("flowerSizer", FRONT);
  };

  const broken = (id) => {
    const el = document.getElementById(id);
    if (!el) return false;
    // an <img> with no src at all is not broken - it is just empty
    if (!el.getAttribute("src")) return false;
    return el.complete && el.naturalWidth === 0;
  };

    /* One shared error handler for every layer: if the remote lily fails on
     any of them, all three fall back to the procedural bloom together. */
  IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("error", swapAll, { once: true });
  });

/* One shared timeout, one shared verdict. The remote lily is ~300KB, so
     give it longer than two seconds before declaring it dead. */
  setTimeout(() => {
    if (IDS.some(broken)) swapAll();
  }, 6000);
})();
