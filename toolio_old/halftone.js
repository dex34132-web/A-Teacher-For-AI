/* halftone.js — vanilla port of components/ui/halftone-wordmark-footer.tsx.
   No framework, no build step: the same halftone wordmark footer that ships
   as a React component, running on the live static site.

   A 2D canvas prints the wordmark enormous and cropped by the bottom edge as a
   field of halftone dots. Each dot is sized by how much of the letter covers
   its cell, so the type keeps its edges at any scale. Move across it and the
   dots part around the pointer on springs, warming in colour as they are
   pushed off their place; click and a shock ring runs through the word. A
   fixed tile of print grain is laid over every frame. */

(function () {
  "use strict"

  var root = document.getElementById("hwf")
  var canvas = document.getElementById("hwf-canvas")
  if (!root || !canvas) return
  var ctx = canvas.getContext("2d")
  if (!ctx) return

  var CFG = {
    background: "#0b0b0d",
    ink: "#efeae0",
    warm: "#ff3d00",
    wordmark: "school",
    dotGap: 6,
    radius: 80,
    crop: 0.24,
    grain: 0.5,
    fontWeight: 400,
    fontFamily: '"Pusab","Silkscreen","Courier New",monospace',
    monoFamily: '"IBM Plex Mono","SF Mono",ui-monospace,Menlo,Consolas,monospace',
  }

  /* --- helpers: the same pure maths the component exports ---------------- */
  function hwfHex(hex) {
    var m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec((hex || "").trim())
    if (!m) return null
    var h = m[1].length === 3 ? m[1].split("").map(function (c) { return c + c }).join("") : m[1]
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
  }
  function hwfRadius(coverage, gap) {
    var c = coverage < 0 ? 0 : coverage > 1 ? 1 : coverage
    return Math.sqrt(c) * gap * 0.56
  }
  function hwfStep(x, y, vx, vy, hx, hy, px, py, r) {
    var dx = x - px
    var dy = y - py
    var d2 = dx * dx + dy * dy
    if (r > 0 && d2 < r * r) {
      var d = Math.sqrt(d2) + 0.001
      var f = (1 - d / r) * 2.6
      vx += (dx / d) * f
      vy += (dy / d) * f
    }
    vx = (vx + (hx - x) * 0.05) * 0.84
    vy = (vy + (hy - y) * 0.05) * 0.84
    return [x + vx, y + vy, vx, vy]
  }
  function hwfWarmth(x, y, hx, hy, span) {
    var d = Math.hypot(x - hx, y - hy)
    return span > 0 ? Math.min(1, d / span) : 0
  }
  function hwfFitSize(measured, width) {
    return measured > 0 ? (width / measured) * 100 : 0
  }

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  var w = 0
  var h = 0
  var dpr = 1
  var px = -1e5
  var py = -1e5
  var raf = 0
  var visible = true
  var awake = true
  var ring = { x: 0, y: 0, t: -1 }
  var dots = new Float32Array(0)
  var count = 0
  var grainTile = null
  var ink = hwfHex(CFG.ink) || [239, 234, 224]
  var warm = hwfHex(CFG.warm) || [255, 61, 0]

  function layout() {
    var rect = root.getBoundingClientRect()
    w = Math.max(1, Math.round(rect.width))
    h = Math.max(1, Math.round(rect.height))
    dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)

    /* Set the word once, at a size that fills the width, on a 1x mask. */
    var mask = document.createElement("canvas")
    mask.width = w
    mask.height = h
    var m = mask.getContext("2d", { willReadFrequently: true })
    if (!m) return
    var word = CFG.wordmark || " "
    m.font = CFG.fontWeight + " 100px " + CFG.fontFamily
    var fit = hwfFitSize(m.measureText(word).width, w * 1.02)
    m.font = CFG.fontWeight + " " + fit + "px " + CFG.fontFamily
    var box = m.measureText(word)
    var cap = box.actualBoundingBoxAscent || fit * 0.72
    var crop = Math.max(0, Math.min(0.6, CFG.crop))
    m.fillStyle = "#000"
    m.textBaseline = "alphabetic"
    m.fillText(word, (w - box.width) / 2, h + cap * crop)
    var img = m.getImageData(0, 0, w, h).data

    var gap = Math.max(3, CFG.dotGap)
    var cols = Math.ceil(w / gap)
    var rows = Math.ceil(h / gap)
    var tmp = []
    for (var gy = 0; gy < rows; gy++) {
      for (var gx = 0; gx < cols; gx++) {
        /* Coverage: average alpha over a 3x3 sample of the cell. */
        var sum = 0
        for (var sy = 0; sy < 3; sy++) {
          for (var sx = 0; sx < 3; sx++) {
            var x = Math.min(w - 1, Math.floor(gx * gap + ((sx + 0.5) * gap) / 3))
            var y = Math.min(h - 1, Math.floor(gy * gap + ((sy + 0.5) * gap) / 3))
            sum += img[(y * w + x) * 4 + 3]
          }
        }
        var cov = sum / (9 * 255)
        if (cov < 0.06) continue
        var hx = gx * gap + gap / 2
        var hy = gy * gap + gap / 2
        tmp.push(hx, hy, 0, 0, hx, hy, hwfRadius(cov, gap))
      }
    }
    dots = new Float32Array(tmp)
    count = tmp.length / 7

    /* A fixed tile of print grain, drawn once and laid over every frame. */
    grainTile = document.createElement("canvas")
    grainTile.width = 256
    grainTile.height = 256
    var g = grainTile.getContext("2d")
    if (g) {
      var id = g.createImageData(256, 256)
      for (var i = 0; i < id.data.length; i += 4) {
        var v = Math.random() * 255
        id.data[i] = id.data[i + 1] = id.data[i + 2] = v
        id.data[i + 3] = Math.random() < 0.5 ? 0 : 255
      }
      g.putImageData(id, 0, 0)
    }
    awake = true
  }

  function draw(now) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.fillStyle = CFG.background
    ctx.fillRect(0, 0, w, h)

    var r = reduced ? 0 : Math.max(0, CFG.radius)
    var ringAge = ring.t < 0 ? 1e9 : now - ring.t
    var ringR = ringAge * 0.9
    var moving = false
    for (var i = 0; i < count; i++) {
      var j = i * 7
      var x = dots[j]
      var y = dots[j + 1]
      var vx = dots[j + 2]
      var vy = dots[j + 3]
      var hx = dots[j + 4]
      var hy = dots[j + 5]
      if (!reduced) {
        if (ringAge < 900) {
          var dx = hx - ring.x
          var dy = hy - ring.y
          var d = Math.sqrt(dx * dx + dy * dy) + 0.001
          var band = 1 - Math.min(1, Math.abs(d - ringR) / 26)
          if (band > 0) {
            var f = band * 3.2 * (1 - ringAge / 900)
            vx += (dx / d) * f
            vy += (dy / d) * f
          }
        }
        var s = hwfStep(x, y, vx, vy, hx, hy, px, py, r)
        x = s[0]
        y = s[1]
        vx = s[2]
        vy = s[3]
        if (Math.abs(vx) + Math.abs(vy) > 0.02 || Math.abs(x - hx) + Math.abs(y - hy) > 0.05) moving = true
        else {
          x = hx
          y = hy
          vx = 0
          vy = 0
        }
        dots[j] = x
        dots[j + 1] = y
        dots[j + 2] = vx
        dots[j + 3] = vy
      }
      var k = hwfWarmth(x, y, hx, hy, 28)
      ctx.fillStyle =
        k > 0.02
          ? "rgb(" +
            Math.round(ink[0] + (warm[0] - ink[0]) * k) + "," +
            Math.round(ink[1] + (warm[1] - ink[1]) * k) + "," +
            Math.round(ink[2] + (warm[2] - ink[2]) * k) + ")"
          : CFG.ink
      ctx.beginPath()
      ctx.arc(x, y, dots[j + 6], 0, 6.2832)
      ctx.fill()
    }

    if (grainTile && CFG.grain > 0) {
      ctx.globalAlpha = Math.min(1, CFG.grain) * 0.09
      ctx.globalCompositeOperation = "overlay"
      var pattern = ctx.createPattern(grainTile, "repeat")
      if (pattern) {
        ctx.fillStyle = pattern
        ctx.fillRect(0, 0, w, h)
      }
      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = "source-over"
    }
    /* Sleep once everything is home and nothing is pushing. */
    awake = moving || ringAge < 900 || px > -1e4
  }

  function loop(now) {
    raf = 0
    if (!visible) return
    draw(now)
    if (awake) raf = requestAnimationFrame(loop)
  }
  function wake() {
    awake = true
    if (!raf && visible) raf = requestAnimationFrame(loop)
  }

  function toLocal(e) {
    var b = canvas.getBoundingClientRect()
    return [e.clientX - b.left, e.clientY - b.top]
  }
  function onMove(e) {
    var p = toLocal(e)
    px = p[0]
    py = p[1]
    wake()
  }
  function onLeave() {
    px = -1e5
    py = -1e5
    wake()
  }
  function onDown(e) {
    if (reduced) return
    if (e.target && e.target.closest && e.target.closest("a,button")) return
    var p = toLocal(e)
    ring = { x: p[0], y: p[1], t: performance.now() }
    wake()
  }

  /* Every re-layout must paint synchronously. Resizing a canvas clears it, and
     a rAF repaint is not guaranteed (throttled tab, headless renderer, a web
     font that lands late). A cleared canvas with no repaint would show no
     wordmark at all — the footer would just be an empty band. */
  function relayout() {
    layout()
    try {
      draw(performance.now())
    } catch (err) {
      window.__hwfErr = String((err && err.stack) || err)
    }
    wake()
  }
  relayout()

  root.addEventListener("pointermove", onMove)
  root.addEventListener("pointerleave", onLeave)
  root.addEventListener("pointerdown", onDown)
  var ro = new ResizeObserver(function () {
    relayout()
  })
  ro.observe(root)
  var io = new IntersectionObserver(function (entries) {
    visible = entries[0] ? entries[0].isIntersecting : true
    if (visible) wake()
  })
  io.observe(root)
  /* A web font that lands late re-sets the word in its real face. */
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      relayout()
    })
  }

  /* Back to top. */
  var up = document.querySelector("[data-hwf-top]")
  if (up) {
    up.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" })
    })
  }
})()
