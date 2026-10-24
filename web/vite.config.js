import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

const target = `ws://${process.env.ESP ?? "192.168.1.37"}`;

export default defineConfig({
  root: "src",                          // relative to this file
  publicDir: false,
  plugins: [tailwindcss()],
  build: {
    outDir: "../../firmware/data",      // = web/src/../../firmware/data
    emptyOutDir: true,                  // required: outDir is outside root
    modulePreload: false,               // single bundle, skip the preload polyfill
  },
  server: {
    proxy: { "/ws": { target, ws: true } },
  },
});