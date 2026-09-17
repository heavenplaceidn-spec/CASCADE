import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

function h12(p, id) {
  const fc = JSON.parse(readFileSync(p, "utf8"));
  const f = fc.features.find((x) => String(x.id || x.properties?.route_id) === id);
  return createHash("sha256").update(JSON.stringify(f.geometry.coordinates)).digest("hex").slice(0, 12);
}
const frozen = {
  "CAS-MRT-C01": "7f4818d71be3",
  "CAS-MRT-C01-A": "ae3767b7fef3",
  "KRL-C03-N": "711afcad81d6",
};
const drift = [];
for (const [id, expect] of Object.entries(frozen)) {
  const got = h12("/workspace/public/data/cascade_candidates.geojson", id);
  if (got !== expect) drift.push(`${id} ${got} != ${expect}`);
}

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(90000);
await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(400);
const body0 = await page.locator("body").innerText();
if (/Memuat peta MAPID/i.test(body0)) drift.push("loading still says MAPID");
if (/ADVANCED DEVELOPMENT/.test(body0) && !/ADVANCED DATA/.test(body0)) drift.push("old branding");
const start = page.getByRole("button", { name: /^EKSPLOR$/i });
if (!(await start.count())) drift.push("missing EKSPLOR");
else {
  await page.waitForFunction(() => {
    const b = [...document.querySelectorAll("button")].find((el) => /^EKSPLOR$/i.test((el.textContent || "").trim()));
    return b && !b.disabled;
  });
  if (!(await start.isEnabled())) drift.push("start never enabled");
  await start.click();
}
await page.getByRole("link", { name: "Eksplorasi" }).waitFor();
const header = await page.locator("header").innerText();
if (!/ADVANCED DATA, AND EXPANSION/.test(header)) drift.push("header branding");
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.());

const named = await page.evaluate(() => {
  const bn = window.__CASCADE_BN;
  if (!bn) return null;
  const pts = [
    ["Sawangan", 106.764, -6.4],
    ["Ciputat", 106.747, -6.317],
    ["Jelambar", 106.786, -6.166],
    ["Central Park", 106.79, -6.177],
    ["Condet", 106.863, -6.283],
    ["Senen", 106.843, -6.176],
    ["Gunung Sahari", 106.833, -6.155],
  ];
  const pack = (status) => Object.fromEntries(pts.map(([n, lng, lat]) => [n, bn.klassOf(bn.peakScore(lng, lat, status))]));
  const scores = (status) => Object.fromEntries(pts.map(([n, lng, lat]) => [n, Number(bn.peakScore(lng, lat, status).toFixed(2))]));
  return { existing: pack("existing"), cascade: pack("cascade"), exScore: scores("existing"), casScore: scores("cascade") };
});
if (!named) drift.push("missing BN helpers");
else {
  if (named.existing.Sawangan === "rendah" || named.exScore.Sawangan < 0.7) drift.push(`Sawangan existing ${named.existing.Sawangan} ${named.exScore.Sawangan}`);
  if (named.cascade.Sawangan === "rendah") drift.push("Sawangan CASCADE hijau");
  if (named.existing.Ciputat === "rendah" || named.exScore.Ciputat < 0.68) drift.push("Ciputat existing too low");
  for (const k of ["Jelambar", "Central Park", "Condet"]) {
    if (named.existing[k] !== "tinggi") drift.push(`${k} existing ${named.existing[k]}`);
  }
  if (named.cascade.Jelambar !== "tinggi") drift.push("Jelambar CASCADE not high");
}

const node = (f, status, mode) => ({
  id: String(f.id || `${f.properties.route_id}-${f.properties.stop_order}`),
  name: String(f.properties.name),
  coord: f.geometry.coordinates,
  status,
  mode,
  corridorId: String(f.properties.route_id || f.properties.line_code || f.properties.corridor_id || ""),
  routeId: String(f.properties.route_id || f.properties.line_code || f.properties.id || ""),
});

const xnet = await page.evaluate(async (makeNode) => {
  const [cas, mrt] = await Promise.all([
    fetch("/data/cascade_stops.geojson").then((r) => r.json()),
    fetch("/data/mrt_stops.geojson").then((r) => r.json()),
  ]);
  const a = cas.features.find((f) => f.properties?.name === "Sawangan" && f.properties?.route_id === "CAS-MRT-C01-A");
  const b = mrt.features.find((f) => f.properties?.name === "Bundaran HI");
  const store = window.__CASCADE;
  store.getState().clearSim();
  store.getState().beginSimFromStation({
    id: String(a.id || "saw"),
    name: String(a.properties.name),
    coord: a.geometry.coordinates,
    status: "cascade",
    mode: "mrt",
    corridorId: "CAS-MRT-C01-A",
    routeId: "CAS-MRT-C01-A",
  });
  store.getState().beginSimFromStation({
    id: String(b.id || "hi"),
    name: String(b.properties.name),
    coord: b.geometry.coordinates,
    status: "existing",
    mode: "mrt",
    corridorId: String(b.properties.line_code || "NS"),
    routeId: String(b.properties.line_code || "NS"),
  });
  return { origin: store.getState().simOrigin?.name, dest: store.getState().simDest?.name, a: !!a, b: !!b };
}, null);
if (xnet.origin !== "Sawangan" || xnet.dest !== "Bundaran HI") drift.push(`xnet nodes ${JSON.stringify(xnet)}`);

await page.getByLabel("Tampilan").getByRole("link", { name: "Simulasi" }).click();
await page.getByRole("button", { name: /PLAY SIMULATION/i }).click();
await page.waitForFunction(() => (window.__CASCADE?.getState()?.simResult?.km || 0) > 3, null, { timeout: 60000 });
const flow = await page.evaluate(() => {
  const store = window.__CASCADE.getState();
  const coords = (store.simPath?.features || []).find((f) => f.geometry?.type === "LineString")?.geometry?.coordinates || [];
  const nearFat = coords.some((c) => Math.hypot(c[0] - 106.7925, c[1] + 6.2925) < 0.01);
  const o = store.simOrigin.coord;
  const d = store.simDest.coord;
  let pathM = 0;
  for (let i = 1; i < coords.length; i++) {
    const to = (x) => (x * Math.PI) / 180;
    const dlon = to(coords[i][0] - coords[i - 1][0]);
    const dlat = to(coords[i][1] - coords[i - 1][1]);
    const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(coords[i - 1][1])) * Math.cos(to(coords[i][1])) * Math.sin(dlon / 2) ** 2;
    pathM += 6371000 * 2 * Math.asin(Math.sqrt(h));
  }
  const crow = (() => {
    const to = (x) => (x * Math.PI) / 180;
    const dlon = to(d[0] - o[0]);
    const dlat = to(d[1] - o[1]);
    const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(o[1])) * Math.cos(to(d[1])) * Math.sin(dlon / 2) ** 2;
    return 6371000 * 2 * Math.asin(Math.sqrt(h));
  })();
  return {
    km: store.simResult?.km,
    n: coords.length,
    hops: store.simResult?.hops,
    note: store.simResult?.note,
    transfers: (store.simResult?.transfers || []).map((t) => t.name),
    nearFat,
    ratio: crow ? pathM / crow : 0,
    first: coords[0],
    last: coords[coords.length - 1],
  };
});
if (flow.n < 20) drift.push(`path too short ${flow.n}`);
if (flow.km < 5) drift.push(`km ${flow.km}`);
if (!flow.nearFat && !(flow.hops || []).some((h) => /Fatmawati/i.test(h))) drift.push("no Fatmawati interchange");
if (flow.ratio < 1.02 && flow.n < 30) drift.push("looks like straight line");

const persist = await page.evaluate(() => window.__CASCADE.getState().simOrigin?.name);
await page.getByLabel("Tampilan").getByRole("link", { name: "Analisis" }).click();
await page.getByRole("button", { name: /DRAG TO IDENTIFY/i }).waitFor();
const an = await page.locator("body").innerText();
if (!/DRAG TO IDENTIFY/i.test(an)) drift.push("missing identify");
if (!/DECISION SUPPORT/i.test(an)) drift.push("missing decision");
await page.getByLabel("Tampilan").getByRole("link", { name: "Simulasi" }).click();
await page.waitForTimeout(200);
const persist2 = await page.evaluate(() => ({
  o: window.__CASCADE.getState().simOrigin?.name,
  d: window.__CASCADE.getState().simDest?.name,
  km: window.__CASCADE.getState().simResult?.km,
}));
if (persist2.o !== persist || persist2.d !== "Bundaran HI") drift.push(`state reset ${JSON.stringify(persist2)}`);
if (!persist2.km) drift.push("sim result lost on tab change");

await page.screenshot({ path: "/workspace/screenshots/final-analisis.png" });
await page.getByLabel("Tampilan").getByRole("link", { name: "Eksplorasi" }).click();
await page.screenshot({ path: "/workspace/screenshots/final-explore.png" });
await page.getByLabel("Tampilan").getByRole("link", { name: "Simulasi" }).click();
await page.screenshot({ path: "/workspace/screenshots/final-sim.png" });

console.log(JSON.stringify({ drift, header: header.slice(0, 180), named, xnet, flow, persist2 }, null, 2));
await browser.close();
if (drift.length) {
  console.error("FAIL", drift);
  process.exit(1);
}
console.log("OK");
