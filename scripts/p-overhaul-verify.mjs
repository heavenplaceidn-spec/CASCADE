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
  "CAS-MRT-C01": "7f4818d71be3",
  "CAS-MRT-C01-E": "8e91302068d2",
  "CAS-MRT-C01-BR02": "ea815685e1c9",
  "CAS-MRT-C01-A": "ae3767b7fef3",
  "KRL-C03-N": "711afcad81d6",
  "KRL-C03-S": "c6ce84ce0d82",
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

await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1000);
const start = page.getByRole("button", { name: "START EXPLORATION" });
await start.first().click({ force: true });
await page.getByRole("link", { name: "Eksplorasi" }).waitFor({ timeout: 15000 });
const chrome = await page.locator("header").innerText();
if (!/CASCADE/.test(chrome) || !/CORRIDOR AI FOR SPATIAL CONGESTION ADVANCED DEVELOPMENT/.test(chrome)) {
  throw new Error(`header mismatch: ${chrome}`);
}
if (!(await page.getByRole("link", { name: "Eksplorasi" }).count())) throw new Error("nav missing");

const cascadeToggle = page.getByRole("button", { name: /^CASCADE$/ });
if (!(await cascadeToggle.count())) throw new Error("accordion CASCADE missing");
const mrtRow = page.getByRole("button", { name: /^MRT$/ });
if (!(await mrtRow.count())) throw new Error("CASCADE MRT child missing while open");

await page.screenshot({ path: "/workspace/screenshots/overhaul-explore.png" });

await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), null, { timeout: 45000 });
await page.waitForTimeout(1800);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const minz = (id) => (map.getLayer(id) ? map.getLayer(id).minzoom : null);
  return {
    casColor: map.getPaintProperty("candidate", "line-color"),
    casDash: map.getPaintProperty("candidate", "line-dasharray"),
    krlColor: map.getPaintProperty("krl-existing-line", "line-color"),
    mpColor: map.getPaintProperty("masterplan-line-dash", "line-color"),
    zoom: {
      cascade: minz("cascade-stop"),
      krl: minz("krl-existing-stop"),
      lrt: minz("lrt-existing-stop"),
      mrt: minz("mrt-existing-stop"),
      tj: minz("tj-existing-stop"),
      mp: minz("masterplan-stop"),
      casLabel: minz("cascade-label"),
      krlLabel: minz("krl-existing-label"),
    },
    layers: (map.getStyle()?.layers || []).map((l) => l.id),
  };
});

const zoomVals = Object.values(info.zoom).filter((z) => z != null);
const stopZooms = ["cascade", "krl", "lrt", "mrt", "tj", "mp"].map((k) => info.zoom[k]);
if (stopZooms.some((z) => z !== 12)) {
  drift.push(`station minzoom ${JSON.stringify(info.zoom)}`);
}
if (info.zoom.casLabel !== 14 || info.zoom.krlLabel !== 14) {
  drift.push(`label minzoom ${JSON.stringify(info.zoom)}`);
}

await page.getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(400);
const header2 = await page.locator("header").innerText();
if (!/CORRIDOR AI FOR SPATIAL CONGESTION ADVANCED DEVELOPMENT/.test(header2)) {
  drift.push("header changed on simulasi");
}
await page.getByRole("link", { name: "Eksplorasi" }).click();
await page.waitForTimeout(400);

const sim = await page.evaluate(async () => {
  const stops = await fetch("/data/cascade_stops.geojson").then((r) => r.json());
  const find = (name, route) =>
    stops.features.find((f) => String(f.properties?.name || "") === name && String(f.properties?.route_id) === route);
  const a = find("Depok Baru", "CAS-MRT-C01");
  const b = find("Senen", "CAS-MRT-C01");
  const store = window.__CASCADE;
  if (!a || !b || !store) return { error: "missing stations or store", a: !!a, b: !!b, store: !!store };
  const node = (f) => ({
    id: String(f.id || `${f.properties.route_id}-S${f.properties.stop_order}`),
    name: String(f.properties.name),
    coord: f.geometry.coordinates,
    status: "cascade",
    mode: String(f.properties.mode || "mrt"),
    corridorId: String(f.properties.corridor_id || f.properties.route_id),
    routeId: String(f.properties.route_id),
  });
  store.getState().beginSimFromStation(node(a));
  store.getState().beginSimFromStation(node(b));
  store.getState().setSimNetwork("cascade");
  store.getState().setSimCompare("cascade");
  return { origin: store.getState().simOrigin?.name, dest: store.getState().simDest?.name, routeA: a.properties.route_id, routeB: b.properties.route_id };
});

if (sim.error || !sim.origin || !sim.dest) {
  console.error("SIM", sim);
  process.exit(1);
}

await page.getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(400);
const play = page.getByRole("button", { name: /PLAY SIMULATION/i });
await page.waitForFunction(() => {
  const s = window.__CASCADE?.getState();
  return !!(s?.simOrigin && s?.simDest);
}, null, { timeout: 8000 });
await play.click();
await page.waitForTimeout(1800);

const flow = await page.evaluate(() => {
  const store = window.__CASCADE;
  const map = window.__CASCADE_MAP;
  const coords = store?.getState().simPath?.features?.[0]?.geometry?.coordinates || [];
  let maxDx = 0;
  for (let i = 1; i < coords.length; i++) {
    maxDx = Math.max(maxDx, Math.abs(coords[i][0] - coords[i - 1][0]) + Math.abs(coords[i][1] - coords[i - 1][1]));
  }
  const nPart = map.getSource("sim-particles") ? map.querySourceFeatures("sim-particles").length : 0;
  return {
    n: coords.length,
    maxStep: maxDx,
    first: coords[0],
    last: coords[coords.length - 1],
    particles: nPart,
    km: store?.getState().simResult?.km,
    hops: store?.getState().simResult?.hops,
    hasGradient: map.getLayer("sim-route") ? !!map.getPaintProperty("sim-route", "line-gradient") : false,
  };
});

await page.screenshot({ path: "/workspace/screenshots/overhaul-sim.png" });
await page.getByRole("link", { name: "Analisis" }).click();
await page.waitForTimeout(500);
await page.screenshot({ path: "/workspace/screenshots/overhaul-analisis.png" });

const out = { drift, info, sim, flow, zoomVals };
console.log(JSON.stringify(out, null, 2));
if (drift.length) {
  console.error("DRIFT", drift);
  process.exit(1);
}
if (sim.error) {
  console.error("SIM", sim);
  process.exit(1);
}
if (!flow.n || flow.n < 8) {
  console.error("flow too short", flow);
  process.exit(1);
}
if (flow.maxStep > 0.08) {
  console.error("straight-line shortcut suspected", flow.maxStep);
  process.exit(1);
}
await browser.close();
console.log("OK");
