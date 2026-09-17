#!/usr/bin/env node
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });
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

const BN = new Set(["#DC2626", "#EAB308", "#16A34A"]);
function toHex(c) {
  if (c && typeof c === "object" && "r" in c) {
    const n = (v) => Math.round((Number(v) <= 1 ? Number(v) * 255 : Number(v)));
    return `#${[n(c.r), n(c.g), n(c.b)].map((x) => x.toString(16).padStart(2, "0")).join("")}`.toUpperCase();
  }
  const s = String(c);
  const m = s.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
  if (m) {
    const n = (v) => Math.round(Number(v) <= 1 && !v.includes(".") ? Number(v) : Number(v) <= 1 ? Number(v) * 255 : Number(v));
    return `#${[n(m[1]), n(m[2]), n(m[3])].map((x) => Math.round(Number(x) <= 1 && String(x).includes(".") ? Number(x) * 255 : Number(x)).toString(16).padStart(2, "0")).join("")}`.toUpperCase();
  }
  return s.toUpperCase();
}

await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
await page.waitForFunction(() => {
  const b = [...document.querySelectorAll("button")].find((x) => /Mulai Eksplorasi/.test(x.textContent || ""));
  return b && !b.disabled;
}, { timeout: 70000 });
await page.getByRole("button", { name: /Mulai Eksplorasi/ }).click();
await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
await page.waitForTimeout(700);

const layout = await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  const vis = (id) => m?.getLayer?.(id) && m.getLayoutProperty(id, "visibility") !== "none";
  return {
    dual: vis("candidate") && vis("candidate-mode"),
    mark: document.querySelectorAll("img.cascade-mark").length,
    status: /STATUS GARIS/.test(document.body.innerText || ""),
    bnLegend: /STATUS KEMACETAN/.test(document.body.innerText || ""),
  };
});
check(layout.dual, "dual-color pathway layers on");
check(layout.mark === 1, "one brand mark");
check(layout.status, "legend STATUS GARIS");
check(layout.bnLegend, "legend STATUS KEMACETAN");

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(300);
await page.waitForFunction(() => window.__CASCADE.getState().networkReady === true, { timeout: 25000 }).catch(() => {});

async function pickStation(label, query, hint) {
  const input = page.getByLabel(label, { exact: true });
  await input.fill("");
  await input.fill(query);
  await page.waitForTimeout(800);
  const hinted = page.locator("ul button").filter({ hasText: hint }).first();
  if (await hinted.count()) {
    await hinted.click();
    return true;
  }
  const any = page.locator("ul button").first();
  if (await any.count()) {
    await any.click();
    return true;
  }
  return false;
}

async function runPair(fromQ, fromHint, toQ, toHint) {
  const reset = page.getByRole("button", { name: "Reset" });
  if (await reset.count()) await reset.click();
  await page.waitForTimeout(180);
  const a = await pickStation("Asal", fromQ, fromHint);
  const b = await pickStation("Tujuan", toQ, toHint);
  if (!a || !b) return { error: "stations missing" };
  await page.getByRole("button", { name: "Jalankan" }).click();
  await page.waitForFunction(() => (window.__CASCADE.getState().simResult?.km || 0) > 0, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1400);
  return page.evaluate(() => {
    const st = window.__CASCADE.getState();
    const map = window.__CASCADE_MAP;
    const anim = window.__CASCADE_ANIM || {};
    const api = window.__CASCADE_ANIM_API;
    const bn = window.__CASCADE_CONGESTION || {};
    const vis = (id) => map?.getLayer?.(id) && map.getLayoutProperty(id, "visibility") !== "none";
    const cars = api?.sample ? api.sample(10) : [];
    const pxGaps = [];
    for (let i = 1; i < cars.length; i++) {
      const p0 = map.project([cars[i - 1].lng, cars[i - 1].lat]);
      const p1 = map.project([cars[i].lng, cars[i].lat]);
      pxGaps.push(Math.hypot(p0.x - p1.x, p0.y - p1.y));
    }
    const gradient = map?.getLayer?.("sim-route") ? map.getPaintProperty("sim-route", "line-gradient") : null;
    const gColors = [];
    if (Array.isArray(gradient)) {
      for (let i = 4; i < gradient.length; i += 2) {
        const raw = gradient[i];
        let hex = String(raw).toUpperCase();
        if (raw && typeof raw === "object" && "r" in raw) {
          const n = (v) => Math.round(Number(v) <= 1 ? Number(v) * 255 : Number(v));
          hex = `#${[n(raw.r), n(raw.g), n(raw.b)].map((x) => x.toString(16).padStart(2, "0")).join("")}`.toUpperCase();
        } else {
          const m = String(raw).match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
          if (m) {
            const n = (v) => {
              const num = Number(v);
              return Math.round(num <= 1 ? num * 255 : num);
            };
            hex = `#${[n(m[1]), n(m[2]), n(m[3])].map((x) => x.toString(16).padStart(2, "0")).join("")}`.toUpperCase();
          }
        }
        gColors.push(hex);
      }
    }
    const src = map.getSource("sim-route");
    let metrics = false;
    try { metrics = !!src?.serialize?.().lineMetrics; } catch { /* */ }
    const fills = [];
    if (api?.track?.samples) {
      const t = api.track;
      for (const sec of [0, t.duration * 0.25, t.duration * 0.5, t.duration * 0.75, t.duration * 0.95]) {
        const c = api.sample(sec);
        if (c[0]) fills.push({ sec, bn: c[0].bn, klass: c[0].klass });
      }
    }
    return {
      km: st.simResult?.km,
      segs: (st.simResult?.segments || []).map((s) => s.routeId || s.kind),
      vehicles: [...new Set((st.simResult?.segments || []).map((s) => s.vehicle))],
      duration: api?.track?.duration,
      n: cars.length,
      unique: new Set(cars.map((c) => `${c.lng.toFixed(5)},${c.lat.toFixed(5)}`)).size,
      pxGaps,
      maxPx: pxGaps.length ? Math.max(...pxGaps) : 0,
      fill: anim.fill,
      pathway: vis("candidate") && vis("candidate-mode") && vis("krl-existing-line") && vis("tj-existing-line"),
      simRouteVis: map?.getLayer?.("sim-route") ? map.getLayoutProperty("sim-route", "visibility") : "missing",
      casingVis: map?.getLayer?.("sim-congestion-casing") ? map.getLayoutProperty("sim-congestion-casing", "visibility") : "missing",
      opacity: map?.getLayer?.("sim-route") ? map.getPaintProperty("sim-route", "line-opacity") : 0,
      gradientKind: Array.isArray(gradient) ? gradient[0] : null,
      gradientProp: Array.isArray(gradient) ? JSON.stringify(gradient[2]) : null,
      gColors: [...new Set(gColors)],
      gAllBn: gColors.length > 0 && gColors.every((c) => ["#DC2626", "#EAB308", "#16A34A"].includes(c)),
      gRaw: Array.isArray(gradient) ? gradient.slice(3, 8) : null,
      metrics,
      shp: bn,
      vehicleOn: vis("sim-vehicle"),
      fills,
      sizeExpr: map?.getLayer?.("sim-vehicle") ? map.getLayoutProperty("sim-vehicle", "icon-size") : null,
      playing: st.simPlaying,
    };
  });
}

function inspect(info, tag, expectN, expectV) {
  check(info.duration === 20, `${tag} 20s`, `${tag} ${info.duration}`);
  check(info.n === expectN, `${tag} ${expectN} unit`, `${tag} n ${info.n}`);
  if (expectN > 1) {
    check(info.unique === expectN, `${tag} separate carriages`, `${tag} unique ${info.unique}`);
    check(info.maxPx > 8 && info.maxPx < 56, `${tag} tight coupling`, `${tag} maxPx ${info.maxPx}`);
  }
  check((info.vehicles || []).includes(expectV), `${tag} vehicle ${expectV}`, `${tag} ${JSON.stringify(info.vehicles)}`);
  check(info.pathway, `${tag} identity pathway still visible`);
  check(info.simRouteVis === "visible", `${tag} SHP congestion visible`, `${tag} sim-route ${info.simRouteVis}`);
  check(info.casingVis === "visible", `${tag} SHP casing visible`, `${tag} casing ${info.casingVis}`);
  check(info.opacity >= 0.8, `${tag} SHP opacity`, `${tag} opacity ${info.opacity}`);
  check(info.gradientKind === "interpolate" && /line-progress/.test(info.gradientProp || ""), `${tag} spatialGradient line-progress`, `${tag} grad ${info.gradientKind} ${info.gradientProp}`);
  check(info.gAllBn && info.gColors.length >= 1, `${tag} SHP uses G/Y/R only`, `${tag} colors ${JSON.stringify(info.gColors)}`);
  check(info.metrics, `${tag} lineMetrics on`);
  check(info.shp?.features >= 1 && info.shp?.coords > 1, `${tag} original SHP features`, `${tag} shp ${JSON.stringify(info.shp)}`);
  check(info.vehicleOn, `${tag} vehicle visible`);
  check(/^#[0-9a-f]{6}$/i.test(info.fill || ""), `${tag} body congestion color`);
  check(info.fills?.length >= 3, `${tag} vehicle reads SHP along path`);
}

const tj = await runPair("Koja", "CASTJ26", "Cengkareng Business City", "CASTJ26");
inspect(tj, "TJ", 1, "bus");
check(tj.km > 20 && tj.km < 40, "CASTJ26 km");
await page.screenshot({ path: "/workspace/screenshots/p29-tj.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.jumpTo({ center: [a.lng, a.lat], zoom: 13 });
});
await page.waitForTimeout(400);
const tjClose = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return {
    vis: map.getLayoutProperty("sim-route", "visibility"),
    op: map.getPaintProperty("sim-route", "line-opacity"),
    dual: map.getLayoutProperty("candidate", "visibility"),
    veh: map.getLayoutProperty("sim-vehicle", "visibility") !== "none",
  };
});
check(tjClose.vis === "visible" && tjClose.op >= 0.8, "TJ close SHP still visible", JSON.stringify(tjClose));
check(tjClose.dual !== "none", "TJ close identity still on");
check(tjClose.veh, "TJ close vehicle on");
await page.screenshot({ path: "/workspace/screenshots/p29-tj-close.png" });

const krl = await runPair("Sentul", "KRL-C04", "Maja", "KRL-C04");
inspect(krl, "KRL", 3, "krl");
await page.screenshot({ path: "/workspace/screenshots/p29-krl.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.jumpTo({ center: [a.lng, a.lat], zoom: 13.2 });
});
await page.waitForTimeout(300);
const krlClose = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const api = window.__CASCADE_ANIM_API;
  const cars = api?.sample ? api.sample(10) : [];
  const px = [];
  for (let i = 1; i < cars.length; i++) {
    const p0 = map.project([cars[i - 1].lng, cars[i - 1].lat]);
    const p1 = map.project([cars[i].lng, cars[i].lat]);
    px.push(Math.round(Math.hypot(p0.x - p1.x, p0.y - p1.y)));
  }
  return {
    n: cars.length,
    px,
    pathway: map.getLayoutProperty("krl-existing-line", "visibility") !== "none",
    shp: map.getLayoutProperty("sim-route", "visibility"),
    op: map.getPaintProperty("sim-route", "line-opacity"),
  };
});
check(krlClose.n === 3, "KRL close 3 cars");
check(krlClose.px.every((p) => p > 10 && p < 56), "KRL close tight", "KRL close px " + krlClose.px);
check(krlClose.pathway, "KRL identity visible at close zoom");
check(krlClose.shp === "visible" && krlClose.op >= 0.8, "KRL SHP visible at close zoom", JSON.stringify(krlClose));
await page.screenshot({ path: "/workspace/screenshots/p29-krl-close.png" });

const lrt = await runPair("Cibubur Junction", "CAS-LRT-C02", "Mekarsari", "CAS-LRT-C02");
inspect(lrt, "LRT", 3, "lrt");
await page.screenshot({ path: "/workspace/screenshots/p29-lrt.png" });

const mrt = await runPair("Lebak Bulus", "MRT-CASCADE-01", "ICE BSD", "MRT-CASCADE-01");
inspect(mrt, "MRT", 3, "mrt");
await page.screenshot({ path: "/workspace/screenshots/p29-mrt.png" });

const multi = await runPair("Pinang Ranti", "CASTJ16", "ICE BSD", "MRT-CASCADE-01");
check((multi.vehicles || []).includes("bus") && (multi.vehicles || []).includes("mrt"), "multimodal bus→MRT", JSON.stringify(multi.vehicles));
check(multi.pathway, "multimodal identity visible");
check(multi.simRouteVis === "visible", "multimodal SHP visible", "multi sim-route " + multi.simRouteVis);
check(multi.duration === 20, "multimodal 20s");
check(multi.gAllBn, "multimodal SHP G/Y/R", JSON.stringify(multi.gColors));

const engine = await page.evaluate(() => {
  const { peakScore, klassOf } = window.__CASCADE_BN;
  return {
    jelambar: klassOf(peakScore(106.786, -6.166, "existing")),
    ciputat: klassOf(peakScore(106.747, -6.317, "existing")),
    calm: klassOf(peakScore(106.833, -6.128, "existing")),
  };
});
check(engine.jelambar === "tinggi", "engine red at Jelambar existing", "jelambar " + engine.jelambar);
check(engine.ciputat === "tinggi", "engine red at Ciputat existing", "ciputat " + engine.ciputat);
check(engine.calm !== "tinggi", "engine calm is not red", "calm " + engine.calm);

await page.getByLabel("Mode jaringan simulasi").selectOption("existing");
const exist = await runPair("Grogol", "Grogol", "Jakarta Kota", "Jakarta Kota");
check((exist.gColors || []).includes("#DC2626") || (exist.gColors || []).includes("#DC2626"), "existing Grogol SHP has red", JSON.stringify(exist.gColors));
check((exist.gColors || []).length >= 1 && exist.simRouteVis === "visible", "existing SHP visible");
await page.screenshot({ path: "/workspace/screenshots/p29-existing-red.png" });

const mixed = [tj, krl, lrt, mrt, multi, exist].some((x) => (x.gColors || []).length >= 2);
check(mixed, "at least one corridor has 2+ SHP colors", "all corridors single color");
const anyRed = [tj, krl, lrt, mrt, multi, exist].some((x) => (x.gColors || []).includes("#DC2626"));
const anyYel = [tj, krl, lrt, mrt, multi, exist].some((x) => (x.gColors || []).includes("#EAB308"));
const anyGrn = [tj, krl, lrt, mrt, multi, exist].some((x) => (x.gColors || []).includes("#16A34A"));
check(anyRed, "red SHP segment present", "red missing " + JSON.stringify({ tj: tj.gColors, krl: krl.gColors, lrt: lrt.gColors, mrt: mrt.gColors, multi: multi.gColors, exist: exist.gColors, raw: exist.gRaw }));
check(anyYel, "yellow SHP segment present");
check(anyGrn, "green SHP segment present");

const z11 = Array.isArray(tj.sizeExpr) ? tj.sizeExpr[tj.sizeExpr.indexOf(11) + 1] : null;
check(z11 >= 0.65 && z11 <= 1.35, "scale still ~1.5×", "z11 " + z11);

const afterPlay = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  return {
    vis: map.getLayoutProperty("sim-route", "visibility"),
    op: map.getPaintProperty("sim-route", "line-opacity"),
    dual: map.getLayoutProperty("candidate-mode", "visibility"),
  };
});
check(afterPlay.vis === "visible" && afterPlay.op >= 0.8, "SHP remains after animation", JSON.stringify(afterPlay));
check(afterPlay.dual !== "none", "identity remains after animation");

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
