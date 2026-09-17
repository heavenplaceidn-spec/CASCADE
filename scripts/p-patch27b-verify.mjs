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
await page.waitForSelector("img[data-sim-mode]", { timeout: 15000 });

const layout = await page.evaluate(() => {
  const stack = document.querySelector("[data-legend-stack]");
  const scroll = document.querySelector(".legend-scroll");
  const mark = document.querySelector("img.cascade-mark");
  const sr = stack?.getBoundingClientRect();
  const mr = mark?.getBoundingClientRect();
  const overlap = !!(sr && mr && sr.left < mr.right && sr.right > mr.left && sr.top < mr.bottom && sr.bottom > mr.top);
  const imgs = [...document.querySelectorAll("img[data-sim-mode]")].map((img) => ({
    mode: img.getAttribute("data-sim-mode"),
    cars: Number(img.getAttribute("data-cars") || 0),
    w: img.naturalWidth,
    h: img.naturalHeight,
    displayW: img.getBoundingClientRect().width,
    srcType: (img.getAttribute("src") || "").startsWith("data:image/png"),
  }));
  const asides = [...document.querySelectorAll("aside")].map((a) => a.getBoundingClientRect());
  const right = asides.find((a) => a.left > 900);
  const text = stack?.innerText || "";
  const cs = stack ? getComputedStyle(stack) : null;
  const scs = scroll ? getComputedStyle(scroll) : null;
  return {
    stackH: sr?.height || 0,
    stackTop: sr?.top || 0,
    stackBottom: sr?.bottom || 0,
    markBottom: mr?.bottom || 0,
    markTop: mr?.top || 0,
    markVisible: !!(mr && mr.height > 24 && getComputedStyle(mark).display !== "none"),
    overlap,
    overflow: scs?.overflowY,
    maxH: cs?.maxHeight,
    panelH: right?.height || 0,
    panelTop: right?.top || 0,
    panelBottom: right?.bottom || 0,
    imgs,
    statusJalur: /STATUS JALUR/.test(text),
    statusGaris: /Existing/.test(text) && /Masterplan/.test(text) && /CASCADE/.test(text),
    modeSim: /MODE SIMULASI/.test(text),
    kondisi: /KONDISI JALUR/.test(text) && /Lancar/.test(text) && /Sedang/.test(text) && /Macet/.test(text),
    keterangan: /Garis solid/.test(text) && /putus-putus/.test(text),
    dual: !!document.querySelector(".legend-dual"),
    emoji: /[\u{1F680}-\u{1F6FF}\u{1F300}-\u{1F5FF}]/u.test(text),
    scrollable: scroll ? scroll.scrollHeight > scroll.clientHeight - 1 : false,
  };
});

check(layout.markVisible, "CASCADE mark visible");
check(!layout.overlap, "legend does not cover branding", "legend overlaps branding");
check(layout.stackTop >= layout.markBottom - 8, "legend sits below branding", `legend top ${layout.stackTop} mark bottom ${layout.markBottom}`);
check(layout.markTop <= 8, "CASCADE mark sits near the top", "mark top " + layout.markTop);
check(Math.abs(layout.stackH - layout.panelH) < 24, "legend height matches LAPISAN panel", `legend ${layout.stackH} panel ${layout.panelH}`);
check(Math.abs(layout.stackTop - layout.panelTop) < 8, "legend top aligns with LAPISAN", `legend top ${layout.stackTop} panel top ${layout.panelTop}`);
check(layout.overflow === "auto" || layout.overflow === "scroll", "legend inner overflow-y auto", "overflow " + layout.overflow);
check(layout.scrollable, "legend content can scroll");
check(layout.statusJalur, "STATUS JALUR section");
check(layout.statusGaris, "Existing/Masterplan/CASCADE remain");
check(layout.dual, "dual-color line samples remain");
check(layout.modeSim, "MODE SIMULASI section");
check(layout.kondisi, "KONDISI JALUR line legend");
check(layout.keterangan, "keterangan solid vs dashed");
check(!layout.emoji, "no emoji in legend");

const byMode = Object.fromEntries(layout.imgs.map((x) => [x.mode, x]));
check(byMode.bus?.cars === 1, "TJ 1 bus");
check(byMode.krl?.cars === 3, "KRL 3 gerbong");
check(byMode.lrt?.cars === 3, "LRT 3 gerbong");
check(byMode.mrt?.cars === 3, "MRT 3 gerbong");
check(layout.imgs.every((x) => x.srcType && x.w > 40), "legend vehicles are canvas sprites", JSON.stringify(layout.imgs.map((x) => ({ m: x.mode, w: x.w }))));
check(byMode.krl && byMode.bus && byMode.krl.w > byMode.bus.w * 1.2, "KRL consist wider than TJ bus", `krl ${byMode.krl?.w} bus ${byMode.bus?.w}`);
check(byMode.lrt && byMode.lrt.w > (byMode.bus?.w || 0) * 1.2, "LRT consist wider than TJ bus");
check(byMode.mrt && byMode.mrt.w > (byMode.bus?.w || 0) * 1.2, "MRT consist wider than TJ bus");

await page.screenshot({ path: "/workspace/screenshots/p27b-legend.png" });

const scrolled = await page.evaluate(() => {
  const el = document.querySelector(".legend-scroll");
  if (!el) return 0;
  el.scrollTop = el.scrollHeight;
  return el.scrollTop;
});
check(scrolled > 8, "legend scrolls internally", "scrollTop " + scrolled);
await page.screenshot({ path: "/workspace/screenshots/p27b-legend-scroll.png" });

await page.getByRole("link", { name: "Simulasi", exact: true }).click();
await page.waitForTimeout(400);
const simPanel = await page.evaluate(() => {
  const stack = document.querySelector("[data-legend-stack]")?.getBoundingClientRect();
  const asides = [...document.querySelectorAll("aside")].map((a) => a.getBoundingClientRect());
  const right = asides.find((a) => a.left > 900);
  return {
    legendH: stack?.height || 0,
    panelH: right?.height || 0,
    dual: !!document.querySelector(".legend-dual"),
    modes: [...document.querySelectorAll("img[data-sim-mode]")].map((x) => x.getAttribute("data-sim-mode")),
    mark: !!document.querySelector("img.cascade-mark"),
  };
});
check(Math.abs(simPanel.legendH - simPanel.panelH) < 24, "sim view legend matches right panel", `legend ${simPanel.legendH} panel ${simPanel.panelH}`);
check(simPanel.mark, "branding still visible on simulasi");
check(simPanel.modes.includes("krl") && simPanel.modes.includes("bus"), "sim view still shows vehicle legend");

await page.waitForFunction(() => window.__CASCADE.getState().networkReady === true, { timeout: 25000 }).catch(() => {});
const input = page.getByLabel("Asal", { exact: true });
await input.fill("Koja");
await page.waitForTimeout(800);
const hinted = page.locator("ul button").filter({ hasText: "CASTJ26" }).first();
if (await hinted.count()) await hinted.click();
else {
  const any = page.locator("ul button").first();
  if (await any.count()) await any.click();
}
const dest = page.getByLabel("Tujuan", { exact: true });
await dest.fill("Cengkareng Business City");
await page.waitForTimeout(800);
const dh = page.locator("ul button").filter({ hasText: "CASTJ26" }).first();
if (await dh.count()) await dh.click();
else {
  const any = page.locator("ul button").first();
  if (await any.count()) await any.click();
}
await page.getByRole("button", { name: "Jalankan" }).click();
await page.waitForFunction(() => (window.__CASCADE.getState().simResult?.km || 0) > 0, { timeout: 20000 }).catch(() => {});
await page.waitForTimeout(1000);
const live = await page.evaluate(() => {
  const map = window.__CASCADE_MAP;
  const vis = (id) => map?.getLayer?.(id) && map.getLayoutProperty(id, "visibility") !== "none";
  const anim = window.__CASCADE_ANIM || {};
  return {
    km: window.__CASCADE.getState().simResult?.km,
    duration: anim.duration,
    pathway: vis("candidate") && vis("candidate-mode"),
    shp: vis("sim-route"),
    vehicle: vis("sim-vehicle"),
    n: document.querySelectorAll("img[data-sim-mode]").length,
  };
});
check(live.km > 20 && live.km < 40, "CASTJ26 still routes");
check(live.duration === 20, "playback still 20s", "duration " + live.duration);
check(live.pathway, "dual-color still on during sim");
check(live.shp, "SHP congestion still visible");
check(live.vehicle, "vehicle animation still on");
check(live.n === 4, "four legend vehicles during sim");
await page.screenshot({ path: "/workspace/screenshots/p27b-sim.png" });

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
