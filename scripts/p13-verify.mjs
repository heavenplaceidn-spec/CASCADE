import { chromium } from "playwright";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);

await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.addInitScript(() => { try { sessionStorage.setItem("cascade-splash-v8", "1"); } catch {} });
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(2500);

const btn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await btn.count()) {
  await btn.click();
  await page.waitForTimeout(1500);
}

await page.waitForFunction(() => window.__CASCADE_MAP && window.__CASCADE_MAP.isStyleLoaded && window.__CASCADE_MAP.isStyleLoaded(), { timeout: 30000 }).catch(() => {});
await page.waitForTimeout(4000);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const src = (id) => {
    const s = map.getSource(id);
    if (!s) return { missing: true };
    const feats = map.querySourceFeatures(id);
    return { n: feats.length, sample: feats[0]?.properties || null };
  };
  const layers = map.getStyle()?.layers?.map((l) => l.id) || [];
  const tjColor = map.getLayer("tj-existing-line") ? map.getPaintProperty("tj-existing-line", "line-color") : null;
  const roadColor = map.getLayer("roads") ? map.getPaintProperty("roads", "line-color") : null;
  const stopColor = map.getLayer("tj-existing-stop") ? map.getPaintProperty("tj-existing-stop", "circle-color") : null;
  const vis = {
    tj: map.getLayoutProperty("tj-existing-line", "visibility") ?? "visible",
    roads: map.getLayoutProperty("roads", "visibility") ?? "visible",
  };
  return {
    zoom: map.getZoom(),
    center: map.getCenter(),
    tjColor,
    roadColor,
    stopColor,
    layers: layers.filter((id) => /tj|road|stop|krl|mrt|lrt|candidate|master/i.test(id)),
    src: {
      tj: src("tj"),
      tjStops: src("tj-stops"),
      roads: src("roads"),
      krl: src("krl"),
      stops: src("stops"),
    },
    vis,
  };
});
console.log("INFO", JSON.stringify(info, null, 2));

await page.screenshot({ path: "/workspace/screenshots/p13-explore.png", fullPage: false });

// Click Koridor 1
const k1 = page.getByRole("button", { name: /Koridor 1/i }).first();
await k1.click();
await page.waitForTimeout(1800);
const k1info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return { zoom: map.getZoom(), center: map.getCenter(), bounds: map.getBounds() };
});
console.log("K1", JSON.stringify(k1info));
await page.screenshot({ path: "/workspace/screenshots/p13-k1.png" });

// Click map center to try popup on line
const box = await page.locator('div[aria-label="Peta CASCADE Jabodetabek"]').boundingBox();
if (box) {
  await page.mouse.click(box.x + box.width * 0.42, box.y + box.height * 0.48);
  await page.waitForTimeout(600);
}
const popup1 = await page.locator(".cascade-panel").filter({ hasText: /Koridor|Halte|Sumber|Blok/ }).count();
console.log("popup-ish panels", popup1);
await page.screenshot({ path: "/workspace/screenshots/p13-k1-click.png" });

// Filter 9
await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "9");
await page.waitForTimeout(1800);
const k9 = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const tj = map.querySourceFeatures("tj");
  const shown = map.queryRenderedFeatures({ layers: map.getLayer("tj-existing-line") ? ["tj-existing-line"] : [] });
  return {
    zoom: map.getZoom(),
    center: map.getCenter(),
    rendered: shown.length,
    props: shown[0]?.properties || null,
  };
});
console.log("K9", JSON.stringify(k9));
await page.screenshot({ path: "/workspace/screenshots/p13-k9.png" });

await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "13");
await page.waitForTimeout(1800);
await page.screenshot({ path: "/workspace/screenshots/p13-k13.png" });

await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "12");
await page.waitForTimeout(1800);
await page.screenshot({ path: "/workspace/screenshots/p13-k12.png" });

await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "all");
await page.waitForTimeout(1500);
await page.screenshot({ path: "/workspace/screenshots/p13-all.png" });

await page.getByRole("link", { name: "Analisis" }).click();
await page.waitForTimeout(1200);
await page.screenshot({ path: "/workspace/screenshots/p13-analisis.png" });

await browser.close();
