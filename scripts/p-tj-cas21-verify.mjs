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
await page.waitForTimeout(1200);

const ok = [];
const fail = [];

const idsBefore = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return [...new Set(map.querySourceFeatures("candidate").map((f) => f.properties?.route_id || f.properties?.id))];
});
if (idsBefore.includes("KRL-C04") && idsBefore.includes("MRT-CASCADE-02")) ok.push("map KRL-C04+MRT kept");
else fail.push("rail missing before TJ filter " + idsBefore.filter((x) => /KRL|MRT/.test(String(x))).join(","));

await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(800);
const side = await page.locator("button").evaluateAll((els) =>
  els.map((e) => e.textContent?.replace(/\s+/g, " ").trim()).filter(Boolean).join(" | "),
);
for (const name of [
  "Petojo – Pulo Gebang",
  "Pinang Ranti – Lebak Bulus",
  "Perpanjangan Koridor 7: Trikora – UI",
  "Pinang Ranti – Marunda Center",
  "Pinang Ranti – Tanjung Priok",
  "UI – Galunggung",
  "Perpanjangan Koridor 6: Ragunan – Jagakarsa",
  "Jagakarsa – Grogol Reformasi",
  "Bumi Perkemahan Cibubur – Blok M",
]) {
  if (side.includes(name)) ok.push("sidebar " + name);
  else fail.push("sidebar missing " + name);
}
if (side.includes("CAS-TJ02") || side.includes("Pulo Gadung – Transera")) fail.push("old CAS-TJ still in sidebar");
else ok.push("old CAS-TJ removed");

const ids = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return [...new Set(map.querySourceFeatures("candidate").map((f) => f.properties?.route_id || f.properties?.id))];
});
for (const id of ["CASTJ15", "CASTJ16", "CASTJ07-EXT", "CASTJ17", "CASTJ18", "CASTJ19", "CASTJ06-EXT", "CASTJ20", "CASTJ21"]) {
  if (ids.includes(id)) ok.push("map " + id);
  else fail.push("map missing " + id);
}
if (ids.some((id) => String(id).startsWith("CAS-TJ"))) fail.push("old CAS-TJ still on map " + ids.filter((id) => String(id).startsWith("CAS-TJ")).join(","));
else ok.push("map old CAS-TJ gone");

const c21 = page.locator("button").filter({ hasText: "Bumi Perkemahan Cibubur" });
if (await c21.count()) {
  await c21.first().click();
  await page.waitForTimeout(1400);
  const b = await page.evaluate(() => {
    const x = window.__CASCADE_MAP.getBounds();
    return { w: x.getWest(), e: x.getEast(), s: x.getSouth(), n: x.getNorth() };
  });
  if (b.e > 106.88 && b.w < 106.85) ok.push("fit CAS21");
  else fail.push("fit CAS21 " + JSON.stringify(b));
} else fail.push("cannot click CAS21");
await page.screenshot({ path: "/workspace/screenshots/tj-cas21.png" });

await page.getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(400);
async function pick(label, q, want) {
  const input = page.getByLabel(label);
  await input.fill(q);
  await page.waitForTimeout(700);
  const btn = page.getByRole("button", { name: new RegExp(want, "i") });
  if (await btn.count()) {
    await btn.first().click();
    return true;
  }
  fail.push("search " + want);
  return false;
}
await pick("Asal", "Trikora", "Trikora");
await pick("Tujuan", "UI", "UI");
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2200);
const hops7 = await page.evaluate(() => window.__CASCADE?.getState?.()?.simResult?.hops || []);
if (hops7.join(" ").match(/UI/i) && hops7.join(" ").match(/Trikora/i)) ok.push("sim CASTJ07 " + hops7.join(" > "));
else fail.push("sim CASTJ07 " + JSON.stringify(hops7));

await pick("Asal", "Pinang Ranti", "Pinang Ranti");
await pick("Tujuan", "Lebak Bulus", "Lebak Bulus");
await page.getByRole("button", { name: /^Jalankan$/ }).click();
await page.waitForTimeout(2200);
const hops = await page.evaluate(() => window.__CASCADE?.getState?.()?.simResult?.hops || []);
if (hops.join(" ").match(/Lebak Bulus/i)) ok.push("sim CASTJ16 " + hops.join(" > "));
else fail.push("sim CASTJ16 " + JSON.stringify(hops));

await page.getByRole("link", { name: "Analisis", exact: true }).first().click();
await page.waitForTimeout(600);
const body = await page.locator("body").innerText();
if (/CASTJ21|Cibubur|elevated|pelebaran/i.test(body)) ok.push("analysis has TJ");
else ok.push("analysis loaded");

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
