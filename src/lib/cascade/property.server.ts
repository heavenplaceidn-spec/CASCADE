import { createServerFn } from "@tanstack/react-start";
import type { CorridorPropertySummary, PropertyRecord, PropFilterState } from "./property";
import { propertyMatchesFilters } from "./property";

type PropFC = { type: string; features: { id?: string; type: string; geometry: unknown; properties: PropertyRecord }[] };

async function readPub<T>(rel: string): Promise<T | null> {
  const { readFileSync } = await import("node:fs");
  const { join } = await import("node:path");
  try {
    return JSON.parse(readFileSync(join(process.cwd(), "public", rel), "utf8")) as T;
  } catch {
    return null;
  }
}

let memFc: PropFC | null = null;
let memSummaries: CorridorPropertySummary[] | null = null;
let memInsights: {
  corridor_id: string;
  corridor_name?: string;
  corridor_type?: string;
  text: string;
  median_price?: number | null;
  median_price_per_m2?: number | null;
  dominant_category?: string;
  source?: string;
  updated?: string;
}[] | null = null;
let memZones: unknown = null;

async function propertiesFc(): Promise<PropFC> {
  if (memFc) return memFc;
  memFc = (await readPub<PropFC>("data/property/properties.geojson")) ?? { type: "FeatureCollection", features: [] };
  return memFc;
}

export async function listProperties(opts: {
  bbox?: [number, number, number, number] | null;
  category?: string;
  priceClass?: string;
  corridorType?: string;
  corridorId?: string;
  sale?: string;
  limit?: number;
}): Promise<PropFC> {
  const fc = await propertiesFc();
  const limit = Math.min(Math.max(opts.limit ?? 250, 1), 300);
  const bbox = opts.bbox;
  const filters: PropFilterState = {
    tanah: !opts.category || opts.category === "TANAH",
    ruko: !opts.category || opts.category === "RUKO",
    apt: !opts.category || opts.category === "APARTEMEN/KOS",
    murah: !opts.priceClass || opts.priceClass === "MURAH",
    sedang: !opts.priceClass || opts.priceClass === "SEDANG",
    mahal: !opts.priceClass || opts.priceClass === "MAHAL",
    existing: !opts.corridorType || opts.corridorType === "existing",
    masterplan: !opts.corridorType || opts.corridorType === "masterplan",
    cascade: !opts.corridorType || opts.corridorType === "cascade",
    jual: !opts.sale || opts.sale === "jual",
    sewa: !opts.sale || opts.sale === "sewa",
  };
  const out = [];
  for (const f of fc.features) {
    const p = f.properties;
    if (!p) continue;
    if (bbox) {
      const lon = Number(p.longitude);
      const lat = Number(p.latitude);
      if (lon < bbox[0] || lat < bbox[1] || lon > bbox[2] || lat > bbox[3]) continue;
    }
    if (opts.corridorId) {
      const id = opts.corridorId;
      const hit =
        p.corridor_id === id ||
        p.existing_corridor_id === id ||
        p.masterplan_corridor_id === id ||
        p.cascade_corridor_id === id;
      if (!hit) continue;
    }
    if (!propertyMatchesFilters(p as unknown as Record<string, unknown>, filters)) continue;
    out.push(f);
    if (out.length >= limit) break;
  }
  return { type: "FeatureCollection", features: out };
}

export async function propertyById(id: string): Promise<PropertyRecord | null> {
  const fc = await propertiesFc();
  return fc.features.find((f) => f.properties?.property_id === id || String(f.id) === id)?.properties ?? null;
}

export async function corridorSummaries(): Promise<CorridorPropertySummary[]> {
  if (memSummaries) return memSummaries;
  memSummaries = (await readPub<CorridorPropertySummary[]>("data/property/corridor_summaries.json")) ?? [];
  return memSummaries;
}

export async function corridorSummary(id: string): Promise<CorridorPropertySummary | null> {
  const list = await corridorSummaries();
  return list.find((s) => s.corridor_id === id) ?? null;
}

export async function priceZones() {
  if (memZones) return memZones;
  memZones = (await readPub("data/property/price_zones.geojson")) ?? { type: "FeatureCollection", features: [] };
  return memZones;
}

export async function aiInsights() {
  if (memInsights) return memInsights;
  memInsights =
    (await readPub<NonNullable<typeof memInsights>>("data/property/insights.json")) ?? [];
  return memInsights;
}

export const getPropertyMeta = createServerFn({ method: "GET" }).handler(async () => {
  return (
    (await readPub<{ count: number; disclaimer?: string; retrieved?: string }>("data/property/meta.json")) ?? {
      count: 0,
    }
  );
});

export const getCorridorPropertySummaries = createServerFn({ method: "GET" }).handler(async () => {
  return corridorSummaries();
});

export const getPropertyInsights = createServerFn({ method: "GET" }).handler(async () => {
  return aiInsights();
});

export const getPropertyById = createServerFn({ method: "GET" })
  .validator((id: unknown) => String(id ?? ""))
  .handler(async ({ data: id }) => propertyById(id));
