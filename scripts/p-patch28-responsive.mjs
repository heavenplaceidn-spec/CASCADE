#!/usr/bin/env node
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

mkdirSync("/workspace/screenshots", { recursive: true });
const browser = await chromium.launch({ args: ["--use-gl=angle", "--ignore-gpu-blocklist"] });
const ok = [];
const fail = [];
const check = (cond, yes, no) => {
  if (cond) ok.push(yes);
  else fail.push(no || yes);
};

async function enterApp(page) {
  await page.goto("http://127.0.0.1:8080/", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => {
    const b = [...document.querySelectorAll("button")].find((x) => /Mulai Eksplorasi/.test(x.textContent || ""));
    return b && !b.disabled;
  }, { timeout: 70000 });
  const splashText = await page.evaluate(() => document.body.innerText || "");
  check(!/Mode Desktop|Mode Mobile|Pilih tampilan|Choose Desktop|Choose Mobile/i.test(splashText), "splash has no device-mode picker");
  await page.getByRole("button", { name: /Mulai Eksplorasi/ }).click();
  await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
  await page.waitForTimeout(500);
}

function layoutProbe() {
  return pageEvaluateLayout;
}

const pageEvaluateLayout = () => {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const nav = document.querySelector("[data-mobile-nav]");
  const headerNav = document.querySelector("header nav");
  const legend = document.querySelector("[data-legend-stack]");
  const panel = document.querySelector("[data-work-panel]");
  const mark = document.querySelector("img.cascade-mark");
  const lr = legend?.getBoundingClientRect();
  const pr = panel?.getBoundingClientRect();
  const mr = mark?.getBoundingClientRect();
  const nr = nav?.getBoundingClientRect();
  const overlapMark = !!(lr && mr && lr.left < mr.right && lr.right > mr.left && lr.top < mr.bottom && lr.bottom > mr.top);
  const overflow = document.documentElement.scrollWidth > w + 1 || document.body.scrollWidth > w + 1;
  const map = document.querySelector(".maplibregl-map")?.getBoundingClientRect();
  return {
    w,
    h,
    overflow,
    mobileNav: !!(nav && getComputedStyle(nav).display !== "none" && (nr?.height || 0) > 8),
    headerNav: !!(headerNav && getComputedStyle(headerNav).display !== "none"),
    legendLeft: lr?.left ?? -1,
    legendTop: lr?.top ?? -1,
    legendH: lr?.height ?? 0,
    panelRight: pr ? w - pr.right : -1,
    panelBottom: pr ? h - pr.bottom : -1,
    panelTop: pr?.top ?? -1,
    markVisible: !!(mr && mr.height > 20),
    overlapMark,
    mapW: map?.width ?? 0,
    mapH: map?.height ?? 0,
    sheetCollapsed: panel?.getAttribute("data-collapsed"),
    modes: [...document.querySelectorAll("img[data-sim-mode]")].map((x) => x.getAttribute("data-sim-mode")),
    dual: !!document.querySelector(".legend-dual"),
    kondisi: /Lancar|Macet/.test(legend?.innerText || ""),
  };
};

{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (err) => fail.push("desk pageerror " + err.message));
  await enterApp(page);
  const d = await page.evaluate(pageEvaluateLayout);
  check(!d.overflow, "desktop no horizontal overflow");
  check(!d.mobileNav, "desktop uses header nav, not bottom tabs");
  check(d.headerNav, "desktop header nav visible");
  check(d.legendLeft < 80, "desktop legend on the left");
  check(d.panelRight < 40, "desktop panel on the right");
  check(d.markVisible, "desktop CASCADE branding visible");
  check(!d.overlapMark, "desktop legend does not cover branding");
  check(d.dual && d.kondisi, "desktop legend complete");
  check(d.modes.includes("krl") && d.modes.includes("bus"), "desktop legend vehicles");
  check(d.mapW >= 1400 && d.mapH >= 850, "desktop map fills viewport", `map ${d.mapW}x${d.mapH}`);
  await page.screenshot({ path: "/workspace/screenshots/p28-desktop.png" });
  await page.close();
}

{
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.on("pageerror", (err) => fail.push("m390 pageerror " + err.message));
  await enterApp(page);
  let m = await page.evaluate(pageEvaluateLayout);
  check(!m.overflow, "390 no horizontal overflow", "scrollWidth overflow at 390");
  check(m.mobileNav, "390 bottom navigation");
  check(!m.headerNav, "390 header nav hidden");
  check(m.markVisible, "390 CASCADE branding visible");
  check(!m.overlapMark, "390 legend does not cover branding");
  check(m.legendLeft < 24, "390 legend stays left");
  check(m.legendH > 80 && m.legendH < 320, "390 legend compact", "legend h " + m.legendH);
  check(m.panelBottom < 120, "390 panel is a bottom sheet", "panel bottom gap " + m.panelBottom);
  check(m.mapW >= 380 && m.mapH >= 800, "390 map fills viewport", `map ${m.mapW}x${m.mapH}`);
  check(m.dual && m.kondisi, "390 legend complete");
  check(m.modes.length === 4, "390 MODE SIMULASI vehicles");
  const scrolled = await page.evaluate(() => {
    const el = document.querySelector(".legend-scroll");
    if (!el) return 0;
    el.scrollTop = el.scrollHeight;
    return el.scrollTop;
  });
  check(scrolled > 4, "390 legend inner scroll");
  await page.screenshot({ path: "/workspace/screenshots/p28-mobile-390.png" });
  const sheetBtn = page.getByRole("button", { name: /Buka panel|Tutup panel/ });
  if (await sheetBtn.count()) {
    const expanded = await page.evaluate(() => document.querySelector("[data-work-panel]")?.getAttribute("data-collapsed"));
    if (expanded === "true") await sheetBtn.click();
  }
  await page.getByRole("link", { name: "Simulasi" }).click();
  await page.waitForTimeout(300);
  const sim = await page.evaluate(() => {
    const panel = document.querySelector("[data-work-panel]");
    const r = panel?.getBoundingClientRect();
    return {
      collapsed: panel?.getAttribute("data-collapsed"),
      h: r?.height || 0,
      asal: !!document.querySelector('input[aria-label="Asal"]'),
      overflow: document.body.scrollWidth > window.innerWidth + 1,
    };
  });
  check(sim.asal, "390 simulation origin field reachable");
  check(sim.h > 80, "390 simulation sheet expanded");
  check(!sim.overflow, "390 simulasi no horizontal overflow");
  await page.screenshot({ path: "/workspace/screenshots/p28-mobile-sim.png" });
  await page.close();
}

for (const [w, h, tag] of [
  [360, 800, "360"],
  [412, 915, "412"],
]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await enterApp(page);
  const m = await page.evaluate(pageEvaluateLayout);
  check(!m.overflow, `${tag} no horizontal overflow`);
  check(m.mobileNav, `${tag} bottom nav`);
  check(m.markVisible, `${tag} branding visible`);
  check(!m.overlapMark, `${tag} legend clear of branding`);
  await page.screenshot({ path: `/workspace/screenshots/p28-mobile-${tag}.png` });
  await page.close();
}

{
  const page = await browser.newPage({ viewport: { width: 844, height: 390 } });
  await enterApp(page);
  const m = await page.evaluate(pageEvaluateLayout);
  check(!m.overflow, "landscape 844 no horizontal overflow");
  check(m.markVisible, "landscape branding visible");
  await page.screenshot({ path: "/workspace/screenshots/p28-landscape.png" });
  await page.close();
}

console.log("PASS", ok.length);
console.log(ok.map((x) => "  ok  " + x).join("\n"));
if (fail.length) {
  console.log("FAIL", fail.length);
  console.log(fail.map((x) => "  xx  " + x).join("\n"));
}
await browser.close();
process.exit(fail.length ? 1 : 0);
