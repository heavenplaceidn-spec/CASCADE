import { klassOf, peakScore } from "./bottleneck";
import type { SimResult, SimSegment, SimVehicle, StatusKey } from "./store";
import { carLogicalPx, carriageCount, colorStep, iconSizeAtZoom } from "./vehicle-icons";

type ColorStep = ReturnType<typeof colorStep>;

function hav(a: [number, number], b: [number, number]) {
  const R = 6371000;
  const to = (d: number) => (d * Math.PI) / 180;
  const dlon = to(b[0] - a[0]);
  const dlat = to(b[1] - a[1]);
  const h = Math.sin(dlat / 2) ** 2 + Math.cos(to(a[1])) * Math.cos(to(b[1])) * Math.sin(dlon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function bearing(a: [number, number], b: [number, number]) {
  const to = (d: number) => (d * Math.PI) / 180;
  const y = Math.sin(to(b[0] - a[0])) * Math.cos(to(b[1]));
  const x = Math.cos(to(a[1])) * Math.sin(to(b[1])) - Math.sin(to(a[1])) * Math.cos(to(b[1])) * Math.cos(to(b[0] - a[0]));
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

/** Green fastest, yellow moderate, red slowest. Total still normalizes to ~20s. */
const CONGESTION_MUL: Record<"rendah" | "sedang" | "tinggi", number> = {
  rendah: 1,
  sedang: 0.7,
  tinggi: 0.4,
};

export const PLAYBACK_SEC = 20;

export type AnimSample = {
  d: number;
  lng: number;
  lat: number;
  bearing: number;
  bn: number;
  klass: "tinggi" | "sedang" | "rendah";
  step: ColorStep;
  mode: string;
  vehicle: SimVehicle;
  corridorId: string;
  kind: "ride" | "transfer";
  stop?: string;
};

export type AnimTrack = {
  samples: AnimSample[];
  totalM: number;
  duration: number;
  t: number[];
};

function densify(coords: [number, number][], maxStep = 28): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < coords.length; i++) {
    if (i === 0) {
      out.push(coords[i]);
      continue;
    }
    const a = coords[i - 1];
    const b = coords[i];
    const m = hav(a, b);
    const n = Math.max(1, Math.ceil(m / maxStep));
    for (let k = 1; k <= n; k++) {
      const u = k / n;
      out.push([a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]);
    }
  }
  return out;
}

function lerpSample(a: AnimSample, b: AnimSample, u: number, d: number): AnimSample {
  return {
    ...b,
    lng: a.lng + (b.lng - a.lng) * u,
    lat: a.lat + (b.lat - a.lat) * u,
    bearing: a.bearing + ((((b.bearing - a.bearing + 540) % 360) - 180) * u),
    bn: a.bn + (b.bn - a.bn) * u,
    step: colorStep(a.bn + (b.bn - a.bn) * u),
    d,
  };
}

function atIndex(arr: AnimSample[], tArr: number[], t: number): AnimSample {
  let lo = 0;
  let hi = arr.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (tArr[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  const i = Math.max(1, lo);
  const a = arr[i - 1];
  const b = arr[i];
  const span = tArr[i] - tArr[i - 1] || 1;
  const u = (t - tArr[i - 1]) / span;
  const d = a.d + (b.d - a.d) * u;
  return lerpSample(a, b, u, d);
}

export function buildAnimTrack(result: SimResult | null, fallback: [number, number][], status: StatusKey): AnimTrack | null {
  const segs: SimSegment[] =
    result?.segments && result.segments.length
      ? result.segments
      : fallback.length > 1
        ? [
            {
              corridorId: "",
              routeId: "",
              mode: "transjakarta",
              status,
              kind: "ride",
              coords: fallback,
              meters: 0,
              fromName: "",
              toName: "",
              vehicle: "bus",
              stops: [],
            },
          ]
        : [];
  if (!segs.length) return null;
  const samples: AnimSample[] = [];
  let d = 0;
  for (const seg of segs) {
    const coords = densify(seg.coords);
    if (coords.length < 2) continue;
    const stopAt = new Map<number, string>();
    for (const s of seg.stops || []) {
      let best = 0;
      let bd = Infinity;
      for (let i = 0; i < coords.length; i++) {
        const dd = hav(coords[i], s.coord);
        if (dd < bd) {
          bd = dd;
          best = i;
        }
      }
      if (bd < 220) stopAt.set(best, s.name);
    }
    for (let i = 0; i < coords.length; i++) {
      const a = coords[i];
      const b = coords[Math.min(i + 1, coords.length - 1)];
      const bn = peakScore(a[0], a[1], seg.status || status);
      const klass = klassOf(bn);
      const brg = i < coords.length - 1 ? bearing(a, b) : samples.length ? samples[samples.length - 1].bearing : 0;
      samples.push({
        d,
        lng: a[0],
        lat: a[1],
        bearing: brg,
        bn,
        klass,
        step: colorStep(bn),
        mode: seg.mode,
        vehicle: seg.vehicle || "bus",
        corridorId: seg.corridorId,
        kind: seg.kind,
        stop: stopAt.get(i),
      });
      if (i < coords.length - 1) d += hav(a, b);
    }
  }
  if (samples.length < 2) return null;

  let raw = 0;
  let stops = 0;
  let xf = 0;
  for (let i = 1; i < samples.length; i++) {
    const ds = samples[i].d - samples[i - 1].d;
    raw += ds / CONGESTION_MUL[samples[i - 1].klass];
    if (samples[i].stop) {
      if (samples[i].kind === "transfer") xf += 1;
      else stops += 1;
    }
  }
  const pauseShare = Math.min(0.1, 0.03 + stops * 0.002 + xf * 0.018);
  const pauseTotal = raw * pauseShare;
  const perStop = pauseTotal / (stops + xf * 2 || 1);
  let acc = 0;
  const t = [0];
  for (let i = 1; i < samples.length; i++) {
    const ds = samples[i].d - samples[i - 1].d;
    acc += ds / CONGESTION_MUL[samples[i - 1].klass];
    if (samples[i].stop) acc += samples[i].kind === "transfer" ? perStop * 2 : perStop;
    t.push(acc);
  }
  const end = t[t.length - 1] || 1;
  for (let i = 0; i < t.length; i++) t[i] = (t[i] / end) * PLAYBACK_SEC;

  return { samples, totalM: samples[samples.length - 1].d || 1, duration: PLAYBACK_SEC, t };
}

export function sampleAtTime(track: AnimTrack, sec: number): AnimSample {
  const t = Math.max(0, Math.min(track.duration, sec));
  return atIndex(track.samples, track.t, t);
}

export function sampleTrack(track: AnimTrack, meters: number): AnimSample {
  const arr = track.samples;
  const target = Math.max(0, Math.min(track.totalM, meters));
  let lo = 0;
  let hi = arr.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid].d < target) lo = mid + 1;
    else hi = mid;
  }
  const i = Math.max(1, lo);
  const a = arr[i - 1];
  const b = arr[i];
  const span = b.d - a.d || 1;
  return lerpSample(a, b, (target - a.d) / span, target);
}

export function metersPerPixel(zoom: number, lat: number) {
  return (156543.03392 * Math.cos((lat * Math.PI) / 180)) / 2 ** zoom;
}

export function consistGapM(track: AnimTrack, vehicle: string, zoom: number, lat: number) {
  const n = Math.max(1, carriageCount(vehicle) - 1);
  if (!n) return 0;
  const mpp = metersPerPixel(zoom, lat);
  const bodyPx = carLogicalPx(vehicle) * iconSizeAtZoom(zoom);
  return (bodyPx + 1.6) * mpp;
}

export function consistAtTime(track: AnimTrack, sec: number, zoom: number): AnimSample[] {
  const head = sampleAtTime(track, sec);
  const n = carriageCount(head.vehicle, head.kind);
  const gap = consistGapM(track, head.vehicle, zoom, head.lat);
  const out: AnimSample[] = [head];
  for (let i = 1; i < n; i++) {
    const behind = sampleTrack(track, head.d - i * gap);
    out.push({
      ...behind,
      vehicle: head.vehicle,
      mode: head.mode,
      corridorId: head.corridorId,
      kind: head.kind,
      bn: head.bn,
      step: head.step,
    });
  }
  return out;
}

/** Point-to-polyline distance in meters — QA that the vehicle stays on GeoJSON. */
export function distToPolylineM(lng: number, lat: number, line: [number, number][]) {
  let best = Infinity;
  for (let i = 1; i < line.length; i++) {
    const a = line[i - 1];
    const b = line[i];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const len2 = dx * dx + dy * dy || 1e-12;
    let u = ((lng - a[0]) * dx + (lat - a[1]) * dy) / len2;
    u = Math.max(0, Math.min(1, u));
    const p: [number, number] = [a[0] + dx * u, a[1] + dy * u];
    const d = hav([lng, lat], p);
    if (d < best) best = d;
  }
  return best;
}
