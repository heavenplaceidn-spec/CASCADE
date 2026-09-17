import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.route("**/*", (route) => route.continue());
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
await page.waitForTimeout(2500);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return;
  const checked = await lab.locator("input").first().isChecked();
  if (checked !== wantOn) await lab.click();
}

await toggleIf("KRL", false);
await toggleIf("TransJakarta", false);
await toggleIf("Jaringan LRT", false);
await toggleIf("Jaringan MRT", false);
await toggleIf("Masterplan - acuan", false);
await toggleIf("Jalan - konteks", false);
await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(1000);

const casSelect = page.locator('select[aria-label="Filter koridor usulan CASCADE"]');

async function selectCas(id) {
  const btn = page.locator("button").filter({ hasText: new RegExp(`^${id}\\b`) });
  if (await btn.count()) {
    await btn.first().click();
  } else if (await casSelect.count()) {
    await casSelect.selectOption(id);
  }
  await page.waitForTimeout(1800);
}

async function shotAt(lon, lat, zoom, path) {
  await page.evaluate(
    ([ln, lt, z]) => {
      const map = window.__CASCADE_MAP;
      map.jumpTo({ center: [ln, lt], zoom: z });
    },
    [lon, lat, zoom]
  );
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `/workspace/screenshots/${path}` });
  console.log("SHOT", path);
}

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const feats = map.querySourceFeatures("candidate");
  const stops = map.querySourceFeatures("cascade-stops");
  const names = (rid) =>
    [...new Set(feats.filter((f) => (f.properties?.route_id || f.properties?.id) === rid).map((f) => f.properties?.name))];
  const stopNames = (rid) =>
    stops.filter((f) => f.properties?.route_id === rid).map((f) => f.properties?.stop_name || f.properties?.name);
  return {
    casColor: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
    ids: [...new Set(feats.map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))].sort(),
    tj06: names("CAS-TJ06"),
    tj07: names("CAS-TJ07"),
    tj06stops: stopNames("CAS-TJ06"),
    tj07stops: stopNames("CAS-TJ07"),
  };
});
console.log("MAP", JSON.stringify(info, null, 2));

await page.screenshot({ path: "/workspace/screenshots/tj0607-all.png" });

await selectCas("CAS-TJ06");
await page.screenshot({ path: "/workspace/screenshots/tj-cas-tj06-puri-indah.png" });
console.log("SHOT CAS-TJ06 overview");
await shotAt(106.8205, -6.1785, 15, "tj06-monas-abdul-muis.png");
await shotAt(106.794, -6.206, 14.8, "tj06-palmerah.png");
await shotAt(106.784, -6.190, 14.8, "tj06-kemanggisan.png");
await shotAt(106.769, -6.198, 14.5, "tj06-kebon-jeruk.png");
await shotAt(106.753, -6.198, 14.8, "tj06-meruya-ilir.png");
await shotAt(106.738, -6.191, 14.6, "tj06-puri-kencana.png");
await shotAt(106.7339, -6.1883, 15, "tj06-puri-indah-zoom.png");

await selectCas("CAS-TJ07");
await page.screenshot({ path: "/workspace/screenshots/tj-cas-tj07-puri-beta.png" });
console.log("SHOT CAS-TJ07 overview");
await shotAt(106.7943, -6.2076, 15, "tj07-palmerah.png");
await shotAt(106.73, -6.219, 14.5, "tj07-joglo-jengkol.png");
await shotAt(106.7245, -6.226, 14.5, "tj07-ujung-beta.png");

if (await casSelect.count()) await casSelect.selectOption("all");
await page.waitForTimeout(1200);
await shotAt(106.76, -6.20, 12.4, "tj0607-west-split.png");

const panel = await page.evaluate(() => {
  const texts = [...document.querySelectorAll("button, option, li, label, span")].map((el) => el.textContent || "").join("\n");
  const buttons = [...document.querySelectorAll("button")].map((el) => (el.textContent || "").trim());
  return {
    tj06indah: /CAS-TJ06[\s\S]{0,40}Puri Indah/i.test(texts),
    tj07beta: /CAS-TJ07[\s\S]{0,40}Puri Beta/i.test(texts),
    tj06button: buttons.some((t) => /^CAS-TJ06\b/.test(t) && /Puri Indah/i.test(t)),
    tj07button: buttons.some((t) => /^CAS-TJ07\b/.test(t) && /Puri Beta/i.test(t)),
    jengkol: /Gang Jengkol/i.test(texts),
    kemanggisanBtn: /Kemanggisan/i.test(texts),
  };
});
console.log("PANEL", panel);

const mapqa = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const feats = map.querySourceFeatures("candidate");
  const stops = map.querySourceFeatures("cascade-stops");
  const of = (rid) => feats.filter((f) => (f.properties?.route_id || f.properties?.id) === rid);
  const st = (rid) => stops.filter((f) => f.properties?.route_id === rid).map((f) => f.properties?.stop_name || f.properties?.name);
  const name = (rid) => [...new Set(of(rid).map((f) => f.properties?.name || f.properties?.route_name))];
  return {
    ids: [...new Set(feats.map((f) => f.properties?.id || f.properties?.route_id).filter(Boolean))].sort(),
    color: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
    tj06: name("CAS-TJ06"),
    tj07: name("CAS-TJ07"),
    tj06stops: st("CAS-TJ06"),
    tj07stops: st("CAS-TJ07"),
  };
});
console.log("MAPQA", JSON.stringify(mapqa, null, 2));

await browser.close();
