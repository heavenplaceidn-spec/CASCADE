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
  await page.getByRole("button", { name: /Mulai Eksplorasi/ }).click();
  await page.waitForFunction(() => window.__CASCADE_MAP?.isStyleLoaded?.(), { timeout: 45000 });
  await page.waitForTimeout(600);
}

async function waitSurvey(page, min = 1) {
  await page.waitForFunction(
    (n) => {
      const m = window.__CASCADE_MAP;
      const s = m?.getSource?.("survey");
      let count = 0;
      try {
        const data = s?.serialize?.()?.data;
        count = Array.isArray(data?.features) ? data.features.length : 0;
      } catch {
        count = 0;
      }
      return count >= n;
    },
    min,
    { timeout: 35000 },
  );
}

{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (err) => fail.push("desk pageerror " + err.message));
  await enterApp(page);

  const api = await page.evaluate(async () => {
    const r = await fetch("/api/survey-activities");
    return r.json();
  });
  check(api.ok === true, "survey API ok");
  check(Number(api.count) >= 70, `survey API count ${api.count} >= 70`, `survey API count ${api.count}`);
  check(api.hashtag === "#geounjukkebolehan", "survey API hashtag");
  check(api.source === "MAPID Survey Activity", "survey API source");
  const feats = Array.isArray(api.features) ? api.features : [];
  check(feats.length === api.count, "survey API features match count");
  const blob = JSON.stringify(api);
  check(!/[REDACTED]|[REDACTED]|MAPID_API_KEY/.test(blob), "survey API has no MAPID key");
  check(!/"user_phone|"user_email|"phone_number/.test(blob), "survey API has no PII fields");
  const titles = feats.map((f) => String(f.properties?.title || "").toLowerCase());
  check(titles.some((t) => t.includes("grogol")), "excel grogol recovered");
  check(titles.some((t) => t.includes("harmoni")), "excel harmoni recovered");
  check(titles.some((t) => t.includes("mampang") || t.includes("amari")), "excel mampang/amari recovered");
  check(titles.some((t) => t.includes("ragunan")), "excel ragunan present");
  check(
    feats.every((f) => f.geometry?.type === "Point" && Array.isArray(f.geometry.coordinates) && f.geometry.coordinates.length >= 2),
    "all survey features are points",
  );
  check(
    feats.every((f) => {
      const c = f.geometry.coordinates;
      return c[0] >= 105.5 && c[0] <= 107.8 && c[1] <= -5.7 && c[1] >= -7.2;
    }),
    "all survey coords in jabodetabek",
  );

  const html = await page.content();
  check(!/[REDACTED]|[REDACTED]/.test(html), "page html has no pasted API keys");

  const toggle = page.locator("[data-survey-toggle]");
  check((await toggle.count()) === 1, "eksplorasi has Bukti survei checkbox");
  check(await toggle.isChecked(), "survey toggle default on");
  const countText = await page.locator("[data-survey-count]").innerText();
  check(/#geounjukkebolehan/.test(countText), "panel shows hashtag");
  check(/\d+\s+titik/.test(countText), "panel shows titik count");
  check((await page.locator("[data-survey-legend]").count()) === 1, "legend has survey marker");
  const legendText = await page.locator("[data-legend-stack]").innerText();
  check(/Titik Survei/.test(legendText) && /MAPID Survey Activity/.test(legendText), "legend TITIK DATA survey");

  await waitSurvey(page, 20);
  const layer = await page.evaluate(() => {
    const m = window.__CASCADE_MAP;
    const s = m.getSource("survey");
    const data = s?.serialize?.()?.data;
    const paint = m.getPaintProperty("survey-point", "circle-color");
    return {
      vis: m.getLayoutProperty("survey-point", "visibility"),
      n: data?.features?.length || 0,
      color: String(paint || ""),
      dual: !!(m.getLayer("candidate") && m.getLayer("candidate-mode")),
      vehicle: !!m.getLayer("sim-vehicle"),
      congestion: !!m.getLayer("sim-route"),
    };
  });
  check(layer.vis === "visible", "survey-point layer visible");
  check(layer.n >= 70, `map source has ${layer.n} survey points`, `map source count ${layer.n}`);
  check(/#EA580C/i.test(layer.color) || layer.color.toLowerCase().includes("234,88,12"), "survey color orange #EA580C");
  check(layer.dual, "dual-color corridor layers intact");
  check(layer.vehicle, "sim-vehicle layer intact");
  check(layer.congestion, "sim-route SHP layer intact");

  const hit = await page.evaluate(async () => {
    const m = window.__CASCADE_MAP;
    const s = m.getSource("survey");
    const data = s?.serialize?.()?.data;
    const f = data?.features?.find((x) => Array.isArray(x?.geometry?.coordinates));
    if (!f) return null;
    const c = f.geometry.coordinates;
    m.jumpTo({ center: c, zoom: 15 });
    await new Promise((r) => setTimeout(r, 700));
    const p = m.project(c);
    return { x: p.x, y: p.y, title: String(f.properties?.title || "") };
  });
  check(!!hit, "found a survey point to click");
  if (hit) {
    await page.mouse.click(hit.x, hit.y);
    await page.waitForTimeout(400);
    const pop = page.locator("[data-survey-popup]");
    check((await pop.count()) === 1, "survey popup opens");
    const popText = (await pop.count()) ? await pop.innerText() : "";
    check(/#geounjukkebolehan/.test(popText), "popup has hashtag");
    check(/Hashtag/.test(popText), "popup has hashtag row");
    check(/Bukti survei/.test(popText), "popup labeled bukti survei");
    const img = pop.locator("img.survey-photo");
    const noPhoto = /Bukti foto tidak tersedia/.test(popText);
    check((await img.count()) === 1 || noPhoto, "popup has compact photo or no-photo note");
    if (await img.count()) {
      const h = await img.evaluate((el) => el.getBoundingClientRect().height);
      check(h > 40 && h < 90, `photo compact height ${h.toFixed(0)}px`, `photo height ${h}`);
    }
    check(!/SIMULASIKAN PERJALANAN/.test(popText), "survey popup is not a transport CTA");
    check(!/Existing|Masterplan/.test(popText.split("\n")[0] || ""), "survey popup has no status tabs in title");
  }

  await toggle.click();
  await page.waitForTimeout(250);
  const off = await page.evaluate(() => window.__CASCADE_MAP.getLayoutProperty("survey-point", "visibility"));
  check(off === "none", "toggle off hides survey points");
  await toggle.click();
  await page.waitForTimeout(400);
  const onAgain = await page.evaluate(() => window.__CASCADE_MAP.getLayoutProperty("survey-point", "visibility"));
  check(onAgain === "visible", "toggle on shows survey points");

  await page.screenshot({ path: "/workspace/screenshots/p30-desktop.png" });
  await page.close();
}

{
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.on("pageerror", (err) => fail.push("m390 pageerror " + err.message));
  await enterApp(page);
  const sheetBtn = page.getByRole("button", { name: /Buka panel|Tutup panel/ });
  if (await sheetBtn.count()) {
    const collapsed = await page.evaluate(() => document.querySelector("[data-work-panel]")?.getAttribute("data-collapsed"));
    if (collapsed === "true") await sheetBtn.click();
  }
  await page.waitForTimeout(300);
  const mobileToggle = page.locator("[data-survey-toggle]");
  check((await mobileToggle.count()) === 1, "mobile sheet has survey checkbox");
  const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth + 1);
  check(!overflow, "mobile no horizontal overflow");
  await waitSurvey(page, 10).catch(() => {});
  const hit = await page.evaluate(async () => {
    const m = window.__CASCADE_MAP;
    const s = m.getSource("survey");
    const data = s?.serialize?.()?.data;
    const f = data?.features?.[0];
    if (!f) return null;
    const c = f.geometry.coordinates;
    m.jumpTo({ center: c, zoom: 15 });
    await new Promise((r) => setTimeout(r, 700));
    const p = m.project(c);
    return { x: p.x, y: p.y };
  });
  if (hit) {
    await page.mouse.click(hit.x, hit.y);
    await page.waitForTimeout(400);
    const pop = page.locator("[data-survey-popup]");
    if (await pop.count()) {
      const box = await pop.boundingBox();
      check(!!box && box.width < 280, "mobile survey popup compact");
      const img = pop.locator("img.survey-photo");
      if (await img.count()) {
        const h = await img.evaluate((el) => el.getBoundingClientRect().height);
        check(h < 100, `mobile photo ${h.toFixed(0)}px stays small`, `mobile photo ${h}`);
      }
    }
  }
  await page.screenshot({ path: "/workspace/screenshots/p30-mobile-390.png" });
  await page.close();
}

console.log(`PASS ${ok.length}`);
for (const x of ok) console.log("  ok", x);
console.log(`FAIL ${fail.length}`);
for (const x of fail) console.log("  fail", x);
await browser.close();
if (fail.length) process.exit(1);
