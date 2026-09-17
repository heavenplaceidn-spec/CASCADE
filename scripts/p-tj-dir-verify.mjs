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
await page.waitForTimeout(800);

const ok = [];
const fail = [];
const geo = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj24").then((x) => x.json());
  const s = await fetch("/data/cascade_stops.geojson?v=tj24").then((x) => x.json());
  const pick = (id) => {
    const f = r.features.find((x) => String(x.id) === id);
    const c = f.geometry.coordinates;
    const names = s.features.filter((x) => x.properties.route_id === id).map((x) => x.properties.name);
    return { start: c[0], end: c[c.length - 1], n: c.length, names, short: f.properties.short };
  };
  return {
    gj: pick("CASTJ-GJ"),
    ext6: pick("CASTJ06-EXT"),
    c20: pick("CASTJ20"),
    c21: pick("CASTJ21"),
  };
});

const south = geo.ext6.end[1] < -6.33;
if (south && geo.ext6.names.includes("Moh Kahfi")) ok.push("CASTJ06 Moh Kahfi south " + geo.ext6.end[1].toFixed(4));
else fail.push("CASTJ06 not south/Moh Kahfi " + JSON.stringify(geo.ext6));

if (geo.gj.end[1] < geo.gj.start[1] && geo.gj.names.includes("Jagakarsa")) ok.push("CASTJ-GJ toward Jagakarsa");
else fail.push("CASTJ-GJ not toward Jagakarsa " + JSON.stringify(geo.gj));

if (geo.c20.end[1] > -6.18 && geo.c20.names.includes("Grogol Reformasi") && geo.c20.names.includes("Andara")) ok.push("CASTJ20 to Grogol via Andara");
else fail.push("CASTJ20 " + JSON.stringify({ end: geo.c20.end, names: geo.c20.names }));

if (geo.c21.names.includes("ASEAN") && geo.c21.names.includes("Kejaksaan Agung") && geo.c21.end[0] < 106.81) ok.push("CASTJ21 ASEAN/Kejaksaan");
else fail.push("CASTJ21 " + JSON.stringify({ end: geo.c21.end, names: geo.c21.names }));

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(600);
const side = await page.locator("body").innerText();
for (const t of ["Perpanjangan Galunggung – Jagakarsa", "Perpanjangan Koridor 6: Ragunan – Jagakarsa", "Jagakarsa – Grogol Reformasi", "Bumi Perkemahan Cibubur – Blok M"]) {
  if (side.includes(t)) ok.push("sidebar " + t);
  else fail.push("sidebar missing " + t);
}

const row = page.locator("button").filter({ hasText: "Perpanjangan Koridor 6: Ragunan" });
await row.first().click();
await page.waitForTimeout(1200);
const b = await page.evaluate(() => {
  const x = window.__CASCADE_MAP.getBounds();
  return { s: x.getSouth(), n: x.getNorth() };
});
if (b.s < -6.33) ok.push("popup CASTJ06 flies south " + b.s.toFixed(3));
else fail.push("popup CASTJ06 still north " + JSON.stringify(b));

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
