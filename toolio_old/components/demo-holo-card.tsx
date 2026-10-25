"use client";

import * as React from "react";
import { HoloCard } from "@/components/ui/holo-card";

/* The card, on its own. No controls, no chrome under it. */

/* Geist + Geist Mono from Google Fonts */
function useGeist() {
  React.useEffect(() => {
    if (document.getElementById("geist-font")) return;
    const l = document.createElement("link");
    l.id = "geist-font";
    l.rel = "stylesheet";
    l.href = "https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@500;600&display=swap";
    document.head.appendChild(l);
  }, []);
}

export default function HoloCardDemo() {
  useGeist();
  return (
    <div
      className="flex min-h-screen w-full items-center justify-center px-4 py-10"
      style={{ fontFamily: "Geist, -apple-system, BlinkMacSystemFont, Inter, 'Segoe UI', Roboto, sans-serif" }}
    >
      <HoloCard />
    </div>
  );
}
