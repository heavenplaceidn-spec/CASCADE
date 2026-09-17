#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";

const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(90000);
const ok = [];
const fail = [];
const check = (cond, yes, no) => {
  if (cond) ok.push(yes);
  else fail.push(no || yes);
};

page.on("pageerror", (err) => fail.push("pageerror " + err.message));

await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });

const hero = await page.locator("img.landing-hero").getAttribute("src");
check(hero && hero.includes("cascade-hero"), "loading hero intact", "hero " + hero);

await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => /Mulai Eksplorasi/.test(x.textContent || ""));
  return b && !b.disabled;
}, { timeout: 70000 });
await page.getByRole("button", { name: /Mulai Eksplorasi/ }).click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(600);

const body = await page.evaluate(() => document.body.innerText);
check(!/Intelijen/i.test(body), "Intelijen gone");
check(!/Jalan konteks/.test(body), "Jalan konteks checkbox gone");
check(!/Gaya MAPID/.test(body), "Gaya MAPID renamed");
check(!/\bCOMPARE\b/.test(body), "COMPARE not on explore");
check(/Tampilan Peta/.test(body), "Tampilan Peta present");
check(/PROPERTI/.test(body), "PROPERTI heading");
check(/Jual/.test(body) && /Sewa/.test(body), "Jual/Sewa kept");
check(/Tanah/.test(body) && /Ruko/.test(body), "category filters kept");
check(/Lapisan properti/.test(body), "property layer toggle kept");
check(/Relasi transportasi/.test(body) === false, "Relasi checkboxes gone");
check(/Jaringan transportasi:/.test(body), "legend network footer");
check(/koridor usulan/.test(body), "usulan count in legend");
check(/asking price/i.test(body), "asking-price disclaimer");

const mark = page.locator("img.cascade-mark");
check((await mark.count()) === 1, "one brand mark", "mark count " + (await mark.count()));

const layout = await page.evaluate(() => {
  const legend = [...document.querySelectorAll("p")].find((p) => p.textContent?.trim() === "LEGENDA");
  const gaya = document.querySelector('select[aria-label="Tampilan Peta"]');
  const panel = legend?.closest("div.cascade-panel");
  const gayaBox = gaya?.closest("div.cascade-panel")?.getBoundingClientRect();
  const legBox = panel?.getBoundingClientRect();
  const aside = document.querySelector("aside");
  const asideBox = aside?.getBoundingClientRect();
  return {
    leg: legBox ? { x: Math.round(legBox.x), y: Math.round(legBox.y), r: Math.round(legBox.right), b: Math.round(legBox.bottom), w: Math.round(legBox.width) } : null,
    gaya: gayaBox ? { x: Math.round(gayaBox.x), y: Math.round(gayaBox.y) } : null,
    aside: asideBox ? { x: Math.round(asideBox.x), w: Math.round(asideBox.width) } : null,
    vw: window.innerWidth,
  };
});
check(layout.leg && layout.leg.x < 80 && layout.leg.w < 280, "legend left compact", "legend " + JSON.stringify(layout.leg));
check(layout.gaya && layout.leg && layout.gaya.y >= layout.leg.b - 4, "Tampilan Peta below legend", "gaya " + JSON.stringify(layout));
check(layout.aside && layout.aside.x > layout.vw / 2, "right panel remains right", "aside " + JSON.stringify(layout.aside));

const styles = ["dark", "satellite", "basic"];
for (const key of styles) {
  await page.selectOption('select[aria-label="Tampilan Peta"]', key);
  await page.waitForTimeout(400);
  await page.waitForFunction((k) => {
    const m = window.__CASCADE_MAP;
    return window.__CASCADE.getState().styleKey === k && !!m?.getLayer?.("candidate-mode") && !!m?.getLayer?.("tj-existing-mode");
  }, key, { timeout: 20000 });
  await page.waitForTimeout(400);
  const vis = await page.evaluate(() => {
    const m = window.__CASCADE_MAP;
    const layers = ["candidate", "candidate-mode", "tj-existing-line", "krl-existing-line", "mrt-existing-mode", "cascade-stop"];
    let dual = null;
    try {
      dual = m?.getLayer?.("candidate-mode") ? m.getPaintProperty("candidate-mode", "line-color") : null;
    } catch {
      dual = "err";
    }
    return {
      style: window.__CASCADE.getState().styleKey,
      loaded: !!m?.isStyleLoaded?.(),
      layers: Object.fromEntries(layers.map((id) => [id, !!m?.getLayer?.(id)])),
      dual,
    };
  });
  const allOn = Object.values(vis.layers).every(Boolean);
  check(vis.style === key && allOn, `basemap ${key} overlays remain`, `basemap ${key} ${JSON.stringify(vis)}`);
  check(vis.dual != null && vis.dual !== "#ef4444" && vis.dual !== "red", `dual-color intact after ${key}`, `dual ${key} ${JSON.stringify(vis.dual)}`);
}

await page.getByRole("link", { name: /^Simulasi$/ }).click();
await page.waitForTimeout(400);
const simText = await page.evaluate(() => document.body.innerText);
check(!/\bCOMPARE\b/.test(simText), "COMPARE removed from simulasi");
check(/Mode jaringan/.test(simText), "Mode jaringan kept");
check(/Existing/.test(simText) && /Masterplan/.test(simText) && /CASCADE/.test(simText), "scenario labels in simulasi");

await page.getByRole("link", { name: /^Analisis$/ }).click();
await page.waitForTimeout(500);
check(await page.getByRole("button", { name: /Seret untuk pilih area/ }).count() > 0, "drag identify control");

async function runIdentify(bbox, label) {
  await page.evaluate((b) => {
    window.__CASCADE.getState().setIdentifyBbox(b);
  }, bbox);
  await page.waitForFunction(() => {
    const t = document.body.innerText;
    return /koridor beririsan|Tidak ada koridor transportasi yang teridentifikasi/.test(t);
  }, { timeout: 25000 });
  await page.waitForTimeout(400);
  return page.evaluate(() => {
    const text = document.body.innerText;
    const cards = [...document.querySelectorAll("article")].map((el) => el.innerText);
    const map = window.__CASCADE_MAP;
    let dual = null;
    try {
      dual = map?.getLayer?.("candidate-mode") ? map.getPaintProperty("candidate-mode", "line-color") : null;
    } catch {
      dual = "err";
    }
    return {
      text,
      cards,
      nCards: cards.length,
      bboxLayer: !!map?.getLayer?.("identify-area"),
      hitsLayer: !!map?.getLayer?.("identify-hits"),
      hitsN: map?.getSource?.("identify-hits")?._data?.features?.length ?? map?.querySourceFeatures?.("identify-hits")?.length ?? null,
      dual: map?.getPaintProperty?.("candidate-mode", "line-color"),
      selected: window.__CASCADE.getState().selectedId,
      identifyHits: window.__CASCADE.getState().identifyHits?.features?.map((f) => f.properties?.sdss_id || f.properties?.id || f.id) ?? [],
    };
  }).then((r) => ({ ...r, label }));
}

const dense = await runIdentify([106.8, -6.22, 106.86, -6.16], "dense");
check(dense.nCards <= 3, "max 3 cards in dense area", "dense cards " + dense.nCards);
check(dense.nCards >= 1, "dense has results", "dense empty");
check(/Menampilkan hingga 3 koridor/.test(dense.text), "max-3 copy");
check(/Prioritas (tinggi|sedang|rendah)/i.test(dense.text), "priority labels");
check(/Halte \/ stasiun/.test(dense.text), "station heading");
check(/Perkiraan biaya indikatif/.test(dense.text), "cost heading");
check(/bukan RAB\/DED/.test(dense.text), "cost disclaimer");
check(/Alasan analisis/.test(dense.text), "rationale");
check(/Konteks properti/.test(dense.text), "property context");
check(/Dasar penilaian/.test(dense.text), "score factors");
check(dense.bboxLayer, "persistent bbox layer");
check(dense.identifyHits.length > 0 && dense.identifyHits.length <= 3, "hits highlight <=3", "hits " + JSON.stringify(dense.identifyHits));
check(dense.dual != null, "dual-color still on candidate-mode");

const prios = dense.cards.map((t) => {
  if (/Prioritas tinggi/.test(t)) return "tinggi";
  if (/Prioritas sedang/.test(t)) return "sedang";
  if (/Prioritas rendah/.test(t)) return "rendah";
  return "?";
});
check(prios.some((p) => p !== "tinggi") || dense.nCards < 3, "not all HIGH when mixed", "all HIGH " + prios.join(","));
check(
  dense.cards.every((t) => /CASTJ|CAS-|tj-k|krl-|mrt-|lrt-|MRT_|LRT_|KRL_|OUTER_|Koridor \d+|Prioritas/.test(t)),
  "cards have corridor ids",
  "card ids " + dense.cards.map((t) => t.split("\n").slice(0, 4).join(" | ")).join(" || "),
);

const joglo = await runIdentify([106.73, -6.24, 106.78, -6.2], "joglo");
const jogloIds = joglo.cards.map((t) => t).join("\n");
check(/CASTJ24/.test(jogloIds), "Joglo finds CASTJ24", "joglo cards " + jogloIds.slice(0, 400));
check(!/CASTJ25/.test(jogloIds), "Joglo does not merge CASTJ25", "joglo leaked CASTJ25");

const meruya = await runIdentify([106.72, -6.21, 106.76, -6.17], "meruya");
const meruyaIds = meruya.cards.map((t) => t).join("\n");
check(/CASTJ25/.test(meruyaIds), "Meruya finds CASTJ25", "meruya cards " + meruyaIds.slice(0, 400));
check(!/CASTJ24/.test(meruyaIds), "Meruya does not merge CASTJ24", "meruya leaked CASTJ24");

const empty = await runIdentify([104.5, -5.5, 105.0, -5.0], "empty");
check(/Tidak ada koridor transportasi yang teridentifikasi pada area ini/.test(empty.text), "empty-area copy");
check(empty.nCards === 0, "empty shows 0 cards", "empty cards " + empty.nCards);

await page.getByRole("button", { name: /Hapus area/ }).click();
await page.waitForTimeout(300);
const cleared = await page.evaluate(() => window.__CASCADE.getState().identifyBbox);
check(cleared == null, "clear selection works");

await page.getByRole("button", { name: /Seret untuk pilih area/ }).click();
const overlay = page.locator("div.cursor-crosshair");
check((await overlay.count()) > 0, "drag overlay on");
const box = await overlay.boundingBox();
if (box) {
  const sx = box.x + box.width * 0.42;
  const sy = box.y + box.height * 0.42;
  await page.mouse.move(sx, sy);
  await page.mouse.down();
  await page.mouse.move(sx + 180, sy + 140, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(1500);
  const afterDrag = await page.evaluate(() => {
    const st = window.__CASCADE.getState();
    return { bbox: st.identifyBbox, n: (st.identifyHits?.features || []).length, mode: st.identifyMode };
  });
  check(!!afterDrag.bbox, "real drag writes geographic bbox", "drag bbox " + JSON.stringify(afterDrag));
  check(afterDrag.mode === true, "identify stays on for re-drag", "identifyMode " + afterDrag.mode);
}

await page.getByRole("link", { name: /^Eksplorasi$/ }).click();
await page.waitForTimeout(400);
await page.getByRole("button", { name: /^TransJakarta$/ }).first().click();
await page.waitForTimeout(300);
const castj24 = page.locator("button").filter({ hasText: "CBD Ciledug – Monas via Joglo" }).first();
if (await castj24.count()) {
  await castj24.click();
  await page.waitForTimeout(800);
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 15000 }),
    page.locator("aside").getByRole("button", { name: /Unduh GeoJSON CASTJ24/ }).click(),
  ]);
  const name = download.suggestedFilename();
  const path = await download.path();
  const raw = fs.readFileSync(path, "utf8");
  const fc = JSON.parse(raw);
  const id = String(fc.features?.[0]?.id || fc.features?.[0]?.properties?.id || "");
  const stations = fc.features?.[0]?.properties?.station_names || fc.features?.[0]?.properties?.stations;
  check(id.includes("CASTJ24") || /CASTJ24/.test(name), "CASTJ24 download id", "dl " + name + " " + id);
  check(!/CASTJ25/.test(raw) || (id.includes("CASTJ24") && !id.includes("CASTJ25")), "CASTJ24 file not CASTJ25");
  check(!/key=/i.test(raw), "no secrets in geojson");
  check(Array.isArray(fc.features) && fc.features.length === 1, "one feature per corridor download");
  const stationOk = typeof stations === "string" ? stations.length > 0 : Array.isArray(stations) && stations.length > 0;
  if (stations) check(stationOk, "download has stations");
} else {
  fail.push("CASTJ24 row missing in explore");
}

const mark2 = await page.locator("img.cascade-mark").count();
check(mark2 === 1, "branding remains after analysis");
const loadGone = await page.locator("img.landing-hero").count();
check(loadGone === 0, "loading screen dismissed, not rebuilt");

console.log(JSON.stringify({ ok, fail }, null, 2));
await browser.close();
if (fail.length) process.exit(1);
