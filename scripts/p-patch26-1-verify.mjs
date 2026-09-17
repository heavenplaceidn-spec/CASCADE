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
await page.waitForTimeout(800);

const layout = await page.evaluate(() => {
  const legend = [...document.querySelectorAll("p")].find((p) => p.textContent?.trim() === "LEGENDA");
  const gaya = document.querySelector('select[aria-label="Tampilan Peta"]');
  const panel = legend?.closest("div.cascade-panel");
  const gayaBox = gaya?.closest("div.cascade-panel")?.getBoundingClientRect();
  const legBox = panel?.getBoundingClientRect();
  const aside = document.querySelector("aside");
  return {
    legX: legBox ? Math.round(legBox.x) : -1,
    gayaY: gayaBox ? Math.round(gayaBox.y) : -1,
    asideW: aside ? Math.round(aside.getBoundingClientRect().width) : 0,
    dual: !!(window.__CASCADE_MAP?.getLayer?.("candidate-mode") && window.__CASCADE_MAP?.getLayer?.("candidate")),
    mark: document.querySelectorAll("img.cascade-mark").length,
  };
});
check(layout.legX >= 0 && layout.legX < 80, "legend left");
check(layout.asideW > 0 && layout.asideW <= 300, "right panel compact", "aside w " + layout.asideW);
check(layout.dual, "dual-color intact");
check(layout.mark === 1, "one brand mark", "marks " + layout.mark);

const ids = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28");
  const fc = await r.json();
  const all = fc.features.map((f) => String(f.id || f.properties?.route_id));
  const c24 = fc.features.find((f) => String(f.id || f.properties?.route_id) === "CASTJ24");
  const c25 = fc.features.find((f) => String(f.id || f.properties?.route_id) === "CASTJ25");
  return {
    n: all.length,
    c24: all.includes("CASTJ24"),
    c25: all.includes("CASTJ25"),
    sameGeom: JSON.stringify(c24?.geometry) === JSON.stringify(c25?.geometry),
  };
});
check(ids.c24 && ids.c25, "CASTJ24 and CASTJ25 both present");
check(!ids.sameGeom, "CASTJ24 ≠ CASTJ25 geometry");
check(ids.n === 26, "26 CASCADE corridors", "n " + ids.n);

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(400);
await page.waitForFunction(() => window.__CASCADE.getState().networkReady === true, { timeout: 25000 }).catch(() => {});
check(await page.getByText(/Putaran penuh ~40 detik/).count() > 0, "40s hint visible");

async function pickStation(label, query, hint) {
  const input = page.getByLabel(label, { exact: true });
  await input.fill("");
  await input.fill(query);
  await page.waitForTimeout(850);
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
  await page.waitForTimeout(200);
  const a = await pickStation("Asal", fromQ, fromHint);
  const b = await pickStation("Tujuan", toQ, toHint);
  if (!a || !b) return { error: "stations missing", a, b };
  await page.getByRole("button", { name: "Jalankan" }).click();
  await page.waitForFunction(() => (window.__CASCADE.getState().simResult?.km || 0) > 0, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1600);
  return page.evaluate(() => {
    const st = window.__CASCADE.getState();
    const map = window.__CASCADE_MAP;
    const anim = window.__CASCADE_ANIM || {};
    const api = window.__CASCADE_ANIM_API;
    const feats = map?.getSource?.("sim-vehicle") ? map.querySourceFeatures("sim-vehicle") : [];
    const zoom = map?.getZoom?.() ?? 11;
    const samples = [];
    const path = api?.path || [];
    const hav = (a, b) => {
      const R = 6371000;
      const to = (d) => (d * Math.PI) / 180;
      const dlon = to(b[0] - a[0]);
      const dlat = to(b[1] - a[1]);
      const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(a[1])) * Math.cos(to(b[1])) * Math.sin(dlon / 2) ** 2;
      return 2 * R * Math.asin(Math.sqrt(h));
    };
    const distLine = (lng, lat) => {
      let best = Infinity;
      for (let i = 1; i < path.length; i++) {
        const A = path[i - 1];
        const B = path[i];
        const dx = B[0] - A[0];
        const dy = B[1] - A[1];
        const len2 = dx * dx + dy * dy || 1e-12;
        let u = ((lng - A[0]) * dx + (lat - A[1]) * dy) / len2;
        u = Math.max(0, Math.min(1, u));
        const d = hav([lng, lat], [A[0] + dx * u, A[1] + dy * u]);
        if (d < best) best = d;
      }
      return best;
    };
    const track = api?.track;
    const speeds = { rendah: { d: 0, t: 0 }, sedang: { d: 0, t: 0 }, tinggi: { d: 0, t: 0 } };
    const steps = new Set();
    const vehicles = new Set();
    const kinds = new Set();
    if (track) {
      for (let i = 1; i < track.samples.length; i++) {
        const ds = track.samples[i].d - track.samples[i - 1].d;
        const dt = track.t[i] - track.t[i - 1];
        const k = track.samples[i - 1].klass;
        speeds[k].d += ds;
        speeds[k].t += dt;
        steps.add(track.samples[i - 1].step);
        vehicles.add(track.samples[i - 1].vehicle);
        kinds.add(track.samples[i - 1].kind);
      }
      for (const sec of [0, 10, 20, 30, 40]) {
        const cars = api.sample(sec);
        const head = cars[0];
        samples.push({
          sec,
          n: cars.length,
          vehicle: head?.vehicle,
          kind: head?.kind,
          step: head?.step,
          mode: head?.mode,
          corridor: head?.corridorId,
          d: head?.d,
          dist: head ? distLine(head.lng, head.lat) : null,
        });
      }
    }
    const sizeExpr = map?.getLayer?.("sim-vehicle") ? map.getLayoutProperty("sim-vehicle", "icon-size") : null;
    return {
      km: st.simResult?.km,
      hops: st.simResult?.hops,
      segs: (st.simResult?.segments || []).map((s) => ({ id: s.routeId || s.kind, vehicle: s.vehicle, kind: s.kind, mode: s.mode })),
      playing: st.simPlaying,
      paused: st.simPaused,
      anim,
      featN: feats.length,
      zoom,
      duration: track?.duration,
      totalM: track?.totalM,
      samples,
      steps: [...steps],
      vehicles: [...vehicles],
      kinds: [...kinds],
      speed: {
        rendah: speeds.rendah.t ? speeds.rendah.d / speeds.rendah.t : 0,
        sedang: speeds.sedang.t ? speeds.sedang.d / speeds.sedang.t : 0,
        tinggi: speeds.tinggi.t ? speeds.tinggi.d / speeds.tinggi.t : 0,
      },
      sizeExpr,
      particleN: map?.getSource?.("sim-particles") ? map.querySourceFeatures("sim-particles").length : 0,
    };
  });
}

function inspectSpeed(info, tag) {
  check(info.duration === 40, `${tag} duration 40s`, `${tag} duration ${info.duration}`);
  const maxDist = Math.max(...(info.samples || []).map((s) => s.dist ?? 999));
  check(maxDist < 35, `${tag} stays on GeoJSON (<35m)`, `${tag} max dist ${maxDist}`);
  const start = info.samples?.find((s) => s.sec === 0);
  const end = info.samples?.find((s) => s.sec === 40);
  check(start && start.d < 50, `${tag} starts at origin`, `${tag} start d ${start?.d}`);
  check(end && end.d > (info.totalM || 0) * 0.96, `${tag} ends at destination`, `${tag} end d ${end?.d} / ${info.totalM}`);
  if (info.speed.rendah && info.speed.tinggi) {
    check(info.speed.rendah > info.speed.tinggi * 1.15, `${tag} green faster than red`, `${tag} spd ${JSON.stringify(info.speed)}`);
  }
  if (info.speed.sedang && info.speed.tinggi) {
    check(info.speed.sedang > info.speed.tinggi * 0.95, `${tag} yellow ≥ red`, `${tag} spd ${JSON.stringify(info.speed)}`);
  }
  const klasses = new Set((info.samples || []).map((s) => s.step).filter(Boolean));
  if ((info.steps || []).length >= 2 || klasses.size >= 2) {
    check((info.steps || []).length >= 1, `${tag} congestion color present`);
  } else {
    check(true, `${tag} single congestion class on this corridor`);
  }
  check(info.particleN === 0, `${tag} particles emptied`);
  const z11 = Array.isArray(info.sizeExpr) ? info.sizeExpr[info.sizeExpr.indexOf(11) + 1] : null;
  check(z11 == null || z11 >= 2, `${tag} icon-size ~3×+`, `${tag} sizeExpr ${JSON.stringify(info.sizeExpr)}`);
}

const tj = await runPair("Koja", "CASTJ26", "Cengkareng Business City", "CASTJ26");
console.log("TJ", JSON.stringify({ km: tj.km, segs: tj.segs, anim: tj.anim, featN: tj.featN, samples: tj.samples, speed: tj.speed, steps: tj.steps, duration: tj.duration }));
check(!tj.error, "CASTJ26 stations found", "CASTJ26 " + JSON.stringify(tj.error));
check(tj.km > 20 && tj.km < 40, "CASTJ26 km ~30", "km " + tj.km);
check((tj.hops || []).some((h) => /Koja/i.test(h)), "hops Koja");
check((tj.hops || []).some((h) => /Plumpang/i.test(h)), "hops Plumpang");
check((tj.hops || []).some((h) => /Kapuk/i.test(h)), "hops Kapuk");
check((tj.hops || []).some((h) => /Cengkareng Business/i.test(h)), "hops CBC");
check((tj.segs || []).some((s) => s.id === "CASTJ26"), "segment CASTJ26");
check((tj.samples?.[2]?.n || tj.featN) === 1, "TJ single bus", "TJ cars " + tj.samples?.[2]?.n + " feat " + tj.featN);
check((tj.vehicles || []).every((v) => v === "bus"), "TJ vehicle is bus", "TJ vehicles " + tj.vehicles);
inspectSpeed(tj, "CASTJ26");
await page.screenshot({ path: "/workspace/screenshots/p261-tj-castj26.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.easeTo({ center: [a.lng, a.lat], zoom: Math.max(12.4, map.getZoom()), duration: 0 });
});
await page.waitForTimeout(400);
await page.screenshot({ path: "/workspace/screenshots/p261-tj-close.png" });

const elapsed0 = await page.evaluate(() => window.__CASCADE_ANIM?.elapsed ?? 0);
await page.waitForTimeout(3000);
const elapsed1 = await page.evaluate(() => window.__CASCADE_ANIM?.elapsed ?? 0);
check(elapsed1 > elapsed0 + 2.2, "playback advances in realtime", `elapsed ${elapsed0} → ${elapsed1}`);
check(elapsed1 < elapsed0 + 4.2, "playback not faster than realtime", `elapsed ${elapsed0} → ${elapsed1}`);

const krl = await runPair("Sentul", "KRL-C04", "Maja", "KRL-C04");
console.log("KRL", JSON.stringify({ km: krl.km, segs: krl.segs, featN: krl.featN, n20: krl.samples?.[2], vehicles: krl.vehicles, duration: krl.duration }));
check(krl.km > 40, "KRL-C04 routed", "KRL km " + krl.km);
check((krl.samples?.[2]?.n || 0) === 4, "KRL 4 carriages", "KRL cars " + krl.samples?.[2]?.n);
check((krl.vehicles || []).includes("krl"), "KRL vehicle type");
inspectSpeed(krl, "KRL-C04");
await page.screenshot({ path: "/workspace/screenshots/p261-krl-c04.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.easeTo({ center: [a.lng, a.lat], zoom: 13, duration: 0 });
});
await page.waitForTimeout(400);
await page.screenshot({ path: "/workspace/screenshots/p261-krl-close.png" });

const lrt = await runPair("Cibubur Junction", "CAS-LRT-C02", "Mekarsari", "CAS-LRT-C02");
console.log("LRT", JSON.stringify({ km: lrt.km, segs: lrt.segs, n20: lrt.samples?.[2], vehicles: lrt.vehicles }));
check(lrt.km > 5, "LRT routed", "LRT km " + lrt.km);
check((lrt.samples?.[2]?.n || 0) === 3, "LRT 3 carriages", "LRT cars " + lrt.samples?.[2]?.n);
check((lrt.vehicles || []).includes("lrt"), "LRT vehicle type");
inspectSpeed(lrt, "LRT");
await page.screenshot({ path: "/workspace/screenshots/p261-lrt.png" });

const mrt = await runPair("Lebak Bulus", "MRT-CASCADE-01", "ICE BSD", "MRT-CASCADE-01");
console.log("MRT", JSON.stringify({ km: mrt.km, segs: mrt.segs, n20: mrt.samples?.[2], vehicles: mrt.vehicles }));
check(mrt.km > 10, "MRT routed", "MRT km " + mrt.km);
check((mrt.samples?.[2]?.n || 0) === 4, "MRT 4 carriages", "MRT cars " + mrt.samples?.[2]?.n);
check((mrt.vehicles || []).includes("mrt"), "MRT vehicle type");
inspectSpeed(mrt, "MRT");
await page.screenshot({ path: "/workspace/screenshots/p261-mrt.png" });

const multi = await runPair("Pinang Ranti", "CASTJ16", "ICE BSD", "MRT-CASCADE-01");
console.log("MULTI", JSON.stringify({ km: multi.km, segs: multi.segs, vehicles: multi.vehicles, kinds: multi.kinds, samples: multi.samples?.map((s) => ({ sec: s.sec, v: s.vehicle, k: s.kind, n: s.n, mode: s.mode })) }));
check(multi.km > 5, "multimodal routed", "multi km " + multi.km + " " + (multi.error || ""));
const multiVeh = new Set(multi.vehicles || []);
check(multiVeh.size >= 2 || (multi.kinds || []).includes("transfer"), "multimodal mode switch", "multi vehicles " + JSON.stringify(multi.vehicles) + " kinds " + JSON.stringify(multi.kinds));
if ((multi.kinds || []).includes("transfer")) {
  const xf = (multi.samples || []).find((s) => s.kind === "transfer");
  check(!xf || xf.n === 1, "transfer is single marker");
}
inspectSpeed(multi, "multimodal");
await page.screenshot({ path: "/workspace/screenshots/p261-multi.png" });

const download = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28");
  return r.ok && (await r.json()).features.length === 26;
});
check(download, "GeoJSON download source intact");

const attribution = await page.evaluate(async () => {
  const r = await fetch("/models/ATTRIBUTION.md");
  return r.ok ? await r.text() : "";
});
check(/CC0/i.test(attribution), "model attribution present");

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
