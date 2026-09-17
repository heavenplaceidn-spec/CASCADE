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
await page.waitForTimeout(600);

const ok = [];
const fail = [];
const geo = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28").then((x) => x.json());
  const s = await fetch("/data/cascade_stops.geojson?v=tj28").then((x) => x.json());
  const m = await fetch("/data/cascade_existing.json?v=tj28").then((x) => x.json());
  const names = (id) =>
    s.features.filter((f) => f.properties.route_id === id).sort((a, b) => a.properties.stop_order - b.properties.stop_order).map((f) => f.properties.name);
  const line = (id) => {
    const f = r.features.find((x) => String(x.id) === id);
    const c = f.geometry.coordinates;
    return { start: c[0], end: c.at(-1), parent: f.properties.parent_route, plan: f.properties.plan_type, short: f.properties.short };
  };
  return {
    ids: r.features.map((f) => String(f.id)),
    meta: m.corridors.map((c) => c.id),
    c22: !!r.features.find((f) => f.id === "CASTJ22"),
    c26: !!r.features.find((f) => f.id === "CASTJ26"),
    c06: !!r.features.find((f) => f.id === "CASTJ06-EXT"),
    e3: { ...line("CASTJ03-EXT"), names: names("CASTJ03-EXT") },
    e2: { ...line("CASTJ02-EXT"), names: names("CASTJ02-EXT") },
    e14: { ...line("CASTJ14-EXT"), names: names("CASTJ14-EXT") },
  };
});

if (geo.c22 && geo.c26 && geo.c06) ok.push("old CASTJ frozen present");
else fail.push("old CASTJ missing");
if (geo.e3.names[0] === "Kalideres" && geo.e3.names.at(-1).includes("Bandara") && geo.e3.parent === "Koridor 3") ok.push("EXT3");
else fail.push("EXT3 " + JSON.stringify(geo.e3));
if (geo.e2.names[0] === "Pulo Gadung" && geo.e2.names.at(-1) === "Harapan Indah" && geo.e2.parent === "Koridor 2") ok.push("EXT2");
else fail.push("EXT2 " + JSON.stringify(geo.e2));
if (geo.e14.names[0] === "JIS" && geo.e14.names.includes("Cilincing") && geo.e14.names.at(-1) === "Marunda") ok.push("EXT14");
else fail.push("EXT14 " + JSON.stringify(geo.e14));
if (geo.e3.plan === "EXTENSION" && geo.e2.plan === "EXTENSION" && geo.e14.plan === "EXTENSION") ok.push("plan_type EXTENSION");

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(400);
const side = await page.locator("body").innerText();
for (const t of [
  "Perpanjangan Koridor 3 – Arah Bandara",
  "Perpanjangan Koridor 2 – Arah Harapan Indah",
  "Perpanjangan Koridor 14 – JIS–Marunda via Cilincing",
  "Sawangan – Blok M via UPN Veteran",
  "Perpanjangan Koridor 6: Ragunan – Jagakarsa",
]) {
  if (side.includes(t)) ok.push("sidebar " + t);
  else fail.push("sidebar missing " + t);
}

await page.locator("button").filter({ hasText: "Perpanjangan Koridor 3 – Arah Bandara" }).first().click();
await page.waitForTimeout(1100);
const b = await page.evaluate(() => {
  const x = window.__CASCADE_MAP.getBounds();
  return { w: x.getWest(), e: x.getEast(), s: x.getSouth(), n: x.getNorth() };
});
if (b.w < 106.71 && b.e > 106.66 && b.s < -6.15) ok.push("fly EXT3 Kalideres–Bandara");
else fail.push("fly EXT3 " + JSON.stringify(b));

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
