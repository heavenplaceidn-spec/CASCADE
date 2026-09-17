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
  const st = (rid) =>
    stops
      .filter((f) => f.properties?.route_id === rid)
      .map((f) => f.properties?.stop_name || f.properties?.name);
  return {
    color: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
    ids: [...new Set(feats.map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))].sort(),
    main: name("CAS-MRT-C01"),
    branch: name("CAS-MRT-C01-A"),
    br02: name("CAS-MRT-C01-BR02"),
    mainStops: st("CAS-MRT-C01"),
    forbidden: st("CAS-MRT-C01").filter((n) =>
      /Kampung Rambutan|Ciracas|Pasar Rebo|Cibubur|Cimanggis/.test(n || "")
    ),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));

async function shotAt(lon, lat, zoom, path) {
  await page.evaluate(([ln, lt, z]) => window.__CASCADE_MAP.jumpTo({ center: [ln, lt], zoom: z }), [lon, lat, zoom]);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `/workspace/screenshots/${path}` });
  console.log("SHOT", path);
}

await page.screenshot({ path: "/workspace/screenshots/mrt-cas-c01-all.png" });
await shotAt(106.83, -6.37, 12.8, "mrt-margonda.png");
await shotAt(106.843, -6.365, 13.4, "mrt-kelapa-dua.png");
await shotAt(106.850, -6.325, 13.0, "mrt-ra-fadilah.png");
await shotAt(106.862, -6.312, 13.2, "mrt-cijantung.png");
await shotAt(106.882, -6.310, 13.0, "mrt-kampung-rambutan-pgc.png");
await shotAt(106.868, -6.348, 12.4, "mrt-raya-bogor-cibubur.png");
await shotAt(106.856, -6.277, 13.4, "mrt-condet.png");
await shotAt(106.866, -6.262, 13.0, "mrt-pgc-condet-melayu.png");
await shotAt(106.866, -6.192, 13.2, "mrt-pramuka.png");
await shotAt(106.845, -6.15, 12.4, "mrt-senen-ancol.png");
await shotAt(106.792, -6.292, 13.2, "mrt-fatmawati-branch.png");
await shotAt(106.747, -6.312, 13.0, "mrt-lebak-bulus-ciputat.png");

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li, label, span")].map((el) => el.textContent || "").join("\n");
  return {
    mrtMain: /CAS-MRT-C01/.test(texts),
    mrtBranch: /CAS-MRT-C01-A/.test(texts),
    br02: /CAS-MRT-C01-BR02/.test(texts),
    condet: /Condet/i.test(texts),
    kelapa: /Kelapa Dua/i.test(texts),
    rambutan: /Kampung Rambutan/i.test(texts),
    ciracas: /Ciracas/i.test(texts),
  };
});
console.log("PANEL", panel);

await browser.close();
