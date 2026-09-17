import type { Map as MapLibreMap } from "maplibre-gl";
import type { SimVehicle } from "./store";

/** 1.5× original sprite scale. Canvas 128 / pixelRatio 2 = 64 logical px. */
export const VEHICLE_SCALE = 1.5;
export const VEHICLE_ICON_SIZE = ["interpolate", ["linear"], ["zoom"], 8, 0.72, 9, 0.78, 11, 0.88, 13, 1.02, 15, 1.14] as const;

export function iconSizeAtZoom(z: number) {
  const stops = [
    [8, 0.72],
    [9, 0.78],
    [11, 0.88],
    [13, 1.02],
    [15, 1.14],
  ] as const;
  if (z <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (z <= stops[i][0]) {
      const [z0, s0] = stops[i - 1];
      const [z1, s1] = stops[i];
      return s0 + ((z - z0) / (z1 - z0)) * (s1 - s0);
    }
  }
  return stops[stops.length - 1][1];
}

/** Logical px of the colored body along the travel axis at icon-size 1. */
export function carLogicalPx(vehicle: string) {
  if (vehicle === "krl") return 23;
  if (vehicle === "mrt") return 24;
  if (vehicle === "lrt") return 21;
  return 20;
}

export type VehiclePart = "bus" | "krl-front" | "krl-car" | "lrt-front" | "lrt-car" | "mrt-front" | "mrt-car" | "xfer";

export function carriageCount(vehicle: string, kind?: string) {
  if (kind === "transfer") return 1;
  if (vehicle === "krl" || vehicle === "mrt" || vehicle === "lrt") return 3;
  return 1;
}

export function vehiclePart(vehicle: string, index: number, kind?: string): VehiclePart {
  if (kind === "transfer") return "xfer";
  if (vehicle === "krl") return index === 0 ? "krl-front" : "krl-car";
  if (vehicle === "lrt") return index === 0 ? "lrt-front" : "lrt-car";
  if (vehicle === "mrt") return index === 0 ? "mrt-front" : "mrt-car";
  return "bus";
}

export const ICON_VER = "v5";
export function vehicleBodyId(part: string) {
  return `veh-${ICON_VER}-body-${part}`;
}
export function vehicleChromeId(part: string) {
  return `veh-${ICON_VER}-chrome-${part}`;
}

const GREEN: [number, number, number] = [22, 163, 74];
const YELLOW: [number, number, number] = [234, 179, 8];
const RED: [number, number, number] = [220, 38, 38];

function mix(a: [number, number, number], b: [number, number, number], u: number): [number, number, number] {
  const t = Math.max(0, Math.min(1, u));
  return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)];
}

export function bnToHex(bn: number): string {
  const t = Math.max(0, Math.min(1, bn));
  const [r, g, b] = t < 0.5 ? mix(GREEN, YELLOW, t / 0.5) : mix(YELLOW, RED, (t - 0.5) / 0.5);
  return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

export function colorStep(bn: number): "rendah" | "lime" | "sedang" | "oranye" | "tinggi" {
  if (bn >= 0.74) return "tinggi";
  if (bn >= 0.62) return "oranye";
  if (bn >= 0.5) return "sedang";
  if (bn >= 0.4) return "lime";
  return "rendah";
}

type Kind = "bus" | "krl" | "lrt" | "mrt";
const SPEC: Record<Kind, { hw: number; len: number; depth: number }> = {
  bus: { hw: 22, len: 40, depth: 12 },
  krl: { hw: 16, len: 46, depth: 9 },
  lrt: { hw: 11, len: 42, depth: 7 },
  mrt: { hw: 14, len: 48, depth: 8 },
};

function hull(ctx: CanvasRenderingContext2D, kind: Kind, nose: "cab" | "car") {
  const { hw, len, depth } = SPEC[kind];
  const y0 = -len / 2;
  const y1 = len / 2;
  const dx = depth;
  const dy = depth * 0.42;
  ctx.beginPath();
  if (kind === "bus") {
    ctx.moveTo(-hw + 8, y0);
    ctx.quadraticCurveTo(0, y0 - 6, hw - 8, y0);
    ctx.lineTo(hw, y0 + 10);
    ctx.lineTo(hw + dx, y0 + 10 + dy);
    ctx.lineTo(hw + dx, y1 + dy);
    ctx.lineTo(-hw + 4, y1);
    ctx.quadraticCurveTo(-hw, y1 - 6, -hw, y1 - 14);
    ctx.lineTo(-hw, y0 + 12);
    ctx.closePath();
  } else if (kind === "krl" && nose === "cab") {
    ctx.moveTo(-hw + 2, y0 + 8);
    ctx.lineTo(-hw + 6, y0 + 1);
    ctx.lineTo(hw - 6, y0 + 1);
    ctx.lineTo(hw + 2, y0 + 8);
    ctx.lineTo(hw + dx, y0 + 8 + dy);
    ctx.lineTo(hw + dx, y1 + dy);
    ctx.lineTo(-hw, y1);
    ctx.lineTo(-hw, y0 + 8);
    ctx.closePath();
  } else if (kind === "lrt" && nose === "cab") {
    ctx.moveTo(0, y0 - 4);
    ctx.quadraticCurveTo(hw - 2, y0 + 6, hw, y0 + 16);
    ctx.lineTo(hw + dx, y0 + 16 + dy);
    ctx.lineTo(hw + dx, y1 + dy);
    ctx.lineTo(-hw + 2, y1);
    ctx.lineTo(-hw, y0 + 16);
    ctx.quadraticCurveTo(-hw + 2, y0 + 6, 0, y0 - 4);
    ctx.closePath();
  } else if (kind === "mrt" && nose === "cab") {
    ctx.moveTo(0, y0 - 8);
    ctx.quadraticCurveTo(hw, y0 + 2, hw, y0 + 18);
    ctx.lineTo(hw + dx, y0 + 18 + dy);
    ctx.lineTo(hw + dx, y1 + dy - 4);
    ctx.quadraticCurveTo(hw + dx * 0.4, y1 + dy + 2, -hw + 4, y1);
    ctx.lineTo(-hw, y0 + 18);
    ctx.quadraticCurveTo(-hw, y0 + 2, 0, y0 - 8);
    ctx.closePath();
  } else {
    ctx.moveTo(-hw, y0 + 3);
    ctx.lineTo(hw, y0 + 3);
    ctx.lineTo(hw + dx, y0 + 3 + dy);
    ctx.lineTo(hw + dx, y1 + dy - 3);
    ctx.lineTo(-hw, y1 - 3);
    ctx.closePath();
  }
}

function windows(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, n: number, gap: number) {
  const inner = w - gap * (n + 1);
  const ww = Math.max(2, inner / n);
  ctx.fillStyle = "rgba(248,250,252,0.95)";
  for (let i = 0; i < n; i++) {
    const xx = x + gap + i * (ww + gap);
    ctx.fillRect(xx, y, ww, h);
  }
}

function sideShade(ctx: CanvasRenderingContext2D, kind: Kind, nose: "cab" | "car") {
  const { hw, len, depth } = SPEC[kind];
  const y0 = -len / 2;
  const y1 = len / 2;
  const dx = depth;
  const dy = depth * 0.42;
  ctx.fillStyle = "rgba(15,23,42,0.32)";
  ctx.beginPath();
  ctx.moveTo(hw - 1, nose === "cab" && kind !== "krl" ? y0 + 12 : y0 + 4);
  ctx.lineTo(hw + dx, nose === "cab" && kind !== "krl" ? y0 + 12 + dy : y0 + 4 + dy);
  ctx.lineTo(hw + dx, y1 + dy - 2);
  ctx.lineTo(hw - 1, y1 - 2);
  ctx.closePath();
  ctx.fill();
}

function wheels(ctx: CanvasRenderingContext2D, kind: Kind) {
  const { hw, len, depth } = SPEC[kind];
  const y0 = -len / 2 + (kind === "bus" ? 12 : 14);
  const y1 = len / 2 - 12;
  ctx.fillStyle = "#0f172a";
  for (const y of [y0, y1]) {
    ctx.beginPath();
    ctx.ellipse(-hw + 2, y, kind === "bus" ? 5 : 3.6, kind === "bus" ? 5 : 3.6, 0, 0, Math.PI * 2);
    ctx.ellipse(hw + depth * 0.15, y + depth * 0.2, kind === "bus" ? 5 : 3.6, kind === "bus" ? 5 : 3.6, 0, 0, Math.PI * 2);
    ctx.fill();
  }
}

function chromeBus(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.bus;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.6;
  hull(ctx, "bus", "cab");
  ctx.stroke();
  sideShade(ctx, "bus", "cab");
  ctx.fillStyle = "rgba(248,250,252,0.96)";
  ctx.beginPath();
  ctx.moveTo(-hw + 7, -len / 2 + 2);
  ctx.quadraticCurveTo(0, -len / 2 - 3, hw - 9, -len / 2 + 2);
  ctx.lineTo(hw - 6, -len / 2 + 12);
  ctx.lineTo(-hw + 6, -len / 2 + 12);
  ctx.closePath();
  ctx.fill();
  windows(ctx, -hw + 4, -4, hw * 2 - 10, 7, 3, 3);
  ctx.fillStyle = "#fde68a";
  ctx.beginPath();
  ctx.arc(-11, -len / 2 + 6, 2.6, 0, Math.PI * 2);
  ctx.arc(9, -len / 2 + 6, 2.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-10, len / 2 - 6, 20, 4);
  wheels(ctx, "bus");
}

function chromeKrlFront(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.krl;
  const y0 = -len / 2;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.6;
  hull(ctx, "krl", "cab");
  ctx.stroke();
  sideShade(ctx, "krl", "cab");
  ctx.fillStyle = "rgba(248,250,252,0.95)";
  ctx.fillRect(-hw + 4, y0 + 8, hw * 2 - 10, 9);
  windows(ctx, -hw + 3, y0 + 22, hw * 2 - 8, 7, 3, 2);
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(-6, y0 + 4);
  ctx.lineTo(-6, y0 - 8);
  ctx.lineTo(6, y0 - 8);
  ctx.lineTo(6, y0 + 4);
  ctx.moveTo(-10, y0 - 8);
  ctx.lineTo(10, y0 - 8);
  ctx.stroke();
  ctx.fillStyle = "#fde68a";
  ctx.fillRect(-hw + 5, y0 + 6, 4, 3);
  ctx.fillRect(hw - 10, y0 + 6, 4, 3);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-4, len / 2 - 2, 8, 5);
  wheels(ctx, "krl");
}

function chromeKrlCar(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.krl;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.6;
  hull(ctx, "krl", "car");
  ctx.stroke();
  sideShade(ctx, "krl", "car");
  windows(ctx, -hw + 3, -len / 2 + 8, hw * 2 - 8, 8, 4, 2);
  windows(ctx, -hw + 3, 4, hw * 2 - 8, 8, 4, 2);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-4, -len / 2 - 1, 8, 5);
  ctx.fillRect(-4, len / 2 - 4, 8, 5);
  wheels(ctx, "krl");
}

function chromeLrtFront(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.lrt;
  const y0 = -len / 2;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.4;
  hull(ctx, "lrt", "cab");
  ctx.stroke();
  sideShade(ctx, "lrt", "cab");
  ctx.fillStyle = "rgba(248,250,252,0.96)";
  ctx.beginPath();
  ctx.moveTo(0, y0 + 2);
  ctx.lineTo(hw - 4, y0 + 16);
  ctx.lineTo(-hw + 4, y0 + 16);
  ctx.closePath();
  ctx.fill();
  windows(ctx, -hw + 2, y0 + 20, hw * 2 - 6, 8, 2, 2);
  ctx.fillStyle = "#fde68a";
  ctx.beginPath();
  ctx.arc(-5, y0 + 10, 1.8, 0, Math.PI * 2);
  ctx.arc(5, y0 + 10, 1.8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-3, len / 2 - 2, 6, 4);
  wheels(ctx, "lrt");
}

function chromeLrtCar(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.lrt;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.4;
  hull(ctx, "lrt", "car");
  ctx.stroke();
  sideShade(ctx, "lrt", "car");
  windows(ctx, -hw + 2, -len / 2 + 8, hw * 2 - 6, 9, 2, 2);
  windows(ctx, -hw + 2, 4, hw * 2 - 6, 9, 2, 2);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-3, -len / 2, 6, 4);
  ctx.fillRect(-3, len / 2 - 4, 6, 4);
  wheels(ctx, "lrt");
}

function chromeMrtFront(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.mrt;
  const y0 = -len / 2;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.5;
  hull(ctx, "mrt", "cab");
  ctx.stroke();
  sideShade(ctx, "mrt", "cab");
  ctx.fillStyle = "rgba(248,250,252,0.95)";
  ctx.beginPath();
  ctx.ellipse(0, y0 + 10, hw - 5, 8, 0, Math.PI, 0);
  ctx.fill();
  windows(ctx, -hw + 3, y0 + 22, hw * 2 - 8, 6, 2, 3);
  ctx.fillStyle = "#fde68a";
  ctx.beginPath();
  ctx.arc(-6, y0 + 8, 2, 0, Math.PI * 2);
  ctx.arc(6, y0 + 8, 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-3, len / 2 - 3, 6, 4);
  wheels(ctx, "mrt");
}

function chromeMrtCar(ctx: CanvasRenderingContext2D) {
  const { hw, len } = SPEC.mrt;
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.5;
  hull(ctx, "mrt", "car");
  ctx.stroke();
  sideShade(ctx, "mrt", "car");
  windows(ctx, -hw + 3, -len / 2 + 8, hw * 2 - 8, 7, 3, 2);
  windows(ctx, -hw + 3, 5, hw * 2 - 8, 7, 3, 2);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(-3, -len / 2 + 1, 6, 4);
  ctx.fillRect(-3, len / 2 - 5, 6, 4);
  wheels(ctx, "mrt");
}

function chromeXfer(ctx: CanvasRenderingContext2D) {
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2.6;
  ctx.beginPath();
  ctx.arc(0, 0, 13, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "#0f172a";
  ctx.beginPath();
  ctx.moveTo(-7, -4);
  ctx.lineTo(1, -4);
  ctx.lineTo(1, -8);
  ctx.lineTo(10, 0);
  ctx.lineTo(1, 8);
  ctx.lineTo(1, 4);
  ctx.lineTo(-7, 4);
  ctx.closePath();
  ctx.fill();
}

function paint(ctx: CanvasRenderingContext2D, s: number, part: VehiclePart, layer: "sdf" | "chrome") {
  ctx.clearRect(0, 0, s, s);
  ctx.save();
  ctx.translate(s / 2, s / 2);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  if (layer === "sdf") {
    ctx.fillStyle = "#ffffff";
    if (part === "bus") hull(ctx, "bus", "cab");
    else if (part === "krl-front") hull(ctx, "krl", "cab");
    else if (part === "krl-car") hull(ctx, "krl", "car");
    else if (part === "lrt-front") hull(ctx, "lrt", "cab");
    else if (part === "lrt-car") hull(ctx, "lrt", "car");
    else if (part === "mrt-front") hull(ctx, "mrt", "cab");
    else if (part === "mrt-car") hull(ctx, "mrt", "car");
    else {
      ctx.beginPath();
      ctx.arc(0, 0, 13, 0, Math.PI * 2);
    }
    ctx.fill();
  } else if (part === "bus") chromeBus(ctx);
  else if (part === "krl-front") chromeKrlFront(ctx);
  else if (part === "krl-car") chromeKrlCar(ctx);
  else if (part === "lrt-front") chromeLrtFront(ctx);
  else if (part === "lrt-car") chromeLrtCar(ctx);
  else if (part === "mrt-front") chromeMrtFront(ctx);
  else if (part === "mrt-car") chromeMrtCar(ctx);
  else chromeXfer(ctx);
  ctx.restore();
}

function makeImage(part: VehiclePart, layer: "sdf" | "chrome", size = 128): ImageData {
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const ctx = c.getContext("2d");
  if (!ctx) return new ImageData(size, size);
  paint(ctx, size, part, layer);
  return ctx.getImageData(0, 0, size, size);
}

const PARTS: VehiclePart[] = ["bus", "krl-front", "krl-car", "lrt-front", "lrt-car", "mrt-front", "mrt-car", "xfer"];

export function ensureVehicleIcons(map: MapLibreMap) {
  for (const part of PARTS) {
    const body = vehicleBodyId(part);
    const chrome = vehicleChromeId(part);
    if (!map.hasImage(body)) {
      try {
        map.addImage(body, makeImage(part, "sdf"), { pixelRatio: 2, sdf: true });
      } catch {
        /* style not ready */
      }
    }
    if (!map.hasImage(chrome)) {
      try {
        map.addImage(chrome, makeImage(part, "chrome"), { pixelRatio: 2 });
      } catch {
        /* style not ready */
      }
    }
  }
}

function fillAndChrome(ctx: CanvasRenderingContext2D, part: VehiclePart, fill: string) {
  ctx.fillStyle = fill;
  if (part === "bus") hull(ctx, "bus", "cab");
  else if (part === "krl-front") hull(ctx, "krl", "cab");
  else if (part === "krl-car") hull(ctx, "krl", "car");
  else if (part === "lrt-front") hull(ctx, "lrt", "cab");
  else if (part === "lrt-car") hull(ctx, "lrt", "car");
  else if (part === "mrt-front") hull(ctx, "mrt", "cab");
  else if (part === "mrt-car") hull(ctx, "mrt", "car");
  else {
    ctx.beginPath();
    ctx.arc(0, 0, 13, 0, Math.PI * 2);
  }
  ctx.fill();
  if (part === "bus") chromeBus(ctx);
  else if (part === "krl-front") chromeKrlFront(ctx);
  else if (part === "krl-car") chromeKrlCar(ctx);
  else if (part === "lrt-front") chromeLrtFront(ctx);
  else if (part === "lrt-car") chromeLrtCar(ctx);
  else if (part === "mrt-front") chromeMrtFront(ctx);
  else if (part === "mrt-car") chromeMrtCar(ctx);
  else chromeXfer(ctx);
}

const legendCache = new Map<string, string>();

/** Static consist thumbnail from the same hull/chrome sprites as the map animation. */
export function legendConsistUrl(vehicle: "bus" | "krl" | "lrt" | "mrt", fill: string): string {
  const key = `${ICON_VER}:${vehicle}:${fill}`;
  const hit = legendCache.get(key);
  if (hit) return hit;
  if (typeof document === "undefined") return "";
  const n = carriageCount(vehicle);
  const size = 128;
  const kind: Kind = vehicle;
  const pitch = SPEC[kind].len + (vehicle === "bus" ? 6 : 14);
  const w = size + Math.max(0, n - 1) * pitch;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = size;
  const ctx = c.getContext("2d");
  if (!ctx) return "";
  for (let i = 0; i < n; i++) {
    const part = vehiclePart(vehicle, i);
    ctx.save();
    ctx.translate(size / 2 + i * pitch, size / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    fillAndChrome(ctx, part, fill);
    ctx.restore();
  }
  const url = c.toDataURL("image/png");
  legendCache.set(key, url);
  return url;
}

export type { SimVehicle };

