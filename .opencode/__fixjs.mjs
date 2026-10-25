import { readFileSync, writeFileSync } from "node:fs";
const p = "C:/Users/dex34/OneDrive/Documents/Teach/schoolio/main.js";
let s = readFileSync(p, "utf8");
const bad = 'src: ["git clone https://github.com/dex34132-web/lerev.git\\ncd lerev\\npip install -e .", "editable install, python 3.10+"].join("\\n").split("|")[0] ? ["git clone https://github.com/dex34132-web/lerev.git\\ncd lerev\\npip install -e .", "editable install, python 3.10+"] : ["", ""]';
const good = 'src: ["git clone https://github.com/dex34132-web/lerev.git\\ncd lerev\\npip install -e .", "editable install, python 3.10+"]';
if (!s.includes(bad)) { console.log("PATTERN NOT FOUND"); } else { s = s.replace(bad, good); writeFileSync(p, s); console.log("patched"); }
