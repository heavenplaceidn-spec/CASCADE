#!/usr/bin/env node
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);
await page.addInitScript(() => {
  try {
    sessionStorage.setItem("cascade-splash-v8", "1");
  } catch {}
});
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
const startBtn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await startBtn.count()) await startBtn.click({ force: true }).catch(() => {});
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(2500);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return;
  const checked = await lab.locator("input").first().isChecked();
  if (checked !== wantOn) await lab.click();
}

await toggleIf("KRL", false);
await toggleIf("TransJakarta", false);
await toggleIf("Jaringan LRT", false);
await toggleIf("Jaringan MRT", false);
await toggleIf("Masterplan - acuan", false);
await toggleIf("Jalan - konteks", false);
await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(800);

const casSelect = page.locator('select[aria-label="Filter koridor usulan CASCADE"]');
await casSelect.selectOption("CAS-MRT-C01").catch(() => {});
await page.waitForTimeout(1800);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("candidate");
  const stops = map.querySourceFeatures("cascade-stops");
  const of = (rid) => feats.filter((f) => (f.properties?.route_id || f.properties?.id) === rid);
  const st = (rid) =>
    stops
      .filter((f) => f.properties?.route_id === rid)
      .map((f) => f.properties?.stop_name || f.properties?.name);
  return {
    ids: [...new Set(feats.map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))].sort(),
    mainStops: st("CAS-MRT-C01"),
    branchStops: st("CAS-MRT-C01-A"),
    br02Stops: st("CAS-MRT-C01-BR02"),
    color: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
  };
});
console.log("MAP", JSON.stringify(info, null, 2));

async function shotAt(lon, lat, zoom, path) {
  await page.evaluate(([ln, lt, z]) => window.__CASCADE_MAP.jumpTo({ center: [ln, lt], zoom: z }), [lon, lat, zoom]);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `/workspace/screenshots/${path}` });
  console.log("SHOT", path);
}

await page.screenshot({ path: "/workspace/screenshots/mrt-intent-overview.png" });
await shotAt(106.76, -6.30, 12.0, "mrt-lebak-ciputat.png");
await shotAt(106.747, -6.312, 13.4, "mrt-ciputat-split.png");
await shotAt(106.742, -6.405, 13.0, "mrt-parung-bend.png");
await shotAt(106.764, -6.400, 13.3, "mrt-sawangan-split.png");
await shotAt(106.79, -6.32, 12.4, "mrt-fatmawati-branch.png");
await shotAt(106.83, -6.37, 12.8, "mrt-margonda.png");
await shotAt(106.865, -6.35, 12.4, "mrt-cibubur-raya-bogor.png");
await shotAt(106.862, -6.313, 14.0, "mrt-cijantung.png");
await shotAt(106.875, -6.29, 12.6, "mrt-kr-pgc.png");
await shotAt(106.86, -6.27, 13.4, "mrt-pgc-condet.png");
await shotAt(106.86, -6.24, 13.0, "mrt-condet-dewi-sartika.png");
await shotAt(106.855, -6.21, 13.4, "mrt-manggarai-matraman.png");
await shotAt(106.858, -6.193, 13.6, "mrt-salemba-pramuka.png");
await shotAt(106.845, -6.16, 12.8, "mrt-senen-gunung-sahari.png");
await shotAt(106.842, -6.14, 12.6, "mrt-ancol-terminus.png");
await shotAt(106.70, -6.33, 12.2, "mrt-br02-bsd.png");

await casSelect.selectOption("CAS-MRT-C01-A").catch(() => {});
await page.waitForTimeout(800);
await shotAt(106.79, -6.33, 12.2, "mrt-c01a-only.png");

await browser.close();
console.log("DONE");
