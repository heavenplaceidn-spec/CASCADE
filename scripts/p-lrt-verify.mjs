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
await page.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" });
const startBtn = page.getByRole("button", { name: /Mulai Eksplorasi/i });
if (await startBtn.count()) await startBtn.click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());
await page.waitForTimeout(2000);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
  await page.waitForTimeout(200);
  return { name, wantOn, was: checked };
}

await toggleIf("KRL", false);
await toggleIf("Jaringan MRT", false);
await toggleIf("Jaringan LRT", true);
await toggleIf("TransJakarta", false);
await toggleIf("Masterplan - acuan", true);
await toggleIf("CASCADE - usulan", true);
await toggleIf("Jalan - konteks", false);

const panel = await page.evaluate(() => document.body.innerText);
const hasBrtHead = /USULAN CASCADE — BRT/.test(panel);
const hasLrtHead = /USULAN CASCADE — LRT/.test(panel);
const hasC02btn = /CAS-LRT-C02/.test(panel);
const hasC04btn = /CAS-LRT-C04/.test(panel);
const hasBogorCas = /CAS-LRT.*Baranangsiang|Harjamukti – Baranangsiang/.test(panel);
console.log("PANEL", JSON.stringify({ hasBrtHead, hasLrtHead, hasC02btn, hasC04btn, hasBogorCas }));

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const ids = (src) => [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))];
  const mpIds = (src) =>
    map.querySourceFeatures(src).map((f) => ({
      id: f.properties?.id || f.properties?.corridor_id,
      name: f.properties?.name || f.properties?.short,
      status: f.properties?.status,
      mode: f.properties?.mode,
    }));
  return {
    casColor: paint("candidate", "line-color"),
    casDash: paint("candidate", "line-dasharray"),
    lrtColor: paint("lrt-existing-line", "line-color") || paint("lrt-line", "line-color"),
    mpColor: paint("masterplan-line-dash", "line-color") || paint("masterplan-line-ref", "line-color"),
    casIds: ids("candidate"),
    mpSample: mpIds("masterplan").slice(0, 12),
    layers: (map.getStyle()?.layers || []).map((l) => l.id).filter((id) => /lrt|candidate|masterplan|cascade/i.test(id)),
  };
});
console.log("INFO", JSON.stringify(info, null, 2));

async function fit(b, shot, zoomPad = 0.08) {
  await page.evaluate((bbox) => {
    const map = window.__CASCADE_MAP;
    map.fitBounds(
      [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[3]],
      ],
      { padding: 48, duration: 0 },
    );
  }, b);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `/workspace/screenshots/${shot}` });
}

async function clickCas(id) {
  const btn = page.locator("button").filter({ hasText: new RegExp(`${id}\\b`) });
  if (await btn.count()) {
    await btn.first().click();
    await page.waitForTimeout(1400);
    return true;
  }
  console.log("missing button", id);
  return false;
}

await page.screenshot({ path: "/workspace/screenshots/lrt-panel.png" });

await clickCas("CAS-LRT-C02");
await page.screenshot({ path: "/workspace/screenshots/lrt-c02-full.png" });
await fit([106.888, -6.422, 106.992, -6.362], "lrt-c02-corridor.png");
await fit([106.888, -6.378, 106.902, -6.364], "lrt-c02-cibubur.png");
await fit([106.960, -6.420, 106.990, -6.400], "lrt-c02-mekarsari.png");
await fit([106.80, -6.62, 106.95, -6.35], "lrt-c02-not-baranangsiang.png");

await clickCas("CAS-LRT-C04");
await page.screenshot({ path: "/workspace/screenshots/lrt-c04-full.png" });
await fit([106.805, -6.214, 106.830, -6.198], "lrt-c04-dukuh-benhil.png");
await fit([106.806, -6.212, 106.818, -6.184], "lrt-c04-benhil-ta.png");
await fit([106.798, -6.182, 106.816, -6.164], "lrt-c04-petojo.png");
await fit([106.72, -6.14, 106.76, -6.10], "lrt-c04-pik.png");
await fit([106.648, -6.138, 106.678, -6.112], "lrt-c04-airport.png");
await fit([106.65, -6.22, 106.83, -6.08], "lrt-c04-overview.png");

// Masterplan Bogor should still exist independently
const mp = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("masterplan") || [];
  const bogor = feats.filter((f) => {
    const blob = `${f.properties?.id || ""} ${f.properties?.name || ""} ${f.properties?.corridor_id || ""}`.toLowerCase();
    return blob.includes("bogor") || blob.includes("baranangsiang") || blob.includes("harjamukti");
  });
  return bogor.map((f) => ({
    id: f.properties?.id || f.properties?.corridor_id,
    name: f.properties?.name,
    status: f.properties?.status,
    mode: f.properties?.mode,
  }));
});
console.log("MASTERPLAN_BOGOR", JSON.stringify(mp, null, 2));
await fit([106.82, -6.62, 107.02, -6.35], "lrt-masterplan-bogor.png");

await browser.close();
console.log("done");
