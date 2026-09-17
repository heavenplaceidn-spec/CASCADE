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
    simRoute: m?.getLayer?.("sim-route") ? m.getLayoutProperty("sim-route", "visibility") : "missing",
    mark: document.querySelectorAll("img.cascade-mark").length,
    status: /STATUS GARIS/.test(document.body.innerText || ""),
  };
});
check(layout.dual, "dual-color pathway layers on");
check(layout.simRoute === "none" || layout.simRoute === "missing", "sim-route hidden", "sim-route " + layout.simRoute);
check(layout.mark === 1, "one brand mark");
check(layout.status, "legend STATUS GARIS");

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
  await page.waitForTimeout(1200);
  return page.evaluate(() => {
    const st = window.__CASCADE.getState();
    const map = window.__CASCADE_MAP;
    const anim = window.__CASCADE_ANIM || {};
    const api = window.__CASCADE_ANIM_API;
    const vis = (id) => map?.getLayer?.(id) && map.getLayoutProperty(id, "visibility") !== "none";
    const cars = api?.sample ? api.sample(10) : [];
    const pxGaps = [];
    for (let i = 1; i < cars.length; i++) {
      const p0 = map.project([cars[i - 1].lng, cars[i - 1].lat]);
      const p1 = map.project([cars[i].lng, cars[i].lat]);
      pxGaps.push(Math.hypot(p0.x - p1.x, p0.y - p1.y));
    }
    const bodies = [...new Set(cars.map((c, i) => {
      const v = c.vehicle;
      if (v === "bus") return "bus";
      if (i === 0) return v + "-front";
      return v + "-car";
    }))];
    return {
      km: st.simResult?.km,
      segs: (st.simResult?.segments || []).map((s) => s.routeId || s.kind),
      vehicles: [...new Set((st.simResult?.segments || []).map((s) => s.vehicle))],
      duration: api?.track?.duration,
      n: cars.length,
      unique: new Set(cars.map((c) => `${c.lng.toFixed(5)},${c.lat.toFixed(5)}`)).size,
      pxGaps,
      maxPx: pxGaps.length ? Math.max(...pxGaps) : 0,
      bodies,
      fill: anim.fill,
      pathway: vis("candidate") && vis("candidate-mode") && vis("krl-existing-line") && vis("tj-existing-line"),
      simRouteVis: map?.getLayer?.("sim-route") ? map.getLayoutProperty("sim-route", "visibility") : "missing",
      trail: map?.getLayer?.("sim-route") ? map.getPaintProperty("sim-route", "line-opacity") : 0,
      halo: map?.getLayer?.("sim-vehicle") ? map.getPaintProperty("sim-vehicle", "icon-halo-width") : 0,
      sizeExpr: map?.getLayer?.("sim-vehicle") ? map.getLayoutProperty("sim-vehicle", "icon-size") : null,
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
  check(info.pathway, `${tag} original pathway still visible`);
  check(info.simRouteVis === "none" || info.simRouteVis === "missing", `${tag} no animation polyline`, `${tag} sim-route ${info.simRouteVis}`);
  check(!info.trail, `${tag} no trail opacity`, `${tag} trail ${info.trail}`);
  check(/^#[0-9a-f]{6}$/i.test(info.fill || ""), `${tag} body congestion color`);
}

const tj = await runPair("Koja", "CASTJ26", "Cengkareng Business City", "CASTJ26");
inspect(tj, "TJ", 1, "bus");
check(tj.km > 20 && tj.km < 40, "CASTJ26 km");
await page.screenshot({ path: "/workspace/screenshots/p28-tj.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.jumpTo({ center: [a.lng, a.lat], zoom: 13 });
});
await page.waitForTimeout(300);
await page.screenshot({ path: "/workspace/screenshots/p28-tj-close.png" });

const krl = await runPair("Sentul", "KRL-C04", "Maja", "KRL-C04");
inspect(krl, "KRL", 3, "krl");
await page.screenshot({ path: "/workspace/screenshots/p28-krl.png" });
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
  return { n: cars.length, px, pathway: map.getLayoutProperty("krl-existing-line", "visibility") !== "none" };
});
check(krlClose.n === 3, "KRL close 3 cars");
check(krlClose.px.every((p) => p > 10 && p < 56), "KRL close tight", "KRL close px " + krlClose.px);
check(krlClose.pathway, "KRL pathway visible at close zoom");
await page.screenshot({ path: "/workspace/screenshots/p28-krl-close.png" });

const lrt = await runPair("Cibubur Junction", "CAS-LRT-C02", "Mekarsari", "CAS-LRT-C02");
inspect(lrt, "LRT", 3, "lrt");
await page.screenshot({ path: "/workspace/screenshots/p28-lrt.png" });

const mrt = await runPair("Lebak Bulus", "MRT-CASCADE-01", "ICE BSD", "MRT-CASCADE-01");
inspect(mrt, "MRT", 3, "mrt");
await page.screenshot({ path: "/workspace/screenshots/p28-mrt.png" });

const multi = await runPair("Pinang Ranti", "CASTJ16", "ICE BSD", "MRT-CASCADE-01");
check((multi.vehicles || []).includes("bus") && (multi.vehicles || []).includes("mrt"), "multimodal bus→MRT", JSON.stringify(multi.vehicles));
check(multi.pathway, "multimodal pathway visible");
check(multi.duration === 20, "multimodal 20s");

const z11 = Array.isArray(tj.sizeExpr) ? tj.sizeExpr[tj.sizeExpr.indexOf(11) + 1] : null;
check(z11 >= 0.65 && z11 <= 1.35, "scale still ~1.5×", "z11 " + z11);

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
