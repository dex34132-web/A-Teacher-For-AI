import * as React from "react";
import { createRoot } from "react-dom/client";
import HoloCard from "../components/ui/holo-card";

/* The holo card lives in the poster stage, bottom left, under the copy.
   It turns by itself until you touch it, and the number reveals on a loop. */
const Holo = () => (
  <HoloCard
    holder="Dksh School"
    number="4716 0381 9254 4242"
    expires="09/29"
    cvv="731"
    tier="Titanium"
    autoSpin
    revealEvery={3000}
  />
);

const mount = document.getElementById("holoMount");
if (mount) {
  createRoot(mount).render(
    <React.StrictMode>
      <Holo />
    </React.StrictMode>,
  );
}

export default Holo;
