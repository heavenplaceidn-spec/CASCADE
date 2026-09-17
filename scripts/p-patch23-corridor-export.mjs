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
await page.waitForTimeout(600);

const ok = [];
const fail = [];

async function expand(name) {
  const btn = page.getByRole("button", { name: new RegExp(`^${name}$`) });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
  await page.waitForTimeout(150);
}

async function openMode(group, mode) {
  await expand(group);
  const modes = page.getByRole("button", { name: new RegExp(`^${mode}$`) });
  const n = await modes.count();
  const idx = group === "CASCADE" ? 0 : group === "EXISTING" ? 1 : Math.min(2, n - 1);
  const btn = modes.nth(Math.max(0, idx));
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
  await page.waitForTimeout(250);
}

async function grab(id, extra = {}) {
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 20000 }),
    page.locator(`button[aria-label="Unduh GeoJSON ${id}"]`).click(),
  ]);
  const name = download.suggestedFilename();
  const fc = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
  const feats = fc.features || [];
  const ids = [...new Set(feats.map((f) => String(f.properties?.corridor_id || f.id || "")))];
  const g = feats[0]?.geometry;
  const p = feats[0]?.properties || {};
  const check = {
    file: name,
    type: fc.type,
    n: feats.length,
    ids,
    geom: g?.type,
    stations: p.station_count,
    names: String(p.station_names || ""),
    category: p.category,
    mode: p.mode,
  };
  const mixed = ids.some((x) => x && x !== id && x !== extra.allowId);
  const line = g?.type === "LineString" || g?.type === "MultiLineString";
  const hasNames = extra.allowEmptyStations || (Number(p.station_count) > 0 && check.names.includes("; ") || Number(p.station_count) >= 1);
  if (fc.type === "FeatureCollection" && feats.length >= 1 && !mixed && line && g.coordinates && hasNames && !/key=/i.test(JSON.stringify(p))) {
    ok.push(`${id} ${name} n=${feats.length} st=${p.station_count} geom=${g.type}`);
  } else fail.push(`${id} ${JSON.stringify(check)}`);
  if (extra.forbid && String(p.station_names).includes(extra.forbid)) fail.push(`${id} leaked station ${extra.forbid}`);
  if (extra.mustName && !String(p.station_names).includes(extra.mustName)) fail.push(`${id} missing station ${extra.mustName}`);
  if (extra.mustNotId && ids.includes(extra.mustNotId)) fail.push(`${id} contains ${extra.mustNotId}`);
  return { fc, p, ids, name };
}

await openMode("CASCADE", "TransJakarta");
const c24 = await grab("CASTJ24", { mustName: "Joglo", mustNotId: "CASTJ25", forbid: "Meruya Utara" });
const c25 = await grab("CASTJ25", { mustName: "Meruya", mustNotId: "CASTJ24" });
await grab("CASTJ22", { mustName: "Sawangan" });
await grab("CASTJ23", { mustName: "Pondok Labu" });
await grab("CASTJ26", { mustName: "Koja" });
await grab("CASTJ20", { mustName: "Jagakarsa" });
await grab("CASTJ06-EXT", { mustName: "Ragunan" });
await grab("CASTJ15", { mustName: "Petojo" });

await openMode("CASCADE", "KRL");
const n = await grab("KRL-C03-N", { mustName: "Mauk", mustNotId: "KRL-C03-S" });
await grab("KRL-C03-S", { mustName: "Bitung", mustNotId: "KRL-C03-N" });
await grab("KRL-C04", { mustName: "Dramaga" });

await openMode("CASCADE", "MRT");
await grab("MRT-CASCADE-01", { mustName: "Lebak Bulus" });
await grab("MRT-CASCADE-02", { mustName: "Depok Baru" });

await openMode("CASCADE", "LRT");
await grab("LRT-CASCADE-NEW-01", { mustName: "Dukuh Atas" });

await openMode("EXISTING", "TransJakarta");
await grab("tj-k1", { mustName: "Blok M" });

await openMode("EXISTING", "KRL");
await grab("krl-B", { mustName: "Bogor" });

await openMode("EXISTING", "LRT");
await grab("lrt-CB", { mustName: "Harjamukti" });

await openMode("EXISTING", "MRT");
await grab("mrt-NS", { mustName: "Lebak Bulus" });

await openMode("MASTERPLAN", "KRL");
await grab("KRL_PP_CITAYAM", { mustName: "Parung Panjang" });

await openMode("MASTERPLAN", "MRT");
await grab("MRT_2A", { mustName: "Bundaran HI" });

const legendLeft = await page.evaluate(() => {
  const p = [...document.querySelectorAll("p")].find((x) => x.textContent?.trim() === "LEGENDA");
  return p?.closest("div.cascade-panel")?.getBoundingClientRect().x ?? -1;
});
if (legendLeft >= 0 && legendLeft < 80) ok.push("legend untouched left");
else fail.push("legend moved " + legendLeft);

console.log("OK", ok);
console.log("FAIL", fail);
console.log("CASTJ24 names", c24.p.station_names);
console.log("CASTJ25 names", c25.p.station_names);
console.log("C03-N names head", String(n.p.station_names).slice(0, 80));
await browser.close();
if (fail.length) process.exit(1);
