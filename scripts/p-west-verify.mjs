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
await casSelect.selectOption("krl").catch(() => {});
await page.waitForTimeout(1200);

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
    n: name("KRL-C03-N"),
    s: name("KRL-C03-S"),
    br02: name("CAS-MRT-C01-BR02"),
    nStops: st("KRL-C03-N"),
    sStops: st("KRL-C03-S"),
    brStops: st("CAS-MRT-C01-BR02"),
    mrtMain: name("CAS-MRT-C01"),
    fat: name("CAS-MRT-C01-A"),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));

await page.screenshot({ path: "/workspace/screenshots/west-krl-all.png" });

async function shotAt(lon, lat, zoom, path) {
  await page.evaluate(([ln, lt, z]) => window.__CASCADE_MAP.jumpTo({ center: [ln, lt], zoom: z }), [lon, lat, zoom]);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `/workspace/screenshots/${path}` });
  console.log("SHOT", path);
}

await shotAt(106.63, -6.177, 13.4, "west-tangerang-split.png");
await shotAt(106.56, -6.15, 12.6, "west-kutabumi.png");
await shotAt(106.515, -6.08, 12.2, "west-rajeg-mauk.png");
await shotAt(106.57, -6.24, 12.4, "west-curug-legok.png");
await shotAt(106.569, -6.344, 13.2, "west-parung-panjang.png");

await casSelect.selectOption("CAS-MRT-C01").catch(() => {});
await page.waitForTimeout(1200);
await shotAt(106.70, -6.32, 12.0, "west-mrt-bsd-overview.png");
await shotAt(106.747, -6.312, 13.2, "west-ciputat-branch.png");
await shotAt(106.715, -6.346, 13.0, "west-siliwangi.png");
await shotAt(106.682, -6.329, 13.4, "west-taman-kota-2.png");
await shotAt(106.675, -6.315, 13.2, "west-rawa-buntu.png");
await shotAt(106.645, -6.300, 13.0, "west-bsd-ice.png");

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li, label, span")].map((el) => el.textContent || "").join("\n");
  return {
    krlN: /KRL-C03-N/.test(texts),
    krlS: /KRL-C03-S/.test(texts),
    br02: /CAS-MRT-C01-BR02/.test(texts),
    fat: /CAS-MRT-C01-A/.test(texts),
    main: /CAS-MRT-C01/.test(texts),
    mauk: /Mauk/i.test(texts),
    ice: /ICE BSD/i.test(texts),
  };
});
console.log("PANEL", panel);

await browser.close();
