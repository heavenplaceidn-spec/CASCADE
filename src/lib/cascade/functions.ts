import { createServerFn } from "@tanstack/react-start";
import { emptyFC, type FeatureCollection } from "./geojson";

function dataDir() {
  return `${process.cwd()}/public/data`;
}

async function readJson<T>(name: string): Promise<T | null> {
  const { readFileSync } = await import("node:fs");
  const { join } = await import("node:path");
  try {
    return JSON.parse(readFileSync(join(dataDir(), name), "utf8")) as T;
  } catch {
    return null;
  }
}

export const getTransport = createServerFn({ method: "GET" }).handler(async () => {
  return { krl: emptyFC(), mrt: emptyFC(), lrt: emptyFC(), transjakarta: emptyFC() };
});

export const getStops = createServerFn({ method: "GET" }).handler(async () => {
  return { krl: emptyFC(), mrt: emptyFC(), lrt: emptyFC(), transjakarta: emptyFC() };
});

export const getCorridors = createServerFn({ method: "GET" }).handler(async () => {
  return { collection: emptyFC() };
});

export type CascadeMeta = {
  id: string;
  name: string;
  short: string;
  endpoint: string;
  from_name: string;
  to_name: string;
  length_km: number;
  stop_count: number;
  geometry_confidence: string;
  source: string;
  status: string;
  network_type: string;
  mode?: string;
  bbox?: [number, number, number, number];
};

export const getCascadeExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: CascadeMeta[] }>("cascade_existing.json");
  return { collection: emptyFC(), stops: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export const getMasterplan = createServerFn({ method: "GET" }).handler(async () => emptyFC());

export const getRoads = createServerFn({ method: "GET" }).handler(async () => emptyFC());

export type TjCorridorMeta = {
  corridor_no: number;
  id: string;
  name: string;
  endpoint: string;
  from_name: string;
  to_name: string;
  ruas: string[];
  length_km: number;
  stop_count: number;
  geometry_type: string;
  has_toll: boolean;
  status: string;
  source: string;
  bbox?: [number, number, number, number];
};

export type KrlLineMeta = {
  id: string;
  line_code: string;
  filter_key: string;
  name: string;
  short: string;
  endpoint: string;
  from_name: string;
  to_name: string;
  branch: string;
  stations: string[];
  stop_count: number;
  length_km: number | null;
  source: string;
  source_type: string;
  bbox?: [number, number, number, number];
};

export type RailLineMeta = {
  id: string;
  line_code: string;
  filter_key: string;
  name: string;
  short: string;
  endpoint: string;
  from_name: string;
  to_name: string;
  branch: string;
  stations: string[];
  stop_count: number;
  length_km: number | null;
  source: string;
  source_type: string;
  bbox?: [number, number, number, number];
};

export const getTjExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: TjCorridorMeta[] }>("tj_existing.json");
  return { collection: emptyFC() as FeatureCollection, stops: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export const getKrlExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: KrlLineMeta[] }>("krl_existing.json");
  return { collection: emptyFC(), stops: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export const getLrtExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: RailLineMeta[] }>("lrt_existing.json");
  return { collection: emptyFC(), stops: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export const getMrtExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: RailLineMeta[] }>("mrt_existing.json");
  return { collection: emptyFC(), stops: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export type MasterplanMeta = {
  id: string;
  name: string;
  short: string;
  mode: string;
  status: string;
  endpoint: string;
  length_km: number;
  length_source_km: number | null;
  stop_count: number;
  expected_station_count?: number;
  geometry_confidence: string;
  source: string;
  source_year: number;
  bbox?: [number, number, number, number];
};

export const getMasterplanExisting = createServerFn({ method: "GET" }).handler(async () => {
  const parsed = await readJson<{ corridors?: MasterplanMeta[] }>("masterplan_existing.json");
  return { collection: emptyFC(), stations: emptyFC(), corridors: parsed?.corridors ?? [] };
});

export const getCatalog = createServerFn({ method: "GET" }).handler(async () => {
  const sources =
    (await readJson<{ dataset: string; count: number; source_type: string; source: string }[]>("sources.json")) ?? [];
  const by = Object.fromEntries(sources.map((s) => [s.dataset, s]));
  const n = (key: string) => by[key]?.count ?? 0;
  const krlS = n("krl_stops");
  const mrtS = n("mrt_stops");
  const lrtS = n("lrt_stops");
  const tjS = n("transjakarta_stops");
  return {
    krl: n("krl_routes"),
    mrt: n("mrt_routes"),
    lrt: n("lrt_routes"),
    transjakarta: n("transjakarta_routes"),
    candidates: n("cascade_candidates"),
    masterplan: n("masterplan"),
    roads: n("roads"),
    tjStops: tjS,
    krlStops: krlS,
    lrtStops: lrtS,
    mrtStops: mrtS,
    masterplanStops: n("masterplan_stations"),
    cascadeStops: n("cascade_stops"),
    stops: krlS + mrtS + lrtS + tjS,
    sources,
  };
});
