import { chromium } from "playwright";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(60000);
await page.addInitScript(() => { try { sessionStorage.setItem("cascade-splash-v8", "1"); } catch {} });
await page.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" });
const btn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await btn.count()) await btn.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());
await page.waitForTimeout(3500);

// turn off TJ for KRL visual
const tjLabel = page.locator("label").filter({ hasText: /^TransJakarta$/ });
if (await tjLabel.count()) {
  const checked = await tjLabel.locator("input").isChecked();
  if (checked) await tjLabel.click();
}
await page.waitForTimeout(400);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const srcN = (id) => map.querySourceFeatures(id).length;
  const layers = (map.getStyle()?.layers || []).map((l) => l.id).filter((id) => /krl|tj|road|stop/i.test(id));
  return {
    zoom: map.getZoom(),
    krlColor: paint("krl-existing-line", "line-color"),
    krlStop: paint("krl-existing-stop", "circle-color"),
    tjColor: paint("tj-existing-line", "line-color"),
    roadColor: paint("roads", "line-color"),
    layers,
    src: { krl: srcN("krl"), krlStops: srcN("krl-stops"), tj: srcN("tj"), tjStops: srcN("tj-stops") },
  };
});
console.log("INFO", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/p14-krl-all.png" });

async function selectLine(value, shot) {
  await page.selectOption('select[aria-label="Filter lintasan KRL"]', value);
  await page.waitForTimeout(1600);
  const d = await page.evaluate(() => {
    const map = window.__CASCADE_MAP;
    const line = map.queryRenderedFeatures({ layers: map.getLayer("krl-existing-line") ? ["krl-existing-line"] : [] });
    const stops = map.queryRenderedFeatures({ layers: map.getLayer("krl-existing-stop") ? ["krl-existing-stop"] : [] });
    const names = [...new Set(stops.map((f) => f.properties?.name).filter(Boolean))];
    return {
      zoom: map.getZoom(),
      center: map.getCenter(),
      lineN: line.length,
      lineId: line[0]?.properties?.id,
      lineName: line[0]?.properties?.name,
      stopNames: names.sort(),
      color: map.getPaintProperty("krl-existing-line", "line-color"),
    };
  });
  console.log(shot, JSON.stringify(d));
  await page.screenshot({ path: `/workspace/screenshots/${shot}.png` });
  return d;
}

await selectLine("B", "p14-bogor");
await selectLine("R", "p14-rangkas");
await selectLine("C", "p14-cikarang");
await selectLine("T", "p14-tangerang");
await selectLine("TP", "p14-priok");

// zoom Bogor Citayam for Nambo + Gunung Putri check
await page.selectOption('select[aria-label="Filter lintasan KRL"]', "B");
await page.waitForTimeout(800);
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.83, -6.46], zoom: 12.4, duration: 0 }));
await page.waitForTimeout(1200);
const nambo = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const stops = map.queryRenderedFeatures({ layers: ["krl-existing-stop"] });
  const names = [...new Set(stops.map((s) => s.properties?.name))];
  const src = map.querySourceFeatures("krl-stops").map((s) => s.properties?.name);
  return { rendered: names.sort(), hasGunungPutri: src.includes("Gunung Putri"), hasPondokRajeg: src.includes("Pondok Rajeg"), hasNambo: src.includes("Nambo") };
});
console.log("NAMBO_AREA", JSON.stringify(nambo));
await page.screenshot({ path: "/workspace/screenshots/p14-nambo.png" });

// Jatake
await page.selectOption('select[aria-label="Filter lintasan KRL"]', "R");
await page.waitForTimeout(600);
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.6056, -6.3352], zoom: 13.2, duration: 0 }));
await page.waitForTimeout(1000);
const jatake = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const stops = map.queryRenderedFeatures({ layers: ["krl-existing-stop"] });
  return { names: [...new Set(stops.map((s) => s.properties?.name))].sort() };
});
console.log("JATAKE_AREA", JSON.stringify(jatake));
await page.screenshot({ path: "/workspace/screenshots/p14-jatake.png" });

// click a station
const click = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const f = map.queryRenderedFeatures({ layers: ["krl-existing-stop"] }).find((x) => x.properties?.name === "Jatake")
    || map.queryRenderedFeatures({ layers: ["krl-existing-stop"] })[0];
  if (!f || f.geometry.type !== "Point") return { n: 0 };
  const p = map.project(f.geometry.coordinates);
  return { n: 1, name: f.properties?.name, p };
});
console.log("CLICK", click);
if (click.p) {
  await page.mouse.click(click.p.x, click.p.y);
  await page.waitForTimeout(500);
}
const popup = await page.locator(".cascade-panel").filter({ hasText: /Lintasan|Kode stasiun|Jatake|Stasiun/ }).first().innerText().catch(() => "none");
console.log("POPUP", popup.slice(0, 400));
await page.screenshot({ path: "/workspace/screenshots/p14-halte.png" });

// toggle KRL off
await page.locator("label").filter({ hasText: /^KRL$/ }).click();
await page.waitForTimeout(400);
const off = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return {
    line: map.queryRenderedFeatures({ layers: map.getLayer("krl-existing-line") ? ["krl-existing-line"] : [] }).length,
    stop: map.queryRenderedFeatures({ layers: map.getLayer("krl-existing-stop") ? ["krl-existing-stop"] : [] }).length,
    src: map.querySourceFeatures("krl").length,
  };
});
console.log("KRL_OFF", off);
await page.screenshot({ path: "/workspace/screenshots/p14-krl-off.png" });

// analisis
await page.getByRole("link", { name: "Analisis" }).click();
await page.waitForTimeout(1000);
await page.screenshot({ path: "/workspace/screenshots/p14-analisis.png" });

await browser.close();
