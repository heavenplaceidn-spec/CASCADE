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
  const panel = legend?.closest("div.cascade-panel");
  const text = panel?.textContent || "";
  const aside = document.querySelector("aside");
  return {
    legX: panel ? Math.round(panel.getBoundingClientRect().x) : -1,
    asideW: aside ? Math.round(aside.getBoundingClientRect().width) : 0,
    dual: !!(window.__CASCADE_MAP?.getLayer?.("candidate-mode") && window.__CASCADE_MAP?.getLayer?.("candidate")),
    mark: document.querySelectorAll("img.cascade-mark").length,
    status: /STATUS GARIS/.test(text),
    existingSolid: /Existing/.test(text) && /Sudah tersedia/.test(text),
    mpDash: /Masterplan/.test(text) && /Rencana/.test(text),
    casDash: /CASCADE/.test(text) && /Usulan/.test(text),
    solidNote: /garis solid/.test(text),
    dashNote: /garis putus-putus/.test(text),
    lineSamples: panel ? panel.querySelectorAll(".legend-dual").length : 0,
  };
});
check(layout.legX >= 0 && layout.legX < 80, "legend left");
check(layout.asideW > 0 && layout.asideW <= 300, "right panel compact", "aside w " + layout.asideW);
check(layout.dual, "dual-color intact");
check(layout.mark === 1, "one brand mark", "marks " + layout.mark);
check(layout.status, "legend STATUS GARIS");
check(layout.existingSolid, "legend Existing = sudah tersedia");
check(layout.mpDash, "legend Masterplan = rencana");
check(layout.casDash, "legend CASCADE = usulan");
check(layout.solidNote, "legend solid note");
check(layout.dashNote, "legend dashed note");
check(layout.lineSamples >= 12, "legend uses line samples", "samples " + layout.lineSamples);

const ids = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28");
  const fc = await r.json();
  const all = fc.features.map((f) => String(f.id || f.properties?.route_id));
  const c24 = fc.features.find((f) => String(f.id || f.properties?.route_id) === "CASTJ24");
  const c25 = fc.features.find((f) => String(f.id || f.properties?.route_id) === "CASTJ25");
  return { n: all.length, c24: all.includes("CASTJ24"), c25: all.includes("CASTJ25"), sameGeom: JSON.stringify(c24?.geometry) === JSON.stringify(c25?.geometry) };
});
check(ids.c24 && ids.c25, "CASTJ24 and CASTJ25 both present");
check(!ids.sameGeom, "CASTJ24 ≠ CASTJ25 geometry");
check(ids.n === 26, "26 CASCADE corridors", "n " + ids.n);

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(400);
await page.waitForFunction(() => window.__CASCADE.getState().networkReady === true, { timeout: 25000 }).catch(() => {});
check((await page.getByText(/Putaran penuh ~20 detik/).count()) > 0, "20s hint visible");

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
  await page.waitForTimeout(1400);
  return page.evaluate(() => {
    const st = window.__CASCADE.getState();
    const map = window.__CASCADE_MAP;
    const anim = window.__CASCADE_ANIM || {};
    const api = window.__CASCADE_ANIM_API;
    const path = api?.path || [];
    const hav = (A, B) => {
      const R = 6371000;
      const to = (d) => (d * Math.PI) / 180;
      const dlon = to(B[0] - A[0]);
      const dlat = to(B[1] - A[1]);
      const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(A[1])) * Math.cos(to(B[1])) * Math.sin(dlon / 2) ** 2;
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
    const vehicles = new Set();
    const kinds = new Set();
    const bns = new Set();
    if (track) {
      for (let i = 1; i < track.samples.length; i++) {
        const ds = track.samples[i].d - track.samples[i - 1].d;
        const dt = track.t[i] - track.t[i - 1];
        const k = track.samples[i - 1].klass;
        speeds[k].d += ds;
        speeds[k].t += dt;
        vehicles.add(track.samples[i - 1].vehicle);
        kinds.add(track.samples[i - 1].kind);
        bns.add(Number(track.samples[i - 1].bn.toFixed(2)));
      }
    }
    const samples = [];
    if (api?.sample) {
      for (const sec of [0, 10, 20]) {
        const cars = api.sample(sec);
        const head = cars[0];
        const gaps = [];
        for (let i = 1; i < cars.length; i++) gaps.push(Math.abs((cars[i - 1].d ?? 0) - (cars[i].d ?? 0)));
        samples.push({
          sec,
          n: cars.length,
          vehicle: head?.vehicle,
          kind: head?.kind,
          mode: head?.mode,
          corridor: head?.corridorId,
          d: head?.d,
          dist: head ? distLine(head.lng, head.lat) : null,
          uniquePos: new Set(cars.map((c) => `${c.lng.toFixed(5)},${c.lat.toFixed(5)}`)).size,
          minGap: gaps.length ? Math.min(...gaps) : 0,
        });
      }
    }
    const sizeExpr = map?.getLayer?.("sim-vehicle") ? map.getLayoutProperty("sim-vehicle", "icon-size") : null;
    const trail = map?.getLayer?.("sim-route") ? map.getPaintProperty("sim-route", "line-gradient") : "none";
    const halo = map?.getLayer?.("sim-vehicle") ? map.getPaintProperty("sim-vehicle", "icon-halo-width") : null;
    return {
      km: st.simResult?.km,
      hops: st.simResult?.hops,
      segs: (st.simResult?.segments || []).map((s) => ({ id: s.routeId || s.kind, vehicle: s.vehicle, kind: s.kind, mode: s.mode })),
      anim,
      duration: track?.duration,
      totalM: track?.totalM,
      samples,
      vehicles: [...vehicles],
      kinds: [...kinds],
      bnRange: bns.size,
      speed: {
        rendah: speeds.rendah.t ? speeds.rendah.d / speeds.rendah.t : 0,
        sedang: speeds.sedang.t ? speeds.sedang.d / speeds.sedang.t : 0,
        tinggi: speeds.tinggi.t ? speeds.tinggi.d / speeds.tinggi.t : 0,
      },
      sizeExpr,
      trail,
      halo,
      particleN: map?.getSource?.("sim-particles") ? map.querySourceFeatures("sim-particles").length : 0,
      chrome: !!map?.getLayer?.("sim-vehicle-chrome"),
    };
  });
}

function inspect(info, tag) {
  check(info.duration === 20, `${tag} duration 20s`, `${tag} duration ${info.duration}`);
  const maxDist = Math.max(...(info.samples || []).map((s) => s.dist ?? 999));
  check(maxDist < 35, `${tag} stays on GeoJSON (<35m)`, `${tag} max dist ${maxDist}`);
  const start = info.samples?.find((s) => s.sec === 0);
  const end = info.samples?.find((s) => s.sec === 20);
  check(start && start.d < 50, `${tag} starts at origin`, `${tag} start d ${start?.d}`);
  check(end && end.d > (info.totalM || 0) * 0.96, `${tag} ends at destination`, `${tag} end d ${end?.d} / ${info.totalM}`);
  check(info.particleN === 0, `${tag} no particle trail`);
  check(!info.trail, `${tag} no congestion trail line`, `${tag} trail ${info.trail}`);
  check(info.halo === 0 || info.halo == null, `${tag} no icon halo trail`, `${tag} halo ${info.halo}`);
  check(info.chrome, `${tag} chrome overlay`);
  check(/^#[0-9a-f]{6}$/i.test(info.anim?.fill || ""), `${tag} body color hex`, `${tag} fill ${info.anim?.fill}`);
  const nums = Array.isArray(info.sizeExpr) ? info.sizeExpr.filter((x) => typeof x === "number" && x < 8) : [];
  const z11 = Array.isArray(info.sizeExpr) ? info.sizeExpr[info.sizeExpr.indexOf(11) + 1] : null;
  check(z11 == null || (z11 >= 0.65 && z11 <= 1.35), `${tag} icon-size ~1.5× original`, `${tag} sizeExpr ${JSON.stringify(info.sizeExpr)} nums ${JSON.stringify(nums)}`);
}

const tj = await runPair("Koja", "CASTJ26", "Cengkareng Business City", "CASTJ26");
console.log("TJ", JSON.stringify({ km: tj.km, segs: tj.segs, anim: tj.anim, samples: tj.samples, duration: tj.duration, trail: tj.trail, fill: tj.anim?.fill }));
check(!tj.error, "CASTJ26 stations found", "CASTJ26 " + JSON.stringify(tj.error));
check(tj.km > 20 && tj.km < 40, "CASTJ26 km ~30", "km " + tj.km);
check((tj.hops || []).some((h) => /Koja/i.test(h)), "hops Koja");
check((tj.hops || []).some((h) => /Cengkareng Business/i.test(h)), "hops CBC");
check((tj.segs || []).some((s) => s.id === "CASTJ26"), "segment CASTJ26");
check((tj.samples?.[1]?.n || 0) === 1, "TJ single bus", "TJ cars " + tj.samples?.[1]?.n);
check((tj.vehicles || []).every((v) => v === "bus"), "TJ vehicle is bus", "TJ vehicles " + tj.vehicles);
inspect(tj, "CASTJ26");
await page.screenshot({ path: "/workspace/screenshots/p27-tj.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.easeTo({ center: [a.lng, a.lat], zoom: 13, duration: 0 });
});
await page.waitForTimeout(350);
await page.screenshot({ path: "/workspace/screenshots/p27-tj-close.png" });

const elapsed0 = await page.evaluate(() => window.__CASCADE_ANIM?.elapsed ?? 0);
await page.waitForTimeout(2500);
const elapsed1 = await page.evaluate(() => window.__CASCADE_ANIM?.elapsed ?? 0);
check(elapsed1 > elapsed0 + 1.8, "playback advances in realtime", `elapsed ${elapsed0} → ${elapsed1}`);
check(elapsed1 < elapsed0 + 3.4, "playback not faster than realtime", `elapsed ${elapsed0} → ${elapsed1}`);

const krl = await runPair("Sentul", "KRL-C04", "Maja", "KRL-C04");
console.log("KRL", JSON.stringify({ km: krl.km, n10: krl.samples?.[1], vehicles: krl.vehicles, duration: krl.duration }));
check(krl.km > 40, "KRL-C04 routed", "KRL km " + krl.km);
check((krl.samples?.[1]?.n || 0) === 4, "KRL 4 carriages", "KRL cars " + krl.samples?.[1]?.n);
check((krl.samples?.[1]?.uniquePos || 0) >= 4, "KRL carriages are separate points", "KRL unique " + krl.samples?.[1]?.uniquePos);
check((krl.samples?.[1]?.minGap || 0) > 8, "KRL carriage gap", "KRL gap " + krl.samples?.[1]?.minGap);
check((krl.vehicles || []).includes("krl"), "KRL vehicle type");
inspect(krl, "KRL-C04");
await page.screenshot({ path: "/workspace/screenshots/p27-krl.png" });
await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const a = window.__CASCADE_ANIM;
  if (map && a?.lng) map.easeTo({ center: [a.lng, a.lat], zoom: 13.2, duration: 0 });
});
await page.waitForTimeout(350);
await page.screenshot({ path: "/workspace/screenshots/p27-krl-close.png" });

const lrt = await runPair("Cibubur Junction", "CAS-LRT-C02", "Mekarsari", "CAS-LRT-C02");
check(lrt.km > 5, "LRT routed", "LRT km " + lrt.km);
check((lrt.samples?.[1]?.n || 0) === 3, "LRT 3 carriages", "LRT cars " + lrt.samples?.[1]?.n);
check((lrt.samples?.[1]?.uniquePos || 0) >= 3, "LRT carriages separate", "LRT unique " + lrt.samples?.[1]?.uniquePos);
check((lrt.vehicles || []).includes("lrt"), "LRT vehicle type");
inspect(lrt, "LRT");
await page.screenshot({ path: "/workspace/screenshots/p27-lrt.png" });

const mrt = await runPair("Lebak Bulus", "MRT-CASCADE-01", "ICE BSD", "MRT-CASCADE-01");
check(mrt.km > 10, "MRT routed", "MRT km " + mrt.km);
check((mrt.samples?.[1]?.n || 0) === 4, "MRT 4 carriages", "MRT cars " + mrt.samples?.[1]?.n);
check((mrt.samples?.[1]?.uniquePos || 0) >= 4, "MRT carriages separate", "MRT unique " + mrt.samples?.[1]?.uniquePos);
check((mrt.vehicles || []).includes("mrt"), "MRT vehicle type");
inspect(mrt, "MRT");
await page.screenshot({ path: "/workspace/screenshots/p27-mrt.png" });

const multi = await runPair("Pinang Ranti", "CASTJ16", "ICE BSD", "MRT-CASCADE-01");
console.log("MULTI", JSON.stringify({ km: multi.km, segs: multi.segs, vehicles: multi.vehicles, samples: (multi.samples || []).map((s) => ({ sec: s.sec, v: s.vehicle, n: s.n, mode: s.mode })) }));
check(multi.km > 5, "multimodal routed", "multi km " + multi.km);
check((multi.vehicles || []).includes("bus") && (multi.vehicles || []).some((v) => v === "mrt" || v === "krl" || v === "lrt"), "multimodal mode switch", "multi vehicles " + JSON.stringify(multi.vehicles));
inspect(multi, "multimodal");

const dl = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28");
  const fc = await r.json();
  const f = fc.features.find((x) => String(x.id || x.properties?.route_id) === "CASTJ26");
  return { ok: !!f && f.geometry?.type === "LineString", n: f?.geometry?.coordinates?.length || 0 };
});
check(dl.ok && dl.n > 100, "GeoJSON download source intact", JSON.stringify(dl));

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
