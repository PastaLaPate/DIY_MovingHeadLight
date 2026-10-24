import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = dirname(fileURLToPath(import.meta.url));
const out = resolve(root, "../firmware/data");
const gzip = !process.argv.includes("--no-gzip");

execFileSync("pnpm", ["exec", "vite", "build"],
  { cwd: root, stdio: "inherit", shell: process.platform === "win32" });

const COMPRESS = new Set([".html", ".css", ".js", ".svg", ".json"]);
const walk = (d) => readdirSync(d, { withFileTypes: true })
  .flatMap((e) => (e.isDirectory() ? walk(join(d, e.name)) : [join(d, e.name)]));

let total = 0;
for (let p of walk(out)) {
  if (gzip && COMPRESS.has(extname(p))) {
    writeFileSync(p + ".gz", gzipSync(readFileSync(p), { level: 9 }));
    rmSync(p);
    p += ".gz";
  }
  const size = statSync(p).size;
  total += size;
  console.log(`${String(size).padStart(7)}  ${p.replace(out, "data")}`);
}
console.log(`${String(total).padStart(7)}  total`);