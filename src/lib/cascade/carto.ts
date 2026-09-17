export const MODE_COLOR = {
  krl: "#DC2626",
  mrt: "#247A67",
  lrt: "#4FAF86",
  transjakarta: "#5865C7",
} as const;

export const COLOR = {
  road: "#94a3b8",
  masterplan: "#E58A3A",
  cascade: "#7C3AED",
  selected: "#7C3AED",
  survey: "#111827",
  existing: "#C9A227",
  tj: "#5865C7",
  krl: "#DC2626",
  lrt: "#4FAF86",
  mrt: "#247A67",
  bnHigh: "#DC2626",
  bnMid: "#EAB308",
  bnLow: "#16A34A",
};

export const STATION_MINZOOM = 12;
export const STATION_LABEL_MINZOOM = 14;

/** Mode color from feature.mode — visual only, not a second geometry. */
export const MODE_COLOR_EXPR = [
  "match",
  ["slice", ["downcase", ["to-string", ["coalesce", ["get", "mode"], ""]]], 0, 3],
  "krl",
  COLOR.krl,
  "mrt",
  COLOR.mrt,
  "lrt",
  COLOR.lrt,
  "tra",
  COLOR.tj,
  "tj",
  COLOR.tj,
  COLOR.tj,
] as unknown as import("maplibre-gl").ExpressionSpecification;

export const DUAL_WIDTH = ["interpolate", ["linear"], ["zoom"], 9, 2.05, 12, 2.85, 15, 3.9] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_L = ["interpolate", ["linear"], ["zoom"], 9, -1.05, 12, -1.45, 15, -1.95] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_R = ["interpolate", ["linear"], ["zoom"], 9, 1.05, 12, 1.45, 15, 1.95] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_WIDTH_EXISTING = ["interpolate", ["linear"], ["zoom"], 9, 2.2, 12, 3.1, 15, 4.2] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_EXISTING_L = ["interpolate", ["linear"], ["zoom"], 9, -1.1, 12, -1.55, 15, -2.1] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_EXISTING_R = ["interpolate", ["linear"], ["zoom"], 9, 1.1, 12, 1.55, 15, 2.1] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_WIDTH_MP = ["interpolate", ["linear"], ["zoom"], 9, 1.8, 12, 2.5, 15, 3.3] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_MP_L = ["interpolate", ["linear"], ["zoom"], 9, -0.9, 12, -1.25, 15, -1.65] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DUAL_OFFSET_MP_R = ["interpolate", ["linear"], ["zoom"], 9, 0.9, 12, 1.25, 15, 1.65] as unknown as import("maplibre-gl").ExpressionSpecification;
export const DASH_CASCADE: [number, number] = [2.2, 1.5];
export const DASH_MASTERPLAN: [number, number] = [4.2, 2.6];
