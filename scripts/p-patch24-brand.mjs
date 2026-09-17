#!/usr/bin/env node
import { chromium } from "playwright";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(80000);
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });

const ok = [];
const fail = [];

const hero = await page.locator("img.landing-hero").getAttribute("src");
if (hero && hero.includes("cascade-hero")) ok.push("loading hero " + hero);
else fail.push("no hero " + hero);

const seen = new Set();
for (let i = 0; i < 40; i++) {
  const t = await page.locator(".landing-ui p").first().textContent();
  const m = String(t || "").match(/(\d+)%/);
  if (m) seen.add(Number(m[1]));
  const btn = page.getByRole("button", { name: /Mulai Eksplorasi/ });
  if (await btn.isEnabled()) break;
  await page.waitForTimeout(250);
}
const steps = [...seen].sort((a, b) => a - b);
if (steps.some((n) => n % 10 === 0)) ok.push("progress " + steps.join(","));
else fail.push("progress " + JSON.stringify(steps));

const start = page.getByRole("button", { name: /Mulai Eksplorasi/ });
await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => /Mulai Eksplorasi/.test(x.textContent || ""));
  return b && !b.disabled;
}, { timeout: 70000 });
await start.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(400);

const oldCard = await page.evaluate(() => {
  const t = document.body.innerText;
  return /MAPID WebGIS Competition 2026/.test(t) && /Maps That Think/.test(t);
});
if (!oldCard) ok.push("old title card gone");
else fail.push("old title card still present");

const mark = page.locator("img.cascade-mark");
if ((await mark.count()) === 1) ok.push("one brand mark");
else fail.push("mark count " + (await mark.count()));
const markBox = await mark.boundingBox();
if (markBox && markBox.x < 80 && markBox.y < 80 && markBox.width < 420) ok.push("mark compact top-left");
else fail.push("mark box " + JSON.stringify(markBox));
const bg = await mark.evaluate((el) => getComputedStyle(el.parentElement).backgroundColor);
if (!/rgb\(18,\s*16,\s*28\)/.test(bg)) ok.push("no dark card behind mark");
else fail.push("card bg " + bg);

const legend = await page.evaluate(() => {
  const p = [...document.querySelectorAll("p")].find((x) => x.textContent?.trim() === "LEGENDA");
  const panel = p?.closest("div.cascade-panel")?.getBoundingClientRect();
  const gaya = document.querySelector('select[aria-label="Gaya MAPID"]')?.closest("div.cascade-panel")?.getBoundingClientRect();
  return { lx: panel?.x, ly: panel?.y, gy: gaya?.y, gx: gaya?.x };
});
if (legend.lx < 80) ok.push("legend left");
else fail.push("legend " + JSON.stringify(legend));
if (legend.gy > legend.ly) ok.push("gaya below legend");
else fail.push("gaya " + JSON.stringify(legend));

const layerRight = await page.evaluate(() => {
  const p = [...document.querySelectorAll("p")].find((x) => x.textContent?.trim() === "LAPISAN");
  const box = p?.closest("aside, div.cascade-panel")?.getBoundingClientRect();
  return box ? { x: box.x, r: box.right } : null;
});
if (layerRight && layerRight.x > 900) ok.push("layer panel right");
else fail.push("layer " + JSON.stringify(layerRight));

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(300);
if ((await page.locator("img.cascade-mark").count()) === 1) ok.push("tab simulasi brand");
else fail.push("simulasi brand missing");

await page.getByRole("link", { name: "Analisis", exact: true }).click();
await page.waitForTimeout(400);
if ((await page.locator("img.cascade-mark").count()) === 1) ok.push("tab analisis brand");
else fail.push("analisis brand missing");
const analysisRight = await page.evaluate(() => {
  const asides = [...document.querySelectorAll("aside")].map((a) => a.getBoundingClientRect());
  const vis = asides.filter((b) => b.width > 100 && b.height > 100);
  return vis.map((b) => ({ x: Math.round(b.x), w: Math.round(b.width) }));
});
if (analysisRight.some((b) => b.x > 900)) ok.push("analisis panel right " + JSON.stringify(analysisRight));
else fail.push("analisis not right " + JSON.stringify(analysisRight));

const legendStill = await page.evaluate(() => {
  const p = [...document.querySelectorAll("p")].find((x) => x.textContent?.trim() === "LEGENDA");
  return p?.closest("div.cascade-panel")?.getBoundingClientRect().x;
});
if (legendStill < 80) ok.push("legend still left on analisis");
else fail.push("legend moved on analisis " + legendStill);

console.log("OK", ok);
console.log("FAIL", fail);
await browser.close();
if (fail.length) process.exit(1);
