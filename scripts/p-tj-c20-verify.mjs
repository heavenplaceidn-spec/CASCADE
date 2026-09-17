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
  const r = await fetch("/data/cascade_candidates.geojson?v=tj25").then((x) => x.json());
  const s = await fetch("/data/cascade_stops.geojson?v=tj25").then((x) => x.json());
  const line = (id) => {
    const f = r.features.find((x) => String(x.id) === id);
    const c = f.geometry.coordinates;
    return { start: c[0], end: c.at(-1), south: Math.min(...c.map((p) => p[1])), north: Math.max(...c.map((p) => p[1])), n: c.length };
  };
  const names = (id) => s.features.filter((f) => f.properties.route_id === id).map((f) => f.properties.name);
  const pal = s.features.find((f) => f.properties.route_id === "CASTJ20" && f.properties.name === "Palmerah");
  return {
    c20: { ...line("CASTJ20"), names: names("CASTJ20") },
    c06: line("CASTJ06-EXT"),
    c21: line("CASTJ21"),
    pal: pal?.geometry.coordinates,
  };
});

if (geo.c20.south < -6.33 && geo.c20.names.includes("Moh Kahfi")) ok.push("CASTJ20 Moh Kahfi");
else fail.push("no Moh Kahfi " + geo.c20.south);
for (const n of ["Andara", "Kemang", "ASEAN", "Senayan City", "Palmerah", "Tanjung Duren", "Grogol Reformasi"]) {
  if (geo.c20.names.includes(n)) ok.push("stop " + n);
  else fail.push("missing " + n);
}
if (geo.c20.names.includes("Blok M")) fail.push("CASTJ20 directed to Blok M");
else ok.push("CASTJ20 not Blok M terminus");
if (geo.c20.end[1] > -6.18) ok.push("end Grogol");
else fail.push("end " + geo.c20.end);
if (geo.c06.south < -6.33 && geo.c06.start[1] > -6.31) ok.push("CASTJ06 unchanged south");
else fail.push("CASTJ06 " + JSON.stringify(geo.c06));
if (Math.abs(geo.c21.end[0] - 106.7992) < 0.002) ok.push("CASTJ21 ASEAN frozen");
else fail.push("CASTJ21 moved " + geo.c21.end);
const krl = [106.7971063, -6.2082024];
const dPal = Math.hypot((geo.pal[0] - krl[0]) * 111000, (geo.pal[1] - krl[1]) * 111000);
if (dPal > 40) ok.push("Palmerah not snapped to KRL " + Math.round(dPal) + "m");
else fail.push("Palmerah snapped " + dPal);

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(400);
const row = page.locator("button").filter({ hasText: "Jagakarsa – Grogol Reformasi" });
await row.first().click();
await page.waitForTimeout(1400);
const b = await page.evaluate(() => {
  const x = window.__CASCADE_MAP.getBounds();
  return { s: x.getSouth(), n: x.getNorth() };
});
if (b.s < -6.32 && b.n > -6.20) ok.push("popup CASTJ20 spans Moh Kahfi→Grogol");
else fail.push("fly bounds " + JSON.stringify(b));

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
