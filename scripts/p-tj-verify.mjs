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
if (await startBtn.count()) {
  await startBtn.click({ force: true }).catch(() => {});
}
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(2800);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return { missing: true, name };
  const checked = await lab.locator("input").first().isChecked();
  if (checked !== wantOn) await lab.click();
  return { name, wantOn, was: checked };
}

await toggleIf("KRL", false);
await toggleIf("TransJakarta", false);
await toggleIf("Jaringan LRT", false);
await toggleIf("Jaringan MRT", false);
await toggleIf("Masterplan - acuan", false);
await toggleIf("Jalan - konteks", false);
await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(1200);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const ids = (src) => [
    ...new Set(map.querySourceFeatures(src).map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean)),
  ];
  const names = (src) => [
    ...new Set(map.querySourceFeatures(src).map((f) => f.properties?.stop_name || f.properties?.name).filter(Boolean)),
  ];
  return {
    casColor: paint("candidate", "line-color"),
    casDash: paint("candidate", "line-dasharray"),
    casIds: ids("candidate").sort(),
    hasCas06: ids("candidate").includes("CAS-06"),
    hasCas07: ids("candidate").includes("CAS-07"),
    hasCasTj07: ids("candidate").includes("CAS-TJ07"),
    hasHarjamukti: names("cascade-stops").some((n) => String(n).toLowerCase().includes("harjamukti")),
    stopIds: [...new Set(map.querySourceFeatures("cascade-stops").map((f) => f.properties?.route_id).filter(Boolean))].sort(),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/tj-all.png" });

async function flyCas(id, shot) {
  const btn = page.locator("button").filter({ hasText: new RegExp(`^${id}\\b`) });
  const n = await btn.count();
  if (!n) {
    console.log("missing button", id);
    const opt = page.locator("select").locator(`option[value="${id}"]`);
    if (await opt.count()) {
      await page.locator("select").first().selectOption(id).catch(() => {});
    }
  } else {
    await btn.first().click();
  }
  await page.waitForTimeout(1800);
  const cam = await page.evaluate(() => {
    const map = window.__CASCADE_MAP;
    return map ? { center: map.getCenter(), zoom: map.getZoom() } : null;
  });
  console.log("FLY", id, cam);
  await page.screenshot({ path: `/workspace/screenshots/${shot}` });
}

await flyCas("CAS-TJ01", "tj-cas-tj01.png");
await flyCas("CAS-TJ02", "tj-cas-tj02.png");
await flyCas("CAS-TJ03", "tj-cas-tj03.png");
await flyCas("CAS-TJ04", "tj-cas-tj04.png");
await flyCas("CAS-TJ05", "tj-cas-tj05.png");
await flyCas("CAS-TJ06", "tj-cas-tj06.png");

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li")].map((el) => el.textContent || "").join("\n");
  return {
    hasTj01: texts.includes("CAS-TJ01"),
    hasTj06: texts.includes("CAS-TJ06"),
    hasCas01: /\bCAS-01\b/.test(texts),
    hasCas07: /\bCAS-07\b/.test(texts),
    hasTj07: texts.includes("CAS-TJ07"),
    hasHarja: /harjamukti/i.test(texts),
  };
});
console.log("PANEL", panel);

await browser.close();
