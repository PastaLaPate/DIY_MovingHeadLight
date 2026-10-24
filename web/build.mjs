import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = dirname(fileURLToPath(import.meta.url));
const src = join(root, "src");
const out = resolve(root, "../firmware/data");
const gzip = !process.argv.includes("--no-gzip");

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

// 1. static sources (skip the Tailwind entry and any dev-generated css)
for (const f of readdirSync(src)) {
  if (f === "input.css" || f === "main.css") continue;
  cpSync(join(src, f), join(out, f), { recursive: true });
}

// 2. Tailwind
execFileSync("pnpm",
  ["exec", "tailwindcss", "-i", join(src, "input.css"), "-o", join(out, "main.css"), "--minify"],
  { cwd: root, stdio: "inherit", shell: process.platform === "win32" });

// 3. gzip (serveStatic finds foo.css.gz when /foo.css is requested)
const COMPRESS = new Set([".html", ".css", ".js", ".svg", ".json"]);
let total = 0;
(function walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    if (gzip && COMPRESS.has(extname(p))) {
      writeFileSync(p + ".gz", gzipSync(readFileSync(p), { level: 9 }));
      rmSync(p);
    }
  }
})(out);
(function sizes(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { sizes(p); continue; }
    total += statSync(p).size;
    console.log(`${String(statSync(p).size).padStart(7)}  ${p.replace(out, "data")}`);
  }
})(out);
console.log(`${String(total).padStart(7)}  total`);