#!/usr/bin/env node
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });
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
await page.waitForTimeout(1500);

const ok = [];
const fail = [];

await page.waitForTimeout(400);

const side = await page.locator("button").evaluateAll((els) =>
  els.map((e) => e.textContent?.replace(/\s+/g, " ").trim()).filter(Boolean),
);
const sideText = side.join(" | ");
for (const name of ["Lebak Bulus – ICE BSD", "Lebak Bulus – Depok Baru", "Depok Baru – Jonggol", "Depok Baru – Ancol"]) {
  if (sideText.includes(name)) ok.push("sidebar " + name);
  else fail.push("sidebar missing " + name);
}

const mapIds = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("candidate");
  return [...new Set(feats.map((f) => f.properties?.route_id || f.properties?.id).filter(Boolean))];
});
for (const id of ["MRT-CASCADE-01", "MRT-CASCADE-02", "MRT-CASCADE-03", "MRT-CASCADE-04"]) {
  if (mapIds.includes(id)) ok.push("map " + id);
  else fail.push("map missing " + id);
}

const ice = page.locator("button").filter({ hasText: "Lebak Bulus – ICE BSD" });
if (await ice.count()) {
  await ice.first().click();
  await page.waitForTimeout(1400);
  const b = await page.evaluate(() => {
    const x = window.__CASCADE_MAP.getBounds();
    return { w: x.getWest(), s: x.getSouth(), e: x.getEast(), n: x.getNorth() };
  });
  if (b.w < 106.66 && b.e > 106.76) ok.push("fit ICE BSD");
  else fail.push("fit ICE BSD " + JSON.stringify(b));
} else fail.push("cannot click ICE BSD");

await page.evaluate(() => window.__CASCADE_MAP.jumpTo({ center: [106.775, -6.289], zoom: 14 }));
await page.waitForTimeout(700);
const lb = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const stops = [
    ...map.queryRenderedFeatures({ layers: ["cascade-stop"] }),
    ...map.queryRenderedFeatures({ layers: ["mrt-existing-stop"] }),
  ];
  return stops.filter((f) => /Lebak Bulus/i.test(String(f.properties?.name || f.properties?.stop_name || "")));
});
if (lb.length >= 1) ok.push("Lebak Bulus node");

await page.getByRole("button", { name: /^LRT$/ }).first().click();
await page.waitForTimeout(500);
const lrtBtn = page.locator("button").filter({ hasText: "Dukuh Atas – Tanah Abang" });
if (await lrtBtn.count()) {
  ok.push("sidebar LRT");
  await lrtBtn.first().click();
  await page.waitForTimeout(1400);
  const b = await page.evaluate(() => {
    const x = window.__CASCADE_MAP.getBounds();
    return { w: x.getWest(), e: x.getEast() };
  });
  if (b.w < 106.70 && b.e > 106.80) ok.push("fit LRT");
  else fail.push("fit LRT " + JSON.stringify(b));
} else fail.push("sidebar missing LRT");

await page.getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(500);

const rides = await page.evaluate(async () => {
  const fn = window.__CASCADE_RIDES;
  if (!fn) return null;
  return {
    c01: await fn("MRT-CASCADE-01"),
    c02: await fn("MRT-CASCADE-02"),
    c03: await fn("MRT-CASCADE-03"),
    c04: await fn("MRT-CASCADE-04"),
    lrt: await fn("LRT-CASCADE-NEW-01"),
  };
});
console.log("RIDES", rides);

async function pick(label, q, want) {
  const input = page.getByLabel(label);
  await input.fill(q);
  await page.waitForTimeout(800);
  const btn = page.getByRole("button", { name: new RegExp(want) });
  if (await btn.count()) {
    await btn.first().click();
    return true;
  }
  fail.push("search " + want);
  return false;
}

await pick("Asal", "Lebak Bulus", "Lebak Bulus");
await pick("Tujuan", "Jonggol", "Jonggol");
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2500);
const hops = await page.evaluate(() => window.__CASCADE?.getState?.()?.simResult?.hops || []);
const origin = await page.evaluate(() => window.__CASCADE?.getState?.()?.simOrigin);
if (hops.some((h) => /Depok Baru/i.test(h))) ok.push("sim LB→Jonggol " + hops.join(" > "));
else fail.push("sim LB→Jonggol hops=" + JSON.stringify(hops) + " origin=" + origin?.routeId);

await pick("Asal", "Depok Baru", "Depok Baru");
await pick("Tujuan", "Ancol", "Ancol");
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2000);
const hops2 = await page.evaluate(() => window.__CASCADE?.getState?.()?.simResult?.hops || []);
if (hops2.join(" ").match(/Ancol/i)) ok.push("sim Depok→Ancol");
else fail.push("sim Depok→Ancol " + JSON.stringify(hops2));

await pick("Asal", "Dukuh Atas", "Dukuh Atas");
await pick("Tujuan", "Bandara", "Bandara");
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2000);
const hops3 = await page.evaluate(() => window.__CASCADE?.getState?.()?.simResult?.hops || []);
if (hops3.join(" ").match(/Bandara|Soekarno/i)) ok.push("sim LRT");
else fail.push("sim LRT " + JSON.stringify(hops3));

await page.screenshot({ path: "/workspace/screenshots/mrt-lrt-sim.png" });
console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
