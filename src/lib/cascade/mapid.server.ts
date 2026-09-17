import { readFileSync } from "node:fs";
import { join } from "node:path";
import { EMPTY_MAP_STYLE, MAPID_HOST, MAPID_STYLE_IDS, isMapidStyleKey, type MapidStyleKey } from "./mapid";

const UA = "CASCADE-WebGIS/1.0";
const MAPID_FAIL = "MAPID gagal dimuat. Periksa konfigurasi akses atau koneksi basemap.";

type StyleJson = {
  version?: number;
  sources?: Record<string, { type?: string; url?: string; tiles?: string[]; minzoom?: number; maxzoom?: number; attribution?: string; bounds?: number[] }>;
  glyphs?: string;
  sprite?: string;
  layers?: unknown[];
  [k: string]: unknown;
};

const preparedCache = new Map<string, StyleJson>();

function readKeyFromAppEnv(): string {
  const candidates = [join(process.cwd(), ".grok/app-env.json"), join(process.cwd(), "..", ".grok", "app-env.json")];
  for (const file of candidates) {
    try {
      const parsed = JSON.parse(readFileSync(file, "utf8")) as { MAPID_API_KEY?: unknown };
      if (typeof parsed.MAPID_API_KEY === "string" && parsed.MAPID_API_KEY.trim()) {
        return parsed.MAPID_API_KEY.trim();
      }
    } catch {
      /* next */
    }
  }
  return "";
}

export function getMapidApiKey(): string {
  return process.env.MAPID_API_KEY?.trim() || readKeyFromAppEnv() || "";
}

function withKey(url: string, key: string): string {
  const u = new URL(url);
  u.searchParams.set("key", key);
  return u.toString();
}

function isMapidHost(hostname: string): boolean {
  return hostname === MAPID_HOST || hostname.endsWith(`.${MAPID_HOST}`);
}

async function fetchJson(url: string): Promise<{ ok: true; data: unknown; status: number } | { ok: false; status: number; message: string }> {
  try {
    const res = await fetch(url, { headers: { Accept: "application/json", "User-Agent": UA }, signal: AbortSignal.timeout(18000) });
    if (!res.ok) return { ok: false, status: res.status, message: `MAPID menolak permintaan (${res.status})` };
    return { ok: true, data: await res.json(), status: res.status };
  } catch {
    return { ok: false, status: 502, message: "Koneksi ke basemap MAPID gagal" };
  }
}

async function inlineVectorSource(spec: NonNullable<StyleJson["sources"]>[string], key: string): Promise<void> {
  if (!spec.url || !spec.url.includes(MAPID_HOST)) return;
  const got = await fetchJson(withKey(spec.url, key));
  if (!got.ok) return;
  const tj = got.data as { tiles?: string[]; minzoom?: number; maxzoom?: number; attribution?: string; bounds?: number[] };
  spec.tiles = ["/api/mapid/tiles/{z}/{x}/{y}.pbf"];
  if (typeof tj.minzoom === "number") spec.minzoom = tj.minzoom;
  if (typeof tj.maxzoom === "number") spec.maxzoom = tj.maxzoom;
  if (typeof tj.attribution === "string") spec.attribution = tj.attribution;
  if (Array.isArray(tj.bounds)) spec.bounds = tj.bounds;
  delete spec.url;
}

export async function loadPreparedStyle(styleKey: string): Promise<{ ok: true; style: StyleJson; styleId: string } | { ok: false; status: number; stage: string; message: string }> {
  const key = getMapidApiKey();
  if (!key) {
    return { ok: false, status: 503, stage: "config", message: "Konfigurasi akses MAPID tidak tersedia" };
  }
  const normalized: MapidStyleKey = isMapidStyleKey(styleKey) ? styleKey : "basic";
  const styleId = MAPID_STYLE_IDS[normalized];
  const cached = preparedCache.get(styleId);
  if (cached) return { ok: true, style: structuredClone(cached), styleId };
  const got = await fetchJson(withKey(`https://${MAPID_HOST}/styles/${styleId}/style.json`, key));
  if (!got.ok) return { ok: false, status: got.status, stage: "fetch_style", message: got.message };
  const style = got.data as StyleJson;
  for (const spec of Object.values(style.sources ?? {})) {
    if (spec?.url?.includes(MAPID_HOST)) await inlineVectorSource(spec, key);
  }
  if (typeof style.glyphs === "string" && style.glyphs.includes(MAPID_HOST)) {
    style.glyphs = "/api/mapid/fonts/{fontstack}/{range}.pbf";
  }
  if (typeof style.sprite === "string" && style.sprite.includes(MAPID_HOST)) {
    const spritePath = style.sprite.replace(`https://${MAPID_HOST}/`, "").replace(`http://${MAPID_HOST}/`, "");
    style.sprite = `/api/mapid/forward?u=${encodeURIComponent(`https://${MAPID_HOST}/${spritePath}`)}`;
  }
  preparedCache.set(styleId, style);
  return { ok: true, style: structuredClone(style), styleId };
}

export function emptyStyleForError() {
  return EMPTY_MAP_STYLE;
}

export async function proxyMapidPath(path: string): Promise<Response> {
  const key = getMapidApiKey();
  if (!key) return Response.json({ error: MAPID_FAIL, stage: "config" }, { status: 503 });
  const clean = path.replace(/^\/+/, "");
  if (clean.includes("..") || clean.startsWith("http")) return new Response("Bad path", { status: 400 });
  try {
    const res = await fetch(withKey(`https://${MAPID_HOST}/${clean}`, key), { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(20000) });
    const buf = await res.arrayBuffer();
    const headers = new Headers();
    const ct = res.headers.get("content-type");
    if (ct) headers.set("content-type", ct);
    headers.set("cache-control", "public, max-age=3600");
    return new Response(buf, { status: res.status, headers });
  } catch {
    return new Response("MAPID upstream gagal", { status: 502 });
  }
}

export async function proxyMapidUrl(raw: string): Promise<Response> {
  const key = getMapidApiKey();
  if (!key) return Response.json({ error: MAPID_FAIL, stage: "config" }, { status: 503 });
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return new Response("Bad url", { status: 400 });
  }
  if (!isMapidHost(parsed.hostname)) return new Response("Forbidden host", { status: 403 });
  parsed.searchParams.delete("key");
  try {
    const res = await fetch(withKey(parsed.toString(), key), { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(20000) });
    const buf = await res.arrayBuffer();
    const headers = new Headers();
    const ct = res.headers.get("content-type");
    if (ct) headers.set("content-type", ct);
    headers.set("cache-control", "public, max-age=3600");
    return new Response(buf, { status: res.status, headers });
  } catch {
    return new Response("MAPID upstream gagal", { status: 502 });
  }
}
