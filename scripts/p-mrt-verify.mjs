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
await page.waitForTimeout(1500);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("candidate");
  const stops = map.querySourceFeatures("cascade-stops");
  const of = (rid) => feats.filter((f) => (f.properties?.route_id || f.properties?.id) === rid);
  const name = (rid) => [...new Set(of(rid).map((f) => f.properties?.name))];
  const st = (rid) => stops.filter((f) => f.properties?.route_id === rid).map((f) => f.properties?.stop_name || f.properties?.name);
  return {
    color: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
    ids: [...new Set(feats.map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))].sort(),
    main: name("CAS-MRT-C01"),
    branch: name("CAS-MRT-C01-A"),
    mainStops: st("CAS-MRT-C01"),
    branchStops: st("CAS-MRT-C01-A"),
    tj07: name("CAS-TJ07"),
    lrt02: name("CAS-LRT-C02"),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));

await page.screenshot({ path: "/workspace/screenshots/mrt-cas-c01-all.png" });
console.log("SHOT overview");

async function shotAt(lon, lat, zoom, path) {
  await page.evaluate(([ln, lt, z]) => window.__CASCADE_MAP.jumpTo({ center: [ln, lt], zoom: z }), [lon, lat, zoom]);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `/workspace/screenshots/${path}` });
  console.log("SHOT", path);
}

await shotAt(106.76, -6.30, 12.2, "mrt-lebak-bulus-ciputat.png");
await shotAt(106.74, -6.41, 12.4, "mrt-parung-sawangan.png");
await shotAt(106.764, -6.400, 13.2, "mrt-sawangan-split.png");
await shotAt(106.79, -6.32, 12.6, "mrt-cinere-fatmawati.png");
await shotAt(106.83, -6.37, 12.8, "mrt-margonda.png");
await shotAt(106.865, -6.35, 12.2, "mrt-raya-bogor-cibubur.png");
await shotAt(106.87, -6.31, 12.6, "mrt-kampung-rambutan-pgc.png");
await shotAt(106.86, -6.25, 12.8, "mrt-pgc-condet-melayu.png");
await shotAt(106.852, -6.276, 14.0, "mrt-condet.png");
await shotAt(106.85, -6.21, 13.0, "mrt-manggarai.png");
await shotAt(106.845, -6.15, 12.4, "mrt-senen-ancol.png");
await shotAt(106.792, -6.292, 13.4, "mrt-fatmawati-branch.png");

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li, label, span")].map((el) => el.textContent || "").join("\n");
  return {
    mrtMain: /CAS-MRT-C01[\s\S]{0,40}Ancol/i.test(texts),
    mrtBranch: /CAS-MRT-C01-A[\s\S]{0,40}Fatmawati/i.test(texts),
    condet: /Condet/i.test(texts),
    kramatJatiStation: /Kramat Jati/i.test(texts),
    tj07: /CAS-TJ07/.test(texts),
    lrt02: /CAS-LRT-C02/.test(texts),
  };
});
console.log("PANEL", panel);

await browser.close();
