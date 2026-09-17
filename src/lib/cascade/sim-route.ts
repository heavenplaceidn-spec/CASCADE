import { emptyFC, type Feature, type FeatureCollection } from "./geojson";
import { peakScore, spatialGradient } from "./bottleneck";
import { routeViaGraph } from "./graph";
import type { SimNode, SimResult, StatusKey } from "./store";

export { networkBottleneck } from "./bottleneck";
export { spatialGradient };

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

export async function buildSimPath(origin: SimNode, dest: SimNode, status: StatusKey): Promise<{ fc: FeatureCollection; result: SimResult }> {
  return routeViaGraph(origin, dest, status);
}

export function pathCoords(fc: FeatureCollection | null): [number, number][] {
  const f = fc?.features.find((x) => x.geometry.type === "LineString" || x.geometry.type === "MultiLineString");
  return f ? lineCoords(f) : [];
}

export function particlesAlong(coords: [number, number][], t: number, n: number, status: StatusKey): FeatureCollection {
  if (coords.length < 2) return emptyFC();
  const time: number[] = [0];
  for (let i = 1; i < coords.length; i++) {
    const d = hav(coords[i - 1], coords[i]);
    const bn = peakScore(coords[i][0], coords[i][1], status);
    const slow = bn >= 0.7 ? 2.6 : bn >= 0.48 ? 1.5 : 1;
    time.push(time[i - 1] + d * slow);
  }
  const totalT = time[time.length - 1] || 1;
  const feats: Feature[] = [];
  const count = Math.max(4, Math.min(18, n));
  for (let k = 0; k < count; k++) {
    const u = (t + k / count) % 1;
    const target = u * totalT;
    let i = 1;
    while (i < time.length && time[i] < target) i++;
    const a = coords[i - 1];
    const b = coords[Math.min(i, coords.length - 1)];
    const span = time[Math.min(i, time.length - 1)] - time[i - 1] || 1;
    const f = (target - time[i - 1]) / span;
    const lng = a[0] + (b[0] - a[0]) * f;
    const lat = a[1] + (b[1] - a[1]) * f;
    feats.push({
      type: "Feature",
      id: `p${k}`,
      properties: { id: `p${k}`, bn: Number(peakScore(lng, lat, status).toFixed(3)) },
      geometry: { type: "Point", coordinates: [lng, lat] },
    });
  }
  return { type: "FeatureCollection", features: feats };
}

export function pathBbox(coords: [number, number][]): [number, number, number, number] | null {
  if (coords.length < 2) return null;
  const xs = coords.map((c) => c[0]);
  const ys = coords.map((c) => c[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}
