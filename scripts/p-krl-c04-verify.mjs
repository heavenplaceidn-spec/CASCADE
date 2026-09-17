#!/usr/bin/env node
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });
const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(70000);
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });

const explor = page.getByRole("button", { name: /^EKSPLOR$/ });
await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => x.textContent?.trim() === "EKSPLOR");
  return b && !b.disabled;
}, { timeout: 60000 });
await explor.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(1500);

const fail = [];
const ok = [];

async function clickText(name) {
  const btn = page.getByRole("button", { name });
  if (await btn.count()) {
    await btn.first().click();
    return true;
  }
  return false;
}

// CASCADE group is open by default. First KRL row is CASCADE → KRL.
const krlRow = page.getByRole("button", { name: /^KRL$/ });
if (await krlRow.count()) await krlRow.first().click();
await page.waitForTimeout(900);

const side = await page.locator("button").evaluateAll((els) =>
  els.map((e) => e.textContent?.replace(/\s+/g, " ").trim()).filter(Boolean),
);
const sideText = side.join(" | ");
for (const id of ["KRL-C03-N", "KRL-C03-S", "KRL-C04"]) {
  if (sideText.includes(id)) ok.push(`sidebar ${id}`);
  else fail.push(`sidebar missing ${id}`);
}

const mapIds = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("candidate");
  const ids = [...new Set(feats.map((f) => f.properties?.route_id || f.properties?.id).filter(Boolean))];
  return {
    ids,
    krl: ids.filter((id) => String(id).startsWith("KRL-C")),
    color: map.getPaintProperty("candidate", "line-color"),
  };
});
if (mapIds.krl.includes("KRL-C03-N")) ok.push("map C03-N");
else fail.push("map missing C03-N");
if (mapIds.krl.includes("KRL-C03-S")) ok.push("map C03-S");
else fail.push("map missing C03-S");
if (mapIds.krl.includes("KRL-C04")) ok.push("map C04");
else fail.push("map missing C04 " + JSON.stringify(mapIds.ids));
if (String(mapIds.color).toLowerCase().includes("7c3aed") || mapIds.color === "#7C3AED") ok.push("cascade purple");

await page.screenshot({ path: "/workspace/screenshots/krl-cascade-list.png" });

const c04 = page.locator("button").filter({ hasText: "KRL-C04" });
if (await c04.count()) {
  await c04.first().scrollIntoViewIfNeeded();
  await c04.first().click();
  await page.waitForTimeout(1400);
} else fail.push("cannot click C04");

const bounds = await page.evaluate(() => {
  const b = window.__CASCADE_MAP.getBounds();
  return { w: b.getWest(), s: b.getSouth(), e: b.getEast(), n: b.getNorth(), z: window.__CASCADE_MAP.getZoom() };
});
// C04 geom bbox ~ 106.39,-6.58,106.85,-6.33
const coversSentul = bounds.e > 106.82 && bounds.s < -6.50;
const coversMaja = bounds.w < 106.42 && bounds.n > -6.36;
if (coversSentul && coversMaja) ok.push("C04 fit bounds");
else fail.push(`C04 fit incomplete ${JSON.stringify(bounds)}`);

await page.screenshot({ path: "/workspace/screenshots/krl-c04-fit.png" });

// Zoom in on Dramaga
await page.evaluate(() => window.__CASCADE_MAP.jumpTo({ center: [106.73, -6.56], zoom: 13.2 }));
await page.waitForTimeout(900);
const dramaga = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const stops = map.queryRenderedFeatures({ layers: ["cascade-stop"] });
  return stops.map((f) => f.properties?.name || f.properties?.stop_name).filter(Boolean);
});
if (dramaga.some((n) => /Dramaga/i.test(n))) ok.push("Dramaga visible");
else fail.push("Dramaga not rendered " + JSON.stringify(dramaga.slice(0, 12)));
await page.screenshot({ path: "/workspace/screenshots/krl-dramaga.png" });

// Simulation search + transfer
await page.getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(500);
const asal = page.getByLabel("Asal");
const tujuan = page.getByLabel("Tujuan");
await asal.fill("Mauk");
await page.waitForTimeout(600);
await page.getByRole("button", { name: /Mauk/ }).first().click().catch(() => fail.push("search Mauk"));
await tujuan.fill("Parung Panjang");
await page.waitForTimeout(700);
await page.getByRole("button", { name: /Parung Panjang/ }).first().click().catch(() => fail.push("search Parung Panjang"));
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2000);
const hops1 = await page.locator("body").innerText();
if (/Tangerang/i.test(hops1) && /pindah/i.test(hops1)) ok.push("transfer Tangerang N→S");
else if (/km/i.test(hops1)) ok.push("route N→S ran (check hops) " + hops1.match(/Jarak[\s\S]{0,80}/)?.[0]);
else fail.push("sim N→S failed");

await asal.fill("Maja");
await page.waitForTimeout(700);
await page.getByRole("button", { name: /^Maja/ }).first().click().catch(() => fail.push("search Maja"));
await tujuan.fill("Dramaga");
await page.waitForTimeout(700);
await page.getByRole("button", { name: /Dramaga/ }).first().click().catch(() => fail.push("search Dramaga"));
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2000);
const hops2 = await page.locator("body").innerText();
if (/Dramaga/i.test(hops2) && /km/i.test(hops2)) ok.push("C04 Maja→Dramaga");
else fail.push("sim C04 failed");

await page.screenshot({ path: "/workspace/screenshots/krl-sim.png" });

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
