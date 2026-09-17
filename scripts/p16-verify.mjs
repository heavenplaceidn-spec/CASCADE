import { chromium } from "playwright";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);
await page.addInitScript(() => {
  try {
    sessionStorage.setItem("cascade-splash-v8", "1");
  } catch {}
});
await page.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" });
const btn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await btn.count()) await btn.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());
await page.waitForTimeout(2800);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
  await page.waitForTimeout(200);
  return { name, wantOn, was: checked };
}

await toggleIf("KRL", true);
await toggleIf("TransJakarta", true);
await toggleIf("Jaringan LRT", true);
await toggleIf("Jaringan MRT", true);
await toggleIf("Masterplan - acuan", true);
await toggleIf("Jalan - konteks", true);
await page.waitForTimeout(1200);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const srcN = (id) => (map.getSource(id) ? map.querySourceFeatures(id).length : -1);
  const names = (src) =>
    [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.name).filter(Boolean))].sort();
  const ids = (src) => [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.id).filter(Boolean))];
  return {
    zoom: map.getZoom(),
    mpColorSolid: paint("masterplan-line-solid", "line-color"),
    mpColorDash: paint("masterplan-line-dash", "line-color"),
    mpStop: paint("masterplan-stop", "circle-color"),
    krlColor: paint("krl-existing-line", "line-color"),
    tjColor: paint("tj-existing-line", "line-color"),
    lrtColor: paint("lrt-existing-line", "line-color"),
    mrtColor: paint("mrt-existing-line", "line-color"),
    roadColor: paint("roads", "line-color"),
    layers: (map.getStyle()?.layers || []).map((l) => l.id),
    src: {
      masterplan: srcN("masterplan"),
      mpStops: srcN("masterplan-stops"),
      krl: srcN("krl"),
      tj: srcN("tj"),
      lrt: srcN("lrt"),
      mrt: srcN("mrt"),
    },
    mpIds: ids("masterplan"),
    mpStopNames: names("masterplan-stops"),
    hasPasarMinggu: names("masterplan-stops").includes("Pasar Minggu"),
  };
});
console.log("INFO", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/p16-all-modes.png" });

async function flyCorridor(id, shot, zoomWait = 1600) {
  const btn = page.locator("button").filter({ hasText: new RegExp(id) });
  if (await btn.count()) {
    await btn.first().click();
    await page.waitForTimeout(zoomWait);
  }
  await page.screenshot({ path: `/workspace/screenshots/${shot}` });
}

await flyCorridor("MRT 2A", "p16-mrt-2a.png");
await flyCorridor("MRT East-West", "p16-mrt-3.png", 1800);
await flyCorridor("MRT 4", "p16-mrt-4.png");
await flyCorridor("LRT Jakarta 1B", "p16-lrt-1b.png");
await flyCorridor("LRT Bogor", "p16-lrt-bogor.png", 1800);
await flyCorridor("Outer Ring", "p16-outer-ring.png", 1800);

// popup: click Thamrin station
await flyCorridor("MRT 2A", "p16-mrt-2a-again.png", 1400);
const clicked = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const hits = map.querySourceFeatures("masterplan-stops").filter((f) => f.properties?.name === "Thamrin");
  if (!hits.length) return { error: "no Thamrin" };
  const c = hits[0].geometry.coordinates;
  const pt = map.project(c);
  map.fire("click", { lngLat: { lng: c[0], lat: c[1] }, point: pt });
  return { lng: c[0], lat: c[1], x: pt.x, y: pt.y };
});
console.log("CLICK", JSON.stringify(clicked));
await page.waitForTimeout(600);
const popupText = await page.locator(".cascade-panel").filter({ hasText: /Thamrin|THAMRIN/i }).first().innerText().catch(() => "");
console.log("POPUP", popupText.slice(0, 400));
await page.screenshot({ path: "/workspace/screenshots/p16-popup.png" });

await toggleIf("Masterplan - acuan", false);
await page.waitForTimeout(400);
const off = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const srcN = (id) => {
    const s = map.getSource(id);
    if (!s) return -1;
    return map.querySourceFeatures(id).length;
  };
  return { mp: srcN("masterplan"), stops: srcN("masterplan-stops"), krl: srcN("krl") };
});
console.log("OFF", JSON.stringify(off));
await page.screenshot({ path: "/workspace/screenshots/p16-masterplan-off.png" });

await toggleIf("Masterplan - acuan", true);
await page.waitForTimeout(400);
await page.screenshot({ path: "/workspace/screenshots/p16-all.png" });

await page.click('a[href="/analisis"], button:has-text("Analisis"), a:has-text("Analisis")').catch(() => {});
const anal = page.getByRole("link", { name: /Analisis/i });
if (await anal.count()) {
  await anal.first().click();
  await page.waitForTimeout(800);
}
await page.screenshot({ path: "/workspace/screenshots/p16-analisis.png" });

await browser.close();
console.log("DONE");
