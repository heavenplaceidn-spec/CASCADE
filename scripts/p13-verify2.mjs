import { chromium } from "playwright";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);
await page.addInitScript(() => { try { sessionStorage.setItem("cascade-splash-v8", "1"); } catch {} });
await page.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" });
const btn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await btn.count()) await btn.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());
await page.waitForTimeout(3000);

// Koridor 1 then zoom in
await page.getByRole("button", { name: /Koridor 1/i }).first().click();
await page.waitForTimeout(1600);
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ zoom: 14.2, duration: 0 }));
await page.waitForTimeout(1200);

const stopClick = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.queryRenderedFeatures({ layers: ["tj-existing-stop"] });
  if (!feats.length) return { n: 0 };
  const f = feats[0];
  const ll = f.geometry.type === "Point" ? f.geometry.coordinates : null;
  const p = ll ? map.project(ll) : null;
  return { n: feats.length, name: f.properties?.name, koridor: f.properties?.koridor_label, prev: f.properties?.prev_stop, next: f.properties?.next_stop, p };
});
console.log("STOPS", JSON.stringify(stopClick));
if (stopClick.p) {
  await page.mouse.click(stopClick.p.x, stopClick.p.y);
  await page.waitForTimeout(500);
}
const popupText = await page.locator(".cascade-panel").filter({ hasText: /Halte sebelumnya|Koridor/ }).nth(0).innerText().catch(() => "none");
console.log("POPUP", popupText.slice(0, 500));
await page.screenshot({ path: "/workspace/screenshots/p13-halte.png" });

// Toggle TransJakarta off
await page.getByText("TransJakarta", { exact: true }).click();
await page.waitForTimeout(400);
const hidden = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const line = map.queryRenderedFeatures({ layers: map.getLayer("tj-existing-line") ? ["tj-existing-line"] : [] }).length;
  const stop = map.queryRenderedFeatures({ layers: map.getLayer("tj-existing-stop") ? ["tj-existing-stop"] : [] }).length;
  const srcN = map.querySourceFeatures("tj").length;
  return { line, stop, srcN };
});
console.log("TJ OFF", hidden);
await page.screenshot({ path: "/workspace/screenshots/p13-tj-off.png" });

// back on, K3 and K14
await page.getByText("TransJakarta", { exact: true }).click();
await page.waitForTimeout(300);
await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "3");
await page.waitForTimeout(1600);
await page.screenshot({ path: "/workspace/screenshots/p13-k3.png" });
await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "14");
await page.waitForTimeout(1600);
await page.screenshot({ path: "/workspace/screenshots/p13-k14.png" });
await page.selectOption('select[aria-label="Filter koridor TransJakarta"]', "4");
await page.waitForTimeout(1600);
await page.screenshot({ path: "/workspace/screenshots/p13-k4.png" });

await browser.close();
