#!/usr/bin/env node
import { chromium } from "playwright";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(80000);

const seen = [];
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
for (let i = 0; i < 40; i++) {
  const t = await page.locator("body").innerText();
  const m = t.match(/Memuat peta (\d+)%/);
  if (m) {
    const n = Number(m[1]);
    if (!seen.includes(n)) seen.push(n);
  }
  const readyBtn = page.getByRole("button", { name: /^EKSPLOR$/ });
  const enabled = await readyBtn.isEnabled().catch(() => false);
  if (enabled) break;
  await page.waitForTimeout(80);
}

const ok = [];
const fail = [];
const stepped = seen.every((n) => n % 10 === 0) && seen.includes(10) && !seen.some((n) => n === 18);
if (stepped) ok.push("loading 10-step " + seen.join(","));
else fail.push("loading jumps " + seen.join(","));

await page.getByRole("button", { name: /^EKSPLOR$/ }).click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(800);

const paint = await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const g = (id) => {
    if (!m.getLayer(id)) return null;
    return {
      color: m.getPaintProperty(id, "line-color"),
      offset: m.getPaintProperty(id, "line-offset"),
      dash: m.getPaintProperty(id, "line-dasharray"),
    };
  };
  return {
    cas: g("candidate"),
    casMode: g("candidate-mode"),
    tj: g("tj-existing-line"),
    tjMode: g("tj-existing-mode"),
    mp: g("masterplan-line-dash"),
    mpMode: g("masterplan-line-dash-mode"),
  };
});
if (paint.cas && paint.casMode && paint.cas.offset && paint.casMode.offset) ok.push("CASCADE dual layers");
else fail.push("CASCADE dual missing " + JSON.stringify(paint));
if (paint.tj && paint.tjMode) ok.push("existing TJ dual");
else fail.push("existing TJ dual missing");
if (paint.mp && paint.mpMode && paint.mp.dash) ok.push("masterplan dual dashed");
else fail.push("masterplan dual " + JSON.stringify(paint.mp));

const legend = await page.locator("body").innerText();
if (legend.includes("CASCADE") && legend.includes("Existing") && legend.includes("Masterplan")) ok.push("legend groups");
else fail.push("legend groups missing");
if (!legend.includes("titik merah")) ok.push("no old legend copy");

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(400);
await page.locator("button").filter({ hasText: "Sawangan – Blok M via UPN Veteran" }).first().click();
await page.waitForTimeout(1400);
const clicked = await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const p = m.project({ lng: 106.78512, lat: -6.32136 });
  const hits = m.queryRenderedFeatures(p, { layers: ["candidate", "candidate-mode", "candidate-casing"].filter((id) => m.getLayer(id)) });
  m.fire("click", { lngLat: { lng: 106.78512, lat: -6.32136 }, point: p });
  return hits.map((h) => h.properties?.id || h.layer.id);
});
await page.waitForTimeout(600);
if (clicked.length) ok.push("map hit " + clicked[0]);
const pop = await page.locator("body").innerText();
if (pop.includes("Unduh GeoJSON")) ok.push("popup download");
else fail.push("no download button");

const dl = page.getByRole("button", { name: "Unduh GeoJSON" });
if (await dl.count()) {
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 20000 }),
    dl.first().click(),
  ]);
  const name = download.suggestedFilename();
  if (name.includes("CASTJ22") && name.endsWith(".geojson")) ok.push("filename " + name);
  else fail.push("filename " + name);
  const path = await download.path();
  const fs = await import("node:fs");
  const raw = fs.readFileSync(path, "utf8");
  const fc = JSON.parse(raw);
  if (fc.type === "FeatureCollection" && fc.features[0].geometry.type === "LineString") ok.push("FC LineString");
  else fail.push("bad geojson");
  if (!/key=/i.test(raw)) ok.push("no api key");
  const coords = fc.features[0].geometry.coordinates;
  if (Math.abs(coords[0][0] - 106.77266) < 0.02 || String(fc.features[0].properties.id || fc.features[0].id || "").includes("CASTJ")) {
    ok.push("raw geometry " + (fc.features[0].properties.corridor_id || fc.features[0].id));
  } else fail.push("geometry " + JSON.stringify(coords[0]));
} else {
  fail.push("download btn missing. popup: " + pop.slice(0, 400));
}

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
