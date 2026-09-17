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
const startBtn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await startBtn.count()) await startBtn.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());
await page.waitForTimeout(2500);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
  await page.waitForTimeout(250);
  return { name, wantOn, was: checked };
}

await toggleIf("KRL", true);
await toggleIf("TransJakarta", true);
await toggleIf("Masterplan - acuan", false);
await toggleIf("CASCADE - usulan", false);
await toggleIf("Jalan - konteks", true);
await page.waitForTimeout(800);
await page.screenshot({ path: "/workspace/screenshots/p17-cascade-off.png" });

await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(1400);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const srcN = (id) => (map.getSource(id) ? map.querySourceFeatures(id).length : -1);
  const ids = (src) => [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))];
  const names = (src) => [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.stop_name || f.properties?.name).filter(Boolean))];
  return {
    zoom: map.getZoom(),
    casColor: paint("candidate", "line-color"),
    casDash: paint("candidate", "line-dasharray"),
    casStop: paint("cascade-stop", "circle-color"),
    tjColor: paint("tj-existing-line", "line-color"),
    krlColor: paint("krl-existing-line", "line-color"),
    mpColor: paint("masterplan-line-dash", "line-color"),
    layers: (map.getStyle()?.layers || []).map((l) => l.id),
    src: { candidate: srcN("candidate"), casStops: srcN("cascade-stops"), tj: srcN("tj"), krl: srcN("krl") },
    casIds: ids("candidate"),
    hasCas06: ids("candidate").includes("CAS-06"),
    hasHarjamukti: names("cascade-stops").some((n) => String(n).toLowerCase().includes("harjamukti")),
    stopSample: names("cascade-stops").slice(0, 20),
  };
});
console.log("INFO", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/p17-all.png" });

async function flyCas(id, shot) {
  const btn = page.locator("button").filter({ hasText: new RegExp(`^${id}\\b`) });
  if (await btn.count()) {
    await btn.first().click();
    await page.waitForTimeout(1600);
  } else {
    console.log("missing button", id);
  }
  await page.screenshot({ path: `/workspace/screenshots/${shot}` });
}

await flyCas("CAS-01", "p17-cas01.png");
await flyCas("CAS-02", "p17-cas02.png");
await flyCas("CAS-03", "p17-cas03.png");
await flyCas("CAS-04", "p17-cas04.png");
await flyCas("CAS-05", "p17-cas05.png");
await flyCas("CAS-07", "p17-cas07.png");
await flyCas("CAS-08", "p17-cas08.png");
await flyCas("CAS-09", "p17-cas09.png");
await flyCas("CAS-10", "p17-cas10.png");
await flyCas("CAS-11", "p17-cas11.png");
await flyCas("CAS-12", "p17-cas12.png");

// popup on CAS-07
await page.locator("button").filter({ hasText: /^CAS-07\b/ }).first().click();
await page.waitForTimeout(1200);
const mapBox = page.locator('[aria-label="Peta CASCADE Jabodetabek"]');
const box = await mapBox.boundingBox();
if (box) {
  await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.48);
  await page.waitForTimeout(700);
}
await page.screenshot({ path: "/workspace/screenshots/p17-popup.png" });

await page.getByRole("button", { name: /Analisis/i }).click();
await page.waitForTimeout(800);
await page.screenshot({ path: "/workspace/screenshots/p17-analisis.png" });

await page.getByRole("button", { name: /Simulasi/i }).click();
await page.waitForTimeout(800);
await page.screenshot({ path: "/workspace/screenshots/p17-simulasi.png" });

await page.getByRole("button", { name: /Eksplorasi/i }).click();
await toggleIf("Masterplan - acuan", true);
await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(1000);
await page.screenshot({ path: "/workspace/screenshots/p17-with-masterplan.png" });

await browser.close();
console.log("p17 screenshots done");
