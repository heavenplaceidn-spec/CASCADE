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
await page.waitForTimeout(3500);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
  await page.waitForTimeout(250);
  return { name, wantOn, was: checked };
}

// Isolate LRT: KRL/TJ off, LRT on, MRT off
await toggleIf("KRL", false);
await toggleIf("TransJakarta", false);
await toggleIf("Jaringan LRT", true);
await toggleIf("Jaringan MRT", false);
await page.waitForTimeout(600);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const srcN = (id) => (map.getSource(id) ? map.querySourceFeatures(id).length : -1);
  const names = (src) =>
    [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.name).filter(Boolean))].sort();
  return {
    zoom: map.getZoom(),
    lrtColor: paint("lrt-existing-line", "line-color"),
    lrtStop: paint("lrt-existing-stop", "circle-color"),
    mrtColor: paint("mrt-existing-line", "line-color"),
    mrtStop: paint("mrt-existing-stop", "circle-color"),
    krlColor: paint("krl-existing-line", "line-color"),
    tjColor: paint("tj-existing-line", "line-color"),
    roadColor: paint("roads", "line-color"),
    layers: (map.getStyle()?.layers || []).map((l) => l.id).filter((id) => /lrt|mrt|krl|tj|road|stop/i.test(id)),
    src: {
      lrt: srcN("lrt"),
      lrtStops: srcN("lrt-stops"),
      mrt: srcN("mrt"),
      mrtStops: srcN("mrt-stops"),
      krl: srcN("krl"),
      tj: srcN("tj"),
    },
    lrtNames: names("lrt-stops"),
    mrtNames: names("mrt-stops"),
  };
});
console.log("INFO", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/p15-lrt-all.png" });

async function selectLrt(value, shot) {
  await page.selectOption('select[aria-label="Filter lintasan LRT"]', value);
  await page.waitForTimeout(1600);
  const d = await page.evaluate(() => {
    const map = window.__CASCADE_MAP;
    const line = map.queryRenderedFeatures({ layers: map.getLayer("lrt-existing-line") ? ["lrt-existing-line"] : [] });
    const stops = map.queryRenderedFeatures({ layers: map.getLayer("lrt-existing-stop") ? ["lrt-existing-stop"] : [] });
    const srcStops = map.querySourceFeatures("lrt-stops").map((f) => f.properties?.name).filter(Boolean);
    const filtered = map.getFilter?.("lrt-existing-stop");
    return {
      zoom: map.getZoom(),
      center: map.getCenter(),
      lineN: line.length,
      lineId: line[0]?.properties?.id,
      lineName: line[0]?.properties?.name,
      stopNames: [...new Set(stops.map((f) => f.properties?.name).filter(Boolean))].sort(),
      srcStopNames: [...new Set(srcStops)].sort(),
      color: map.getPaintProperty("lrt-existing-line", "line-color"),
      filter: filtered,
    };
  });
  console.log(shot, JSON.stringify(d));
  await page.screenshot({ path: `/workspace/screenshots/${shot}.png` });
  return d;
}

await selectLrt("CB", "p15-cibubur");
await selectLrt("BK", "p15-bekasi");
await selectLrt("all", "p15-lrt-all2");

// Cawang click
await page.selectOption('select[aria-label="Filter lintasan LRT"]', "all");
await page.waitForTimeout(400);
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.8712, -6.2459], zoom: 14.2, duration: 0 }));
await page.waitForTimeout(1200);
const cawang = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const stops = map.queryRenderedFeatures({ layers: ["lrt-existing-stop"] });
  const f = stops.find((x) => x.properties?.name === "Cawang") || stops[0];
  if (!f || f.geometry.type !== "Point") return { n: 0, names: [...new Set(stops.map((s) => s.properties?.name))] };
  const p = map.project(f.geometry.coordinates);
  return { n: 1, name: f.properties?.name, type: f.properties?.station_type, lines: f.properties?.line_name, p };
});
console.log("CAWANG", JSON.stringify(cawang));
if (cawang.p) {
  await page.mouse.click(cawang.p.x, cawang.p.y);
  await page.waitForTimeout(500);
}
const popupCawang = await page
  .locator(".cascade-panel")
  .filter({ hasText: /Cawang|Lintasan|Simpul/ })
  .first()
  .innerText()
  .catch(() => "none");
console.log("POPUP_CAWANG", popupCawang.slice(0, 500));
await page.screenshot({ path: "/workspace/screenshots/p15-cawang.png" });

// Dukuh Atas LRT
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.8255, -6.2048], zoom: 14.4, duration: 0 }));
await page.waitForTimeout(1000);
const dukuhLrt = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const f = map.queryRenderedFeatures({ layers: ["lrt-existing-stop"] }).find((x) => String(x.properties?.name).includes("Dukuh Atas"));
  if (!f || f.geometry.type !== "Point") return { n: 0 };
  return { n: 1, name: f.properties?.name, p: map.project(f.geometry.coordinates) };
});
console.log("DUKUH_LRT", JSON.stringify(dukuhLrt));
if (dukuhLrt.p) {
  await page.mouse.click(dukuhLrt.p.x, dukuhLrt.p.y);
  await page.waitForTimeout(400);
}
const popupDukuhLrt = await page.locator(".cascade-panel").filter({ hasText: /Dukuh Atas/ }).first().innerText().catch(() => "none");
console.log("POPUP_DUKUH_LRT", popupDukuhLrt.slice(0, 400));
await page.screenshot({ path: "/workspace/screenshots/p15-dukuh-lrt.png" });

// LRT off
await page.locator("label").filter({ hasText: /^Jaringan LRT$/ }).click();
await page.waitForTimeout(400);
const lrtOff = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return {
    line: map.queryRenderedFeatures({ layers: map.getLayer("lrt-existing-line") ? ["lrt-existing-line"] : [] }).length,
    stop: map.queryRenderedFeatures({ layers: map.getLayer("lrt-existing-stop") ? ["lrt-existing-stop"] : [] }).length,
    src: map.querySourceFeatures("lrt").length,
  };
});
console.log("LRT_OFF", lrtOff);
await page.screenshot({ path: "/workspace/screenshots/p15-lrt-off.png" });

// MRT on
await toggleIf("Jaringan MRT", true);
await page.waitForTimeout(500);
await page.selectOption('select[aria-label="Filter lintasan MRT"]', "all");
await page.waitForTimeout(1600);
const mrtInfo = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const line = map.queryRenderedFeatures({ layers: map.getLayer("mrt-existing-line") ? ["mrt-existing-line"] : [] });
  const srcStops = map.querySourceFeatures("mrt-stops").map((f) => f.properties?.name).filter(Boolean);
  return {
    color: map.getPaintProperty("mrt-existing-line", "line-color"),
    stopColor: map.getPaintProperty("mrt-existing-stop", "circle-color"),
    lineN: line.length,
    lineId: line[0]?.properties?.id,
    srcStops: [...new Set(srcStops)],
    srcN: map.querySourceFeatures("mrt-stops").length,
  };
});
console.log("MRT", JSON.stringify(mrtInfo));
await page.screenshot({ path: "/workspace/screenshots/p15-mrt-all.png" });

await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.775, -6.289], zoom: 14.2, duration: 0 }));
await page.waitForTimeout(1000);
await page.screenshot({ path: "/workspace/screenshots/p15-lebak-bulus.png" });

await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.8228, -6.2008], zoom: 14.6, duration: 0 }));
await page.waitForTimeout(1000);
const dukuhMrt = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const f = map.queryRenderedFeatures({ layers: ["mrt-existing-stop"] }).find((x) => x.properties?.name === "Dukuh Atas");
  if (!f || f.geometry.type !== "Point") return { n: 0, names: map.queryRenderedFeatures({ layers: ["mrt-existing-stop"] }).map((s) => s.properties?.name) };
  return { n: 1, name: f.properties?.name, p: map.project(f.geometry.coordinates) };
});
console.log("DUKUH_MRT", JSON.stringify(dukuhMrt));
if (dukuhMrt.p) {
  await page.mouse.click(dukuhMrt.p.x, dukuhMrt.p.y);
  await page.waitForTimeout(400);
}
const popupDukuhMrt = await page.locator(".cascade-panel").filter({ hasText: /Dukuh Atas/ }).first().innerText().catch(() => "none");
console.log("POPUP_DUKUH_MRT", popupDukuhMrt.slice(0, 400));
await page.screenshot({ path: "/workspace/screenshots/p15-dukuh-mrt.png" });

await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.823, -6.192], zoom: 14.4, duration: 0 }));
await page.waitForTimeout(900);
await page.screenshot({ path: "/workspace/screenshots/p15-bundaran-hi.png" });

// All four modes
await toggleIf("KRL", true);
await toggleIf("TransJakarta", true);
await toggleIf("Jaringan LRT", true);
await toggleIf("Jaringan MRT", true);
await page.evaluate(() => window.__CASCADE_MAP.easeTo({ center: [106.82, -6.22], zoom: 12.2, duration: 0 }));
await page.waitForTimeout(1200);
const allModes = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  return {
    krl: paint("krl-existing-line", "line-color"),
    tj: paint("tj-existing-line", "line-color"),
    lrt: paint("lrt-existing-line", "line-color"),
    mrt: paint("mrt-existing-line", "line-color"),
    road: paint("roads", "line-color"),
    src: {
      krl: map.querySourceFeatures("krl").length,
      tj: map.querySourceFeatures("tj").length,
      lrt: map.querySourceFeatures("lrt").length,
      mrt: map.querySourceFeatures("mrt").length,
      lrtStops: map.querySourceFeatures("lrt-stops").length,
      mrtStops: map.querySourceFeatures("mrt-stops").length,
    },
  };
});
console.log("ALL_MODES", JSON.stringify(allModes));
await page.screenshot({ path: "/workspace/screenshots/p15-all-modes.png" });

await page.getByRole("link", { name: "Analisis" }).click();
await page.waitForTimeout(1200);
await page.screenshot({ path: "/workspace/screenshots/p15-analisis.png" });

await browser.close();
