"use client";

import * as React from "react";

/* ------------------------------------------------------------------ */
/*  HoloCard — a pearl titanium card with a thin-film hologram.        */
/*  Tilts with the cursor (or the phone), spins when dragged,          */
/*  flips on tap, and scrambles the number in on reveal.               */
/*                                                                     */
/*  Ported for the School site: the utility classes were rewritten as   */
/*  plain CSS (the site ships no Tailwind), and the card gained three  */
/*  behaviours: it spins on its own until you touch it, the number      */
/*  reveals on a loop, and the holder reads "Dksh School".             */
/* ------------------------------------------------------------------ */

export type HoloCardHandle = {
  flip: () => void;
  reveal: (show?: boolean) => void;
  /** iOS asks for permission before motion can be read; call this from a tap */
  enableMotion: () => Promise<boolean>;
};

export type HoloCardProps = {
  holder?: string;
  /** full 16-digit number, spaces optional; only the last 4 show until revealed */
  number?: string;
  expires?: string;
  cvv?: string;
  /** small label top right */
  tier?: string;
  /** your logo, top left; a placeholder shows by default */
  logo?: React.ReactNode;
  /** network mark bottom right; two neutral circles by default */
  network?: React.ReactNode;
  /** max tilt in degrees. Default 14. */
  maxTilt?: number;
  /** 0–1.5, strength of the hologram. Default 1. */
  foil?: number;
  /** follow the phone's tilt where allowed. Default true. */
  motion?: boolean;
  /** spin by itself until the user touches it. Default true. */
  autoSpin?: boolean;
  /** how often the number reveals itself, in ms. 0 = never. Default 3000. */
  revealEvery?: number;
  onFlip?: (side: "front" | "back") => void;
  onReveal?: (shown: boolean) => void;
  className?: string;
};

const INK = "#1d1d1f";
const FONT = "Geist, -apple-system, BlinkMacSystemFont, Inter, 'Segoe UI', Roboto, sans-serif";
const MONO = "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace";

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9 .02' numOctaves='2' seed='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")";

const CSS = `
.hc-face{position:absolute;inset:0;border-radius:18px;overflow:hidden;backface-visibility:hidden;-webkit-backface-visibility:hidden;color:${INK};
  background:linear-gradient(135deg,#fdfdfe 0%,#ececf1 38%,#f8f8fa 62%,#e2e2e8 100%);
  box-shadow:inset 0 0 0 .5px rgba(0,0,0,.08),inset 0 1px 0 rgba(255,255,255,.9)}
.hc-layer{position:absolute;pointer-events:none}
.hc-grain{inset:0;opacity:.35;mix-blend-mode:soft-light;background-image:${GRAIN};background-size:200px 200px}
.hc-film{inset:-30%;mix-blend-mode:multiply;opacity:calc(var(--ho,.6) * var(--foil,1));
  background:linear-gradient(115deg,#ffd9ec 0%,#ffe6cf 12%,#fff6c9 22%,#d4f7e4 34%,#c9ecff 46%,#d9d4ff 58%,#f6d0ff 70%,#ffd9ec 82%,#ffe6cf 100%);
  background-size:300% 300%;background-position:var(--hx,50%) var(--hy,50%);
  -webkit-mask-image:radial-gradient(85% 110% at var(--mx,50%) var(--my,50%),#000 0%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.15) 85%);
  mask-image:radial-gradient(85% 110% at var(--mx,50%) var(--my,50%),#000 0%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.15) 85%)}
.hc-film2{inset:-30%;mix-blend-mode:color;opacity:calc(var(--ho,.6) * .55 * var(--foil,1));
  background:conic-gradient(from var(--ca,0deg) at var(--mx,50%) var(--my,50%),#ff9ad5,#ffc58f,#fff08f,#9ff0c6,#8fd6ff,#b8a6ff,#ff9ad5);
  -webkit-mask-image:radial-gradient(60% 80% at var(--mx,50%) var(--my,50%),#000,transparent 75%);
  mask-image:radial-gradient(60% 80% at var(--mx,50%) var(--my,50%),#000,transparent 75%)}
.hc-lines{inset:0;mix-blend-mode:soft-light;opacity:calc(var(--ho,.6) * .5 * var(--foil,1));
  background:repeating-linear-gradient(115deg,rgba(255,255,255,.9) 0 1px,transparent 1px 3px)}
.hc-streak{inset:-40%;mix-blend-mode:soft-light;opacity:.9;transform:translateX(var(--st,0%));
  background:linear-gradient(115deg,transparent 42%,rgba(255,255,255,.95) 49%,rgba(255,255,255,.95) 51%,transparent 58%)}
.hc-glare{inset:0;mix-blend-mode:screen;background:radial-gradient(45% 65% at var(--mx,50%) var(--my,50%),rgba(255,255,255,.55),rgba(255,255,255,0) 65%)}
.hc-edge{inset:0;border-radius:18px;padding:1px;
  background:linear-gradient(var(--ea,135deg),#fff,rgba(0,0,0,.06) 30%,rgba(0,0,0,.04) 70%,rgba(255,255,255,.8));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
.hc-chip{width:44px;height:34px;border-radius:7px;position:relative;overflow:hidden;
  background:linear-gradient(135deg,#e9d6a2,#b89850 45%,#f4e3b0 60%,#9c7c3a);box-shadow:inset 0 0 0 .5px rgba(0,0,0,.35)}
.hc-chip:before,.hc-chip:after{content:"";position:absolute;border:1px solid rgba(80,60,20,.45)}
.hc-chip:before{left:30%;right:30%;top:-1px;bottom:-1px;border-top:0;border-bottom:0}
.hc-chip:after{top:35%;bottom:35%;left:-1px;right:-1px;border-left:0;border-right:0}
.hc-label{display:block;font-size:10px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:rgba(29,29,31,.45);margin-bottom:4px}
/* --- layout (the Tailwind utilities of the original, in plain CSS) --- */
.hc-root{position:relative;width:100%;max-width:380px}
.hc-stage{position:relative;width:100%;user-select:none;-webkit-user-select:none}
.hc-shadow{position:absolute;bottom:-16px;left:10%;right:10%;height:36px;border-radius:50%;filter:blur(22px);pointer-events:none}
.hc-card{position:absolute;inset:0;cursor:grab}
.hc-card:active{cursor:grabbing}
.hc-inner{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;padding:22px 24px 20px}
.hc-row{display:flex;align-items:center;justify-content:space-between}
.hc-logo{display:flex;align-items:center;gap:8px;font-size:17px;font-weight:600;letter-spacing:-.04em}
.hc-logoMark{display:grid;place-items:center;width:22px;height:22px;border-radius:7px}
.hc-logoGlyph{width:8px;height:8px;transform:rotate(45deg);border-radius:2px;background:#fff}
.hc-tier{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.12em}
.hc-number{display:flex;width:-webkit-fit-content;width:fit-content;gap:14px;border-radius:6px;border:0;background:none;padding:0;
  text-align:left;font-size:20px;font-weight:500;line-height:1;letter-spacing:.06em;font-variant-numeric:tabular-nums;
  outline:none;color:inherit;cursor:pointer}
.hc-number:focus-visible{box-shadow:0 0 0 2px #007AFF,0 0 0 6px rgba(0,0,0,.08)}
.hc-group{display:inline-block;min-width:3.4ch}
.hc-foot{display:flex;align-items:flex-end;justify-content:space-between}
.hc-holder{min-width:0}
.hc-holderName{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:15px;font-weight:600;text-transform:uppercase;letter-spacing:-.01em}
.hc-exp{font-size:15px;font-weight:600;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.hc-net{display:flex}
.hc-net>span{display:block;width:30px;height:30px;border-radius:50%}
.hc-net>span+span{margin-left:-12px}
.hc-strip{position:absolute;left:0;right:0;top:24px;height:42px}
.hc-cvv{position:absolute;left:24px;right:24px;top:86px;display:flex;height:38px;align-items:center;justify-content:flex-end;gap:10px;
  border-radius:8px;padding:0 12px;border:0;outline:none;cursor:pointer}
.hc-cvv:focus-visible{box-shadow:0 0 0 2px #007AFF,0 0 0 6px rgba(0,0,0,.08)}
.hc-cvvLbl{font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:.12em}
.hc-cvvVal{font-size:15px;font-weight:500;letter-spacing:.12em}
.hc-note{position:absolute;bottom:18px;left:24px;right:24px;font-size:10px;line-height:14px}
`;

const Layers = () => (
  <>
    <div className="hc-layer hc-grain" />
    <div className="hc-layer hc-film" />
    <div className="hc-layer hc-film2" />
    <div className="hc-layer hc-lines" />
    <div className="hc-layer hc-streak" />
    <div className="hc-layer hc-glare" />
  </>
);

/* scramble random digits into the target, left to right */
function useScramble() {
  return React.useCallback((el: HTMLElement | null, to: string, ms = 520) => {
    if (!el) return;
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      let out = "";
      for (let i = 0; i < to.length; i++) out += k > (i + 1) / to.length ? to[i] : String((Math.random() * 10) | 0);
      el.textContent = k < 1 ? out : to;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, []);
}

export const HoloCard = React.forwardRef<HoloCardHandle, HoloCardProps>(function HoloCard(
  {
    holder = "Dksh School",
    number = "4716 0381 9254 4242",
    expires = "09/29",
    cvv = "731",
    tier = "Titanium",
    logo,
    network,
    maxTilt = 14,
    foil = 1,
    motion = true,
    autoSpin = true,
    revealEvery = 3000,
    onFlip,
    onReveal,
    className = "",
  },
  ref,
) {
  const groups = (number.replace(/\D/g, "").padStart(16, "0").match(/.{4}/g) ?? []).slice(0, 4);
  const stageRef = React.useRef<HTMLDivElement>(null);
  const cardRef = React.useRef<HTMLDivElement>(null);
  const shadowRef = React.useRef<HTMLDivElement>(null);
  const groupRefs = React.useRef<(HTMLSpanElement | null)[]>([]);
  const cvvRef = React.useRef<HTMLSpanElement>(null);
  const scramble = useScramble();
  const [shown, setShown] = React.useState(false);
  const [cvvShown, setCvvShown] = React.useState(false);
  const [side, setSide] = React.useState<"front" | "back">("front");

  const s = React.useRef({
    tx: 0, ty: 0, ttx: 0, tty: 0, ry: 0, vry: 0, target: 0, drag: false, lastX: 0, lastT: 0, moved: 0,
    lx: 0.5, ly: 0.35, tlx: 0.5, tly: 0.35, raf: 0,
    /* auto: the card turns by itself until the user takes over */
    auto: autoSpin, touched: false,
  });
  const reduce = React.useRef(false);

  const buzz = (p: number | number[]) => {
    try {
      navigator.vibrate?.(p);
    } catch {
      /* not supported */
    }
  };

  /* animation loop: ease tilt and light, spin with inertia, settle on a face */
  React.useEffect(() => {
    reduce.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const st = s.current;
    const loop = () => {
      st.tx += (st.ttx - st.tx) * 0.12;
      st.ty += (st.tty - st.ty) * 0.12;
      st.lx += (st.tlx - st.lx) * 0.12;
      st.ly += (st.tly - st.ly) * 0.12;
      if (st.auto && !reduce.current && !st.drag) {
        /* it turns by itself, forever, until the user touches it */
        st.ry += 0.55;
        st.target = Math.round(st.ry / 180) * 180;
      }
      if (!st.drag) {
        st.vry *= 0.95;
        st.ry += st.vry;
        if (Math.abs(st.vry) < 1.2) st.ry += (st.target - st.ry) * (reduce.current ? 1 : 0.09);
        else st.target = Math.round(st.ry / 180) * 180;
      }
      const ry = st.ry + st.ty;
      const spin = ((ry % 360) + 360) % 360;
      const sweep = Math.sin((spin * Math.PI) / 180);
      const card = cardRef.current;
      if (card) {
        card.style.transform = `rotateX(${st.tx}deg) rotateY(${ry}deg)`;
        const mx = st.lx * 100 + sweep * 40;
        const my = st.ly * 100;
        card.style.setProperty("--mx", `${mx}%`);
        card.style.setProperty("--my", `${my}%`);
        card.style.setProperty("--hx", `${mx * 1.6}%`);
        card.style.setProperty("--hy", `${my * 1.2}%`);
        card.style.setProperty("--ho", (0.45 + Math.min(0.5, (Math.abs(st.tx) + Math.abs(st.ty)) / 26 + Math.abs(sweep) * 0.4)).toFixed(3));
        card.style.setProperty("--ca", `${st.ty * 6 + spin}deg`);
        card.style.setProperty("--st", `${st.ty * 4 + sweep * 60}%`);
        card.style.setProperty("--ea", `${135 + st.ty * 3}deg`);
      }
      const sh = shadowRef.current;
      if (sh) sh.style.transform = `translateX(${-st.ty * 1.4}px) scaleX(${(1 - Math.abs(sweep) * 0.45).toFixed(3)})`;
      const face = Math.round(st.target / 180) % 2 === 0 ? "front" : "back";
      setSide((prev) => (prev === face ? prev : face));
      st.raf = requestAnimationFrame(loop);
    };
    st.raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(st.raf);
  }, []);

  React.useEffect(() => onFlip?.(side), [side, onFlip]);

  const flip = React.useCallback(() => {
    const st = s.current;
    st.target = Math.round(st.ry / 180) * 180 + 180;
    st.vry = 0;
    buzz(10);
  }, []);

  const shownRef = React.useRef(false);
  const reveal = React.useCallback(
    (show?: boolean) => {
      const next = show ?? !shownRef.current;
      shownRef.current = next;
      setShown(next);
      groupRefs.current.forEach((el, i) => {
        if (!el || i === 3) return;
        setTimeout(() => (next ? scramble(el, groups[i]) : (el.textContent = "••••")), i * 90);
      });
      onReveal?.(next);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scramble, number, onReveal],
  );

  /* the number shows itself on a loop */
  React.useEffect(() => {
    if (!revealEvery) return;
    let hideTimer = 0;
    const id = window.setInterval(() => {
      reveal(true);
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(() => reveal(false), Math.max(600, revealEvery - 900));
    }, revealEvery);
    return () => {
      window.clearInterval(id);
      window.clearTimeout(hideTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealEvery]);

  /* phone tilt */
  const gyroOn = React.useRef(false);
  const listenGyro = React.useCallback(() => {
    if (gyroOn.current) return;
    gyroOn.current = true;
    window.addEventListener("deviceorientation", (e) => {
      if (e.beta == null || e.gamma == null) return;
      const st = s.current;
      const m = reduce.current ? 0 : maxTilt;
      st.ttx = Math.max(-m, Math.min(m, -(e.beta - 45) * 0.5));
      st.tty = Math.max(-m, Math.min(m, e.gamma * 0.6));
      st.tlx = 0.5 + e.gamma / 90;
      st.tly = 0.5 + (e.beta - 45) / 90;
    });
  }, [maxTilt]);

  const enableMotion = React.useCallback(async () => {
    const DOE = (typeof DeviceOrientationEvent !== "undefined" ? DeviceOrientationEvent : undefined) as unknown as { requestPermission?: () => Promise<string> } | undefined;
    try {
      if (DOE?.requestPermission) {
        const r = await DOE.requestPermission();
        if (r !== "granted") return false;
      }
      listenGyro();
      return true;
    } catch {
      return false;
    }
  }, [listenGyro]);

  React.useEffect(() => {
    if (!motion || !window.matchMedia("(hover: none)").matches) return;
    const DOE = (typeof DeviceOrientationEvent !== "undefined" ? DeviceOrientationEvent : undefined) as unknown as { requestPermission?: unknown } | undefined;
    if (DOE && typeof DOE.requestPermission !== "function") listenGyro();
  }, [motion, listenGyro]);

  React.useImperativeHandle(ref, () => ({ flip, reveal, enableMotion }), [flip, reveal, enableMotion]);

  /* pointer: tilt on hover, drag to spin, tap to flip */
  const onMove = (e: React.PointerEvent) => {
    const r = stageRef.current!.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    const st = s.current;
    const m = reduce.current ? 0 : maxTilt;
    st.tlx = px;
    st.tly = py;
    if (!st.drag) {
      if (e.pointerType === "mouse") {
        st.tty = (px - 0.5) * 2 * m;
        st.ttx = -(py - 0.5) * 2 * m;
      }
    } else {
      const now = performance.now();
      const dx = e.clientX - st.lastX;
      st.ry += dx * 0.6;
      st.vry = (dx * 0.6) / Math.max(1, (now - st.lastT) / 16);
      st.lastX = e.clientX;
      st.lastT = now;
      st.moved += Math.abs(dx);
    }
  };
  const onDown = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest("[data-hc-tap]")) return;
    const st = s.current;
    /* the user has taken over: the automatic turning stops, but the card
       keeps whatever spin the drag gives it. */
    if (!st.touched) {
      st.touched = true;
      st.auto = false;
    }
    st.drag = true;
    st.moved = 0;
    st.lastX = e.clientX;
    st.lastT = performance.now();
    st.vry = 0;
    stageRef.current?.setPointerCapture(e.pointerId);
    buzz(6);
  };
  const onUp = () => {
    const st = s.current;
    if (!st.drag) return;
    st.drag = false;
    st.target = Math.round((st.ry + st.vry * 8) / 180) * 180;
    if (st.moved < 4) flip();
  };

  const defaultLogo = (
    <span className="hc-logo">
      <span className="hc-logoMark" style={{ background: INK }}>
        <span className="hc-logoGlyph" />
      </span>
      Logo
    </span>
  );
  const defaultNetwork = (
    <span className="hc-net" aria-hidden="true">
      <span style={{ background: "rgba(29,29,31,.85)" }} />
      <span style={{ background: "rgba(29,29,31,.35)" }} />
    </span>
  );

  return (
    <div className={`hc-root ${className}`} style={{ fontFamily: FONT, WebkitFontSmoothing: "antialiased" }}>
      <style>{CSS}</style>
      <div
        ref={stageRef}
        className="hc-stage"
        style={{ aspectRatio: "1.586", perspective: 1100, touchAction: "none" }}
        onPointerMove={onMove}
        onPointerDown={onDown}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onPointerLeave={() => {
          const st = s.current;
          if (st.drag) return;
          st.ttx = 0;
          st.tty = 0;
          st.tlx = 0.5;
          st.tly = 0.35;
        }}
      >
        <div ref={shadowRef} className="hc-shadow" style={{ background: "rgba(40,40,60,.28)" }} />
        <div
          ref={cardRef}
          role="group"
          aria-roledescription="card"
          aria-label={`${tier} card ending ${groups[3]}, ${side === "front" ? "front" : "back"} side. Drag to spin, tap to flip.`}
          className="hc-card"
          style={{ transformStyle: "preserve-3d", willChange: "transform", ["--foil" as string]: String(foil) }}
        >
          {/* front */}
          <div className="hc-face" aria-hidden={side !== "front"}>
            <Layers />
            <div className="hc-inner">
              <div className="hc-row">
                {logo ?? defaultLogo}
                <span className="hc-tier" style={{ color: "rgba(29,29,31,.5)" }}>
                  {tier}
                </span>
              </div>
              <div className="hc-row">
                <span className="hc-chip" />
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(29,29,31,.6)" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                  <path d="M8.5 7.5a6 6 0 0 1 0 9M12 5a9.5 9.5 0 0 1 0 14M15.5 2.5a13 13 0 0 1 0 19" />
                </svg>
              </div>
              <button
                type="button"
                data-hc-tap
                onClick={() => reveal()}
                aria-label={shown ? "Hide card number" : "Show card number"}
                className="hc-number"
                style={{ fontFamily: MONO, color: INK, textShadow: "0 1px 0 rgba(255,255,255,.8)" }}
              >
                {groups.map((g, i) => (
                  <span key={i} ref={(el) => void (groupRefs.current[i] = el)} className="hc-group">
                    {i === 3 ? g : "••••"}
                  </span>
                ))}
              </button>
              <div className="hc-foot">
                <div className="hc-holder">
                  <span className="hc-label">Card holder</span>
                  <b className="hc-holderName">{holder}</b>
                </div>
                <div>
                  <span className="hc-label">Expires</span>
                  <b className="hc-exp">{expires}</b>
                </div>
                {network ?? defaultNetwork}
              </div>
            </div>
            <div className="hc-layer hc-edge" />
          </div>

          {/* back */}
          <div className="hc-face" style={{ transform: "rotateY(180deg)" }} aria-hidden={side !== "back"}>
            <Layers />
            <div className="hc-strip" style={{ background: "linear-gradient(180deg,#2a2a2e,#111)" }} />
            <button
              type="button"
              data-hc-tap
              onClick={() => {
                const next = !cvvShown;
                setCvvShown(next);
                if (next) scramble(cvvRef.current, cvv, 380);
                else if (cvvRef.current) cvvRef.current.textContent = "•••";
              }}
              aria-label={cvvShown ? "Hide security code" : "Show security code"}
              className="hc-cvv"
              style={{ background: "rgba(255,255,255,.75)", boxShadow: "inset 0 0 0 .5px rgba(0,0,0,.08)" }}
            >
              <span className="hc-cvvLbl" style={{ color: "rgba(29,29,31,.45)" }}>
                CVV
              </span>
              <span ref={cvvRef} className="hc-cvvVal" style={{ fontFamily: MONO, color: INK }}>
                •••
              </span>
            </button>
            <div className="hc-note" style={{ color: "rgba(29,29,31,.45)" }}>
              Tilt to see the foil, drag to spin, tap the code to reveal it.
            </div>
            <div className="hc-layer hc-edge" />
          </div>
        </div>
      </div>
    </div>
  );
});

export default HoloCard;
