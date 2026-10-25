"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TiltedGridHeroProps {
  images: { src: string; alt?: string }[];
  speed?: number;
  tileHeight?: number;
  aspectRatio?: number;
  gap?: number;
  axis?: number;
  curve?: number;
  fade?: number;
  children?: React.ReactNode;
  onTileClick?: (index: number) => void;
  className?: string;
}

const SLICES = 16;

export function TiltedGridHero({
  images,
  speed = 4,
  tileHeight = 26,
  aspectRatio = 16 / 9,
  gap = 6,
  axis = 56,
  curve = 80,
  fade = 12,
  children,
  onTileClick,
  className,
}: TiltedGridHeroProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [size, setSize] = React.useState({ w: 0, h: 0 });
  const [tiles, setTiles] = React.useState<{ img: number; key: number }[]>([]);
  const imgCounter = React.useRef(0);
  const tileCount = Math.max(1, Math.ceil(100 / (tileHeight + gap)));
  const curveRad = (Math.min(85, Math.max(5, curve)) * Math.PI) / 180;
  const radius = size.w > 0 ? (size.w / 2) / Math.sin(curveRad / (2 * tileCount)) : 0;
  const tileWidth = size.w > 0 ? (Math.sin(curveRad / tileCount) * radius * 2) / tileCount : 0;
  const tileHeightPx = (size.h * tileHeight) / 100;
  const gapPx = (tileHeightPx * gap) / 100;
  const bandHeight = tileHeightPx + gapPx;
  const bandTop = (size.h * axis) / 100 - bandHeight / 2;

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => {
    if (size.w === 0 || images.length === 0) return;
    const initial = Array.from({ length: tileCount }, (_, i) => ({
      img: i % images.length,
      key: imgCounter.current++,
    }));
    setTiles(initial);
  }, [size.w, tileCount, images.length]);

  const onTileWrap = React.useCallback(
    (idx: number) => {
      setTiles((prev) => {
        const next = [...prev];
        next[idx] = { img: (next[idx].img + tileCount) % images.length, key: imgCounter.current++ };
        return next;
      });
    },
    [tileCount, images.length]
  );

  const fadeMask = `linear-gradient(to right, transparent 0%, black ${fade}%, black ${100 - fade}%, transparent 100%)`;

  return (
    <div
      ref={containerRef}
      className={cn("relative w-full h-full overflow-hidden", className)}
      style={{ containerType: "size" }}
    >
      <div
        className="absolute inset-0"
        style={{
          maskImage: fadeMask,
          WebkitMaskImage: fadeMask,
        }}
      >
        <div
          className="absolute left-1/2 -translate-x-1/2 tgh-band"
          style={{
            top: bandTop,
            height: bandHeight,
            width: "100%",
            transformStyle: "preserve-3d",
            animation: `tgh-spin ${speed}s linear infinite`,
          }}
        >
          {tiles.map((tile, i) => {
            const angle = (i / tileCount) * curveRad - curveRad / 2;
            return (
              <div
                key={tile.key}
                className="absolute top-0 tgh-tile"
                style={{
                  left: `calc(50% - ${tileWidth / 2}px)`,
                  width: tileWidth,
                  height: bandHeight,
                  transform: `rotateY(${angle}rad) translateZ(${radius}px)`,
                  transformStyle: "preserve-3d",
                  cursor: "pointer",
                }}
                onClick={() => onTileClick?.(i)}
              >
                {Array.from({ length: SLICES }).map((_, s) => {
                  const sliceWidth = 100 / SLICES;
                  return (
                    <div
                      key={s}
                      className="absolute top-0 h-full overflow-hidden"
                      style={{
                        left: `${s * sliceWidth}%`,
                        width: `${sliceWidth}%`,
                        transform: `rotateY(${(s / (SLICES - 1) - 0.5) * (curveRad / tileCount)}rad)`,
                        transformOrigin: "center center",
                        transformStyle: "preserve-3d",
                      }}
                    >
                      <img
                        src={images[tile.img % images.length]?.src}
                        alt={images[tile.img % images.length]?.alt || ""}
                        className="absolute top-0 h-full object-cover"
                        style={{
                          left: `${-s * sliceWidth * (100 / sliceWidth)}%`,
                          width: `${100 * SLICES}%`,
                          pointerEvents: "none",
                        }}
                        draggable={false}
                      />
                    </div>
                  );
                })}
                <div className="tgh-tile__label">
                  {images[tile.img % images.length]?.alt}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {children}
      <style>{`
        @keyframes tgh-spin {
          from { transform: translateX(-50%) rotateY(0deg); }
          to { transform: translateX(-50%) rotateY(360deg); }
        }
        .tgh-tile__label {
          position: absolute; left: 10px; bottom: 8px; z-index: 2;
          font-family: "Pusab","Silkscreen","Pixelify Sans",monospace;
          font-size: 14px; color: #fff; text-transform: lowercase;
          letter-spacing: .02em; pointer-events: none;
          text-shadow: 0 2px 14px rgba(0,0,0,.9), 0 0 24px rgba(255,61,0,.4);
        }
        @media (prefers-reduced-motion: reduce) {
          .tgh-band { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

export default TiltedGridHero;
