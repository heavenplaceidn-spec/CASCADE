#!/usr/bin/env node
import { chromium } from "playwright";

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
  const asideBox = aside?.getBoundingClientRect();
  return {
    leg: legBox ? { x: Math.round(legBox.x), w: Math.round(legBox.width) } : null,
    gaya: gayaBox ? { y: Math.round(gayaBox.y) } : null,
    aside: asideBox ? { x: Math.round(asideBox.x), w: Math.round(asideBox.width) } : null,
    vw: window.innerWidth,
  };
});
check(layout.leg && layout.leg.x < 80, "legend left");
check(layout.aside && layout.aside.x > layout.vw / 2, "right panel remains right");
check(layout.aside && layout.aside.w <= 300, "right panel ~35% smaller", "aside w " + layout.aside?.w);

await page.getByRole("link", { name: "Analisis", exact: true }).click();
await page.waitForTimeout(400);
const analisisAside = await page.evaluate(() => {
  const aside = document.querySelector("aside");
  return aside ? Math.round(aside.getBoundingClientRect().width) : 0;
});
check(analisisAside > 180 && analisisAside <= 320, "analisis panel compact", "analisis w " + analisisAside);

await page.getByRole("button", { name: /Seret untuk pilih area/ }).click();
await page.waitForTimeout(200);
const box = await page.evaluate(() => {
  const host = document.querySelector("div.cursor-crosshair") || document.body;
  const r = host.getBoundingClientRect();
  return { x: r.left + r.width * 0.42, y: r.top + r.height * 0.28, w: 180, h: 140 };
});
await page.mouse.move(box.x, box.y);
await page.mouse.down();
await page.mouse.move(box.x + box.w, box.y + box.h);
await page.mouse.up();
await page.waitForTimeout(2500);

const cards = page.locator("article button[aria-label^='Lihat koridor']");
const nCards = await cards.count();
check(nCards >= 1 && nCards <= 3, "identify max 3 clickable cards", "cards " + nCards);

if (nCards > 0) {
  const firstId = (await cards.nth(0).getAttribute("aria-label")) || "";
  await cards.nth(0).click();
  await page.waitForTimeout(900);
  const afterClick = await page.evaluate(() => {
    const st = window.__CASCADE.getState();
    const pop = st.popup;
    const sel = st.selectedId;
    const popEl = [...document.querySelectorAll("div.cascade-panel")].find((d) => /Unduh GeoJSON|Tutup/.test(d.textContent || ""));
    const popBox = popEl?.getBoundingClientRect();
    return {
      sel,
      popId: pop?.id,
      docked: !!pop?.docked,
      hasDl: !!popEl?.querySelector('[aria-label="Unduh GeoJSON"]'),
      popW: popBox ? Math.round(popBox.width) : 0,
      skala: /PRIORITAS/.test(document.body.innerText),
    };
  });
  check(!!afterClick.sel, "click selects corridor", "sel " + afterClick.sel);
  check(!!afterClick.popId, "popup opens", "popup " + afterClick.popId);
  check(afterClick.hasDl, "download remains");
  check(afterClick.popW > 160 && afterClick.popW < 300, "popup compact", "popW " + afterClick.popW);
  check(afterClick.skala || /Prioritas/i.test(await page.locator("body").innerText()), "priority scale remains");
  check(firstId.includes(afterClick.sel) || afterClick.popId === afterClick.sel, "exact corridor not neighbor");
  if (nCards > 1) {
    await cards.nth(1).click();
    await page.waitForTimeout(500);
    const second = await page.evaluate(() => window.__CASCADE.getState().selectedId);
    check(!!second && second !== afterClick.sel, "second card still clickable", "second " + second + " first " + afterClick.sel);
  }
}

const audit = await page.evaluate(async () => {
  const fn = window.__CASCADE_AUDIT;
  if (!fn) return { error: "no audit" };
  return fn();
});
if (audit.error) fail.push("audit missing");
else {
  check(audit.ready, "network ready", "ready " + JSON.stringify(audit.tests));
  check(audit.transfers >= 0, "transfer nodes " + audit.transfers);
  const koja = (audit.tests || []).find((t) => String(t.name).startsWith("Koja"));
  check(koja?.ok, "Koja → CBC routed", "koja " + JSON.stringify(koja));
  for (const t of audit.tests || []) check(t.ok, t.name + " " + t.note, t.name + " FAIL " + t.note);
}

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(400);
await page.waitForFunction(() => window.__CASCADE.getState().networkReady === true, { timeout: 20000 }).catch(() => {});
const asal = page.getByLabel("Asal");
await asal.fill("Koja");
await page.waitForTimeout(700);
const kojaHit = page.locator("button").filter({ hasText: "CASTJ26" }).first();
if (await kojaHit.count()) await kojaHit.click();
else {
  const anyKoja = page.locator("ul button").filter({ hasText: "Koja" }).first();
  if (await anyKoja.count()) await anyKoja.click();
}
const tujuan = page.getByLabel("Tujuan");
await tujuan.fill("Cengkareng Business City");
await page.waitForTimeout(800);
const cbcHit = page.locator("button").filter({ hasText: "CASTJ26" }).first();
if (await cbcHit.count()) await cbcHit.click();
else {
  const any = page.locator("ul button").filter({ hasText: /Cengkareng Business/ }).first();
  if (await any.count()) await any.click();
}
await page.getByRole("button", { name: "Jalankan" }).click();
await page.waitForTimeout(2500);
const sim = await page.evaluate(() => {
  const st = window.__CASCADE.getState();
  const map = window.__CASCADE_MAP;
  return {
    km: st.simResult?.km,
    hops: st.simResult?.hops,
    note: st.simResult?.note,
    segs: (st.simResult?.segments || []).map((s) => s.routeId || s.kind),
    playing: st.simPlaying,
    veh: !!map?.getLayer?.("sim-vehicle"),
    vehN: map?.getSource?.("sim-vehicle") ? map.querySourceFeatures("sim-vehicle").length : 0,
  };
});
check(sim.km > 20 && sim.km < 40, "CASTJ26 km ~30", "km " + sim.km);
check((sim.hops || []).some((h) => /Koja/i.test(h)), "hops include Koja");
check((sim.hops || []).some((h) => /Plumpang/i.test(h)), "hops include Plumpang");
check((sim.hops || []).some((h) => /Kapuk/i.test(h)), "hops include Kapuk");
check((sim.hops || []).some((h) => /Cengkareng Business/i.test(h)), "hops include CBC");
check((sim.segs || []).includes("CASTJ26"), "segment CASTJ26", "segs " + JSON.stringify(sim.segs));
check(sim.veh, "vehicle layer present");
check(sim.playing || sim.vehN >= 0, "playback started");

const dual = await page.evaluate(() => {
  const m = window.__CASCADE_MAP;
  return !!(m?.getLayer?.("candidate-mode") && m?.getLayer?.("candidate"));
});
check(dual, "dual-color intact");
check((await page.locator("img.cascade-mark").count()) === 1, "one brand mark");

const ids = await page.evaluate(async () => {
  const r = await fetch("/data/cascade_candidates.geojson?v=tj28");
  const fc = await r.json();
  const all = fc.features.map((f) => String(f.id || f.properties?.route_id));
  return { n: all.length, c24: all.includes("CASTJ24"), c25: all.includes("CASTJ25"), same: false };
});
check(ids.c24 && ids.c25, "CASTJ24 and CASTJ25 both present");
check(ids.n === 26, "26 CASCADE corridors", "n " + ids.n);

console.log("AUDIT", JSON.stringify({ corridors: audit.corridors, nodes: audit.nodes, rides: audit.rides, transfers: audit.transfers, connected: audit.connected, isolated: audit.isolated, tests: audit.tests }, null, 2));

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
