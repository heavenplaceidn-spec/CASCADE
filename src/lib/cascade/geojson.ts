export type Geometry =
  | { type: "Point"; coordinates: [number, number] }
  | { type: "LineString"; coordinates: [number, number][] }
  | { type: "MultiLineString"; coordinates: [number, number][][] }
  | { type: "Polygon"; coordinates: [number, number][][] };

export type Feature = {
  type: "Feature";
  id?: string | number;
  geometry: Geometry;
  properties: Record<string, string | number | boolean | null | undefined>;
};

export type FeatureCollection = { type: "FeatureCollection"; features: Feature[] };

export function emptyFC(): FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

export function featureBbox(f: Feature): [number, number, number, number] | null {
  const pts: [number, number][] = [];
  const g = f.geometry;
  if (g.type === "Point") pts.push(g.coordinates);
  else if (g.type === "LineString") pts.push(...g.coordinates);
  else if (g.type === "MultiLineString") g.coordinates.forEach((c) => pts.push(...c));
  else if (g.type === "Polygon") g.coordinates.forEach((c) => pts.push(...c));
  if (!pts.length) return null;
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}
