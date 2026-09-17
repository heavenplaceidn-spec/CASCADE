import { chromium } from "playwright";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const frozen = {
  "public/data/krl_routes.geojson": null,
  "public/data/lrt_routes.geojson": null,
  "public/data/mrt_routes.geojson": null,
  "public/data/transjakarta_routes.geojson": null,
  "public/data/masterplan.geojson": null,
  "public/data/cascade_candidates.geojson": null,
};
for (const f of Object.keys(frozen)) {
  frozen[f] = createHash("sha256").update(readFileSync(`/workspace/${f}`)).digest("hex").slice(0, 12);
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
await page.waitForTimeout(1800);

const apis = {};
for (const path of [
  "/api/properties",
  "/api/properties/P-4c2c05feee8e",
  "/api/property-price-zones",
  "/api/property-ai-insights",
  "/api/corridors/CAS-MRT-C01/property-summary",
  "/api/corridors/CAS-MRT-C01/price-distribution",
  "/api/corridors/CAS-MRT-C01/properties",
]) {
  const res = await page.request.get(`http://127.0.0.1:8080${path}`);
  apis[path] = { status: res.status(), bytes: (await res.body()).byteLength };
}

const lab = page.locator("label").filter({ hasText: /^Lapisan properti$/ });
if (await lab.count()) {
  if (!(await lab.locator("input").isChecked())) await lab.click();
}
await page.waitForTimeout(1600);

const info = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const layers = (map.getStyle()?.layers || []).map((l) => l.id);
  const srcN = (id) => (map.getSource(id) ? map.querySourceFeatures(id).length : -1);
  const vis = (id) => (map.getLayer(id) ? map.getLayoutProperty(id, "visibility") : "missing");
  const icons = ["prop-tanah-MURAH", "prop-ruko-SEDANG", "prop-apt-MAHAL"].filter((i) => map.hasImage(i));
  const order = layers.filter((id) =>
    ["roads", "property-zones", "property-point", "property-cluster", "tj-existing-line", "krl-existing-line", "candidate"].includes(id),
  );
  const idx = (id) => layers.indexOf(id);
  return {
    zoom: map.getZoom(),
    order,
    propertyBelowTj: idx("property-point") >= 0 && idx("property-point") < idx("tj-existing-line"),
    src: { property: srcN("property"), zones: srcN("property-zones"), candidate: srcN("candidate") },
    vis: { point: vis("property-point"), cluster: vis("property-cluster"), zones: vis("property-zones") },
    icons,
    casColor: map.getLayer("candidate") ? map.getPaintProperty("candidate", "line-color") : null,
  };
});

await page.screenshot({ path: "/workspace/screenshots/prop-layer-on.png" });

const mrtBtn = page.locator("button").filter({ hasText: /CAS-MRT-C01 Lebak Bulus/ });
if (await mrtBtn.count()) await mrtBtn.first().click();
await page.waitForTimeout(1200);
const summaryText = await page.locator("text=Median jual").count();
await page.screenshot({ path: "/workspace/screenshots/prop-c01-summary.png" });

const popup = await page.evaluate(async () => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  map.easeTo({ center: [106.8324, -6.3682], zoom: 14.2, duration: 0 });
  await new Promise((r) => setTimeout(r, 900));
  const pts = map.queryRenderedFeatures({ layers: ["property-point"].filter((l) => map.getLayer(l)) });
  const f = pts[0];
  if (!f || f.geometry.type !== "Point") {
    return { rendered: pts.length, clicked: false };
  }
  const px = map.project(f.geometry.coordinates);
  map.fire("click", { lngLat: { lng: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }, point: px });
  await new Promise((r) => setTimeout(r, 200));
  return {
    rendered: pts.length,
    cats: [...new Set(pts.map((x) => x.properties?.category))],
    classes: [...new Set(pts.map((x) => x.properties?.price_class))],
    title: f.properties?.title || f.properties?.property_name,
    category: f.properties?.category,
    sale: f.properties?.sale_or_rent,
    price_label: f.properties?.price_label,
  };
});
await page.waitForTimeout(400);
const popupUi = {
  title: await page.locator(".cascade-panel.absolute.z-30 p.font-medium").first().textContent().catch(() => null),
  hasAsking: (await page.getByText(/ASKING PRICE|ESTIMATED MARKET RANGE|Harga|Sewa/).count()) > 0,
  hasSource: (await page.getByText(/Sumber/).count()) > 0,
  transportTabs: await page.getByRole("tablist", { name: "Status koridor" }).count(),
};
await page.screenshot({ path: "/workspace/screenshots/prop-popup.png" });

const transportPopup = await page.evaluate(async () => {
  const map = window.__CASCADE_MAP;
  if (!map) return { error: "no map" };
  const lines = map.queryRenderedFeatures({ layers: ["candidate"].filter((l) => map.getLayer(l)) });
  const f = lines[0];
  if (!f) return { clicked: false, n: lines.length };
  const coords =
    f.geometry.type === "LineString"
      ? f.geometry.coordinates[Math.floor(f.geometry.coordinates.length / 2)]
      : null;
  if (!coords) return { clicked: false };
  const px = map.project(coords);
  map.fire("click", { lngLat: { lng: coords[0], lat: coords[1] }, point: px });
  return { clicked: true, id: f.properties?.id || f.properties?.route_id };
});
await page.waitForTimeout(400);
const tabs = {
  list: await page.getByRole("tablist", { name: "Status koridor" }).count(),
  existing: await page.getByRole("tab", { name: "Existing" }).count(),
  masterplan: await page.getByRole("tab", { name: "Masterplan" }).count(),
  cascade: await page.getByRole("tab", { name: "CASCADE" }).count(),
};
if (await page.getByRole("tab", { name: "Existing" }).count()) {
  await page.getByRole("tab", { name: "Existing" }).click();
  await page.waitForTimeout(200);
}
await page.screenshot({ path: "/workspace/screenshots/prop-transport-tabs.png" });

console.log(JSON.stringify({ frozen, apis, info, summaryText, popup, popupUi, transportPopup, tabs }, null, 2));
await browser.close();
