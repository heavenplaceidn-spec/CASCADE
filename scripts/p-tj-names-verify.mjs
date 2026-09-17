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
await page.waitForTimeout(1000);

const ok = [];
const fail = [];

const names = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const out = [];
  for (const src of ["cascade-stops", "candidate"]) {
    try {
      for (const f of map.querySourceFeatures(src, { sourceLayer: undefined })) {
        const p = f.properties || {};
        const rid = String(p.route_id || p.id || "");
        if (!rid.startsWith("CASTJ")) continue;
        if (f.geometry?.type === "Point" || p.stop_name || p.name) out.push(String(p.name || p.stop_name || ""));
      }
    } catch {}
  }
  return [...new Set(out)].filter(Boolean);
});
const km = names.filter((n) => /\bKM\b|^KM\s|\bStop\s*\d|\bStation\s*\d/i.test(n));
if (km.length) fail.push("map KM " + km.join(", "));
else ok.push("map no KM (" + names.length + " labels sampled)");

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(500);
const side = await page.locator("body").innerText();
if (/\bKM\s*\d/.test(side)) fail.push("sidebar/body still has KM");
else ok.push("explore body no KM");

await page.getByRole("link", { name: "Simulasi", exact: true }).first().click();
await page.waitForTimeout(500);
const asal = page.getByLabel("Asal");
await asal.fill("Kelapa Dua");
await page.waitForTimeout(700);
const kel = page.getByRole("button", { name: /Kelapa Dua/i });
if (await kel.count()) {
  ok.push("search Kelapa Dua");
  await kel.first().click();
} else fail.push("search missing Kelapa Dua");
const audit = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_stops.geojson?v=tj23").then((x) => x.json());
  const castj = r.features.filter((f) => String(f.properties?.route_id || "").startsWith("CASTJ"));
  const km = castj.filter((f) => /\bKM\b|^KM\s|Stop\s*\d|Station\s*\d/i.test(String(f.properties?.name || "")));
  return { n: castj.length, km: km.map((f) => f.properties.name), sample: [...new Set(castj.map((f) => f.properties.name))].slice(0, 20) };
});
if (audit.km.length) fail.push("CASTJ still KM " + audit.km.join(", "));
else ok.push("CASTJ geojson no KM n=" + audit.n);
await asal.fill("Pasar Rebo");
await page.waitForTimeout(700);
if (await page.getByRole("button", { name: /Pasar Rebo/i }).count()) ok.push("search Pasar Rebo");
else fail.push("search missing Pasar Rebo");

await page.getByRole("link", { name: "Analisis", exact: true }).first().click();
await page.waitForTimeout(500);
const an = await page.locator("body").innerText();
if (/\bKM\s*\d/.test(an)) fail.push("analisis has KM");
else ok.push("analisis no KM");

console.log("OK", ok);
console.log("FAIL", fail);
console.log("SAMPLE NAMES", names.slice(0, 25));
await browser.close();
if (fail.length) process.exit(1);
