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
await page.waitForTimeout(1400);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const paint = (id, prop) => (map.getLayer(id) ? map.getPaintProperty(id, prop) : null);
  const ids = (src) => [
    ...new Set(map.querySourceFeatures(src).map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean)),
  ];
  const names = (src) => [
    ...new Set(map.querySourceFeatures("cascade-stops").map((f) => f.properties?.stop_name || f.properties?.name).filter(Boolean)),
  ];
  return {
    casColor: paint("candidate", "line-color"),
    casDash: paint("candidate", "line-dasharray"),
    casIds: ids("candidate").sort(),
    hasCas06: ids("candidate").includes("CAS-06"),
    hasCas07: ids("candidate").includes("CAS-07"),
    hasCas08: ids("candidate").includes("CAS-08"),
    hasCas11: ids("candidate").includes("CAS-11"),
    hasTj07: ids("candidate").includes("CAS-TJ07"),
    hasTj10: ids("candidate").includes("CAS-TJ10"),
    hasTj11: ids("candidate").includes("CAS-TJ11"),
    hasHarjamukti: names().some((n) => String(n).toLowerCase().includes("harjamukti")),
    hasPuriIndah: names().some((n) => String(n).toLowerCase().includes("puri indah")),
    hasMenwa: names().some((n) => String(n).toLowerCase().includes("menwa")),
    hasCakung: names().some((n) => String(n).toLowerCase().includes("cakung")),
    hasKlender: names().some((n) => String(n).toLowerCase().includes("klender")),
    stopIds: [...new Set(map.querySourceFeatures("cascade-stops").map((f) => f.properties?.route_id).filter(Boolean))].sort(),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));
await page.screenshot({ path: "/workspace/screenshots/tjb-all.png" });

async function flyCas(id, shot) {
  const btn = page.locator("button").filter({ hasText: new RegExp(`^${id}\\b`) });
  const n = await btn.count();
  if (!n) {
    console.log("missing button", id);
    const sel = page.locator("select").filter({ has: page.locator(`option[value="${id}"]`) });
    if (await sel.count()) {
      await sel.first().selectOption(id).catch(() => {});
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

for (const id of ["CAS-TJ06", "CAS-TJ07", "CAS-TJ08", "CAS-TJ09", "CAS-TJ10", "CAS-TJ11"]) {
  await flyCas(id, `tjb-${id.toLowerCase()}.png`);
}

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li")].map((el) => el.textContent || "").join("\n");
  return {
    hasTj06: texts.includes("CAS-TJ06"),
    hasTj07: texts.includes("CAS-TJ07"),
    hasTj08: texts.includes("CAS-TJ08"),
    hasTj09: texts.includes("CAS-TJ09"),
    hasTj10: texts.includes("CAS-TJ10"),
    hasTj11: texts.includes("CAS-TJ11"),
    hasCas08: /\bCAS-08\b/.test(texts),
    hasPuriIndah: /Puri Indah/.test(texts),
    hasHarja: /harjamukti/i.test(texts),
    hasMenwa: /Menwa UI/.test(texts),
  };
});
console.log("PANEL", panel);

await browser.close();
