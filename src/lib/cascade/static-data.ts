import type { CascadeMeta, KrlLineMeta, MasterplanMeta, RailLineMeta, TjCorridorMeta } from "./functions";

export async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "force-cache" });
  if (!res.ok) throw new Error(`Gagal memuat ${url}`);
  return res.json() as Promise<T>;
}

type MetaFile<T> = { corridors?: T[] };

export const loadTjMeta = () => fetchJson<MetaFile<TjCorridorMeta>>("/data/tj_existing.json");
export const loadKrlMeta = () => fetchJson<MetaFile<KrlLineMeta>>("/data/krl_existing.json");
export const loadLrtMeta = () => fetchJson<MetaFile<RailLineMeta>>("/data/lrt_existing.json");
export const loadMrtMeta = () => fetchJson<MetaFile<RailLineMeta>>("/data/mrt_existing.json");
export const loadMasterplanMeta = () => fetchJson<MetaFile<MasterplanMeta>>("/data/masterplan_existing.json");
export const loadCascadeMeta = () => fetchJson<MetaFile<CascadeMeta>>("/data/cascade_existing.json?v=tj28");

export type CatalogCounts = {
  krl: number;
  mrt: number;
  lrt: number;
  transjakarta: number;
  candidates: number;
  masterplan: number;
  roads: number;
  tjStops: number;
  krlStops: number;
  lrtStops: number;
  mrtStops: number;
  masterplanStops: number;
  cascadeStops: number;
  stops: number;
};

export async function loadCatalog(): Promise<CatalogCounts> {
  const [sources, krl, lrt, mrt, tj, mp, cas] = await Promise.all([
    fetchJson<{ dataset: string; count: number }[]>("/data/sources.json"),
    loadKrlMeta(),
    loadLrtMeta(),
    loadMrtMeta(),
    loadTjMeta(),
    loadMasterplanMeta(),
    loadCascadeMeta(),
  ]);
  const by = Object.fromEntries(sources.map((s) => [s.dataset, s.count]));
  const n = (k: string) => by[k] ?? 0;
  const krlS = n("krl_stops");
  const mrtS = n("mrt_stops");
  const lrtS = n("lrt_stops");
  const tjS = n("transjakarta_stops");
  return {
    krl: krl.corridors?.length || n("krl_routes"),
    mrt: mrt.corridors?.length || n("mrt_routes"),
    lrt: lrt.corridors?.length || n("lrt_routes"),
    transjakarta: tj.corridors?.length || n("transjakarta_routes"),
    candidates: cas.corridors?.length || n("cascade_candidates"),
    masterplan: mp.corridors?.length || n("masterplan"),
    roads: n("roads"),
    tjStops: tjS,
    krlStops: krlS,
    lrtStops: lrtS,
    mrtStops: mrtS,
    masterplanStops: n("masterplan_stations"),
    cascadeStops: n("cascade_stops"),
    stops: krlS + mrtS + lrtS + tjS,
  };
}

export function flyBounds(b?: number[] | null) {
  if (!b || b.length < 4) return;
  const bounds = [b[0], b[1], b[2], b[3]] as [number, number, number, number];
  window.dispatchEvent(new CustomEvent("cascade-fly", { detail: { bounds } }));
  const map = (window as unknown as { __CASCADE_MAP?: { fitBounds: (a: unknown, b: unknown) => void } }).__CASCADE_MAP;
  try {
    map?.fitBounds(
      [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]],
      ],
      { padding: 72, duration: 800, maxZoom: 12 },
    );
  } catch {
    /* map not ready */
  }
}

export function unionBboxes(boxes: Array<number[] | null | undefined>): [number, number, number, number] | null {
  const ok = boxes.filter((b): b is number[] => Array.isArray(b) && b.length >= 4);
  if (!ok.length) return null;
  return [
    Math.min(...ok.map((b) => b[0])),
    Math.min(...ok.map((b) => b[1])),
    Math.max(...ok.map((b) => b[2])),
    Math.max(...ok.map((b) => b[3])),
  ];
}

function lineBbox(geom: { type?: string; coordinates?: unknown }): [number, number, number, number] | null {
  const coords: number[][] = [];
  const walk = (v: unknown) => {
    if (!Array.isArray(v) || !v.length) return;
    if (typeof v[0] === "number" && typeof v[1] === "number") coords.push(v as number[]);
    else for (const x of v) walk(x);
  };
  walk(geom?.coordinates);
  if (coords.length < 2) return null;
  const xs = coords.map((c) => c[0]);
  const ys = coords.map((c) => c[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** Fit map to the actual GeoJSON line of a CASCADE corridor (not just termini). */
export async function flyCorridorId(id: string) {
  try {
    const res = await fetch("/data/cascade_candidates.geojson?v=tj28", { cache: "no-store" });
    if (!res.ok) return;
    const fc = (await res.json()) as { features: { id?: string; properties?: Record<string, unknown>; geometry?: { type?: string; coordinates?: unknown } }[] };
    const f = fc.features.find((x) => String(x.id ?? x.properties?.route_id ?? x.properties?.id ?? "") === id);
    flyBounds(f ? lineBbox(f.geometry ?? {}) : null);
  } catch {
    /* ignore */
  }
}

/** Fit to CASCADE corridors of one mode (krl / mrt / lrt). */
export async function flyCascadeKrl(mode = "krl") {
  try {
    const res = await fetch("/data/cascade_candidates.geojson?v=tj28", { cache: "no-store" });
    if (!res.ok) return;
    const fc = (await res.json()) as { features: { properties?: Record<string, unknown>; geometry?: { type?: string; coordinates?: unknown } }[] };
    const boxes = fc.features
      .filter((x) => String(x.properties?.mode ?? "") === mode)
      .map((x) => lineBbox(x.geometry ?? {}));
    flyBounds(unionBboxes(boxes));
  } catch {
    /* ignore */
  }
}

export function flyMeta(items: { bbox?: number[] | null }[] | { bbox?: number[] | null } | null | undefined) {
  if (!items) return;
  const list = Array.isArray(items) ? items : [items];
  flyBounds(unionBboxes(list.map((i) => i.bbox)));
}

export const OVERLAY_URL = {
  krl: "/data/krl_routes.geojson",
  tj: "/data/transjakarta_routes.geojson",
  lrt: "/data/lrt_routes.geojson",
  mrt: "/data/mrt_routes.geojson",
  candidate: "/data/cascade_candidates.geojson?v=tj28",
  masterplan: "/data/masterplan.geojson",
  roads: "/data/roads.geojson",
  "krl-stops": "/data/krl_stops.geojson",
  "tj-stops": "/data/transjakarta_stops.geojson",
  "lrt-stops": "/data/lrt_stops.geojson",
  "mrt-stops": "/data/mrt_stops.geojson",
  "cascade-stops": "/data/cascade_stops.geojson?v=tj28",
  "masterplan-stops": "/data/masterplan_stations.geojson",
  property: "/data/property/properties.geojson",
  "property-zones": "/data/property/price_zones.geojson",
} as const;

const PREFETCH_URLS = [
  OVERLAY_URL.candidate,
  OVERLAY_URL["cascade-stops"],
  OVERLAY_URL.krl,
  OVERLAY_URL.tj,
  OVERLAY_URL.lrt,
  OVERLAY_URL.mrt,
  OVERLAY_URL["krl-stops"],
  OVERLAY_URL["tj-stops"],
  OVERLAY_URL["lrt-stops"],
  OVERLAY_URL["mrt-stops"],
  "/data/cascade_existing.json",
  "/data/tj_existing.json",
  "/data/krl_existing.json",
  "/data/lrt_existing.json",
  "/data/mrt_existing.json",
  "/data/sources.json",
] as const;

export function prefetchOverlays() {
  if (typeof fetch === "undefined") return;
  for (const u of PREFETCH_URLS) void fetch(u, { cache: "force-cache" });
}
