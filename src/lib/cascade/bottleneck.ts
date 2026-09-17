import type { StatusKey } from "./store";

export type Hotspot = {
  name: string;
  lng: number;
  lat: number;
  rKm: number;
  peak: number;
  cascadeRelief: number;
};

/** Titik tekanan dari karakter kawasan, hirarki jalan, dan tekanan transit jam puncak. Bukan real-time. */
export const HOTSPOTS: Hotspot[] = [
  { name: "Sawangan", lng: 106.764, lat: -6.4, rKm: 2.6, peak: 0.86, cascadeRelief: 0.2 },
  { name: "Ciputat", lng: 106.747, lat: -6.317, rKm: 2.2, peak: 0.88, cascadeRelief: 0.2 },
  { name: "Pondok Cabe", lng: 106.759, lat: -6.351, rKm: 1.8, peak: 0.72, cascadeRelief: 0.12 },
  { name: "Depok", lng: 106.822, lat: -6.395, rKm: 2.2, peak: 0.64, cascadeRelief: 0.1 },
  { name: "Jelambar", lng: 106.786, lat: -6.166, rKm: 1.9, peak: 0.87, cascadeRelief: 0.04 },
  { name: "Central Park", lng: 106.79, lat: -6.177, rKm: 1.6, peak: 0.85, cascadeRelief: 0.05 },
  { name: "Tomang", lng: 106.798, lat: -6.178, rKm: 1.4, peak: 0.8, cascadeRelief: 0.05 },
  { name: "Grogol", lng: 106.789, lat: -6.166, rKm: 1.4, peak: 0.8, cascadeRelief: 0.05 },
  { name: "Petojo", lng: 106.816, lat: -6.168, rKm: 1.2, peak: 0.6, cascadeRelief: 0.08 },
  { name: "Condet", lng: 106.863, lat: -6.283, rKm: 1.9, peak: 0.84, cascadeRelief: 0.08 },
  { name: "PGC", lng: 106.87, lat: -6.262, rKm: 1.6, peak: 0.8, cascadeRelief: 0.1 },
  { name: "Kampung Melayu", lng: 106.866, lat: -6.225, rKm: 1.4, peak: 0.78, cascadeRelief: 0.1 },
  { name: "Matraman", lng: 106.861, lat: -6.204, rKm: 1.4, peak: 0.66, cascadeRelief: 0.1 },
  { name: "Senen", lng: 106.843, lat: -6.176, rKm: 1.6, peak: 0.8, cascadeRelief: 0.08 },
  { name: "Gunung Sahari", lng: 106.833, lat: -6.155, rKm: 1.3, peak: 0.4, cascadeRelief: 0.04 },
  { name: "Manggarai", lng: 106.85, lat: -6.21, rKm: 1.5, peak: 0.76, cascadeRelief: 0.06 },
  { name: "Fatmawati", lng: 106.795, lat: -6.289, rKm: 1.5, peak: 0.7, cascadeRelief: 0.1 },
  { name: "Lebak Bulus", lng: 106.775, lat: -6.289, rKm: 1.6, peak: 0.72, cascadeRelief: 0.12 },
  { name: "Kuningan", lng: 106.83, lat: -6.238, rKm: 1.5, peak: 0.72, cascadeRelief: 0.08 },
  { name: "Cibubur", lng: 106.882, lat: -6.37, rKm: 1.8, peak: 0.68, cascadeRelief: 0.1 },
  { name: "BSD", lng: 106.65, lat: -6.301, rKm: 2.2, peak: 0.7, cascadeRelief: 0.16 },
  { name: "Cawang", lng: 106.87, lat: -6.243, rKm: 1.5, peak: 0.76, cascadeRelief: 0.07 },
  { name: "Tangerang Kota", lng: 106.631, lat: -6.177, rKm: 1.8, peak: 0.74, cascadeRelief: 0.14 },
  { name: "Mauk", lng: 106.523, lat: -6.066, rKm: 2.0, peak: 0.62, cascadeRelief: 0.18 },
  { name: "Curug", lng: 106.566, lat: -6.239, rKm: 1.8, peak: 0.66, cascadeRelief: 0.16 },
  { name: "Dramaga", lng: 106.729, lat: -6.557, rKm: 2.0, peak: 0.7, cascadeRelief: 0.16 },
  { name: "Leuwiliang", lng: 106.632, lat: -6.567, rKm: 1.8, peak: 0.6, cascadeRelief: 0.18 },
  { name: "Jasinga", lng: 106.452, lat: -6.455, rKm: 1.8, peak: 0.58, cascadeRelief: 0.2 },
];

type Axis = { pts: [number, number][]; widthKm: number; peak: number; cascadeRelief: number };

/** Koridor komuter jam puncak: kepadatan aktivitas + hirarki jalan + tekanan radial. */
const AXES: Axis[] = [
  {
    pts: [
      [106.764, -6.4],
      [106.76, -6.351],
      [106.747, -6.317],
      [106.775, -6.289],
    ],
    widthKm: 3.4,
    peak: 0.84,
    cascadeRelief: 0.2,
  },
  {
    pts: [
      [106.778, -6.158],
      [106.786, -6.166],
      [106.79, -6.177],
      [106.798, -6.178],
    ],
    widthKm: 2.2,
    peak: 0.84,
    cascadeRelief: 0.05,
  },
  {
    pts: [
      [106.863, -6.283],
      [106.87, -6.262],
      [106.87, -6.243],
      [106.866, -6.225],
      [106.85, -6.21],
    ],
    widthKm: 2.3,
    peak: 0.8,
    cascadeRelief: 0.08,
  },
];

const CALM = [
  { lng: 106.833, lat: -6.128, rKm: 2.4, floor: 0.36 },
  { lng: 106.84, lat: -6.1, rKm: 3.2, floor: 0.34 },
];

export const BN_COLOR = { high: "#DC2626", mid: "#EAB308", low: "#16A34A" } as const;

function distKm(lng: number, lat: number, x: number, y: number) {
  const to = (d: number) => (d * Math.PI) / 180;
  const dlon = to(x - lng);
  const dlat = to(y - lat);
  const a = Math.sin(dlat / 2) ** 2 + Math.cos(to(lat)) * Math.cos(to(y)) * Math.sin(dlon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}

function distToSeg(lng: number, lat: number, a: [number, number], b: [number, number]) {
  const vx = b[0] - a[0];
  const vy = b[1] - a[1];
  const len2 = vx * vx + vy * vy || 1e-12;
  let t = ((lng - a[0]) * vx + (lat - a[1]) * vy) / len2;
  t = Math.max(0, Math.min(1, t));
  return distKm(lng, lat, a[0] + t * vx, a[1] + t * vy);
}

function distToAxis(lng: number, lat: number, pts: [number, number][]) {
  let best = Infinity;
  for (let i = 1; i < pts.length; i++) best = Math.min(best, distToSeg(lng, lat, pts[i - 1], pts[i]));
  return best;
}

function reliefFactor(status: StatusKey) {
  if (status === "cascade") return 1;
  if (status === "masterplan") return 0.4;
  return 0;
}

function arterialFloor(lng: number, lat: number) {
  if (lng < 106.48 || lng > 107.12 || lat > -6.02 || lat < -6.52) return 0.38;
  return 0.5;
}

export function peakScore(lng: number, lat: number, status: StatusKey) {
  const rel = reliefFactor(status);
  let score = arterialFloor(lng, lat);
  for (const ax of AXES) {
    const d = distToAxis(lng, lat, ax.pts);
    if (d > ax.widthKm * 1.8) continue;
    const w = Math.exp(-0.5 * (d / (ax.widthKm * 0.55)) ** 2);
    const raw = Math.max(0.4, ax.peak - ax.cascadeRelief * rel);
    score = Math.max(score, 0.48 + (raw - 0.48) * w);
  }
  for (const h of HOTSPOTS) {
    const d = distKm(lng, lat, h.lng, h.lat);
    if (d > h.rKm * 2.3) continue;
    const w = Math.exp(-0.5 * (d / (h.rKm * 0.6)) ** 2);
    const raw = Math.max(0.4, h.peak - h.cascadeRelief * rel);
    score = Math.max(score, 0.48 + (raw - 0.48) * w);
  }
  for (const c of CALM) {
    const d = distKm(lng, lat, c.lng, c.lat);
    if (d < c.rKm) {
      const w = Math.exp(-0.5 * (d / (c.rKm * 0.7)) ** 2);
      score = score * (1 - 0.42 * w) + c.floor * 0.42 * w;
    }
  }
  return Math.min(0.94, Math.max(0.32, score));
}

export function klassOf(score: number): "tinggi" | "sedang" | "rendah" {
  if (score >= 0.7) return "tinggi";
  if (score >= 0.48) return "sedang";
  return "rendah";
}

export function colorFromScore(score: number) {
  const k = klassOf(score);
  return k === "tinggi" ? BN_COLOR.high : k === "sedang" ? BN_COLOR.mid : BN_COLOR.low;
}

export function hotspotsAlong(coords: [number, number][], status: StatusKey) {
  const hits: { name: string; score: number; klass: "tinggi" | "sedang" | "rendah" }[] = [];
  for (const h of HOTSPOTS) {
    let near = false;
    for (let i = 0; i < coords.length; i += 4) {
      if (distKm(coords[i][0], coords[i][1], h.lng, h.lat) < h.rKm) {
        near = true;
        break;
      }
    }
    if (!near) continue;
    const score = peakScore(h.lng, h.lat, status);
    hits.push({ name: h.name, score: Number(score.toFixed(2)), klass: klassOf(score) });
  }
  return hits;
}

export function spatialGradient(coords: [number, number][], status: StatusKey) {
  if (coords.length < 2) return ["interpolate", ["linear"], ["line-progress"], 0, BN_COLOR.mid, 1, BN_COLOR.mid];
  const n = Math.min(28, Math.max(8, Math.floor(coords.length / 16)));
  const stops: (number | string)[] = [];
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const idx = Math.min(coords.length - 1, Math.round(u * (coords.length - 1)));
    stops.push(Number(u.toFixed(3)), colorFromScore(peakScore(coords[idx][0], coords[idx][1], status)));
  }
  return ["interpolate", ["linear"], ["line-progress"], ...stops];
}

export function meanScore(coords: [number, number][], status: StatusKey) {
  if (!coords.length) return 0;
  let s = 0;
  let n = 0;
  for (let i = 0; i < coords.length; i += 8) {
    s += peakScore(coords[i][0], coords[i][1], status);
    n++;
  }
  return n ? s / n : 0;
}

export function networkBottleneck(status: StatusKey) {
  const before = HOTSPOTS.reduce((a, h) => a + peakScore(h.lng, h.lat, "existing"), 0) / HOTSPOTS.length;
  const after = HOTSPOTS.reduce((a, h) => a + peakScore(h.lng, h.lat, status), 0) / HOTSPOTS.length;
  return {
    before: Number(before.toFixed(2)),
    after: Number(after.toFixed(2)),
    flowChange: Number((before - after).toFixed(2)),
  };
}

export function hotspotsInBbox(b: [number, number, number, number], status: StatusKey) {
  return HOTSPOTS.filter((h) => h.lng >= b[0] && h.lng <= b[2] && h.lat >= b[1] && h.lat <= b[3]).map((h) => {
    const score = peakScore(h.lng, h.lat, status);
    return { name: h.name, score: Number(score.toFixed(2)), klass: klassOf(score) };
  });
}
