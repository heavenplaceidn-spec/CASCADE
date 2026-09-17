#!/usr/bin/env node
import { chromium } from "playwright";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(70000);
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => x.textContent?.trim() === "EKSPLOR");
  return b && !b.disabled;
}, { timeout: 60000 });
await page.getByRole("button", { name: /^EKSPLOR$/ }).click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(700);

const ok = [];
const fail = [];
const geo = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj27").then((x) => x.json());
  const s = await fetch("/data/cascade_stops.geojson?v=tj27").then((x) => x.json());
  const m = await fetch("/data/cascade_existing.json?v=tj27").then((x) => x.json());
  const ids = r.features.map((f) => String(f.id));
  const names = (id) =>
    s.features.filter((f) => f.properties.route_id === id).sort((a, b) => a.properties.stop_order - b.properties.stop_order).map((f) => f.properties.name);
  const line = (id) => {
    const f = r.features.find((x) => String(x.id) === id);
    const c = f.geometry.coordinates;
    return { start: c[0], end: c.at(-1), short: f.properties.short, n: c.length };
  };
  return {
    ids,
    meta: m.corridors.map((c) => c.id),
    c06: line("CASTJ06-EXT"),
    c21: line("CASTJ21"),
    c22: { ...line("CASTJ22"), names: names("CASTJ22") },
    c23: { ...line("CASTJ23"), names: names("CASTJ23") },
    c24: { ...line("CASTJ24"), names: names("CASTJ24") },
    c25: { ...line("CASTJ25"), names: names("CASTJ25") },
    c26: { ...line("CASTJ26"), names: names("CASTJ26") },
  };
});

for (const id of ["CASTJ22", "CASTJ23", "CASTJ24", "CASTJ25", "CASTJ26"]) {
  if (geo.ids.includes(id) && geo.meta.includes(id)) ok.push("data " + id);
  else fail.push("missing " + id);
}
if (geo.c22.names[0] === "Sawangan" && geo.c22.names.includes("UPN Veteran")) ok.push("CASTJ22 Sawangan/UPN");
else fail.push("CASTJ22 names " + geo.c22.names.join(","));
if (geo.c23.names[0] === "Pondok Labu" && geo.c23.names.includes("Puri Indah") && geo.c23.names.at(-1) === "Kalideres") ok.push("CASTJ23");
else fail.push("CASTJ23 " + geo.c23.names.join(","));
if (geo.c24.names.includes("Joglo") && geo.c24.names.at(-1) === "Monas") ok.push("CASTJ24 Joglo–Monas");
else fail.push("CASTJ24 " + geo.c24.names.join(","));
if (geo.c25.names.includes("Meruya") && geo.c25.names.at(-1) === "Monas") ok.push("CASTJ25 Meruya–Monas");
else fail.push("CASTJ25 " + geo.c25.names.join(","));
if (geo.c24.short !== geo.c25.short) ok.push("24≠25 entity");
else fail.push("24/25 merged names");
if (JSON.stringify(geo.c24.start) !== JSON.stringify(geo.c25.start) || geo.c24.n !== geo.c25.n) ok.push("24/25 geometry distinct");
if (geo.c26.names[0] === "Koja" && geo.c26.names.includes("Plumpang") && geo.c26.names.includes("Kapuk") && geo.c26.names.at(-1).includes("Cengkareng")) ok.push("CASTJ26");
else fail.push("CASTJ26 " + geo.c26.names.join(","));
if (geo.c06.start[1] < -6.30) ok.push("CASTJ06 frozen");
if (Math.abs(geo.c21.end[0] - 106.7992) < 0.002) ok.push("CASTJ21 frozen");

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(500);
const side = await page.locator("body").innerText();
for (const t of [
  "Sawangan – Blok M via UPN Veteran",
  "Pondok Labu – Kalideres via Puri Indah",
  "CBD Ciledug – Monas via Joglo",
  "Ciledug – Monas via Meruya",
  "Koja – Cengkareng Business City",
  "Perpanjangan Koridor 6: Ragunan – Jagakarsa",
]) {
  if (side.includes(t)) ok.push("sidebar " + t);
  else fail.push("sidebar missing " + t);
}

const row = page.locator("button").filter({ hasText: "Sawangan – Blok M via UPN Veteran" });
await row.first().click();
await page.waitForTimeout(1200);
const b = await page.evaluate(() => {
  const x = window.__CASCADE_MAP.getBounds();
  return { s: x.getSouth(), n: x.getNorth(), w: x.getWest(), e: x.getEast() };
});
if (b.s < -6.35 && b.n > -6.26) ok.push("fly CASTJ22 spans Sawangan–Blok M");
else fail.push("fly CASTJ22 " + JSON.stringify(b));

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
