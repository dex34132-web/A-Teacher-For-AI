// Tilted Grid Hero — plain-JS island (no React/Tailwind).
// A STATIC tilted grid of section cards. Cards stay flat and readable; the
// whole grid only spins when a card is clicked (fast whirl + white flash +
// scroll to the section). Nothing moves on its own.
(function () {
  "use strict";
  const mount = document.getElementById("tiltedGrid");
  if (!mount) return;

  const sections = [
    { id: "forgetting", title: "forgetting", sub: "the window filled up", img: "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=900&q=80" },
    { id: "pipeline", title: "pipeline", sub: "one request, five hops", img: "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80" },
    { id: "anatomy", title: "anatomy", sub: "what a block holds", img: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=900&q=80" },
    { id: "tools", title: "tools", sub: "fifty-two of them", img: "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=900&q=80" },
    { id: "mcp", title: "mcp", sub: "it speaks mcp too", img: "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=900&q=80" },
    { id: "numbers", title: "measured", sub: "not asserted", img: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80" },
    { id: "install", title: "install", sub: "five real steps", img: "https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=900&q=80" },
  ];

  let busy = false;

  const flash = document.createElement("div");
  flash.className = "tg-flash";
  document.body.appendChild(flash);

  function build() {
    mount.innerHTML = "";
    const plane = document.createElement("div");
    plane.className = "tg-plane";

    const grid = document.createElement("div");
    grid.className = "tg-grid";

    sections.forEach((s) => {
      const a = document.createElement("a");
      a.className = "tg-card";
      a.href = "#" + s.id;
      a.dataset.id = s.id;
      a.setAttribute("aria-label", s.title + " — " + s.sub);

      const img = document.createElement("img");
      img.src = s.img;
      img.alt = "";
      img.loading = "lazy";
      img.draggable = false;
      a.appendChild(img);

      const label = document.createElement("span");
      label.className = "tg-card__label";
      label.textContent = s.title;
      a.appendChild(label);

      const sub = document.createElement("span");
      sub.className = "tg-card__sub";
      sub.textContent = s.sub;
      a.appendChild(sub);

      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        onClick(s.id, plane);
      });
      grid.appendChild(a);
    });

    plane.appendChild(grid);
    mount.appendChild(plane);
  }

  function onClick(id, plane) {
    if (busy) return;
    busy = true;
    if (plane) plane.classList.add("tg-plane--spin");

    setTimeout(function () {
      flash.style.transition = "none";
      flash.style.opacity = "1";
      setTimeout(function () {
        document.documentElement.style.scrollBehavior = "auto";
        const el = document.getElementById(id);
        if (el) window.scrollTo(0, Math.max(0, el.getBoundingClientRect().top + window.scrollY - 60));
        flash.style.transition = "opacity 1.4s ease";
        flash.style.opacity = "0";
        setTimeout(function () { busy = false; }, 1400);
      }, 320);
    }, 420);

    setTimeout(function () {
      if (plane) plane.classList.remove("tg-plane--spin");
    }, 1200);
  }

  build();
  window.addEventListener("resize", function () {}, { passive: true });
})();
