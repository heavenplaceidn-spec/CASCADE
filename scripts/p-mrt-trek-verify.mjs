import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

function h16(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 16);
}
function h12(p, id) {
  const fc = JSON.parse(readFileSync(p, "utf8"));
  const f = fc.features.find((x) => String(x.id || x.properties?.route_id) === id);
  return createHash("sha256").update(JSON.stringify(f.geometry.coordinates)).digest("hex").slice(0, 12);
}

const frozen = {
  "public/data/krl_routes.geojson": "3c5f1d6bbc9f5bac",
  "public/data/lrt_routes.geojson": "c8852cc54513d443",
  "public/data/mrt_routes.geojson": "366e1977c661fefb",
  "public/data/transjakarta_routes.geojson": "f6b6e63b75a4180c",
  "public/data/masterplan.geojson": "fe420c0450d58dba",
};
const frozenIds = {
  "CAS-MRT-C01-A": "ae3767b7fef3",
  "CAS-TJ01": "68374d307e0f",
  "CAS-LRT-C02": "df511bac7ab9",
  "KRL-C03-N": "711afcad81d6",
};
const drift = [];
for (const [p, expect] of Object.entries(frozen)) {
  const got = h16(`/workspace/${p}`);
  if (got !== expect) drift.push(`${p} ${got} != ${expect}`);
}
for (const [id, expect] of Object.entries(frozenIds)) {
  const got = h12("/workspace/public/data/cascade_candidates.geojson", id);
  if (got !== expect) drift.push(`${id} ${got} != ${expect}`);
}

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
await page.waitForTimeout(2200);

async function toggleIf(name, wantOn) {
  const lab = page.locator("label").filter({ hasText: new RegExp(`^${name}$`) });
  if (!(await lab.count())) return;
  const checked = await lab.locator("input").isChecked();
  if (checked !== wantOn) await lab.click();
}
await toggleIf("KRL", false);
await toggleIf("TransJakarta", false);
await toggleIf("Jaringan LRT", false);
await toggleIf("Jaringan MRT", false);
await toggleIf("Masterplan - acuan", false);
await toggleIf("CASCADE - usulan", true);
await page.waitForTimeout(800);

const sel = page.getByLabel("Filter koridor usulan CASCADE");
await sel.selectOption("CAS-MRT-C01");
await page.waitForTimeout(1600);
await page.screenshot({ path: "/workspace/screenshots/mrt-trek-c01.png" });

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const ids = (src) => [...new Set(map.querySourceFeatures(src).map((f) => f.properties?.route_id || f.properties?.id).filter(Boolean))];
  const names = (src) =>
    map
      .querySourceFeatures(src)
      .filter((f) => f.properties?.route_id === "CAS-MRT-C01")
      .map((f) => f.properties?.stop_name || f.properties?.name)
      .filter(Boolean);
  return {
    casColor: map.getPaintProperty("candidate", "line-color"),
    routeIds: ids("candidate"),
    stopNames: [...new Set(names("cascade-stops"))],
    stopN: map.querySourceFeatures("cascade-stops").filter((f) => f.properties?.route_id === "CAS-MRT-C01").length,
  };
});

await sel.selectOption("CAS-MRT-C01-E");
await page.waitForTimeout(1400);
await page.screenshot({ path: "/workspace/screenshots/mrt-trek-c01e-cibubur.png" });

await sel.selectOption("CAS-MRT-C01-BR02");
await page.waitForTimeout(1400);
await page.screenshot({ path: "/workspace/screenshots/mrt-trek-br02.png" });

await sel.selectOption("mrt");
await page.waitForTimeout(1200);
await page.screenshot({ path: "/workspace/screenshots/mrt-trek-all.png" });

const val = JSON.parse(readFileSync("/workspace/public/data/cascade/cascade_validation_mrt_trek.json", "utf8"));
console.log(
  JSON.stringify(
    {
      drift,
      frozenOk: drift.length === 0,
      casColor: info.casColor,
      routeIds: info.routeIds.filter((id) => String(id).startsWith("CAS-MRT") || String(id).startsWith("CAS-LRT") || String(id).startsWith("KRL")),
      c01Stops: val.stops["CAS-MRT-C01"],
      eStops: val.stops["CAS-MRT-C01-E"],
      brStops: val.stops["CAS-MRT-C01-BR02"],
      km: val.km,
      hashes: val.hashes,
    },
    null,
    2,
  ),
);
await browser.close();
