export const MAPID_STYLE_KEYS = ["basic", "street_2d", "satellite", "dark", "light"] as const;
export type MapidStyleKey = (typeof MAPID_STYLE_KEYS)[number];

export const MAPID_STYLE_IDS: Record<MapidStyleKey, string> = {
  basic: "basic",
  street_2d: "street-2d-building",
  satellite: "satellite",
  dark: "dark",
  light: "light",
};

export const MAPID_STYLE_LABELS: Record<MapidStyleKey, string> = {
  basic: "Basic",
  street_2d: "Street",
  satellite: "Satellite",
  dark: "Dark",
  light: "Light",
};

export const MAPID_HOST = "basemap.mapid.io";
export const MAPID_WORKER_URL = "/maplibre/maplibre-gl-worker.mjs";

export const EMPTY_MAP_STYLE = {
  version: 8 as const,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#101218" } }],
};

export function isMapidStyleKey(v: string): v is MapidStyleKey {
  return (MAPID_STYLE_KEYS as readonly string[]).includes(v);
}

export function styleProxyUrl(style: MapidStyleKey): string {
  return `/api/mapid/styles/${style}`;
}
