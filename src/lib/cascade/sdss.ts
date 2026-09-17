import { meanScore, type Hotspot } from "./bottleneck";
import { HOTSPOTS } from "./bottleneck";
import { emptyFC, type Feature, type FeatureCollection } from "./geojson";
import { formatIdr, type CorridorPropertySummary } from "./property";
import { costRange, type CostRange } from "./research";
import { fetchJson, loadCascadeMeta, OVERLAY_URL } from "./static-data";
import type { SimResult, StatusKey } from "./store";

export type SdssPriority = "tinggi" | "sedang" | "rendah";

export type SdssFactors = {
  congestion: number;
  accessibility: number;
  connectivity: number;
  coverage_gap: number;
  property: number;
  planning: number;
};

export type SdssRow = {
  id: string;
  name: string;
  mode: string;
  status: StatusKey;
  score: number;
  priority: SdssPriority;
  factors: SdssFactors;
  why: string[];
  stations: string[];
  km: number;
  stops: number;
  cost: CostRange;
  propertyNote: string;
  feature: Feature;
};

const W = {
  congestion: 0.28,
  accessibility: 0.18,
  connectivity: 0.16,
  coverage_gap: 0.14,
  property: 0.14,
  planning: 0.1,
};

const LINE_PACKS: { url: string; status: StatusKey }[] = [
  { url: OVERLAY_URL.candidate, status: "cascade" },
  { url: OVERLAY_URL.tj, status: "existing" },
  { url: OVERLAY_URL.krl, status: "existing" },
  { url: OVERLAY_URL.lrt, status: "existing" },
  { url: OVERLAY_URL.mrt, status: "existing" },
  { url: OVERLAY_URL.masterplan, status: "masterplan" },
];

const STOP_URLS = [
  OVERLAY_URL["cascade-stops"],
  OVERLAY_URL["tj-stops"],
  OVERLAY_URL["krl-stops"],
  OVERLAY_URL["lrt-stops"],
  OVERLAY_URL["mrt-stops"],
  OVERLAY_URL["masterplan-stops"],
];

const SKIP_IDS = new Set(["krl-network", "lrt-network"]);

const cache = new Map<string, Promise<FeatureCollection>>();

function loadFc(url: string) {
  let p = cache.get(url);
  if (!p) {
    p = fetchJson<FeatureCollection>(url).catch(() => emptyFC());
    cache.set(url, p);
  }
  return p;
}

function str(v: unknown) {
  return v == null ? "" : String(v);
}

function numOr(v: unknown) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function flatten(g: Feature["geometry"]): [number, number][] {
  const out: [number, number][] = [];
  const walk = (v: unknown) => {
    if (!Array.isArray(v) || !v.length) return;
    if (typeof v[0] === "number" && typeof v[1] === "number") out.push(v as [number, number]);
    else for (const x of v) walk(x);
  };
  walk(g?.coordinates);
  return out;
}

function ptIn(p: [number, number], b: [number, number, number, number]) {
  return p[0] >= b[0] && p[0] <= b[2] && p[1] >= b[1] && p[1] <= b[3];
}

function segsCross(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number) {
  const d = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx);
  if (Math.abs(d) < 1e-15) return false;
  const t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / d;
  const u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / d;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

function segHitsBbox(p: [number, number], q: [number, number], b: [number, number, number, number]) {
  if (ptIn(p, b) || ptIn(q, b)) return true;
  const edges: [number, number, number, number][] = [
    [b[0], b[1], b[2], b[1]],
    [b[2], b[1], b[2], b[3]],
    [b[2], b[3], b[0], b[3]],
    [b[0], b[3], b[0], b[1]],
  ];
  return edges.some((e) => segsCross(p[0], p[1], q[0], q[1], e[0], e[1], e[2], e[3]));
}

/** Geographic intersection: vertices inside OR any segment crossing the drag rectangle. */
export function lineHitsBbox(coords: [number, number][], b: [number, number, number, number]) {
  for (let i = 0; i < coords.length; i++) {
    if (ptIn(coords[i], b)) return true;
    if (i > 0 && segHitsBbox(coords[i - 1], coords[i], b)) return true;
  }
  return false;
}

export function bboxPolygon(b: [number, number, number, number]): FeatureCollection {
  const [minX, minY, maxX, maxY] = b;
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { id: "identify-area" },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [minX, minY],
              [maxX, minY],
              [maxX, maxY],
              [minX, maxY],
              [minX, minY],
            ],
          ],
        },
      },
    ],
  };
}

function modeKey(mode?: string, id?: string) {
  const m = `${mode || ""} ${id || ""}`.toLowerCase();
  if (m.includes("mrt")) return "mrt";
  if (m.includes("lrt")) return "lrt";
  if (m.includes("krl") || m.includes("rail")) return "krl";
  return "transjakarta";
}

function modeW(mk: string) {
  return mk === "mrt" ? 1 : mk === "lrt" ? 0.86 : mk === "krl" ? 0.8 : 0.62;
}

function lengthKm(coords: [number, number][]) {
  let m = 0;
  for (let i = 1; i < coords.length; i++) {
    const dx = (coords[i][0] - coords[i - 1][0]) * 111320 * Math.cos(((coords[i][1] + coords[i - 1][1]) / 2) * (Math.PI / 180));
    const dy = (coords[i][1] - coords[i - 1][1]) * 110540;
    m += Math.hypot(dx, dy);
  }
  return m / 1000;
}

function congestionAlong(coords: [number, number][], status: StatusKey, sim?: SimResult | null) {
  const geo = coords.length ? meanScore(coords, status === "cascade" ? "existing" : status) : 0.4;
  if (sim && sim.bottleneckBefore > 0) {
    return Math.min(1, 0.65 * geo + 0.35 * Math.min(1, sim.bottleneckBefore));
  }
  return geo;
}

function hotspotPressure(coords: [number, number][]) {
  if (!coords.length) return 0.4;
  let s = 0;
  let n = 0;
  for (const h of HOTSPOTS as Hotspot[]) {
    for (let i = 0; i < coords.length; i += 10) {
      const dx = (coords[i][0] - h.lng) * 111.32;
      const dy = (coords[i][1] - h.lat) * 110.54;
      if (Math.hypot(dx, dy) < h.rKm) {
        s += h.peak;
        n++;
        break;
      }
    }
  }
  return n ? Math.min(1, s / n) : 0.4;
}

export function classifyScore(score: number): SdssPriority {
  if (score >= 70) return "tinggi";
  if (score >= 48) return "sedang";
  return "rendah";
}

function scoreFactors(opts: {
  coords: [number, number][];
  status: StatusKey;
  mk: string;
  stops: number;
  km: number;
  propN: number;
  sim?: SimResult | null;
  elevatedKm?: number;
  widening?: string;
}): { factors: SdssFactors; score: number; why: string[] } {
  const congestion = Math.max(congestionAlong(opts.coords, opts.status, opts.sim), hotspotPressure(opts.coords));
  const accessibility = Math.min(1, opts.stops / 28);
  const connectivity = modeW(opts.mk);
  const coverage_gap = opts.status === "existing" ? 0.18 : opts.status === "masterplan" ? 0.58 : 0.86;
  const property = Math.min(1, Math.max(0.12, opts.propN / 40));
  const planning = opts.status === "existing" ? 0.32 : opts.status === "masterplan" ? 0.72 : 0.6;
  const factors: SdssFactors = { congestion, accessibility, connectivity, coverage_gap, property, planning };
  const score = Math.round(
    100 *
      (W.congestion * congestion +
        W.accessibility * accessibility +
        W.connectivity * connectivity +
        W.coverage_gap * coverage_gap +
        W.property * property +
        W.planning * planning),
  );
  const why: string[] = [];
  if (congestion >= 0.72) why.push("tekanan kemacetan di koridor relatif tinggi");
  else if (congestion >= 0.5) why.push("tekanan lalu lintas sedang di kawasan yang dilalui");
  else why.push("tekanan kemacetan relatif lebih rendah");
  if (opts.status === "cascade" && coverage_gap >= 0.7) why.push("mengisi celah layanan yang belum tertutup existing");
  if (opts.status === "existing") why.push("jaringan existing; intervensi berupa penguatan, bukan koridor baru");
  if (opts.status === "masterplan") why.push("koridor acuan perencanaan, belum operasi");
  if (accessibility >= 0.55) why.push("jumlah halte/stasiun cukup rapat");
  else if (accessibility < 0.3) why.push("jangkauan halte masih jarang");
  if (connectivity >= 0.8) why.push("moda rel memperkuat konektivitas jaringan");
  if (property >= 0.45) why.push("aktivitas properti di buffer koridor cukup tinggi");
  if (opts.km >= 20) why.push("cakupan spasial koridor panjang");
  const wide = String(opts.widening || "").toUpperCase();
  if (wide === "VERY HIGH" || wide === "HIGH") {
    why.push("segmen tertentu melalui kawasan dengan keterbatasan ruang jalan");
  }
  if ((opts.elevatedKm || 0) > 0) {
    why.push(`sebagian ruas memakai asumsi struktur elevated (${opts.elevatedKm} km)`);
  }
  return { factors, score: Math.max(12, Math.min(96, score)), why: why.slice(0, 5) };
}

function tokens(v: unknown) {
  return str(v)
    .split(/[,;|/]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function stationName(p: Record<string, unknown>) {
  return str(p.stop_name || p.station_name || p.name);
}

function stationSeq(p: Record<string, unknown>) {
  const n = Number(p.stop_order ?? p.station_order ?? p.sequence);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function stationsFor(line: Feature, identity: string, stops: Feature[]) {
  const lp = line.properties ?? {};
  const route = str(lp.route_id || lp.id || line.id || identity);
  const cid = str(lp.corridor_id);
  const cno = numOr(lp.corridor_no);
  const lineMk = modeKey(str(lp.mode), identity);
  const codes = [...tokens(lp.line_code), ...tokens(lp.line_codes)].filter((t) => t && t !== "ALL");
  const rows: { n: string; s: number; i: number }[] = [];
  for (const st of stops) {
    if (st.geometry?.type !== "Point") continue;
    const p = st.properties ?? {};
    const sRoute = str(p.route_id);
    const sCid = str(p.corridor_id);
    const stopMk = modeKey(str(p.mode), str(p.id));
    const sameMode = stopMk === lineMk;
    const ok =
      (sRoute && (sRoute === route || sRoute === identity)) ||
      (!sRoute && cid && sameMode && (sCid === cid || tokens(p.corridor_id).includes(cid))) ||
      (sameMode && cno != null && cno > 0 && numOr(p.corridor_no) === cno) ||
      (sameMode && codes.length > 0 && [...tokens(p.line_code), ...tokens(p.line_codes)].some((c) => codes.includes(c)));
    if (!ok) continue;
    const n = stationName(p);
    if (!n) continue;
    rows.push({ n, s: stationSeq(p), i: rows.length });
  }
  rows.sort((a, b) => (a.s || 9999) - (b.s || 9999) || a.i - b.i);
  const names: string[] = [];
  for (const r of rows) if (!names.includes(r.n)) names.push(r.n);
  return names;
}

function listingsFor(id: string, status: StatusKey, feats: Feature[]) {
  const out: Record<string, unknown>[] = [];
  for (const f of feats) {
    const p = (f.properties ?? {}) as Record<string, unknown>;
    const cid =
      status === "existing" ? str(p.existing_corridor_id) : status === "masterplan" ? str(p.masterplan_corridor_id) : str(p.cascade_corridor_id);
    const dist =
      status === "existing" ? numOr(p.existing_distance_m) : status === "masterplan" ? numOr(p.masterplan_distance_m) : numOr(p.cascade_distance_m);
    const nearId = str(p.corridor_id) === id && (numOr(p.distance_to_corridor) ?? 99999) <= 1000;
    if ((cid === id && dist != null && dist <= 1000) || nearId) out.push(p);
  }
  return out;
}

function median(xs: number[]) {
  if (!xs.length) return null;
  const a = [...xs].sort((x, y) => x - y);
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

function propertyNote(id: string, status: StatusKey, summary: CorridorPropertySummary | undefined, listings: Feature[]) {
  if (summary?.data_sufficient) {
    const med = summary.median_price_per_m2
      ? `Asking rata-rata ${formatIdr(summary.median_price_per_m2)}/m²`
      : `Median asking ${formatIdr(summary.median_price)}`;
    return `${summary.property_count} listing di buffer ${summary.buffer_m} m. ${med}. Asking price, bukan nilai transaksi.`;
  }
  const rows = listingsFor(id, status, listings);
  if (rows.length < 3) return "Data properti yang tersedia belum cukup untuk memberikan ringkasan harga.";
  const ppm = rows.map((p) => numOr(p.price_per_m2)).filter((n): n is number => n != null && n > 0);
  const med = median(ppm);
  const medTxt = med ? `Asking rata-rata ${formatIdr(med)}/m²` : "";
  return `${rows.length} listing dalam 1 km koridor. ${medTxt} Asking price, bukan nilai transaksi.`.replace("  ", " ");
}

type CasExtra = { id: string; elevated_km?: number; widening_level?: string; cost_label?: string };

export async function analyzeIdentifyArea(
  bbox: [number, number, number, number],
  opts?: { summaries?: CorridorPropertySummary[]; sim?: SimResult | null },
): Promise<{ rows: SdssRow[]; candidateCount: number; hits: FeatureCollection; box: FeatureCollection }> {
  const packs = await Promise.all(LINE_PACKS.map(async (p) => ({ ...p, fc: await loadFc(p.url) })));
  const stopPacks = await Promise.all(STOP_URLS.map(loadFc));
  const [propFc, casMeta] = await Promise.all([
    loadFc(OVERLAY_URL.property),
    loadCascadeMeta().catch(() => ({ corridors: [] as CasExtra[] })),
  ]);
  const stops = stopPacks.flatMap((fc) => fc.features);
  const listings = propFc.features;
  const summaries = opts?.summaries ?? [];
  const propBy = Object.fromEntries(summaries.map((s) => [s.corridor_id, s]));
  const extraBy = Object.fromEntries(((casMeta.corridors ?? []) as CasExtra[]).map((c) => [c.id, c]));
  const scored: SdssRow[] = [];
  const seen = new Set<string>();
  for (const pack of packs) {
    for (const f of pack.fc.features) {
      const g = f.geometry;
      if (!g || (g.type !== "LineString" && g.type !== "MultiLineString")) continue;
      const coords = flatten(g);
      if (coords.length < 2) continue;
      if (!lineHitsBbox(coords, bbox)) continue;
      const p = f.properties ?? {};
      const id = str(p.route_id || p.id || f.id);
      if (!id || SKIP_IDS.has(id)) continue;
      const key = `${pack.status}:${id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const mk = modeKey(str(p.mode), id);
      const stations = stationsFor(f, id, stops);
      const km = Number(p.length_km) || lengthKm(coords);
      const stopsN = Number(p.stop_count) || stations.length;
      const extra = extraBy[id];
      const listingN = listingsFor(id, pack.status, listings).length;
      const propN = propBy[id]?.property_count || listingN;
      const { factors, score, why } = scoreFactors({
        coords,
        status: pack.status,
        mk,
        stops: stopsN,
        km,
        propN,
        sim: opts?.sim,
        elevatedKm: extra?.elevated_km,
        widening: extra?.widening_level,
      });
      scored.push({
        id,
        name: str(p.short || p.corridor_name || p.name || p.route_name || id),
        mode: mk,
        status: pack.status,
        score,
        priority: classifyScore(score),
        factors,
        why,
        stations,
        km: Number(km.toFixed(1)),
        stops: stopsN,
        cost:
          pack.status === "existing"
            ? {
                loT: 0,
                hiT: 0,
                label: "Koridor existing — bukan biaya pembangunan baru",
                note: "Angka bersifat indikatif untuk perbandingan awal dan bukan RAB/DED.",
              }
            : costRange(id, mk, km, stopsN, {
                elevatedKm: extra?.elevated_km,
                widening: extra?.widening_level,
                costLabel: extra?.cost_label,
              }),
        propertyNote: propertyNote(id, pack.status, propBy[id], listings),
        feature: {
          type: "Feature",
          id,
          properties: { ...(p as object), sdss_id: id, sdss_status: pack.status },
          geometry: g,
        },
      });
    }
  }
  scored.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const top = scored.slice(0, 3);
  return {
    rows: top,
    candidateCount: scored.length,
    hits: { type: "FeatureCollection", features: top.map((r) => r.feature) },
    box: bboxPolygon(bbox),
  };
}

export function factorRows(f: SdssFactors) {
  return [
    { k: "Kemacetan", v: Math.round(f.congestion * 100) },
    { k: "Aksesibilitas", v: Math.round(f.accessibility * 100) },
    { k: "Konektivitas", v: Math.round(f.connectivity * 100) },
    { k: "Kesenjangan layanan", v: Math.round(f.coverage_gap * 100) },
    { k: "Properti", v: Math.round(f.property * 100) },
    { k: "Konteks perencanaan", v: Math.round(f.planning * 100) },
  ];
}

export function priorityLabel(p: SdssPriority) {
  return p === "tinggi" ? "Prioritas tinggi" : p === "sedang" ? "Prioritas sedang" : "Prioritas rendah";
}

export function priorityHint(p: SdssPriority) {
  if (p === "tinggi") return "Menunjukkan kebutuhan intervensi yang relatif tinggi berdasarkan indikator analisis.";
  if (p === "sedang") return "Menunjukkan kebutuhan intervensi pada tingkat menengah.";
  return "Tekanan pembangunan baru relatif rendah; peningkatan jangkauan dapat menjadi alternatif.";
}

if (typeof window !== "undefined") {
  (window as unknown as { __CASCADE_SDSS?: unknown }).__CASCADE_SDSS = {
    analyzeIdentifyArea,
    lineHitsBbox,
    classifyScore,
  };
}
