import fs from "node:fs";

const text = fs.readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8");

function stripJsonc(source) {
  let out = "";
  let inString = false;
  let escaped = false;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (inString) {
      out += char;
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') inString = false;
      continue;
    }
    if (char === '"') {
      inString = true;
      out += char;
      continue;
    }
    if (char === "/" && source[index + 1] === "/") {
      while (index < source.length && source[index] !== "\n") index += 1;
      out += "\n";
      continue;
    }
    out += char;
  }
  return out;
}

const config = JSON.parse(stripJsonc(text));
const url = config.env?.production?.vars?.NEXT_PUBLIC_API_URL;
if (typeof url !== "string" || !url.startsWith("https://") || url.endsWith("/")) {
  console.error(
    "env.production.vars.NEXT_PUBLIC_API_URL must be an https URL with no trailing slash",
  );
  process.exit(1);
}
process.stdout.write(url);
