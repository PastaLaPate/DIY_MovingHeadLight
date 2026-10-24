import $ from "jquery";

// Friendly names for known keys; unknown keys fall back to a humanized version.
const LABELS = {
  http: "HTTP",
  udp: "UDP",
  top_servo: "Top servo",
  base_servo: "Base servo",
  led_r: "LED red",
  led_g: "LED green",
  led_b: "LED blue",
};
// Per-section value formatting (key = top-level key in the JSON).
const FORMAT = { pins: (v) => `GPIO ${v}` };

const label = (k) =>
  LABELS[k] ?? k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function section(title, entries, fmt = String) {
  const $dl = $("<dl>", { class: "divide-y divide-zinc-800" });
  for (const [k, v] of Object.entries(entries)) {
    $("<div>", { class: "flex items-center justify-between py-1.5" })
      .append($("<dt>", { class: "text-sm text-zinc-300", text: label(k) }))
      .append($("<dd>", { class: "font-mono text-sm text-zinc-100", text: fmt(v) }))
      .appendTo($dl);
  }
  return $("<section>", { class: "rounded-xl bg-zinc-900 p-4 ring-1 ring-zinc-800" })
    .append($("<h3>", {
      class: "mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400",
      text: title,
    }))
    .append($dl);
}

export function mountConfigPanel(selector, { url = "/config", timeoutMs = 4000 } = {}) {
  const $root = $(selector);

  const button = (text) =>
    $("<button>", {
      type: "button",
      class: "rounded-lg bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700 active:opacity-80",
      text,
    }).on("click", load);

  const header = (extra) =>
    $("<div>", { class: "mb-3 flex items-center justify-between" })
      .append($("<h2>", { class: "text-lg font-semibold", text: "Device config" }))
      .append(extra);

  function render(data) {
    const sections = Object.entries(data).map(([key, entries]) =>
      section(label(key), entries, FORMAT[key]),
    );
    $root.empty().append(
      header(button("Refresh")),
      $("<div>", { class: "grid gap-3 sm:grid-cols-2" }).append(...sections),
    );
  }

  function renderError(err) {
    const msg = err.name === "TimeoutError" ? "Request timed out" : err.message;
    $root.empty().append(
      header(button("Retry")),
      $("<p>", { class: "text-sm text-red-400", text: `Couldn't load config: ${msg}` }),
    );
  }

  async function load() {
    $root.empty().append($("<p>", { class: "text-sm text-zinc-400", text: "Loading config…" }));
    try {
      const res = await fetch(url, {
        cache: "no-store",
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      render(await res.json());
    } catch (err) {
      renderError(err);
    }
  }

  load();
  return load; // call it later to refresh programmatically
}