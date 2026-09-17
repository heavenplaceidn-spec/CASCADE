import { emptyFC, type Feature, type FeatureCollection } from "./geojson";
import { hotspotsAlong, meanScore } from "./bottleneck";
import type { SimNode, SimResult, SimSegment, SimVehicle, StatusKey } from "./store";

function hav(a: [number, number], b: [number, number]) {
  const R = 6371000;
  const to = (d: number) => (d * Math.PI) / 180;
  const dlon = to(b[0] - a[0]);
  const dlat = to(b[1] - a[1]);
  const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(a[1])) * Math.cos(to(b[1])) * Math.sin(dlon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function lineCoords(f: Feature): [number, number][] {
  const g = f.geometry;
  if (g.type === "LineString") return g.coordinates as [number, number][];
  if (g.type === "MultiLineString") return (g.coordinates as [number, number][][]).flat();
  return [];
}

function nearestIdx(coords: [number, number][], pt: [number, number]) {
  let best = 0;
  let bd = Infinity;
  for (let i = 0; i < coords.length; i++) {
    const d = hav(coords[i], pt);
    if (d < bd) {
      bd = d;
      best = i;
    }
  }
  return { i: best, d: bd };
}

function sliceLine(coords: [number, number][], a: [number, number], b: [number, number]): [number, number][] {
  const ia = nearestIdx(coords, a);
  const ib = nearestIdx(coords, b);
  if (ia.i === ib.i) return [coords[ia.i]];
  const lo = Math.min(ia.i, ib.i);
  const hi = Math.max(ia.i, ib.i);
  const part = coords.slice(lo, hi + 1);
  return ia.i > ib.i ? part.reverse() : part;
}

function lengthM(coords: [number, number][]) {
  let m = 0;
  for (let i = 1; i < coords.length; i++) m += hav(coords[i - 1], coords[i]);
  return m;
}

function normName(raw: string) {
  return raw
    .toLowerCase()
    .replace(/stasiun|halte|station|terminal|interchange/g, " ")
    .replace(/\b(mrt|lrt|krl|tj|transjakarta|commuter)\b/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function namesClose(a: string, b: string) {
  const na = normName(a);
  const nb = normName(b);
  if (!na || !nb || na.length < 3 || nb.length < 3) return false;
  if (na === nb) return true;
  if (na.length >= 6 && nb.length >= 6 && (na.includes(nb) || nb.includes(na))) return true;
  return false;
}

function modeOf(p: Record<string, unknown>, fallback = ""): string {
  const m = String(p.mode || fallback).toLowerCase();
  if (m.includes("mrt")) return "mrt";
  if (m.includes("lrt")) return "lrt";
  if (m.includes("krl") || m.includes("rail") || m.includes("commuter")) return "krl";
  if (m.includes("transjakarta") || m.includes("brt") || m.includes("bus")) return "transjakarta";
  return m || fallback;
}

function vehicleOf(mode: string): SimVehicle {
  const m = String(mode || "").toLowerCase();
  if (m.includes("mrt")) return "mrt";
  if (m.includes("lrt")) return "lrt";
  if (m.includes("krl") || m.includes("rail") || m.includes("commuter")) return "krl";
  return "bus";
}

function isHub(p: Record<string, unknown>) {
  const v = p.interchange ?? p.is_interchange;
  return v === "YES" || v === "yes" || v === "ya" || v === true || p.existing === "YES";
}

function featId(f: Feature) {
  return String(f.id ?? f.properties.id ?? f.properties.route_id ?? f.properties.corridor_id ?? "");
}

function skipRoute(id: string) {
  return id === "krl-network" || id === "lrt-network" || id.endsWith("-network");
}

/** Walking transfer only at real nearby stations. Geometry crossings without a station are not transfers. */
export const TRANSFER_WALK_M = 130;
export const SAME_NAME_CLUSTER_M = 280;
export const HUB_CLUSTER_M = 420;

const HUB_NAMES = new Set([
  "lebak bulus",
  "fatmawati",
  "dukuh atas",
  "manggarai",
  "senen",
  "cawang",
  "bundaran hi",
  "tanah abang",
  "depok baru",
  "blok m",
  "cibubur",
  "parung panjang",
  "tangerang",
  "maja",
  "dramaga",
  "mauk",
  "sentul",
  "jasinga",
  "leuwiliang",
  "bitung",
  "ice bsd",
  "jonggol",
  "ancol",
  "pik 2",
  "bandara soekarno hatta",
  "jambu dua",
  "ciputat",
  "pinang ranti",
  "pulo gebang",
  "petojo",
  "jagakarsa",
  "kemang",
  "grogol",
  "grogol reformasi",
  "senayan city",
  "galunggung",
  "pasar rebo",
  "pasar minggu",
  "marunda",
  "marunda center",
  "koja",
  "jatiwaringin",
  "ciracas",
  "ragunan",
  "trikora",
  "kelapa dua depok",
  "moh kahfi",
  "andara",
  "petamburan",
  "asean",
  "kejaksaan agung",
  "sawangan",
  "upn veteran",
  "pondok labu",
  "kalideres",
  "puri indah",
  "ciledug",
  "cbd ciledug",
  "joglo",
  "meruya",
  "monas",
  "plumpang",
  "kapuk",
  "cengkareng business city",
  "pulo gadung",
  "harapan indah",
  "jis",
  "cilincing",
]);

type RawStop = {
  id: string;
  name: string;
  norm: string;
  coord: [number, number];
  status: StatusKey;
  mode: string;
  routeId: string;
  corridorId: string;
  hub: boolean;
  lineCodes: string;
  order: number;
};

type Cluster = {
  id: string;
  name: string;
  coord: [number, number];
  hub: boolean;
  modes: Set<string>;
  statuses: Set<StatusKey>;
  routeIds: Set<string>;
};

type Ride = {
  a: string;
  b: string;
  routeId: string;
  status: StatusKey;
  mode: string;
  coords: [number, number][];
  meters: number;
  fromName: string;
  toName: string;
};

type Xfer = { a: string; b: string; meters: number; name: string };

export type TransitGraph = {
  clusters: Map<string, Cluster>;
  rides: Ride[];
  xf: Xfer[];
  adj: Map<string, { to: string; cost: number; ride?: Ride; xfer?: Xfer }[]>;
};

export type NetworkAudit = {
  corridors: number;
  nodes: number;
  rides: number;
  transfers: number;
  connected: number;
  isolated: string[];
  ready: boolean;
  tests: { name: string; ok: boolean; note: string }[];
};

async function loadFc(url: string): Promise<FeatureCollection> {
  const res = await fetch(url, { cache: "force-cache" });
  if (!res.ok) return emptyFC();
  return res.json() as Promise<FeatureCollection>;
}

function packStops(feats: Feature[], status: StatusKey, fallbackMode: string): RawStop[] {
  const out: RawStop[] = [];
  for (const f of feats) {
    if (f.geometry.type !== "Point") continue;
    const p = f.properties;
    const coord = f.geometry.coordinates as [number, number];
    const name = String(p.name || p.stop_name || p.station_name || "Stasiun");
    const routeId = String(p.route_id || p.corridor_id || p.line_code || p.line_id || "");
    const order = Number(p.stop_order ?? p.station_order ?? p.route_order ?? 0);
    const unique =
      String(f.id || "") ||
      String(p.stop_id || "") ||
      String(p.station_id || "") ||
      (String(p.id || "") && String(p.id) !== routeId ? String(p.id) : "") ||
      `${routeId}-S${String(order || 0).padStart(2, "0")}-${name}`;
    out.push({
      id: unique,
      name,
      norm: normName(name),
      coord,
      status,
      mode: modeOf(p, fallbackMode),
      routeId,
      corridorId: String(p.corridor_id || p.route_id || ""),
      hub: isHub(p),
      lineCodes: String(p.line_codes || p.corridor_nos || p.connected_corridors || ""),
      order,
    });
  }
  return out;
}

function projectHubsOntoExisting(stops: RawStop[], routes: { f: Feature; status: StatusKey }[]): RawStop[] {
  const extra: RawStop[] = [];
  const hubs = stops.filter((s) => s.status === "cascade" && s.hub);
  const seen = new Set<string>();
  for (const h of hubs) {
    for (const { f, status } of routes) {
      if (status === "cascade") continue;
      const coords = lineCoords(f);
      if (coords.length < 2) continue;
      const near = nearestIdx(coords, h.coord);
      if (near.d > 95) continue;
      const rid = featId(f);
      const key = `${h.norm}|${rid}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const line = String(f.properties.line_code || "");
      extra.push({
        id: `proj-${h.norm}-${rid}`,
        name: h.name,
        norm: h.norm,
        coord: coords[near.i],
        status,
        mode: modeOf(f.properties, "krl"),
        routeId: rid,
        corridorId: rid,
        hub: true,
        lineCodes: line ? `,${line},` : "",
        order: 0,
      });
    }
  }
  return extra.length ? [...stops, ...extra] : stops;
}

function matchesRoute(s: RawStop, route: Feature, status: StatusKey): boolean {
  if (s.status !== status) return false;
  const p = route.properties;
  const rid = featId(route);
  const routeId = String(p.route_id || rid);
  const rMode = modeOf(p, s.mode);
  if (rMode && s.mode && rMode !== s.mode) return false;
  if (status === "cascade") return s.routeId === rid || s.routeId === routeId;
  if (status === "masterplan") {
    const cid = String(p.corridor_id || rid);
    return s.corridorId === cid || s.routeId === cid;
  }
  const line = String(p.line_code || "");
  if (line && s.lineCodes.includes(`,${line},`)) return true;
  const corr = String(p.corridor_id || "");
  const no = String(p.corridor_no ?? "").replace(/^K/i, "");
  if (corr && (s.corridorId === corr || s.routeId === corr)) return true;
  if (no && (s.lineCodes.includes(`,${no},`) || s.corridorId === `K${no}` || s.corridorId === no)) return true;
  if (s.routeId === rid || s.routeId === routeId) return true;
  return false;
}

function clusterStops(stops: RawStop[]): { clusters: Map<string, Cluster>; of: Map<string, string> } {
  const n = stops.length;
  const parent = stops.map((_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const unite = (a: number, b: number) => {
    const pa = find(a);
    const pb = find(b);
    if (pa !== pb) parent[pa] = pb;
  };
  const byNorm = new Map<string, number[]>();
  for (let i = 0; i < n; i++) {
    const k = stops[i].norm || `__${i}`;
    const arr = byNorm.get(k);
    if (arr) arr.push(i);
    else byNorm.set(k, [i]);
  }
  for (const [k, idxs] of byNorm) {
    if (k.startsWith("__") || k.length < 4 || k.startsWith("km ") || /^km\s*\d/.test(k)) continue;
    const lim = HUB_NAMES.has(k) ? HUB_CLUSTER_M : SAME_NAME_CLUSTER_M;
    for (let a = 0; a < idxs.length; a++) {
      for (let b = a + 1; b < idxs.length; b++) {
        if (hav(stops[idxs[a]].coord, stops[idxs[b]].coord) < lim) unite(idxs[a], idxs[b]);
      }
    }
  }
  const cell = 0.008;
  const grid = new Map<string, number[]>();
  const key = (lng: number, lat: number) => `${Math.floor(lng / cell)}_${Math.floor(lat / cell)}`;
  for (let i = 0; i < n; i++) {
    const k = key(stops[i].coord[0], stops[i].coord[1]);
    const arr = grid.get(k);
    if (arr) arr.push(i);
    else grid.set(k, [i]);
  }
  for (let i = 0; i < n; i++) {
    const [lng, lat] = stops[i].coord;
    const gx = Math.floor(lng / cell);
    const gy = Math.floor(lat / cell);
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const bucket = grid.get(`${gx + dx}_${gy + dy}`);
        if (!bucket) continue;
        for (const j of bucket) {
          if (j <= i) continue;
          const d = hav(stops[i].coord, stops[j].coord);
          if (d < 70) unite(i, j);
          else if (d < 160 && (stops[i].hub || stops[j].hub) && (stops[i].norm === stops[j].norm || stops[i].status !== stops[j].status)) {
            unite(i, j);
          }
        }
      }
    }
  }
  const clusters = new Map<string, Cluster>();
  const of = new Map<string, string>();
  const groups = new Map<number, RawStop[]>();
  for (let i = 0; i < n; i++) {
    const r = find(i);
    const arr = groups.get(r);
    if (arr) arr.push(stops[i]);
    else groups.set(r, [stops[i]]);
  }
  let seq = 0;
  for (const group of groups.values()) {
    const hub = group.find((s) => s.hub) || group[0];
    const id = `h${seq++}`;
    let lng = 0;
    let lat = 0;
    for (const s of group) {
      lng += s.coord[0];
      lat += s.coord[1];
    }
    const c: Cluster = {
      id,
      name: hub.name,
      coord: [lng / group.length, lat / group.length],
      hub: group.some((s) => s.hub),
      modes: new Set(group.map((s) => s.mode)),
      statuses: new Set(group.map((s) => s.status)),
      routeIds: new Set(group.map((s) => s.routeId).filter(Boolean)),
    };
    clusters.set(id, c);
    for (const s of group) of.set(s.id, id);
  }
  return { clusters, of };
}

function buildAdj(rides: Ride[], xf: Xfer[], preferred: StatusKey, preferMode = "", preferRoute = ""): TransitGraph["adj"] {
  const adj: TransitGraph["adj"] = new Map();
  const add = (from: string, to: string, cost: number, extra: { ride?: Ride; xfer?: Xfer }) => {
    const arr = adj.get(from);
    if (arr) arr.push({ to, cost, ...extra });
    else adj.set(from, [{ to, cost, ...extra }]);
  };
  for (const r of rides) {
    const statusBias = r.status === preferred ? 0.8 : 2.4;
    const modeBias = preferMode && r.mode !== preferMode ? 2.2 : 1;
    const routeBias = preferRoute && r.routeId === preferRoute ? 0.55 : 1;
    const cost = Math.max(80, r.meters) * statusBias * modeBias * routeBias;
    add(r.a, r.b, cost, { ride: r });
    add(r.b, r.a, cost, { ride: r });
  }
  for (const x of xf) {
    const cost = 1400 + x.meters * 3.2;
    add(x.a, x.b, cost, { xfer: x });
    add(x.b, x.a, cost, { xfer: x });
  }
  return adj;
}

let cached: { stops: RawStop[]; routes: { f: Feature; status: StatusKey }[]; graph?: TransitGraph } | null = null;

async function loadRaw() {
  if (cached) return cached;
  const [casR, casS, mpR, mpS, krlR, mrtR, lrtR, tjR, krlS, mrtS, lrtS, tjS] = await Promise.all([
    loadFc("/data/cascade_candidates.geojson?v=tj28"),
    loadFc("/data/cascade_stops.geojson?v=tj28"),
    loadFc("/data/masterplan.geojson"),
    loadFc("/data/masterplan_stations.geojson"),
    loadFc("/data/krl_routes.geojson"),
    loadFc("/data/mrt_routes.geojson"),
    loadFc("/data/lrt_routes.geojson"),
    loadFc("/data/transjakarta_routes.geojson"),
    loadFc("/data/krl_stops.geojson"),
    loadFc("/data/mrt_stops.geojson"),
    loadFc("/data/lrt_stops.geojson"),
    loadFc("/data/transjakarta_stops.geojson"),
  ]);
  const routes: { f: Feature; status: StatusKey }[] = [
    ...casR.features.map((f) => ({ f, status: "cascade" as const })),
    ...mpR.features.map((f) => ({ f, status: "masterplan" as const })),
    ...krlR.features.map((f) => ({ f, status: "existing" as const })),
    ...mrtR.features.map((f) => ({ f, status: "existing" as const })),
    ...lrtR.features.map((f) => ({ f, status: "existing" as const })),
    ...tjR.features.map((f) => ({ f, status: "existing" as const })),
  ].filter((r) => !skipRoute(featId(r.f)) && lineCoords(r.f).length > 2);
  const stops = [
    ...packStops(casS.features, "cascade", "mrt"),
    ...packStops(mpS.features, "masterplan", "mrt"),
    ...packStops(krlS.features, "existing", "krl"),
    ...packStops(mrtS.features, "existing", "mrt"),
    ...packStops(lrtS.features, "existing", "lrt"),
    ...packStops(tjS.features, "existing", "transjakarta"),
  ];
  cached = { stops: projectHubsOntoExisting(stops, routes), routes };
  return cached;
}

export async function getTransitGraph(preferred: StatusKey, preferMode = "", preferRoute = ""): Promise<TransitGraph> {
  const raw = await loadRaw();
  if (raw.graph) return rebuildAdj(raw.graph, preferred, preferMode, preferRoute);
  const { clusters, of } = clusterStops(raw.stops);
  const rides: Ride[] = [];
  for (const { f, status } of raw.routes) {
    const coords = lineCoords(f);
    const rid = featId(f);
    const on = raw.stops.filter((s) => matchesRoute(s, f, status) && nearestIdx(coords, s.coord).d < 520);
    if (on.length < 2) continue;
    const ordered = on
      .map((s) => ({
        s,
        i: status === "cascade" && (s.routeId === rid || s.routeId === String(f.properties.route_id || "")) && s.order > 0 ? s.order : nearestIdx(coords, s.coord).i,
      }))
      .sort((a, b) => a.i - b.i);
    const seen = new Set<string>();
    const seq: RawStop[] = [];
    for (const { s } of ordered) {
      const cid = of.get(s.id);
      if (!cid || seen.has(cid)) continue;
      seen.add(cid);
      seq.push(s);
    }
    for (let i = 0; i < seq.length - 1; i++) {
      const a = of.get(seq[i].id)!;
      const b = of.get(seq[i + 1].id)!;
      if (a === b) continue;
      const slice = sliceLine(coords, seq[i].coord, seq[i + 1].coord);
      const meters = lengthM(slice);
      if (meters < 40 || meters > 85000) continue;
      rides.push({
        a,
        b,
        routeId: rid,
        status,
        mode: modeOf(f.properties, seq[i].mode),
        coords: slice.length > 1 ? slice : [seq[i].coord, seq[i + 1].coord],
        meters,
        fromName: seq[i].name,
        toName: seq[i + 1].name,
      });
    }
  }
  const xf: Xfer[] = [];
  const clArr = [...clusters.values()];
  const cell = 0.01;
  const grid = new Map<string, Cluster[]>();
  const gk = (c: Cluster) => `${Math.floor(c.coord[0] / cell)}_${Math.floor(c.coord[1] / cell)}`;
  for (const c of clArr) {
    const k = gk(c);
    const arr = grid.get(k);
    if (arr) arr.push(c);
    else grid.set(k, [c]);
  }
  const seenX = new Set<string>();
  for (const a of clArr) {
    const gx = Math.floor(a.coord[0] / cell);
    const gy = Math.floor(a.coord[1] / cell);
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const bucket = grid.get(`${gx + dx}_${gy + dy}`) || [];
        for (const b of bucket) {
          if (b.id <= a.id) continue;
          const shareRoute = [...a.routeIds].some((r) => b.routeIds.has(r));
          if (shareRoute) continue;
          const d = hav(a.coord, b.coord);
          if (d > 420) continue;
          const modeDiff = [...a.modes].some((m) => !b.modes.has(m)) || [...b.modes].some((m) => !a.modes.has(m));
          const samePlace = namesClose(a.name, b.name);
          const ok =
            (samePlace && d <= HUB_CLUSTER_M) ||
            d <= TRANSFER_WALK_M ||
            ((a.hub || b.hub) && modeDiff && d <= 280);
          if (!ok) continue;
          const key = `${a.id}|${b.id}`;
          if (seenX.has(key)) continue;
          seenX.add(key);
          const rawName = samePlace ? a.name : a.hub ? a.name : b.name;
          const label = /^km\s*\d/i.test(rawName) ? ( /^km\s*\d/i.test(a.name) ? b.name : a.name ) : rawName;
          if (/^km\s*\d/i.test(label)) continue;
          xf.push({ a: a.id, b: b.id, meters: d, name: label });
        }
      }
    }
  }
  const graph: TransitGraph = { clusters, rides, xf, adj: buildAdj(rides, xf, preferred, preferMode, preferRoute) };
  raw.graph = graph;
  return graph;
}

function rebuildAdj(g: TransitGraph, preferred: StatusKey, preferMode = "", preferRoute = ""): TransitGraph {
  return { ...g, adj: buildAdj(g.rides, g.xf, preferred, preferMode, preferRoute) };
}

function snap(g: TransitGraph, node: SimNode, other?: SimNode): string | null {
  let best: string | null = null;
  let bd = Infinity;
  for (const c of g.clusters.values()) {
    const d = hav(c.coord, node.coord);
    const shareDest = other ? [...c.routeIds].some((r) => r === other.routeId) : false;
    const bonus =
      (c.routeIds.has(node.routeId) ? -220 : 0) +
      (shareDest ? -160 : 0) +
      (c.statuses.has(node.status) ? -80 : 0) +
      (namesClose(c.name, node.name) ? -160 : 0);
    const score = d + bonus;
    if (score < bd) {
      bd = score;
      best = c.id;
    }
  }
  if (best == null || hav(g.clusters.get(best)!.coord, node.coord) > 1200) return null;
  return best;
}

type Step = { to: string; ride?: Ride; xfer?: Xfer };

function dijkstra(g: TransitGraph, src: string, dst: string): Step[] | null {
  const dist = new Map<string, number>();
  const prev = new Map<string, Step & { from: string }>();
  const xcount = new Map<string, number>();
  dist.set(src, 0);
  xcount.set(src, 0);
  const used = new Set<string>();
  while (used.size < g.clusters.size) {
    let u: string | null = null;
    let best = Infinity;
    for (const [id, d] of dist) {
      if (used.has(id)) continue;
      if (d < best) {
        best = d;
        u = id;
      }
    }
    if (u == null || best === Infinity) break;
    if (u === dst) break;
    used.add(u);
    const xc = xcount.get(u) || 0;
    if (xc > 2) continue;
    for (const e of g.adj.get(u) || []) {
      const nx = xc + (e.xfer ? 1 : 0);
      if (nx > 2) continue;
      const nd = best + e.cost;
      if (nd < (dist.get(e.to) ?? Infinity)) {
        dist.set(e.to, nd);
        xcount.set(e.to, nx);
        prev.set(e.to, { from: u, to: e.to, ride: e.ride, xfer: e.xfer });
      }
    }
  }
  if (!prev.has(dst) && src !== dst) return null;
  const steps: Step[] = [];
  let cur = dst;
  while (cur !== src) {
    const p = prev.get(cur);
    if (!p) return src === dst ? [] : null;
    steps.push({ to: p.to, ride: p.ride, xfer: p.xfer });
    cur = p.from;
  }
  steps.reverse();
  return steps;
}

function concatGeom(parts: [number, number][][]): [number, number][] {
  const out: [number, number][] = [];
  for (const part of parts) {
    for (const p of part) {
      if (!out.length || hav(out[out.length - 1], p) > 2) out.push(p);
    }
  }
  return out;
}

function failResult(origin: SimNode, dest: SimNode, note: string): { fc: FeatureCollection; result: SimResult } {
  return {
    fc: emptyFC(),
    result: {
      km: 0,
      minutes: 0,
      bottleneckBefore: 0,
      bottleneckAfter: 0,
      flowChange: 0,
      hops: [origin.name, dest.name],
      note,
      hotspots: [],
      transfers: [],
      segments: [],
    },
  };
}

function packResult(
  coords: [number, number][],
  hops: string[],
  transfers: { name: string; coord: [number, number] }[],
  preferred: StatusKey,
  segments: SimSegment[],
  extraNote = "",
): { fc: FeatureCollection; result: SimResult } {
  if (coords.length < 2) {
    return {
      fc: emptyFC(),
      result: {
        km: 0,
        minutes: 0,
        bottleneckBefore: 0,
        bottleneckAfter: 0,
        flowChange: 0,
        hops,
        note: extraNote || "Rute belum terhubung pada jaringan yang tersedia.",
        hotspots: [],
        transfers,
        segments,
      },
    };
  }
  const km = Number((lengthM(coords) / 1000).toFixed(2));
  const minutes = Math.max(4, Math.round((km / 32) * 60) + transfers.length * 4);
  const before = meanScore(coords, "existing");
  const after = meanScore(coords, preferred);
  const line: Feature = {
    type: "Feature",
    id: "sim-path",
    properties: { id: "sim-path", status: preferred, km },
    geometry: { type: "LineString", coordinates: coords },
  };
  const pts: Feature[] = transfers.map((t, i) => ({
    type: "Feature",
    id: `xfer-${i}`,
    properties: { id: `xfer-${i}`, name: t.name, kind: "transfer" },
    geometry: { type: "Point", coordinates: t.coord },
  }));
  const uniqHops = hops.filter((h, i) => i === 0 || h !== hops[i - 1]);
  return {
    fc: { type: "FeatureCollection", features: [line, ...pts] },
    result: {
      km,
      minutes,
      bottleneckBefore: Number(before.toFixed(2)),
      bottleneckAfter: Number(after.toFixed(2)),
      flowChange: Number((before - after).toFixed(2)),
      hops: uniqHops,
      hotspots: hotspotsAlong(coords, preferred),
      transfers,
      segments,
      note: extraNote || (transfers.length ? `Pindah di ${transfers.map((t) => t.name).join(", ")}.` : ""),
    },
  };
}

function stopsAlongSlice(stops: RawStop[], coords: [number, number][], routeId: string): SimSegment["stops"] {
  const out: SimSegment["stops"] = [];
  const on = stops
    .filter((s) => s.routeId === routeId)
    .map((s) => ({ s, idx: nearestIdx(coords, s.coord) }))
    .filter((x) => x.idx.d < 180)
    .sort((a, b) => a.idx.i - b.idx.i);
  let acc = 0;
  let cursor = 0;
  for (const { s, idx } of on) {
    while (cursor < idx.i && cursor < coords.length - 1) {
      acc += hav(coords[cursor], coords[cursor + 1]);
      cursor++;
    }
    if (!out.length || out[out.length - 1].name !== s.name) out.push({ name: s.name, coord: s.coord, atM: acc });
  }
  return out;
}

function directOnCorridor(
  raw: { stops: RawStop[]; routes: { f: Feature; status: StatusKey }[] },
  origin: SimNode,
  dest: SimNode,
  preferred: StatusKey,
): { fc: FeatureCollection; result: SimResult } | null {
  const oN = normName(origin.name);
  const dN = normName(dest.name);
  if (!oN || !dN) return null;
  type Cand = { f: Feature; status: StatusKey; rid: string; o: RawStop; d: RawStop; score: number };
  const cands: Cand[] = [];
  for (const { f, status } of raw.routes) {
    const rid = featId(f);
    const coords = lineCoords(f);
    if (coords.length < 2) continue;
    const on = raw.stops.filter((s) => matchesRoute(s, f, status) && nearestIdx(coords, s.coord).d < 520);
    const oHits = on.filter((s) => s.norm === oN || namesClose(s.name, origin.name) || hav(s.coord, origin.coord) < 90);
    const dHits = on.filter((s) => s.norm === dN || namesClose(s.name, dest.name) || hav(s.coord, dest.coord) < 90);
    if (!oHits.length || !dHits.length) continue;
    const o =
      oHits.find((s) => s.routeId === origin.routeId) ||
      oHits.find((s) => hav(s.coord, origin.coord) < 120) ||
      oHits[0];
    const d =
      dHits.find((s) => s.routeId === dest.routeId) ||
      dHits.find((s) => hav(s.coord, dest.coord) < 120) ||
      dHits[0];
    if (o.id === d.id && hav(o.coord, d.coord) < 40) continue;
    const score =
      (status === preferred ? 0 : 8) +
      (rid === origin.routeId || rid === dest.routeId ? 0 : 5) +
      (status === "cascade" ? 0 : 3) +
      (o.norm === oN ? 0 : 2) +
      (d.norm === dN ? 0 : 2);
    cands.push({ f, status, rid, o, d, score });
  }
  if (!cands.length) return null;
  cands.sort((a, b) => a.score - b.score);
  const pick = cands[0];
  const coords = sliceLine(lineCoords(pick.f), pick.o.coord, pick.d.coord);
  if (coords.length < 2) return null;
  const mode = modeOf(pick.f.properties, pick.o.mode);
  const hops = [pick.o.name];
  const along = stopsAlongSlice(
    raw.stops.filter((s) => s.routeId === pick.rid),
    coords,
    pick.rid,
  );
  for (const s of along) {
    if (s.name !== hops[hops.length - 1]) hops.push(s.name);
  }
  if (hops[hops.length - 1] !== pick.d.name) hops.push(pick.d.name);
  const segment: SimSegment = {
    corridorId: pick.rid,
    routeId: pick.rid,
    mode,
    status: pick.status,
    kind: "ride",
    coords,
    meters: lengthM(coords),
    fromName: pick.o.name,
    toName: pick.d.name,
    vehicle: vehicleOf(mode),
    stops: along,
  };
  return packResult(coords, hops, [], preferred, [segment]);
}

export async function routeViaGraph(
  origin: SimNode,
  dest: SimNode,
  preferred: StatusKey,
): Promise<{ fc: FeatureCollection; result: SimResult }> {
  const raw = await loadRaw();
  const direct = directOnCorridor(raw, origin, dest, preferred);
  if (direct && (direct.result.km > 0 || (direct.result.segments?.length ?? 0) > 0)) return direct;

  const preferRoute = origin.routeId && origin.routeId === dest.routeId ? origin.routeId : origin.routeId || dest.routeId;
  const g = await getTransitGraph(preferred, origin.mode, preferRoute);
  const a = snap(g, origin, dest);
  const b = snap(g, dest, origin);
  if (!a || !b) return failResult(origin, dest, "Stasiun tidak menempel pada koridor yang terpetakan.");
  if (a === b) {
    const c = g.clusters.get(a)!;
    const coords: [number, number][] = [origin.coord, c.coord, dest.coord].filter((p, i, arr) => i === 0 || hav(arr[i - 1], p) > 2);
    return packResult(coords.length > 1 ? coords : [c.coord, c.coord], [origin.name, dest.name], [{ name: c.name, coord: c.coord }], preferred, [], `Pindah di ${c.name}.`);
  }
  const steps = dijkstra(g, a, b);
  if (steps == null) return failResult(origin, dest, "Rute belum terhubung pada jaringan yang tersedia.");
  const parts: [number, number][][] = [];
  const hops: string[] = [origin.name];
  const transfers: { name: string; coord: [number, number] }[] = [];
  const segments: SimSegment[] = [];
  let lastRoute: string | null = null;
  let open: SimSegment | null = null;
  const flush = () => {
    if (open && open.coords.length > 1) segments.push(open);
    open = null;
  };
  for (const st of steps) {
    if (st.ride) {
      const geom = st.to === st.ride.b ? st.ride.coords : [...st.ride.coords].reverse();
      parts.push(geom);
      const fromName = st.to === st.ride.b ? st.ride.fromName : st.ride.toName;
      const toName = st.to === st.ride.b ? st.ride.toName : st.ride.fromName;
      if (lastRoute && lastRoute !== st.ride.routeId) {
        const fromId = st.to === st.ride.b ? st.ride.a : st.ride.b;
        const c = g.clusters.get(fromId);
        if (c) {
          hops.push(`${c.name} (pindah)`);
          transfers.push({ name: c.name, coord: c.coord });
        }
        flush();
      }
      if (!open || open.routeId !== st.ride.routeId) {
        flush();
        open = {
          corridorId: st.ride.routeId,
          routeId: st.ride.routeId,
          mode: st.ride.mode,
          status: st.ride.status,
          kind: "ride",
          coords: [...geom],
          meters: lengthM(geom),
          fromName,
          toName,
          vehicle: vehicleOf(st.ride.mode),
          stops: [
            { name: fromName, coord: geom[0], atM: 0 },
            { name: toName, coord: geom[geom.length - 1], atM: lengthM(geom) },
          ],
        };
      } else {
        const extra = geom.slice(1);
        open.coords.push(...extra);
        open.meters = lengthM(open.coords);
        open.toName = toName;
        open.stops.push({ name: toName, coord: geom[geom.length - 1], atM: open.meters });
      }
      lastRoute = st.ride.routeId;
      if (hops[hops.length - 1] !== toName) hops.push(toName);
    } else if (st.xfer) {
      const from = g.clusters.get(st.xfer.a === st.to ? st.xfer.b : st.xfer.a)!;
      const c = g.clusters.get(st.to)!;
      hops.push(`${st.xfer.name || c.name} (pindah)`);
      transfers.push({ name: st.xfer.name || c.name, coord: c.coord });
      flush();
      const walk: [number, number][] = [from.coord, c.coord];
      segments.push({
        corridorId: "",
        routeId: "",
        mode: "walk",
        status: preferred,
        kind: "transfer",
        coords: walk,
        meters: Math.max(st.xfer.meters, 20),
        fromName: from.name,
        toName: c.name,
        vehicle: open?.vehicle ?? "bus",
        stops: [
          { name: from.name, coord: from.coord, atM: 0 },
          { name: c.name, coord: c.coord, atM: Math.max(st.xfer.meters, 20) },
        ],
      });
      lastRoute = null;
    }
  }
  flush();
  if (hops[hops.length - 1] !== dest.name) hops.push(dest.name);
  const coords = concatGeom(parts);
  if (coords.length < 2) return failResult(origin, dest, "Rute belum terhubung pada jaringan yang tersedia.");
  return packResult(coords, hops, transfers, preferred, segments);
}

export function graphStats(g: TransitGraph) {
  return { hubs: g.clusters.size, rides: g.rides.length, transfers: g.xf.length };
}

export async function searchStations(q: string, limit = 8): Promise<SimNode[]> {
  const raw = await loadRaw();
  const n = q.trim().toLowerCase();
  if (n.length < 2) return [];
  const best = new Map<string, { node: SimNode; q: number }>();
  const quality = (s: RawStop) =>
    (s.status === "cascade" ? 24 : s.status === "masterplan" ? 8 : 4) +
    (s.mode === "mrt" ? 6 : s.mode === "lrt" ? 5 : s.mode === "krl" ? 5 : 4) +
    (s.order === 1 ? 6 : 0) +
    (s.routeId.startsWith("MRT-CASCADE") || s.routeId.startsWith("LRT-CASCADE") || s.routeId.startsWith("KRL-C") || s.routeId.startsWith("CASTJ") ? 4 : 0);
  for (const s of raw.stops) {
    const nm = s.name.toLowerCase();
    if (!nm.includes(n) && !s.norm.includes(n) && !s.routeId.toLowerCase().includes(n)) continue;
    const key = `${s.norm}|${s.routeId}|${s.coord[0].toFixed(4)}|${s.coord[1].toFixed(4)}`;
    const node: SimNode = {
      id: s.id,
      name: s.name,
      coord: s.coord,
      status: s.status,
      mode: s.mode,
      corridorId: s.corridorId,
      routeId: s.routeId,
    };
    const qv = quality(s) + (nm === n || s.norm === n ? 12 : nm.startsWith(n) ? 6 : 0);
    const prev = best.get(key);
    if (!prev || qv > prev.q) best.set(key, { node, q: qv });
  }
  const hits = [...best.values()];
  hits.sort((a, b) => b.q - a.q);
  return hits.slice(0, limit).map((x) => x.node);
}

export async function warmTransitGraph() {
  const g = await getTransitGraph("cascade");
  return graphStats(g);
}

export async function auditTransitNetwork(): Promise<NetworkAudit> {
  const raw = await loadRaw();
  const g = await getTransitGraph("cascade");
  const byRoute = new Map<string, number>();
  for (const r of g.rides) byRoute.set(r.routeId, (byRoute.get(r.routeId) || 0) + 1);
  const corridorIds = [...new Set(raw.routes.map((r) => featId(r.f)))];
  const isolated = corridorIds.filter((id) => (byRoute.get(id) || 0) === 0);
  const tests: NetworkAudit["tests"] = [];
  const pairs: [string, string, string][] = [
    ["Koja", "Cengkareng Business City", "CASTJ26"],
    ["Tangerang", "Parung Panjang", "KRL-C03-S"],
    ["Sentul", "Maja", "KRL-C04"],
    ["Jagakarsa", "Grogol Reformasi", "CASTJ20"],
    ["Petojo", "Pulo Gebang", "CASTJ15"],
    ["Pinang Ranti", "Lebak Bulus", "CASTJ16"],
  ];
  for (const [a, b, expect] of pairs) {
    const oa = (await searchStations(a, 8)).find((s) => s.routeId === expect) || (await searchStations(a, 8))[0];
    const od = (await searchStations(b, 8)).find((s) => s.routeId === expect) || (await searchStations(b, 8))[0];
    if (!oa || !od) {
      tests.push({ name: `${a} → ${b}`, ok: false, note: "stasiun tidak ditemukan" });
      continue;
    }
    const { result } = await routeViaGraph(oa, od, "cascade");
    const via = result.segments?.some((s) => s.routeId === expect) ?? false;
    const ok = result.km > 0 && (via || result.hops.length > 1);
    tests.push({
      name: `${a} → ${b}`,
      ok,
      note: ok ? `${result.km} km via ${(result.segments || []).map((s) => s.routeId || s.kind).join(" → ")}` : result.note,
    });
  }
  const ready = tests.filter((t) => t.ok).length >= 1 && tests.some((t) => t.name.startsWith("Koja") && t.ok);
  return {
    corridors: corridorIds.length,
    nodes: g.clusters.size,
    rides: g.rides.length,
    transfers: g.xf.length,
    connected: corridorIds.length - isolated.length,
    isolated,
    ready,
    tests,
  };
}
