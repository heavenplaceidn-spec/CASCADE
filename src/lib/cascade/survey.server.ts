import type { Feature, FeatureCollection } from "./geojson";
import {
  isTeamSurvey,
  parsePhotoList,
  surveyCategory,
  surveyCongestionHint,
} from "./survey";
import { SURVEY_HASHTAG } from "./survey-allowlist";

const UA = "CASCADE-WebGIS/1.0";
const ACTIVITY_URL = "https://alphaserver.mapid.io/mobile/v2/communities/activities/public";
const CACHE_MS = 12 * 60 * 1000;
const PHOTO_HOST = /(^|\.)mapid\.io$/i;

const TILES: { min_lng: number; min_lat: number; max_lng: number; max_lat: number; limit: number }[] = [
  { min_lng: 106.45, min_lat: -6.72, max_lng: 107.25, max_lat: -5.92, limit: 400 },
  { min_lng: 106.75, min_lat: -6.32, max_lng: 106.9, max_lat: -6.1, limit: 200 },
  { min_lng: 106.78, min_lat: -6.4, max_lng: 106.9, max_lat: -6.25, limit: 200 },
  { min_lng: 106.65, min_lat: -6.25, max_lng: 106.8, max_lat: -6.08, limit: 200 },
  { min_lng: 106.85, min_lat: -6.28, max_lng: 107.08, max_lat: -6.08, limit: 200 },
  { min_lng: 106.9, min_lat: -6.42, max_lng: 107.12, max_lat: -6.14, limit: 200 },
  { min_lng: 106.72, min_lat: -6.55, max_lng: 107.05, max_lat: -6.32, limit: 200 },
  { min_lng: 106.55, min_lat: -6.3, max_lng: 106.75, max_lat: -6.08, limit: 200 },
  { min_lng: 106.68, min_lat: -6.16, max_lng: 106.98, max_lat: -5.95, limit: 200 },
  { min_lng: 106.76, min_lat: -6.2, max_lng: 106.84, max_lat: -6.14, limit: 250 },
  { min_lng: 106.8, min_lat: -6.26, max_lng: 106.86, max_lat: -6.21, limit: 250 },
];

type RawActivity = {
  _id?: string;
  title?: string;
  description?: string;
  user_name?: string;
  geometry?: { type?: string; coordinates?: unknown };
  medias?: unknown;
};

type Cache = { at: number; fc: FeatureCollection; count: number; message: string; ok: boolean };
let cache: Cache | null = null;
let inflight: Promise<Cache> | null = null;

function validCoord(lng: number, lat: number) {
  return Number.isFinite(lng) && Number.isFinite(lat) && lng >= 105.5 && lng <= 107.8 && lat <= -5.7 && lat >= -7.2;
}

function stripPii(s: string) {
  return s
    .replace(/(?:\+62|62|0)8[1-9][0-9]{7,11}/g, "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function safePhotos(raw: unknown): string[] {
  const out: string[] = [];
  for (const u of parsePhotoList(raw)) {
    try {
      const url = new URL(u);
      if (url.protocol !== "https:") continue;
      if (!PHOTO_HOST.test(url.hostname)) continue;
      out.push(url.toString());
    } catch {
      /* skip */
    }
    if (out.length >= 6) break;
  }
  return out;
}

async function fetchTile(tile: (typeof TILES)[number]): Promise<RawActivity[]> {
  const res = await fetch(ACTIVITY_URL, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", "User-Agent": UA },
    body: JSON.stringify({ bbox: { min_lng: tile.min_lng, min_lat: tile.min_lat, max_lng: tile.max_lng, max_lat: tile.max_lat }, limit: tile.limit }),
    signal: AbortSignal.timeout(18000),
  });
  if (!res.ok) return [];
  const json = (await res.json()) as { data?: { activities?: RawActivity[] } };
  return Array.isArray(json?.data?.activities) ? json.data.activities : [];
}

function toFeature(raw: RawActivity): Feature | null {
  const title = String(raw.title || "").trim();
  const description = stripPii(String(raw.description || "").trim());
  const user = String(raw.user_name || "").trim();
  if (!isTeamSurvey({ user, title, description })) return null;
  const g = raw.geometry;
  const coords = g && Array.isArray(g.coordinates) ? g.coordinates : null;
  if (!coords || coords.length < 2) return null;
  const lng = Number(coords[0]);
  const lat = Number(coords[1]);
  if (!validCoord(lng, lat)) return null;
  const id = String(raw._id || `${lng},${lat}`).slice(0, 64);
  const photos = safePhotos(raw.medias);
  return {
    type: "Feature",
    id,
    geometry: { type: "Point", coordinates: [lng, lat] },
    properties: {
      activity_id: id,
      title: title.slice(0, 220) || "Titik survei",
      description: description.slice(0, 420),
      hashtag: `#${SURVEY_HASHTAG}`,
      category: surveyCategory(title, description),
      indication: surveyCongestionHint(title, description),
      latitude: Number(lat.toFixed(6)),
      longitude: Number(lng.toFixed(6)),
      photos: photos.length ? JSON.stringify(photos) : "",
      photo_count: photos.length,
      source: "MAPID Survey Activity",
    },
  };
}

async function loadLive(): Promise<Cache> {
  const settled = await Promise.allSettled(TILES.map((t) => fetchTile(t)));
  const okTiles = settled.filter((s) => s.status === "fulfilled").length;
  if (okTiles === 0) {
    return { at: Date.now(), fc: { type: "FeatureCollection", features: [] }, count: 0, ok: false, message: "Titik survei tidak dapat dimuat." };
  }
  const byId = new Map<string, Feature>();
  for (const s of settled) {
    if (s.status !== "fulfilled") continue;
    for (const raw of s.value) {
      const f = toFeature(raw);
      if (!f) continue;
      const id = String(f.id);
      if (!byId.has(id)) byId.set(id, f);
    }
  }
  const features = [...byId.values()].slice(0, 120);
  const message = features.length
    ? `${features.length} titik #${SURVEY_HASHTAG}`
    : "Tidak ada titik survei untuk hashtag tim.";
  return { at: Date.now(), fc: { type: "FeatureCollection", features }, count: features.length, ok: true, message };
}

export async function listSurveyActivities(opts?: { refresh?: boolean }) {
  if (!opts?.refresh && cache && Date.now() - cache.at < CACHE_MS) return cache;
  if (!opts?.refresh && inflight) return inflight;
  inflight = loadLive()
    .then((next) => {
      cache = next;
      return next;
    })
    .catch(() => {
      const failed: Cache = {
        at: Date.now(),
        fc: { type: "FeatureCollection", features: [] },
        count: 0,
        ok: false,
        message: "Titik survei tidak dapat dimuat.",
      };
      cache = failed;
      return failed;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}
