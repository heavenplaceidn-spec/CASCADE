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
await page.waitForTimeout(3000);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
  await page.waitForTimeout(200);
}

await toggleIf("KRL", true);
await toggleIf("TransJakarta", true);
await toggleIf("Jaringan LRT", true);
await toggleIf("Jaringan MRT", true);
await toggleIf("Masterplan - acuan", true);
await page.waitForTimeout(1500);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const names = (src, cid) =>
    [...new Set(map.querySourceFeatures(src).filter((f) => !cid || f.properties?.corridor_id === cid).map((f) => f.properties?.name).filter(Boolean))].sort();
  const srcN = (id) => (map.getSource(id) ? map.querySourceFeatures(id).length : -1);
  const byCid = {};
  for (const f of map.querySourceFeatures("masterplan-stops")) {
    const c = f.properties?.corridor_id;
    if (!c) continue;
    byCid[c] = (byCid[c] || 0) + 1;
  }
  const lineIds = [...new Set(map.querySourceFeatures("masterplan").map((f) => f.properties?.id))];
  return {
    mpColor: paint("masterplan-line-dash", "line-color"),
    mpSolid: paint("masterplan-line-solid", "line-color"),
    krl: paint("krl-existing-line", "line-color"),
    tj: paint("tj-existing-line", "line-color"),
    lrt: paint("lrt-existing-line", "line-color"),
    mrt: paint("mrt-existing-line", "line-color"),
    layers: (map.getStyle()?.layers || []).map((l) => l.id).filter((id) => /masterplan|krl|tj|lrt|mrt|candidate/i.test(id)),
    lineIds,
    stopByCid: byCid,
    outerNames: names("masterplan-stops", "OUTER_RING_RAIL"),
    lrt09: names("masterplan-stops", "LRT_09"),
    bogor: names("masterplan-stops", "LRT_BOGOR"),
    mrt3n: names("masterplan-stops", "MRT_3"),
    hasPasarMinggu: names("masterplan-stops").includes("Pasar Minggu"),
    hasCandidate: srcN("candidate") > 0,
  };
});
console.log("INFO", JSON.stringify(info, null, 2));

async function selectMp(label, shot) {
  const item = page.locator("button").filter({ hasText: label }).first();
  if (await item.count()) await item.click();
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `/workspace/screenshots/${shot}.png` });
}

await selectMp("Outer Ring", "p16-outer-stn");
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  map.easeTo({ center: [106.94, -6.32], zoom: 11.2, duration: 0 });
});
await page.waitForTimeout(800);
await page.screenshot({ path: "/workspace/screenshots/p16-outer-stn-zoom.png" });

await selectMp("LRT 09", "p16-lrt09");
await selectMp("LRT Bogor", "p16-lrt-bogor-stn");
await selectMp("MRT East-West", "p16-mrt3-stn");

// click a station
const hit = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const f = map.querySourceFeatures("masterplan-stops").find((x) => x.properties?.name === "Cileungsi");
  if (!f) return { miss: true };
  const p = map.project(f.geometry.coordinates);
  return { x: p.x, y: p.y, name: f.properties.name };
});
if (!hit.miss) {
  await page.mouse.click(hit.x, hit.y);
  await page.waitForTimeout(400);
}
const popup = await page.locator(".cascade-panel").filter({ hasText: /Cileungsi|Koridor|indikatif|Interchange/ }).first().innerText().catch(() => "");
console.log("POPUP", popup.slice(0, 500));
await page.screenshot({ path: "/workspace/screenshots/p16-stn-popup.png" });

await page.getByText("Analisis", { exact: true }).click();
await page.waitForTimeout(600);
await page.screenshot({ path: "/workspace/screenshots/p16-analisis-stn.png" });

console.log("DONE");
await browser.close();
