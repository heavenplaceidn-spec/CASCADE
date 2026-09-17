#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(80000);
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => x.textContent?.trim() === "EKSPLOR");
  return b && !b.disabled;
}, { timeout: 70000 });
await page.getByRole("button", { name: /^EKSPLOR$/ }).click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(700);

const ok = [];
const fail = [];

const layout = await page.evaluate(() => {
  const legend = [...document.querySelectorAll("p")].find((p) => p.textContent?.trim() === "LEGENDA");
  const gaya = document.querySelector('select[aria-label="Gaya MAPID"]');
  const panel = legend?.closest("div.cascade-panel");
  const gayaBox = gaya?.closest("div.cascade-panel")?.getBoundingClientRect();
  const legBox = panel?.getBoundingClientRect();
  return {
    leg: legBox ? { x: legBox.x, y: legBox.y, r: legBox.right, b: legBox.bottom, w: legBox.width } : null,
    gaya: gayaBox ? { x: gayaBox.x, y: gayaBox.y } : null,
  };
});
if (layout.leg && layout.leg.x < 80 && layout.leg.w < 280) ok.push("legend left compact");
else fail.push("legend layout " + JSON.stringify(layout.leg));
if (layout.gaya && layout.leg && layout.gaya.y >= layout.leg.b - 2 && Math.abs(layout.gaya.x - layout.leg.x) < 40) ok.push("Gaya MAPID below legend");
else fail.push("gaya pos " + JSON.stringify(layout));

const existingDot = await page.evaluate(() => {
  const row = [...document.querySelectorAll("button")].find((b) => /\bEXISTING\b/.test(b.textContent || "") && b.querySelector("span.size-2"));
  const dot = row?.querySelector("span.size-2");
  if (!dot) return null;
  return getComputedStyle(dot).backgroundColor;
});
if (existingDot && !/rgb\(220,\s*38,\s*38\)/.test(existingDot)) ok.push("existing swatch not red " + existingDot);
else fail.push("existing swatch still red " + existingDot);

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(400);
await page.locator("button").filter({ hasText: "Sawangan – Blok M via UPN Veteran" }).first().click();
await page.waitForTimeout(1200);
await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const p = m.project({ lng: 106.78512, lat: -6.32136 });
  m.fire("click", { lngLat: { lng: 106.78512, lat: -6.32136 }, point: p });
});
await page.waitForTimeout(500);
const dl = page.getByRole("button", { name: "Unduh GeoJSON" });
if (await dl.count()) ok.push("circular download in popup");
else fail.push("no popup download");

async function grab(label, clickFn) {
  if (clickFn) await clickFn();
  await page.waitForTimeout(400);
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 15000 }),
    page.getByRole("button", { name: "Unduh GeoJSON" }).first().click(),
  ]);
  const name = download.suggestedFilename();
  const path = await download.path();
  const raw = fs.readFileSync(path, "utf8");
  const fc = JSON.parse(raw);
  const g = fc.features?.[0]?.geometry;
  const id = String(fc.features?.[0]?.id || fc.features?.[0]?.properties?.id || "");
  const good = fc.type === "FeatureCollection" && g && Array.isArray(g.coordinates) && !/key=/i.test(raw);
  if (good) ok.push(label + " " + name + " " + id);
  else fail.push(label + " bad " + name);
  return { name, id, g };
}

await grab("CASTJ22");

await page.locator("button").filter({ hasText: "CBD Ciledug – Monas via Joglo" }).first().click();
await page.waitForTimeout(1100);
await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const p = m.project({ lng: 106.7484, lat: -6.2175 });
  m.fire("click", { lngLat: { lng: 106.7484, lat: -6.2175 }, point: p });
});
await page.waitForTimeout(500);
const c24 = await grab("CASTJ24");

await page.locator("button").filter({ hasText: "Ciledug – Monas via Meruya" }).first().click();
await page.waitForTimeout(1100);
await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const p = m.project({ lng: 106.7463, lat: -6.1975 });
  m.fire("click", { lngLat: { lng: 106.7463, lat: -6.1975 }, point: p });
});
await page.waitForTimeout(500);
const c25 = await grab("CASTJ25");
if (c24.id !== c25.id) ok.push("24≠25 " + c24.id + " / " + c25.id);
else fail.push("24 merged 25");

async function expand(name) {
  const btn = page.getByRole("button", { name: new RegExp(`^${name}$`) });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
  await page.waitForTimeout(200);
}

await expand("EXISTING");
const [layerDl] = await Promise.all([
  page.waitForEvent("download", { timeout: 15000 }),
  page.locator('button[aria-label="Unduh GeoJSON EXISTING TransJakarta"]').click(),
]);
const lname = layerDl.suggestedFilename();
const lraw = fs.readFileSync(await layerDl.path(), "utf8");
const lfc = JSON.parse(lraw);
if (lfc.type === "FeatureCollection" && lfc.features.length > 1 && lfc.features[0].geometry) ok.push("layer existing TJ " + lname + " n=" + lfc.features.length);
else fail.push("layer existing TJ " + lname);

await expand("MASTERPLAN");
const [mpDl] = await Promise.all([
  page.waitForEvent("download", { timeout: 15000 }),
  page.locator('button[aria-label="Unduh GeoJSON MASTERPLAN KRL"]').click(),
]);
const mraw = fs.readFileSync(await mpDl.path(), "utf8");
const mfc = JSON.parse(mraw);
if (mfc.type === "FeatureCollection" && mfc.features.length > 0) ok.push("layer masterplan KRL n=" + mfc.features.length);
else fail.push("layer masterplan KRL");

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
