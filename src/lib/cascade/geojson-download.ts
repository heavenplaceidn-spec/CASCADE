import { OVERLAY_URL } from "./static-data";

const SECRET = /key|token|secret|password|authorization|api[_-]?key|credential/i;

const LINE_URLS = [
  OVERLAY_URL.candidate,
  OVERLAY_URL.tj,
  OVERLAY_URL.krl,
  OVERLAY_URL.lrt,
  OVERLAY_URL.mrt,
  OVERLAY_URL.masterplan,
];
const STOP_URLS = [
  OVERLAY_URL["cascade-stops"],
  OVERLAY_URL["tj-stops"],
  OVERLAY_URL["krl-stops"],
  OVERLAY_URL["lrt-stops"],
  OVERLAY_URL["mrt-stops"],
  OVERLAY_URL["masterplan-stops"],
];

type Feat = { id?: unknown; type?: string; geometry?: { type?: string } | null; properties?: Record<string, unknown> | null };

const fcCache = new Map<string, Promise<Feat[]>>();

export function slugName(text: string) {
  return String(text || "koridor")
    .normalize("NFKD")
    .replace(/[\/\\:*?"<>|]+/g, "-")
    .replace(/[^\w.\-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80) || "koridor";
}

export function stripSecrets(props: Record<string, unknown> | null | undefined) {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(props ?? {})) {
    if (SECRET.test(k)) continue;
    if (typeof v === "string" && /key=|apikey=/i.test(v)) continue;
    out[k] = v;
  }
  return out;
}

export function downloadBlob(filename: string, text: string) {
  const blob = new Blob([text], { type: "application/geo+json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".geojson") ? filename : `${filename}.geojson`;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function str(v: unknown) {
  return v == null ? "" : String(v);
}

function uniq(xs: string[]) {
  const out: string[] = [];
  for (const x of xs) {
    const t = x.trim();
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

function tokens(v: unknown) {
  return uniq(str(v).split(/[,;|/]+/).map((s) => s.trim()).filter(Boolean));
}

function isLineGeom(g: Feat["geometry"]) {
  const t = g?.type ?? "";
  return t === "LineString" || t === "MultiLineString";
}

function isPointGeom(g: Feat["geometry"]) {
  return g?.type === "Point" || g?.type === "MultiPoint";
}

function loadFeats(url: string) {
  let p = fcCache.get(url);
  if (!p) {
    p = fetch(url, { cache: "force-cache" })
      .then(async (res) => {
        if (!res.ok) return [] as Feat[];
        const fc = (await res.json()) as { features?: Feat[] };
        return fc.features ?? [];
      })
      .catch(() => [] as Feat[]);
    fcCache.set(url, p);
  }
  return p;
}

async function loadAll(urls: readonly string[]) {
  const packs = await Promise.all(urls.map(loadFeats));
  return packs.flat();
}

function matchesLineIdentity(f: Feat, identity: string) {
  if (!identity || !isLineGeom(f.geometry)) return false;
  const p = f.properties ?? {};
  const route = str(p.route_id);
  const fid = str(f.id ?? p.id);
  const lineId = str(p.line_id);
  if (fid === identity || route === identity || lineId === identity) return true;
  const cid = str(p.corridor_id);
  if (!cid || cid !== identity) return false;
  // Shared parent corridor_id (e.g. CAS-KRL-C03 on C03-N and C03-S) must not merge.
  if (route && route !== cid) return false;
  return true;
}

function modeKey(mode: unknown) {
  const m = str(mode).toLowerCase();
  if (m.startsWith("krl")) return "krl";
  if (m.startsWith("mrt")) return "mrt";
  if (m.startsWith("lrt")) return "lrt";
  if (m.includes("transjakarta") || m === "tj" || m === "brt") return "transjakarta";
  return m;
}

function categoryOf(p: Record<string, unknown>, status?: string) {
  const s = str(p.status || p.network_type || status).toLowerCase();
  if (s.includes("cascade") || s.includes("proposed") || s.includes("usulan")) return "CASCADE";
  if (s.includes("master")) return "Masterplan";
  if (s.includes("exist") || s === "existing") return "Existing";
  if (status === "cascade") return "CASCADE";
  if (status === "masterplan") return "Masterplan";
  if (status === "existing") return "Existing";
  return str(p.status_label || p.status || status);
}

function identitiesFrom(opts: { id?: string; routeId?: string; corridorId?: string }) {
  return uniq([str(opts.routeId), str(opts.id), str(opts.corridorId)]);
}

async function resolveLineFeatures(identities: string[]) {
  const lines = await loadAll(LINE_URLS);
  for (const id of identities) {
    const hits = lines.filter((f) => matchesLineIdentity(f, id));
    if (hits.length) return { identity: id, features: hits };
  }
  const stops = await loadAll(STOP_URLS);
  for (const id of identities) {
    const stop = stops.find((f) => {
      const p = f.properties ?? {};
      return str(f.id) === id || str(p.stop_id) === id || str(p.station_id) === id;
    });
    if (!stop) continue;
    const p = stop.properties ?? {};
    const parent = uniq([str(p.route_id), str(p.corridor_id), str(p.line_id), str(p.line_code)]);
    for (const pid of parent) {
      const hits = lines.filter((f) => matchesLineIdentity(f, pid));
      if (hits.length) return { identity: pid, features: hits };
    }
  }
  return { identity: identities[0] || "", features: [] as Feat[] };
}

type StopRow = { name: string; id: string; sequence: number };

function stopName(p: Record<string, unknown>) {
  return str(p.stop_name || p.station_name || p.name);
}

function stopSeq(p: Record<string, unknown>) {
  const n = Number(p.stop_order ?? p.station_order ?? p.sequence);
  return Number.isFinite(n) ? n : 0;
}

function stopId(f: Feat, fallback: string, seq: number) {
  const p = f.properties ?? {};
  const id = str(f.id || p.stop_id || p.station_id || p.node_id);
  if (id && id !== fallback) return id;
  return seq ? `${fallback}-S${String(seq).padStart(2, "0")}` : fallback;
}

function lineCodeTokens(p: Record<string, unknown>) {
  return uniq([...tokens(p.line_code), ...tokens(p.line_codes).filter((t) => t !== "ALL")]);
}

function corridorTokens(p: Record<string, unknown>) {
  return uniq([...tokens(p.corridor_id), ...tokens(p.corridor_nos), ...tokens(p.corridor_no)]);
}

function stationBelongs(stop: Feat, line: Feat, identity: string) {
  if (!isPointGeom(stop.geometry) || !identity) return false;
  const s = stop.properties ?? {};
  const l = line.properties ?? {};
  const route = str(l.route_id || l.id || line.id || identity);
  if (str(s.route_id) && (str(s.route_id) === route || str(s.route_id) === identity)) return true;
  const lineCorr = str(l.corridor_id);
  if (lineCorr && corridorTokens(s).includes(lineCorr) && (!str(s.route_id) || str(s.route_id) === route || str(s.route_id) === identity)) return true;
  const codes = lineCodeTokens(l);
  const stopCodes = lineCodeTokens(s);
  if (codes.length && stopCodes.length && codes.some((c) => c && stopCodes.includes(c))) {
    const branch = str(l.line_id).toLowerCase();
    const sBranch = str(s.branch).toLowerCase();
    if (branch.includes("nambo")) return sBranch === "nambo" || sBranch === "junction";
    if (str(l.id) === "krl-network" || str(l.line_code) === "ALL") return true;
    if (sBranch === "nambo" && !branch.includes("nambo")) return false;
    return true;
  }
  if (identity && str(s.corridor_id) === identity && !str(s.route_id)) return true;
  return false;
}

async function stationsFor(lines: Feat[], identity: string): Promise<StopRow[]> {
  const stops = await loadAll(STOP_URLS);
  const rows: StopRow[] = [];
  const seen = new Set<string>();
  for (const line of lines) {
    const matched = stops.filter((s) => stationBelongs(s, line, identity));
    matched.sort((a, b) => stopSeq(a.properties ?? {}) - stopSeq(b.properties ?? {}) || stopName(a.properties ?? {}).localeCompare(stopName(b.properties ?? {})));
    matched.forEach((s, i) => {
      const p = s.properties ?? {};
      const seq = stopSeq(p) || i + 1;
      const name = stopName(p);
      if (!name) return;
      const key = `${seq}|${name}`;
      if (seen.has(key)) return;
      seen.add(key);
      rows.push({ name, id: stopId(s, identity, seq), sequence: seq });
    });
  }
  rows.sort((a, b) => a.sequence - b.sequence);
  return rows;
}

function buildProps(line: Feat, identity: string, title: string, stations: StopRow[], status?: string) {
  const raw = stripSecrets(line.properties);
  const corridorId = str(raw.route_id || raw.id || line.id || identity);
  const corridorName = str(raw.short || raw.corridor_name || raw.name || raw.route_name || raw.line_name || title || corridorId);
  const names = stations.map((s) => s.name);
  return {
    ...raw,
    corridor_id: corridorId,
    corridor_name: corridorName,
    mode: str(raw.mode || ""),
    category: categoryOf(raw, status),
    status: str(raw.status_label || raw.status || status),
    source: str(raw.source || raw.source_type || ""),
    station_count: stations.length,
    station_names: names.join("; "),
    station_ids: stations.map((s) => s.id).join("; "),
    station_sequence: stations.map((s) => `${s.sequence}. ${s.name}`).join("; "),
  };
}

function exportCollection(lines: Feat[], identity: string, title: string, stations: StopRow[], status?: string) {
  const features = lines.map((line) => {
    const props = buildProps(line, identity, title, stations, status);
    return {
      type: "Feature" as const,
      id: props.corridor_id,
      geometry: line.geometry,
      properties: props,
    };
  });
  const name = str(features[0]?.properties.corridor_name || title || identity);
  const id = str(features[0]?.properties.corridor_id || identity);
  const file = `${id}_${slugName(name)}.geojson`;
  const ids = new Set(features.map((f) => str(f.properties.corridor_id)));
  if (ids.size !== 1) return null;
  return { file, collection: { type: "FeatureCollection" as const, features } };
}

export async function downloadFeatureGeoJSON(opts: {
  id: string;
  title: string;
  role?: string;
  status?: string;
  mode?: string;
  routeId?: string;
  corridorId?: string;
}) {
  const resolved = await resolveLineFeatures(identitiesFrom(opts));
  if (!resolved.features.length) return false;
  const stations = await stationsFor(resolved.features, resolved.identity);
  const pack = exportCollection(resolved.features, resolved.identity, opts.title, stations, opts.status);
  if (!pack) return false;
  downloadBlob(pack.file, JSON.stringify(pack.collection, null, 2));
  return true;
}

export async function downloadLayerGeoJSON(opts: { status: "existing" | "masterplan" | "cascade"; mode: string }) {
  const mk = modeKey(opts.mode);
  const url =
    opts.status === "cascade"
      ? OVERLAY_URL.candidate
      : opts.status === "masterplan"
        ? OVERLAY_URL.masterplan
        : mk === "krl"
          ? OVERLAY_URL.krl
          : mk === "lrt"
            ? OVERLAY_URL.lrt
            : mk === "mrt"
              ? OVERLAY_URL.mrt
              : OVERLAY_URL.tj;
  const raw = (await loadFeats(url)).filter((f) => isLineGeom(f.geometry));
  const lines = raw.filter((f) => {
    if (opts.status === "existing") return str(f.properties?.id) !== "krl-network" && str(f.properties?.id) !== "lrt-network";
    return modeKey(f.properties?.mode) === mk || !f.properties?.mode;
  });
  if (!lines.length) return false;
  const features = [];
  for (const line of lines) {
    const identity = str(line.properties?.route_id || line.id || line.properties?.id);
    const stations = await stationsFor([line], identity);
    const pack = exportCollection([line], identity, str(line.properties?.name), stations, opts.status);
    if (pack) features.push(...pack.collection.features);
  }
  if (!features.length) return false;
  downloadBlob(`${opts.status}_${mk}.geojson`, JSON.stringify({ type: "FeatureCollection", features }, null, 2));
  return true;
}
