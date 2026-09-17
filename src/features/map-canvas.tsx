import { useEffect, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Download } from "lucide-react";
import type { FilterSpecification, GeoJSONSource, Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  COLOR,
  DASH_CASCADE,
  DASH_MASTERPLAN,
  DUAL_OFFSET_EXISTING_L,
  DUAL_OFFSET_EXISTING_R,
  DUAL_OFFSET_L,
  DUAL_OFFSET_MP_L,
  DUAL_OFFSET_MP_R,
  DUAL_OFFSET_R,
  DUAL_WIDTH,
  DUAL_WIDTH_EXISTING,
  DUAL_WIDTH_MP,
  MODE_COLOR_EXPR,
  STATION_LABEL_MINZOOM,
  STATION_MINZOOM,
} from "@/lib/cascade/carto";
import { HOTSPOTS, klassOf, peakScore } from "@/lib/cascade/bottleneck";
import { MAP_CENTER, MAP_ZOOM } from "@/lib/cascade/crs";
import { emptyFC, type Feature, type FeatureCollection } from "@/lib/cascade/geojson";
import { MAPID_WORKER_URL, styleProxyUrl } from "@/lib/cascade/mapid";
import { PROP_COLOR, filterPropertyFeatures, propertyPopupRows } from "@/lib/cascade/property";
import { parsePhotoList, surveyPopupRows, SURVEY_COLOR } from "@/lib/cascade/survey";
import { googleMapsUrl } from "@/lib/cascade/research";
import { bboxPolygon } from "@/lib/cascade/sdss";
import { pathCoords, spatialGradient } from "@/lib/cascade/sim-route";
import { buildAnimTrack, consistAtTime, type AnimTrack } from "@/lib/cascade/anim";
import { bnToHex, ensureVehicleIcons, VEHICLE_ICON_SIZE, vehicleBodyId, vehicleChromeId, vehiclePart } from "@/lib/cascade/vehicle-icons";
import { warmTransitGraph, auditTransitNetwork } from "@/lib/cascade/graph";
import {
  enabledModes,
  useCascade,
  type CasFilter,
  type GroupState,
  type KrlFilter,
  type LrtFilter,
  type MpConf,
  type MpMode,
  type MpStatus,
  type MrtFilter,
  type PropFilters,
  type SimNode,
  type StatusKey,
  type TjFilter,
  type Visibility,
} from "@/lib/cascade/store";
import { OVERLAY_URL } from "@/lib/cascade/static-data";
import { downloadFeatureGeoJSON } from "@/lib/cascade/geojson-download";
import { MapLegend } from "./map-legend";

const HIT = [
  "cascade-stop",
  "candidate",
  "candidate-casing",
  "candidate-mode",
  "krl-existing-stop",
  "tj-existing-stop",
  "lrt-existing-stop",
  "mrt-existing-stop",
  "masterplan-stop",
  "krl-existing-line",
  "krl-existing-mode",
  "tj-existing-line",
  "tj-existing-mode",
  "lrt-existing-line",
  "lrt-existing-mode",
  "mrt-existing-line",
  "mrt-existing-mode",
  "masterplan-line-solid",
  "masterplan-line-solid-mode",
  "masterplan-line-dash",
  "masterplan-line-dash-mode",
  "masterplan-line-ref",
  "masterplan-line-ref-mode",
  "property-point",
  "property-cluster",
  "survey-point",
];
const STOP_IDS = ["tj-existing-stop", "krl-existing-stop", "lrt-existing-stop", "mrt-existing-stop", "masterplan-stop", "cascade-stop"];
const LABEL_IDS = ["tj-existing-label", "krl-existing-label", "lrt-existing-label", "mrt-existing-label", "masterplan-label", "cascade-label"];
const animCursor = { key: "", elapsed: 0, displayBn: 0.35 };

function setData(map: MapLibreMap, id: string, fc: FeatureCollection | string) {
  const src = map.getSource(id) as GeoJSONSource | undefined;
  if (src) src.setData(fc as never);
}

const OVERLAYS: { source: string; url: string; phase: string; on: (v: Visibility) => boolean }[] = [
  { source: "candidate", url: OVERLAY_URL.candidate, phase: "cascade", on: (v) => v.candidate },
  { source: "cascade-stops", url: OVERLAY_URL["cascade-stops"], phase: "cascade", on: (v) => v.candidate },
  { source: "krl", url: OVERLAY_URL.krl, phase: "routes", on: (v) => v.krl },
  { source: "tj", url: OVERLAY_URL.tj, phase: "routes", on: (v) => v.transjakarta },
  { source: "lrt", url: OVERLAY_URL.lrt, phase: "routes", on: (v) => v.lrt },
  { source: "mrt", url: OVERLAY_URL.mrt, phase: "routes", on: (v) => v.mrt },
  { source: "krl-stops", url: OVERLAY_URL["krl-stops"], phase: "stops", on: (v) => v.krl },
  { source: "tj-stops", url: OVERLAY_URL["tj-stops"], phase: "stops", on: (v) => v.transjakarta && v.stops },
  { source: "lrt-stops", url: OVERLAY_URL["lrt-stops"], phase: "stops", on: (v) => v.lrt },
  { source: "mrt-stops", url: OVERLAY_URL["mrt-stops"], phase: "stops", on: (v) => v.mrt },
  { source: "masterplan", url: OVERLAY_URL.masterplan, phase: "heavy", on: (v) => v.masterplan },
  { source: "masterplan-stops", url: OVERLAY_URL["masterplan-stops"], phase: "heavy", on: (v) => v.masterplan },
  { source: "roads", url: OVERLAY_URL.roads, phase: "heavy", on: (v) => v.roads },
  { source: "property-zones", url: OVERLAY_URL["property-zones"], phase: "heavy", on: (v) => v.property },
  { source: "property", url: OVERLAY_URL.property, phase: "heavy", on: (v) => v.property },
];

function overlayWant(o: (typeof OVERLAYS)[number], vis: Visibility) {
  return o.on(vis) ? o.url : "";
}
function applyOverlays(map: MapLibreMap, vis: Visibility, applied: Record<string, string>) {
  for (const o of OVERLAYS) {
    if (o.source === "property") continue;
    const src = map.getSource(o.source) as GeoJSONSource | undefined;
    if (!src) continue;
    const want = overlayWant(o, vis);
    if (applied[o.source] === want) continue;
    src.setData((want ? want : emptyFC()) as never);
    applied[o.source] = want;
  }
}
function findSelectedFeature(map: MapLibreMap, selectedId: string): Feature | null {
  const sources = ["candidate", "krl", "tj", "lrt", "mrt", "masterplan", "cascade-stops", "krl-stops", "tj-stops", "lrt-stops", "mrt-stops", "masterplan-stops"];
  for (const src of sources) {
    if (!map.getSource(src)) continue;
    try {
      const feats = map.querySourceFeatures(src);
      const hit = feats.find((f) => String(f.id ?? f.properties?.id) === selectedId);
      const g = hit?.geometry;
      if (hit && g && (g.type === "LineString" || g.type === "MultiLineString" || g.type === "Point")) {
        return { type: "Feature", id: selectedId, properties: (hit.properties ?? {}) as Feature["properties"], geometry: g as Feature["geometry"] };
      }
    } catch {
      /* source belum siap */
    }
  }
  return null;
}
function applyLayerFilter(map: MapLibreMap, ids: string[], expr: FilterSpecification | null) {
  for (const id of ids) if (map.getLayer(id)) map.setFilter(id, expr);
}
function tjFilterExpr(filter: TjFilter): FilterSpecification | null {
  if (filter === "all") return null;
  return [">=", ["index-of", `,${filter},`, ["get", "corridor_nos"]], 0];
}
function applyTjFilter(map: MapLibreMap, filter: TjFilter) {
  applyLayerFilter(map, ["tj-existing-line", "tj-existing-mode", "tj-existing-stop", "tj-existing-label"], tjFilterExpr(filter));
}
function krlLineFilter(filter: KrlFilter): FilterSpecification {
  if (filter === "all") return ["==", ["get", "id"], "krl-network"];
  return ["all", ["!=", ["get", "id"], "krl-network"], [">=", ["index-of", `,${filter},`, ["get", "line_codes"]], 0]];
}
function krlStopFilter(filter: KrlFilter): FilterSpecification | null {
  if (filter === "all") return null;
  return [">=", ["index-of", `,${filter},`, ["get", "line_codes"]], 0];
}
function applyKrlFilter(map: MapLibreMap, filter: KrlFilter) {
  applyLayerFilter(map, ["krl-existing-line", "krl-existing-mode"], krlLineFilter(filter));
  applyLayerFilter(map, ["krl-existing-stop", "krl-existing-label"], krlStopFilter(filter));
}
function lrtLineFilter(filter: LrtFilter): FilterSpecification {
  if (filter === "all") return ["==", ["get", "id"], "lrt-network"];
  return ["==", ["get", "id"], filter === "CB" ? "lrt-CB" : "lrt-BK"];
}
function applyLrtFilter(map: MapLibreMap, filter: LrtFilter) {
  applyLayerFilter(map, ["lrt-existing-line", "lrt-existing-mode"], lrtLineFilter(filter));
  applyLayerFilter(map, ["lrt-existing-stop", "lrt-existing-label"], filter === "all" ? null : [">=", ["index-of", `,${filter},`, ["get", "line_codes"]], 0]);
}
function applyMrtFilter(map: MapLibreMap, _filter: MrtFilter) {
  applyLayerFilter(map, ["mrt-existing-line", "mrt-existing-mode"], ["==", ["get", "id"], "mrt-NS"]);
  applyLayerFilter(map, ["mrt-existing-stop", "mrt-existing-label"], null);
}
function andFilters(...parts: (FilterSpecification | null)[]): FilterSpecification | null {
  const ok = parts.filter((p): p is FilterSpecification => p != null);
  if (!ok.length) return null;
  if (ok.length === 1) return ok[0];
  return ["all", ...ok] as FilterSpecification;
}
function cascadeModeExpr(g: GroupState): FilterSpecification | null {
  const modes = enabledModes(g);
  if (!modes.length) return ["==", ["get", "mode"], "__none__"];
  if (modes.length === 4) return null;
  return ["in", ["get", "mode"], ["literal", modes]];
}
function masterplanModeExpr(g: GroupState): FilterSpecification | null {
  const modes = enabledModes(g);
  if (!modes.length) return ["==", ["get", "id"], "__none__"];
  if (modes.length === 4) return null;
  const parts: FilterSpecification[] = [];
  if (g.mrt) parts.push([">=", ["index-of", ",mrt,", ["get", "mode_filter"]], 0]);
  if (g.lrt) parts.push([">=", ["index-of", ",lrt,", ["get", "mode_filter"]], 0]);
  if (g.krl) parts.push(["any", [">=", ["index-of", ",krl,", ["get", "mode_filter"]], 0], [">=", ["index-of", ",rail,", ["get", "mode_filter"]], 0]]);
  if (g.transjakarta) parts.push([">=", ["index-of", ",transjakarta,", ["get", "mode_filter"]], 0]);
  if (!parts.length) return ["==", ["get", "id"], "__none__"];
  if (parts.length === 1) return parts[0];
  return ["any", ...parts] as FilterSpecification;
}
function casFilterExpr(filter: CasFilter): FilterSpecification | null {
  if (!filter || filter === "all") return null;
  if (filter === "lrt" || filter === "mrt" || filter === "krl") return ["==", ["get", "mode"], filter];
  if (filter === "brt" || filter === "transjakarta") return ["==", ["get", "mode"], "transjakarta"];
  return ["==", ["get", "route_id"], filter];
}
function applyCasFilter(map: MapLibreMap, filter: CasFilter) {
  const g = useCascade.getState().groups.cascade;
  const expr = andFilters(cascadeModeExpr(g), casFilterExpr(filter));
  applyLayerFilter(map, ["candidate", "candidate-casing", "candidate-mode", "cascade-stop", "cascade-label"], expr);
}
function mpFilterExpr(mode: MpMode, status: MpStatus, conf: MpConf): FilterSpecification | null {
  const parts: FilterSpecification[] = [];
  if (mode === "rail") parts.push(["any", [">=", ["index-of", ",krl,", ["get", "mode_filter"]], 0], [">=", ["index-of", ",rail,", ["get", "mode_filter"]], 0]]);
  else if (mode !== "all") parts.push([">=", ["index-of", `,${mode},`, ["get", "mode_filter"]], 0]);
  if (status !== "all") parts.push([">=", ["index-of", `,${status},`, ["get", "status_filter"]], 0]);
  if (conf !== "all") parts.push([">=", ["index-of", `,${conf},`, ["get", "conf_filter"]], 0]);
  if (!parts.length) return null;
  if (parts.length === 1) return parts[0];
  return ["all", ...parts] as FilterSpecification;
}
function applyMpFilter(map: MapLibreMap, mode: MpMode, status: MpStatus, conf: MpConf) {
  const g = useCascade.getState().groups.masterplan;
  const expr = andFilters(mpFilterExpr(mode, status, conf), masterplanModeExpr(g));
  const pairs: { id: string; base: FilterSpecification | null }[] = [
    { id: "masterplan-line-solid", base: ["==", ["get", "status"], "CONSTRUCTION"] },
    { id: "masterplan-line-solid-mode", base: ["==", ["get", "status"], "CONSTRUCTION"] },
    { id: "masterplan-line-dash", base: ["in", ["get", "status"], ["literal", ["PLANNED", "MASTERPLAN", "FS"]]] },
    { id: "masterplan-line-dash-mode", base: ["in", ["get", "status"], ["literal", ["PLANNED", "MASTERPLAN", "FS"]]] },
    { id: "masterplan-line-ref", base: ["in", ["get", "status"], ["literal", ["UNDER_STUDY", "REFERENCE"]]] },
    { id: "masterplan-line-ref-mode", base: ["in", ["get", "status"], ["literal", ["UNDER_STUDY", "REFERENCE"]]] },
    { id: "masterplan-stop", base: null },
    { id: "masterplan-label", base: null },
  ];
  for (const { id, base } of pairs) {
    if (!map.getLayer(id)) continue;
    if (base && expr) map.setFilter(id, ["all", base, expr] as FilterSpecification);
    else if (base) map.setFilter(id, base);
    else map.setFilter(id, expr);
  }
}

function modeLabel(mode?: string) {
  const m = String(mode || "");
  if (m === "krl") return "KRL";
  if (m === "mrt") return "MRT";
  if (m === "lrt") return "LRT";
  if (m === "rail") return "Rel / outer ring";
  if (m === "transjakarta") return "TransJakarta";
  return m;
}
function structureLabel(s: unknown) {
  const v = String(s || "");
  if (v === "UNDERGROUND") return "Bawah tanah";
  if (v === "ELEVATED") return "Layang";
  if (v === "AT_GRADE") return "Permukaan";
  if (v === "UNDER_REVIEW" || v === "NOT_SPECIFIED" || v === "MIXED") return "Belum ditetapkan";
  return v;
}
function popupRows(props: Record<string, unknown>, layer: string) {
  const key = layer.replace(/-mode$/, "-line");
  const rows: { label: string; value: string }[] = [];
  const add = (label: string, value: unknown) => {
    const v = value == null ? "" : String(value).trim();
    if (!v || v === "—" || v === "null" || v === "undefined") return;
    rows.push({ label, value: v });
  };
  if (key === "tj-existing-stop") {
    add("Koridor", props.koridor_label ? `TransJakarta Koridor ${props.koridor_label}` : props.corridor_id);
    add("Status", props.status_label || "Jaringan saat ini");
    add("Halte sebelumnya", props.prev_stop);
    add("Halte berikutnya", props.next_stop);
    add("Tipe", props.tipe);
    add("Kawasan", [props.kecamatan, props.kota].filter(Boolean).join(", "));
    add("Sumber", props.source);
  } else if (key === "tj-existing-line") {
    add("Nomor", props.corridor_no);
    add("Endpoint", props.endpoint);
    add("Status", props.status_label || "Jaringan saat ini");
    add("Panjang", props.length_km != null ? `${props.length_km} km` : "");
    add("Jumlah halte", props.stop_count);
    add("Sumber", props.source);
  } else if (key === "krl-existing-stop") {
    add("Kode stasiun", props.station_code || props.stop_code);
    add("Lintasan", props.line_name);
    add("Status", props.status_label || "Jaringan saat ini");
    add("Sumber", props.source);
  } else if (key === "krl-existing-line") {
    add("Kode", props.line_code && props.line_code !== "ALL" ? props.line_code : "");
    add("Terminus", props.endpoint || props.terminus);
    add("Status", props.status_label || "Jaringan saat ini");
    add("Jumlah stasiun", props.stop_count);
    add("Panjang", props.length_km != null ? `${props.length_km} km` : "");
    add("Sumber", props.source);
  } else if (key === "lrt-existing-stop" || key === "mrt-existing-stop") {
    add("Kode", props.station_code || props.stop_code);
    add("Lintasan", props.line_name || (key.startsWith("mrt") ? "MRT North-South Line" : props.line));
    add("Status", props.status_label || "Jaringan saat ini");
    add("Sumber", props.source);
  } else if (key === "lrt-existing-line" || key === "mrt-existing-line") {
    add("Lintasan", props.short && props.short !== "Semua" ? props.short : props.name);
    add("Terminus", props.endpoint);
    add("Status", props.status_label || "Jaringan saat ini");
    add("Jumlah stasiun", props.stop_count);
    add("Panjang", props.length_km != null ? `${props.length_km} km` : "");
    add("Sumber", props.source);
  } else if (key === "masterplan-stop") {
    add("Koridor", props.corridor_name);
    add("Moda", modeLabel(String(props.mode || "")));
    add("Status", props.status_label || "Masterplan");
    add("Interchange", props.is_interchange === "ya" ? `Ya · ${props.connected_corridors || ""}` : "");
    add("Sumber", props.source);
  } else if (key.startsWith("masterplan-line")) {
    add("Moda", modeLabel(String(props.mode || "")));
    add("Koridor", props.short || props.route_name);
    add("Status", props.status_label || "Masterplan / acuan");
    add("Struktur", structureLabel(props.structure));
    add("Sumber", props.source);
    add("Keterangan", String(props.disclaimer || "Geometri hasil digitasi dokumen perencanaan. Bukan gambar DED."));
  } else if (key === "cascade-stop") {
    add("Koridor", props.route_id ? `${props.route_id} ${props.route_name || ""}` : props.route_name);
    add("Urutan", props.stop_order);
    add("Status", props.status_label || "Halte usulan");
    add("Sumber", props.source);
    add("Keterangan", String(props.note || "Halte usulan CASCADE. Bukan halte resmi."));
  } else if (key === "candidate" || key === "candidate-casing" || key === "candidate-line") {
    add("Koridor", props.route_id);
    add("Dari", props.from_name);
    add("Ke", props.to_name);
    add("Panjang", props.length_km != null ? `${props.length_km} km` : "");
    add("Jumlah halte", props.stop_count);
    add("Status", props.status_label || "Usulan CASCADE");
    add("Sumber", props.source);
    add("Keterangan", String(props.disclaimer || "Usulan CASCADE. Bukan rute resmi. Bukan DED."));
  } else {
    add("Moda", props.mode ?? layer);
    add("Koridor", props.corridor_id || props.koridor_label);
    add("Status", props.status_label || "Saat ini");
    add("Sumber", props.source);
  }
  return rows;
}
function mapFont(map: MapLibreMap): string[] {
  const layers = map.getStyle()?.layers ?? [];
  for (const l of layers) {
    const layout = (l as { layout?: Record<string, unknown> }).layout;
    const f = layout?.["text-font"];
    if (Array.isArray(f) && f.length) return f as string[];
  }
  return ["Open Sans Regular", "Arial Unicode MS Regular"];
}
function addStopCircle(map: MapLibreMap, id: string, source: string, color: string, minzoom: number) {
  if (map.getLayer(id)) return;
  map.addLayer({
    id,
    type: "circle",
    source,
    minzoom,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], minzoom, 3.4, 15, 6.2],
      "circle-color": color,
      "circle-stroke-width": 1,
      "circle-stroke-color": "#0a0c10",
      "circle-opacity": 0.95,
    },
  });
}
function addStopLabel(map: MapLibreMap, id: string, source: string, minzoom: number) {
  if (map.getLayer(id)) return;
  try {
    map.addLayer({
      id,
      type: "symbol",
      source,
      minzoom,
      layout: { "text-field": ["get", "name"], "text-size": 11, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true, "text-font": mapFont(map) },
      paint: { "text-color": "#1e1b2e", "text-halo-color": "#ffffff", "text-halo-width": 1.2 },
    });
  } catch {
    /* font missing */
  }
}
function sdfIcon(draw: (ctx: CanvasRenderingContext2D, s: number) => void, fill: string, size = 64) {
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const ctx = c.getContext("2d");
  if (!ctx) return new ImageData(size, size);
  ctx.clearRect(0, 0, size, size);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.strokeStyle = "#0a0c10";
  ctx.lineWidth = 6;
  ctx.fillStyle = fill;
  draw(ctx, size);
  ctx.fill();
  ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
}
function tanahPath(ctx: CanvasRenderingContext2D, s: number) {
  const p = s * 0.16;
  ctx.beginPath();
  ctx.rect(p, p, s - 2 * p, s - 2 * p);
}
function rukoPath(ctx: CanvasRenderingContext2D, s: number) {
  ctx.beginPath();
  ctx.moveTo(s * 0.5, s * 0.1);
  ctx.lineTo(s * 0.88, s * 0.42);
  ctx.lineTo(s * 0.88, s * 0.88);
  ctx.lineTo(s * 0.12, s * 0.88);
  ctx.lineTo(s * 0.12, s * 0.42);
  ctx.closePath();
}
function aptPath(ctx: CanvasRenderingContext2D, s: number) {
  ctx.beginPath();
  ctx.rect(s * 0.1, s * 0.3, s * 0.22, s * 0.58);
  ctx.rect(s * 0.36, s * 0.1, s * 0.28, s * 0.78);
  ctx.rect(s * 0.68, s * 0.38, s * 0.22, s * 0.5);
}
function ensurePropIcons(map: MapLibreMap) {
  if (map.hasImage("prop-tanah-MURAH")) return;
  const fills = { MURAH: PROP_COLOR.MURAH, SEDANG: PROP_COLOR.SEDANG, MAHAL: PROP_COLOR.MAHAL };
  for (const [cls, fill] of Object.entries(fills)) {
    map.addImage(`prop-tanah-${cls}`, sdfIcon(tanahPath, fill), { pixelRatio: 2 });
    map.addImage(`prop-ruko-${cls}`, sdfIcon(rukoPath, fill), { pixelRatio: 2 });
    map.addImage(`prop-apt-${cls}`, sdfIcon(aptPath, fill), { pixelRatio: 2 });
  }
}
let propertyCache: FeatureCollection | null = null;
function loadPropertyCache() {
  if (propertyCache) return Promise.resolve(propertyCache);
  return fetch(OVERLAY_URL.property, { cache: "force-cache" })
    .then((r) => r.json())
    .then((fc: FeatureCollection) => {
      propertyCache = fc;
      return fc;
    });
}
function applyPropertyOverlay(map: MapLibreMap, vis: Visibility, filters: PropFilters) {
  const src = map.getSource("property") as GeoJSONSource | undefined;
  if (!src) return;
  for (const id of ["property-zones", "property-zones-outline", "property-cluster", "property-cluster-count", "property-point"]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis.property ? "visible" : "none");
  }
  if (!vis.property) {
    src.setData(emptyFC() as never);
    return;
  }
  void loadPropertyCache().then((fc) => {
    if (!map.getSource("property")) return;
    const live = useCascade.getState();
    if (!live.visibility.property) return;
    src.setData({ type: "FeatureCollection", features: filterPropertyFeatures(fc.features, live.propFilters) } as never);
    applyZoneFilter(map, live.propFilters);
  });
  applyZoneFilter(map, filters);
}
let surveyCache: FeatureCollection | null = null;
let surveyLoad: Promise<FeatureCollection> | null = null;
function loadSurveyCache(refresh = false) {
  if (refresh) {
    surveyCache = null;
    surveyLoad = null;
  }
  if (!refresh && surveyCache) return Promise.resolve(surveyCache);
  if (!refresh && surveyLoad) return surveyLoad;
  surveyLoad = fetch(refresh ? "/api/survey-activities?refresh=1" : "/api/survey-activities")
    .then((r) => r.json())
    .then((body: { type?: string; features?: FeatureCollection["features"] }) => {
      const fc: FeatureCollection = { type: "FeatureCollection", features: Array.isArray(body.features) ? body.features : [] };
      surveyCache = fc;
      return fc;
    })
    .catch(() => ({ type: "FeatureCollection", features: [] }) as FeatureCollection)
    .finally(() => {
      surveyLoad = null;
    });
  return surveyLoad;
}
function applySurveyOverlay(map: MapLibreMap, vis: Visibility, refresh = false) {
  const src = map.getSource("survey") as GeoJSONSource | undefined;
  if (!src) return;
  if (map.getLayer("survey-point")) map.setLayoutProperty("survey-point", "visibility", vis.survey ? "visible" : "none");
  if (!vis.survey) {
    src.setData(emptyFC() as never);
    return;
  }
  void loadSurveyCache(refresh).then((fc) => {
    if (!map.getSource("survey")) return;
    if (!useCascade.getState().visibility.survey) return;
    src.setData(fc as never);
  });
}
function applyZoneFilter(map: MapLibreMap, f: PropFilters) {
  if (!map.getLayer("property-zones")) return;
  const cls: string[] = [];
  if (f.murah) cls.push("MURAH");
  if (f.sedang) cls.push("SEDANG");
  if (f.mahal) cls.push("MAHAL");
  const expr = ["any", ["==", ["get", "status"], "INSUFFICIENT DATA"], ["in", ["get", "price_class"], ["literal", cls.length ? cls : ["__none__"]]]] as never;
  map.setFilter("property-zones", expr);
  if (map.getLayer("property-zones-outline")) map.setFilter("property-zones-outline", expr);
}
function layerStatus(layer: string): StatusKey {
  if (layer.startsWith("masterplan")) return "masterplan";
  if (layer === "cascade-stop" || layer === "candidate" || layer === "candidate-casing" || layer === "candidate-mode") return "cascade";
  return "existing";
}
function inferMode(layer: string, props: Record<string, unknown>) {
  if (props.mode) return String(props.mode);
  if (layer.startsWith("krl")) return "krl";
  if (layer.startsWith("mrt")) return "mrt";
  if (layer.startsWith("lrt")) return "lrt";
  if (layer.startsWith("tj")) return "transjakarta";
  return "";
}
function isStopLayer(layer: string) {
  return layer.includes("-stop") || layer === "cascade-stop" || layer === "masterplan-stop";
}
function simNodeFrom(f: { id?: unknown; properties?: Record<string, unknown> | null; geometry?: { type?: string; coordinates?: unknown } }, layer: string, fallback: [number, number]): SimNode {
  const props = f.properties ?? {};
  const g = f.geometry;
  const coord = g && g.type === "Point" ? (g.coordinates as [number, number]) : fallback;
  const order = props.stop_order;
  const route = String(props.route_id || props.corridor_id || "");
  return {
    id: f.id && String(f.id) !== String(props.id || "") ? String(f.id) : order != null && route ? `${route}-S${order}` : String(props.name || props.id || f.id || ""),
    name: String(props.name || props.stop_name || props.route_name || "Stasiun"),
    coord,
    status: layerStatus(layer),
    mode: inferMode(layer, props),
    corridorId: String(props.corridor_id || props.route_id || props.line_code || ""),
    routeId: String(props.route_id || props.corridor_id || ""),
  };
}
function transportTabs(props: Record<string, unknown>, layer: string, native: { label: string; value: string }[]) {
  const status = layerStatus(layer);
  const tabs = {
    existing: status === "existing" ? native : [{ label: "Status", value: "Bukan jaringan yang sedang beroperasi." }],
    masterplan: status === "masterplan" ? native : [{ label: "Status", value: "Bukan koridor masterplan resmi." }],
    cascade: status === "cascade" ? native : [{ label: "Status", value: "Bukan usulan koridor CASCADE." }],
  };
  if (status === "cascade") {
    const extra: { label: string; value: string }[] = [];
    if (props.existing === "YES") extra.push({ label: "Simpul existing", value: "Menumpang simpul existing." });
    if (props.nearest_transit) extra.push({ label: "Transit terdekat", value: String(props.nearest_transit) });
    if (extra.length) {
      extra.push({ label: "Keterangan", value: "Relasi spasial, bukan status operasi." });
      tabs.existing = extra;
    }
  }
  return tabs;
}
function mountPropertyLayers(map: MapLibreMap) {
  if (!map.getSource("property-zones")) map.addSource("property-zones", { type: "geojson", data: emptyFC() as never, maxzoom: 12, buffer: 0, tolerance: 0.5 });
  if (!map.getSource("property")) {
    map.addSource("property", {
      type: "geojson",
      data: emptyFC() as never,
      cluster: true,
      clusterMaxZoom: 13,
      clusterRadius: 52,
      clusterMinPoints: 2,
      clusterProperties: {
        mahal: ["+", ["case", ["==", ["get", "price_class"], "MAHAL"], 1, 0]],
        sedang: ["+", ["case", ["==", ["get", "price_class"], "SEDANG"], 1, 0]],
        murah: ["+", ["case", ["==", ["get", "price_class"], "MURAH"], 1, 0]],
      },
      promoteId: "property_id",
      maxzoom: 14,
    });
  }
  ensurePropIcons(map);
  if (!map.getLayer("property-zones")) {
    map.addLayer({
      id: "property-zones",
      type: "fill",
      source: "property-zones",
      minzoom: 9,
      maxzoom: 14,
      paint: {
        "fill-color": ["case", ["==", ["get", "status"], "INSUFFICIENT DATA"], "#6e6980", ["match", ["get", "price_class"], "MURAH", PROP_COLOR.MURAH, "SEDANG", PROP_COLOR.SEDANG, PROP_COLOR.MAHAL]],
        "fill-opacity": ["case", ["==", ["get", "status"], "INSUFFICIENT DATA"], 0.08, 0.2],
      },
    });
    map.addLayer({
      id: "property-zones-outline",
      type: "line",
      source: "property-zones",
      minzoom: 9,
      maxzoom: 14,
      paint: {
        "line-color": ["case", ["==", ["get", "status"], "INSUFFICIENT DATA"], "#6e6980", ["match", ["get", "price_class"], "MURAH", PROP_COLOR.MURAH, "SEDANG", PROP_COLOR.SEDANG, PROP_COLOR.MAHAL]],
        "line-width": 0.6,
        "line-opacity": 0.35,
      },
    });
  }
  if (!map.getLayer("property-cluster")) {
    map.addLayer({
      id: "property-cluster",
      type: "circle",
      source: "property",
      filter: ["has", "point_count"],
      paint: {
        "circle-color": ["case", [">", ["get", "mahal"], ["get", "sedang"]], ["case", [">", ["get", "mahal"], ["get", "murah"]], PROP_COLOR.MAHAL, PROP_COLOR.MURAH], ["case", [">", ["get", "sedang"], ["get", "murah"]], PROP_COLOR.SEDANG, PROP_COLOR.MURAH]],
        "circle-radius": ["interpolate", ["linear"], ["get", "point_count"], 2, 9, 8, 14, 20, 20, 60, 28],
        "circle-opacity": 0.9,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#f8fafc",
      },
    });
  }
  if (!map.getLayer("property-cluster-count")) {
    try {
      map.addLayer({
        id: "property-cluster-count",
        type: "symbol",
        source: "property",
        filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 11, "text-font": mapFont(map), "text-allow-overlap": true },
        paint: { "text-color": "#f8fafc", "text-halo-color": "#0a0c10", "text-halo-width": 0.8 },
      });
    } catch {
      /* font */
    }
  }
  if (!map.getLayer("property-point")) {
    map.addLayer({
      id: "property-point",
      type: "circle",
      source: "property",
      filter: ["!", ["has", "point_count"]],
      minzoom: 13,
      paint: {
        "circle-radius": 5.2,
        "circle-color": ["match", ["get", "price_class"], "MURAH", PROP_COLOR.MURAH, "SEDANG", PROP_COLOR.SEDANG, PROP_COLOR.MAHAL],
        "circle-opacity": 0.92,
        "circle-stroke-width": 1,
        "circle-stroke-color": "#0a0c10",
      },
    });
  }
}

function mountSurveyLayers(map: MapLibreMap) {
  if (!map.getSource("survey")) {
    map.addSource("survey", { type: "geojson", data: emptyFC() as never, promoteId: "activity_id", maxzoom: 14 });
  }
  if (!map.getLayer("survey-point")) {
    map.addLayer({
      id: "survey-point",
      type: "circle",
      source: "survey",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 4, 12, 5.5, 15, 7],
        "circle-color": SURVEY_COLOR,
        "circle-opacity": 0.94,
        "circle-stroke-width": 1.4,
        "circle-stroke-color": "#f8fafc",
      },
    });
  }
}

function simRouteHasMetrics(map: MapLibreMap) {
  const src = map.getSource("sim-route") as { serialize?: () => { lineMetrics?: boolean } } | undefined;
  try {
    return !!src?.serialize?.().lineMetrics;
  } catch {
    return false;
  }
}

const CONGESTION_WIDTH = ["interpolate", ["linear"], ["zoom"], 9, 7, 12, 10, 15, 14];
const CONGESTION_CASING_WIDTH = ["interpolate", ["linear"], ["zoom"], 9, 10, 12, 13, 15, 18];

function congestionLineFc(simPath: FeatureCollection | null): FeatureCollection {
  if (!simPath) return emptyFC();
  return {
    type: "FeatureCollection",
    features: simPath.features.filter((f) => f.geometry.type === "LineString" || f.geometry.type === "MultiLineString"),
  };
}

function paintSimCongestion(map: MapLibreMap, simPath: FeatureCollection | null, status: StatusKey) {
  if (!map.getSource("sim-route")) return;
  const lineFc = congestionLineFc(simPath);
  setData(map, "sim-route", lineFc);
  const coords = pathCoords(simPath);
  const gradient = coords.length > 1 ? spatialGradient(coords, status) : null;
  try {
    if (map.getLayer("sim-congestion-casing")) {
      map.setLayoutProperty("sim-congestion-casing", "visibility", "visible");
      map.setPaintProperty("sim-congestion-casing", "line-opacity", coords.length > 1 ? 0.55 : 0);
    }
    if (map.getLayer("sim-route")) {
      map.setLayoutProperty("sim-route", "visibility", "visible");
      map.setPaintProperty("sim-route", "line-opacity", coords.length > 1 ? 0.92 : 0);
      map.setPaintProperty("sim-route", "line-width", CONGESTION_WIDTH as never);
      if (gradient) map.setPaintProperty("sim-route", "line-gradient", gradient as never);
    }
  } catch {
    /* style settling */
  }
  const colors: string[] = [];
  if (Array.isArray(gradient)) {
    for (let i = 4; i < gradient.length; i += 2) colors.push(String(gradient[i]).toUpperCase());
  }
  const uniq = [...new Set(colors)];
  (window as unknown as { __CASCADE_CONGESTION?: unknown }).__CASCADE_CONGESTION = {
    visible: true,
    features: lineFc.features.length,
    coords: coords.length,
    opacity: coords.length > 1 ? 0.92 : 0,
    red: colors.filter((c) => c === "#DC2626").length,
    yellow: colors.filter((c) => c === "#EAB308").length,
    green: colors.filter((c) => c === "#16A34A").length,
    unique: uniq,
    status,
  };
}

function mountSimLayers(map: MapLibreMap) {
  if (map.getSource("sim-route") && !simRouteHasMetrics(map)) {
    for (const id of ["sim-congestion-casing", "sim-route"]) if (map.getLayer(id)) map.removeLayer(id);
    map.removeSource("sim-route");
  }
  if (!map.getSource("sim-route")) map.addSource("sim-route", { type: "geojson", data: emptyFC() as never, lineMetrics: true });
  if (!map.getSource("sim-particles")) map.addSource("sim-particles", { type: "geojson", data: emptyFC() as never });
  if (!map.getSource("sim-hubs")) map.addSource("sim-hubs", { type: "geojson", data: emptyFC() as never });
  if (!map.getSource("sim-vehicle")) map.addSource("sim-vehicle", { type: "geojson", data: emptyFC() as never });
  ensureVehicleIcons(map);
  if (!map.getLayer("sim-congestion-casing")) {
    map.addLayer({
      id: "sim-congestion-casing",
      type: "line",
      source: "sim-route",
      filter: ["==", ["geometry-type"], "LineString"],
      layout: { "line-cap": "round", "line-join": "round", visibility: "visible" },
      paint: {
        "line-width": CONGESTION_CASING_WIDTH as never,
        "line-opacity": 0,
        "line-color": "#0a0c10",
      },
    });
  } else {
    try {
      map.setLayoutProperty("sim-congestion-casing", "visibility", "visible");
    } catch {
      /* settling */
    }
  }
  if (!map.getLayer("sim-route")) {
    map.addLayer({
      id: "sim-route",
      type: "line",
      source: "sim-route",
      filter: ["==", ["geometry-type"], "LineString"],
      layout: { "line-cap": "round", "line-join": "round", visibility: "visible" },
      paint: {
        "line-width": CONGESTION_WIDTH as never,
        "line-opacity": 0,
        "line-gradient": spatialGradient(
          [
            [106.7, -6.3],
            [106.9, -6.2],
          ],
          "cascade",
        ) as never,
      },
    });
  } else {
    try {
      map.setLayoutProperty("sim-route", "visibility", "visible");
      map.setPaintProperty("sim-route", "line-width", CONGESTION_WIDTH as never);
    } catch {
      /* settling */
    }
  }
  if (!map.getLayer("sim-particles")) {
    map.addLayer({
      id: "sim-particles",
      type: "circle",
      source: "sim-particles",
      layout: { visibility: "none" },
      paint: { "circle-radius": 1, "circle-opacity": 0 },
    });
  }
  if (!map.getLayer("sim-hubs")) {
    map.addLayer({
      id: "sim-hubs",
      type: "circle",
      source: "sim-hubs",
      paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 5, 14, 8], "circle-color": "#f8fafc", "circle-stroke-width": 2, "circle-stroke-color": COLOR.cascade, "circle-opacity": 0.95 },
    });
  }
  const vehLayout = {
    "icon-size": VEHICLE_ICON_SIZE as never,
    "icon-rotate": ["get", "bearing"] as never,
    "icon-rotation-alignment": "map" as const,
    "icon-pitch-alignment": "map" as const,
    "icon-allow-overlap": true,
    "icon-ignore-placement": true,
    "icon-anchor": "center" as const,
    "icon-padding": 0,
  };
  if (!map.getLayer("sim-vehicle")) {
    map.addLayer({
      id: "sim-vehicle",
      type: "symbol",
      source: "sim-vehicle",
      layout: { "icon-image": ["get", "body"], ...vehLayout },
      paint: { "icon-color": COLOR.bnMid, "icon-opacity": 1, "icon-halo-width": 0, "icon-color-transition": { duration: 0 } },
    });
  } else {
    try {
      map.setLayoutProperty("sim-vehicle", "icon-size", VEHICLE_ICON_SIZE as never);
      map.setPaintProperty("sim-vehicle", "icon-halo-width", 0);
    } catch {
      /* style settling */
    }
  }
  if (!map.getLayer("sim-vehicle-chrome")) {
    map.addLayer({
      id: "sim-vehicle-chrome",
      type: "symbol",
      source: "sim-vehicle",
      layout: { "icon-image": ["get", "chrome"], ...vehLayout },
      paint: { "icon-opacity": 1, "icon-halo-width": 0 },
    });
  } else {
    try {
      map.setLayoutProperty("sim-vehicle-chrome", "icon-size", VEHICLE_ICON_SIZE as never);
    } catch {
      /* style settling */
    }
  }
}

type DualSpec = {
  id: string;
  source: string;
  identity: string;
  modeColor: unknown;
  width: unknown;
  offsetL: unknown;
  offsetR: unknown;
  dash?: [number, number];
  filter?: FilterSpecification;
};
function upsertDualLine(map: MapLibreMap, spec: DualSpec) {
  const modeId = spec.id.endsWith("-line") ? spec.id.replace(/-line$/, "-mode") : `${spec.id}-mode`;
  const shared = { type: "line" as const, source: spec.source, layout: { "line-cap": "round" as const, "line-join": "round" as const }, ...(spec.filter ? { filter: spec.filter } : {}) };
  if (!map.getLayer(spec.id)) {
    map.addLayer({
      ...shared,
      id: spec.id,
      paint: { "line-color": spec.identity, "line-width": spec.width as never, "line-offset": spec.offsetL as never, "line-opacity": 0.95, ...(spec.dash ? { "line-dasharray": spec.dash } : {}) },
    });
  }
  if (!map.getLayer(modeId)) {
    map.addLayer({
      ...shared,
      id: modeId,
      paint: { "line-color": spec.modeColor as never, "line-width": spec.width as never, "line-offset": spec.offsetR as never, "line-opacity": 0.95, ...(spec.dash ? { "line-dasharray": spec.dash } : {}) },
    });
  }
}
function orderLayers(map: MapLibreMap) {
  const order = [
    "roads", "identify-area", "identify-area-line", "identify-hits", "property-zones", "property-zones-outline",
    "selected", "selected-multi",
    "tj-existing-line", "tj-existing-mode", "krl-existing-line", "krl-existing-mode", "lrt-existing-line", "lrt-existing-mode",
    "mrt-existing-line", "mrt-existing-mode", "masterplan-line-ref", "masterplan-line-ref-mode", "masterplan-line-dash",
    "masterplan-line-dash-mode", "masterplan-line-solid", "masterplan-line-solid-mode", "candidate-casing", "candidate",
    "candidate-mode", "sim-congestion-casing", "sim-route", "tj-existing-stop", "krl-existing-stop", "lrt-existing-stop", "mrt-existing-stop",
    "masterplan-stop", "cascade-stop", "sim-hubs", "tj-existing-label", "krl-existing-label", "lrt-existing-label",
    "mrt-existing-label", "masterplan-label", "cascade-label", "selected-pt", "sim-vehicle",
    "sim-vehicle-chrome", "survey-point", "property-cluster", "property-cluster-count", "property-point",
  ];
  for (const id of order) if (map.getLayer(id)) map.moveLayer(id);
}
function mountLayers(map: MapLibreMap, applied?: Record<string, string>) {
  if (!map.isStyleLoaded()) return false;
  const vis = useCascade.getState().visibility;
  for (const leftover of ["lrt", "mrt", "stops"]) if (map.getLayer(leftover)) map.removeLayer(leftover);
  const ids = ["candidate", "cascade-stops", "krl", "tj", "lrt", "mrt", "krl-stops", "tj-stops", "lrt-stops", "mrt-stops", "masterplan", "masterplan-stops", "roads", "selected", "identify-area", "identify-hits"];
  for (const id of ids) {
    const spec = OVERLAYS.find((o) => o.source === id);
    const data = spec && spec.on(vis) ? spec.url : emptyFC();
    if (!map.getSource(id)) {
      map.addSource(id, { type: "geojson", data: data as never, promoteId: "id", maxzoom: id === "roads" ? 12 : 14, buffer: 0, tolerance: id === "roads" ? 1.6 : 0.55 });
    } else if (id === "candidate" || id === "cascade-stops") setData(map, id, data);
    if (spec && applied) applied[id] = spec.on(vis) ? spec.url : "";
  }
  if (!map.getLayer("roads")) {
    map.addLayer({
      id: "roads",
      type: "line",
      source: "roads",
      minzoom: 12,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": COLOR.road, "line-width": ["interpolate", ["linear"], ["zoom"], 12, 0.6, 15, 1.4], "line-opacity": 0.32 },
    });
  }
  mountPropertyLayers(map);
  mountSurveyLayers(map);
  upsertDualLine(map, { id: "tj-existing-line", source: "tj", identity: COLOR.existing, modeColor: COLOR.tj, width: DUAL_WIDTH_EXISTING, offsetL: DUAL_OFFSET_EXISTING_L, offsetR: DUAL_OFFSET_EXISTING_R });
  upsertDualLine(map, { id: "krl-existing-line", source: "krl", identity: COLOR.existing, modeColor: COLOR.krl, width: DUAL_WIDTH_EXISTING, offsetL: DUAL_OFFSET_EXISTING_L, offsetR: DUAL_OFFSET_EXISTING_R });
  upsertDualLine(map, { id: "lrt-existing-line", source: "lrt", identity: COLOR.existing, modeColor: COLOR.lrt, width: DUAL_WIDTH_EXISTING, offsetL: DUAL_OFFSET_EXISTING_L, offsetR: DUAL_OFFSET_EXISTING_R });
  upsertDualLine(map, { id: "mrt-existing-line", source: "mrt", identity: COLOR.existing, modeColor: COLOR.mrt, width: DUAL_WIDTH_EXISTING, offsetL: DUAL_OFFSET_EXISTING_L, offsetR: DUAL_OFFSET_EXISTING_R });
  upsertDualLine(map, { id: "masterplan-line-solid", source: "masterplan", identity: COLOR.masterplan, modeColor: MODE_COLOR_EXPR, width: DUAL_WIDTH_MP, offsetL: DUAL_OFFSET_MP_L, offsetR: DUAL_OFFSET_MP_R, filter: ["==", ["get", "status"], "CONSTRUCTION"] });
  upsertDualLine(map, { id: "masterplan-line-dash", source: "masterplan", identity: COLOR.masterplan, modeColor: MODE_COLOR_EXPR, width: DUAL_WIDTH_MP, offsetL: DUAL_OFFSET_MP_L, offsetR: DUAL_OFFSET_MP_R, dash: DASH_MASTERPLAN, filter: ["in", ["get", "status"], ["literal", ["PLANNED", "MASTERPLAN", "FS"]]] });
  upsertDualLine(map, { id: "masterplan-line-ref", source: "masterplan", identity: COLOR.masterplan, modeColor: MODE_COLOR_EXPR, width: DUAL_WIDTH_MP, offsetL: DUAL_OFFSET_MP_L, offsetR: DUAL_OFFSET_MP_R, dash: DASH_MASTERPLAN, filter: ["in", ["get", "status"], ["literal", ["UNDER_STUDY", "REFERENCE"]]] });
  if (!map.getLayer("candidate-casing")) {
    map.addLayer({ id: "candidate-casing", type: "line", source: "candidate", paint: { "line-color": "#f8fafc", "line-width": 6, "line-opacity": 0.28, "line-dasharray": DASH_CASCADE } });
  }
  upsertDualLine(map, { id: "candidate", source: "candidate", identity: COLOR.cascade, modeColor: MODE_COLOR_EXPR, width: DUAL_WIDTH, offsetL: DUAL_OFFSET_L, offsetR: DUAL_OFFSET_R, dash: DASH_CASCADE });
  mountSimLayers(map);
  addStopCircle(map, "tj-existing-stop", "tj-stops", COLOR.tj, STATION_MINZOOM);
  addStopLabel(map, "tj-existing-label", "tj-stops", STATION_LABEL_MINZOOM);
  addStopCircle(map, "krl-existing-stop", "krl-stops", COLOR.krl, STATION_MINZOOM);
  addStopLabel(map, "krl-existing-label", "krl-stops", STATION_LABEL_MINZOOM);
  addStopCircle(map, "lrt-existing-stop", "lrt-stops", COLOR.lrt, STATION_MINZOOM);
  addStopLabel(map, "lrt-existing-label", "lrt-stops", STATION_LABEL_MINZOOM);
  addStopCircle(map, "mrt-existing-stop", "mrt-stops", COLOR.mrt, STATION_MINZOOM);
  addStopLabel(map, "mrt-existing-label", "mrt-stops", STATION_LABEL_MINZOOM);
  addStopCircle(map, "masterplan-stop", "masterplan-stops", COLOR.masterplan, STATION_MINZOOM);
  addStopLabel(map, "masterplan-label", "masterplan-stops", STATION_LABEL_MINZOOM);
  if (!map.getLayer("cascade-stop")) {
    map.addLayer({
      id: "cascade-stop",
      type: "circle",
      source: "cascade-stops",
      minzoom: STATION_MINZOOM,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], STATION_MINZOOM, ["case", ["==", ["get", "stop_type"], "TERMINUS"], 4.4, ["==", ["get", "interchange"], "YES"], 4.2, 3.4], 15, ["case", ["==", ["get", "stop_type"], "TERMINUS"], 7, ["==", ["get", "interchange"], "YES"], 6.6, 5.4]],
        "circle-color": COLOR.cascade,
        "circle-stroke-width": ["case", ["==", ["get", "interchange"], "YES"], 2, 1],
        "circle-stroke-color": ["case", ["==", ["get", "interchange"], "YES"], "#f5f3ff", "#0a0c10"],
        "circle-opacity": 0.95,
      },
    });
  }
  addStopLabel(map, "cascade-label", "cascade-stops", STATION_LABEL_MINZOOM);
  if (!map.getLayer("identify-area") && map.getSource("identify-area")) {
    map.addLayer({ id: "identify-area", type: "fill", source: "identify-area", paint: { "fill-color": "#c9c3ff", "fill-opacity": 0.12 } });
    map.addLayer({ id: "identify-area-line", type: "line", source: "identify-area", paint: { "line-color": "#c9c3ff", "line-width": 2, "line-opacity": 0.85 } });
  }
  if (!map.getLayer("identify-hits") && map.getSource("identify-hits")) {
    map.addLayer({ id: "identify-hits", type: "line", source: "identify-hits", paint: { "line-color": "#f8fafc", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 8, 14, 15], "line-opacity": 0.32, "line-blur": 2.2 } });
  }
  if (!map.getLayer("selected")) {
    map.addLayer({ id: "selected", type: "line", source: "selected", filter: ["==", ["geometry-type"], "LineString"], paint: { "line-color": "#f8fafc", "line-width": 8, "line-opacity": 0.32 } });
    map.addLayer({ id: "selected-multi", type: "line", source: "selected", filter: ["==", ["geometry-type"], "MultiLineString"], paint: { "line-color": "#f8fafc", "line-width": 8, "line-opacity": 0.32 } });
    map.addLayer({ id: "selected-pt", type: "circle", source: "selected", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-color": COLOR.selected, "circle-radius": 8, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
  }
  for (const id of STOP_IDS) if (map.getLayer(id)) map.setLayerZoomRange(id, STATION_MINZOOM, 24);
  for (const id of LABEL_IDS) if (map.getLayer(id)) map.setLayerZoomRange(id, STATION_LABEL_MINZOOM, 24);
  orderLayers(map);
  for (const l of map.getStyle()?.layers ?? []) {
    if (l.id.startsWith("poi_")) {
      try {
        map.setLayoutProperty(l.id, "visibility", "none");
      } catch {
        /* ignore */
      }
    }
  }
  if (applied) applyOverlays(map, vis, applied);
  return true;
}
function remountOverlays(map: MapLibreMap, applied: Record<string, string>) {
  if (!map.isStyleLoaded()) return false;
  for (const k of Object.keys(applied)) delete applied[k];
  mountLayers(map, applied);
  const st = useCascade.getState();
  applyTjFilter(map, st.tjFilter);
  applyKrlFilter(map, st.krlFilter);
  applyLrtFilter(map, st.lrtFilter);
  applyMrtFilter(map, st.mrtFilter);
  applyMpFilter(map, st.mpMode, st.mpStatus, st.mpConf);
  applyCasFilter(map, st.casFilter);
  applyOverlays(map, st.visibility, applied);
  applyPropertyOverlay(map, st.visibility, st.propFilters);
  applySurveyOverlay(map, st.visibility);
  if (map.getSource("identify-area")) setData(map, "identify-area", st.identifyBbox ? bboxPolygon(st.identifyBbox) : emptyFC());
  if (map.getSource("identify-hits")) setData(map, "identify-hits", st.identifyHits ?? emptyFC());
  ensureVehicleIcons(map);
  paintSimCongestion(map, st.simPath, st.simCompare);
  map.resize();
  return true;
}

function GisMap() {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const appliedRef = useRef<Record<string, string>>({});
  const styleGen = useRef(0);
  const navigate = useNavigate();
  const [tick, setTick] = useState(0);
  const vis = useCascade((s) => s.visibility);
  const groups = useCascade((s) => s.groups);
  const styleKey = useCascade((s) => s.styleKey);
  const selectedId = useCascade((s) => s.selectedId);
  const selectedFeature = useCascade((s) => s.selectedFeature);
  const tjFilter = useCascade((s) => s.tjFilter);
  const krlFilter = useCascade((s) => s.krlFilter);
  const lrtFilter = useCascade((s) => s.lrtFilter);
  const mrtFilter = useCascade((s) => s.mrtFilter);
  const mpMode = useCascade((s) => s.mpMode);
  const mpStatus = useCascade((s) => s.mpStatus);
  const mpConf = useCascade((s) => s.mpConf);
  const casFilter = useCascade((s) => s.casFilter);
  const propFilters = useCascade((s) => s.propFilters);
  const identifyBbox = useCascade((s) => s.identifyBbox);
  const identifyHits = useCascade((s) => s.identifyHits);
  const simPath = useCascade((s) => s.simPath);
  const simPlaying = useCascade((s) => s.simPlaying);
  const simPaused = useCascade((s) => s.simPaused);
  const simCompare = useCascade((s) => s.simCompare);
  const simResult = useCascade((s) => s.simResult);
  const view = useCascade((s) => s.view);
  const setMapStatus = useCascade((s) => s.setMapStatus);
  const setOverlayPhase = useCascade((s) => s.setOverlayPhase);
  const setLoadProgress = useCascade((s) => s.setLoadProgress);
  const setSelected = useCascade((s) => s.setSelected);
  const setPopup = useCascade((s) => s.setPopup);
  const setPopupStatus = useCascade((s) => s.setPopupStatus);
  const styleUrl = styleProxyUrl(styleKey);

  useEffect(() => {
    if (!ref.current) return;
    let cancelled = false;
    (async () => {
      const gl = await import("maplibre-gl");
      gl.setWorkerUrl(MAPID_WORKER_URL);
      if (cancelled || !ref.current) return;
      const transformRequest = (url: string) => {
        if (!url.includes("basemap.mapid.io")) return { url };
        try {
          const u = new URL(url);
          u.searchParams.delete("key");
          return { url: `/api/mapid/forward?u=${encodeURIComponent(u.toString())}` };
        } catch {
          return { url };
        }
      };
      if (mapRef.current) {
        const map = mapRef.current;
        styleGen.current += 1;
        const gen = styleGen.current;
        const remount = () => {
          if (gen !== styleGen.current || cancelled) return;
          remountOverlays(map, appliedRef.current);
          setTick((n) => n + 1);
        };
        map.once("style.load", remount);
        map.setStyle(styleUrl as never);
        const started = Date.now();
        const iv = window.setInterval(() => {
          if (gen !== styleGen.current) {
            window.clearInterval(iv);
            return;
          }
          if (!map.isStyleLoaded()) return;
          if (!map.getLayer("candidate-mode")) remount();
          else window.clearInterval(iv);
          if (Date.now() - started > 12000) window.clearInterval(iv);
        }, 250);
        return;
      }
      setMapStatus("loading");
      setOverlayPhase("basemap");
      setLoadProgress(10);
      const map = new gl.Map({
        container: ref.current,
        style: styleUrl as never,
        center: MAP_CENTER,
        zoom: MAP_ZOOM,
        attributionControl: { compact: true },
        minZoom: 8,
        maxZoom: 18,
        fadeDuration: 0,
        maxTileCacheSize: 60,
        transformRequest,
      });
      map.addControl(new gl.NavigationControl({ showCompass: false }), "bottom-right");
      map.addControl(new gl.ScaleControl({ maxWidth: 120 }), "bottom-left");
      mapRef.current = map;
      setLoadProgress(20);
      (window as unknown as { __CASCADE_MAP?: MapLibreMap; __CASCADE?: typeof useCascade }).__CASCADE_MAP = map;
      (window as unknown as { __CASCADE?: typeof useCascade }).__CASCADE = useCascade;
      (window as unknown as { __CASCADE_BN?: unknown }).__CASCADE_BN = { peakScore, klassOf, HOTSPOTS };
      (window as unknown as { __CASCADE_AUDIT?: typeof auditTransitNetwork }).__CASCADE_AUDIT = auditTransitNetwork;
      const onReady = () => {
        const already = useCascade.getState().mapStatus === "ready";
        if (!already) {
          setMapStatus("ready");
          setOverlayPhase("jaringan");
          setLoadProgress(30);
        }
        try {
          setLoadProgress(already ? 100 : 50);
          remountOverlays(map, appliedRef.current);
          setOverlayPhase("siap");
          setLoadProgress(80);
        } catch {
          /* settling */
        }
        map.resize();
        setTick((n) => n + 1);
        if (already) {
          setLoadProgress(100);
          return;
        }
        let finished = false;
        const finishLoad = () => {
          if (cancelled || finished) return;
          finished = true;
          setOverlayPhase("siap");
          setLoadProgress(90);
          window.setTimeout(() => {
            if (!cancelled) setLoadProgress(100);
            void warmTransitGraph()
              .then(() => useCascade.getState().setNetworkReady(true))
              .catch(() => useCascade.getState().setNetworkReady(true));
          }, 280);
        };
        map.once("idle", finishLoad);
        if (map.areTilesLoaded()) finishLoad();
      };
      map.on("style.load", onReady);
      map.once("load", onReady);
      map.on("error", (ev: { error?: { message?: string } }) => {
        const msg = ev.error?.message ?? "";
        if (/Style is not done loading|images? not found|does not exist/i.test(msg)) return;
        if (useCascade.getState().mapStatus !== "ready") {
          setMapStatus("error", "MAPID gagal dimuat. Periksa konfigurasi akses atau koneksi basemap.");
        }
      });
      const hitLayers = () => HIT.filter((l) => map.getLayer(l));
      map.on("mousemove", (e: MapMouseEvent) => {
        const hit = map.queryRenderedFeatures(e.point, { layers: hitLayers() });
        map.getCanvas().style.cursor = hit.length ? "pointer" : "";
      });
      map.on("click", (e: MapMouseEvent) => {
        const st = useCascade.getState();
        if (st.identifyMode) return;
        const hit = map.queryRenderedFeatures(e.point, { layers: hitLayers() });
        const surveyHit = hit.find((h) => h.layer.id === "survey-point");
        if (surveyHit?.properties) {
          const pg = surveyHit.geometry;
          const coord: [number, number] = pg && pg.type === "Point" ? (pg.coordinates as [number, number]) : [e.lngLat.lng, e.lngLat.lat];
          const pid = String(surveyHit.properties.activity_id ?? surveyHit.id ?? "");
          setPopup({
            id: pid,
            title: String(surveyHit.properties.title || "Titik survei"),
            x: e.point.x,
            y: e.point.y,
            rows: surveyPopupRows(surveyHit.properties as Record<string, unknown>),
            kind: "survey",
            role: "survey",
            coord,
            photos: parsePhotoList(surveyHit.properties.photos),
          });
          return;
        }
        const transportHit = hit.find((h) => h.layer.id !== "property-point" && h.layer.id !== "property-cluster" && h.layer.id !== "survey-point");
        if (!transportHit) {
          const cluster = hit.find((h) => h.layer.id === "property-cluster");
          if (cluster) {
            const src = map.getSource("property") as GeoJSONSource | undefined;
            const cid = Number(cluster.properties?.cluster_id);
            const g = cluster.geometry;
            if (src && Number.isFinite(cid) && g && g.type === "Point") {
              void src.getClusterExpansionZoom(cid).then((zoom) => {
                map.easeTo({ center: g.coordinates as [number, number], zoom, duration: 450 });
              });
            }
            return;
          }
        }
        const prefer = hit.find((h) => h.layer.id === "cascade-stop" || h.layer.id === "candidate" || h.layer.id === "candidate-casing") || transportHit || hit[0];
        const f = prefer;
        if (f?.properties) {
          const layer = String(f.layer.id);
          if (layer === "property-point") {
            const pid = String(f.properties.property_id ?? f.id ?? "");
            const pg = f.geometry;
            const coord: [number, number] = pg && pg.type === "Point" ? (pg.coordinates as [number, number]) : [e.lngLat.lng, e.lngLat.lat];
            setPopup({
              id: pid,
              title: String(f.properties.property_name || f.properties.title || "Properti"),
              x: e.point.x,
              y: e.point.y,
              rows: propertyPopupRows(f.properties as Record<string, unknown>),
              kind: "property",
              role: "property",
              coord,
              sourceUrl: f.properties.source_url ? String(f.properties.source_url) : null,
              mapsUrl: googleMapsUrl(coord[0], coord[1]),
            });
            return;
          }
          const id = String(f.properties.id ?? f.id ?? "");
          const native = popupRows(f.properties as Record<string, unknown>, layer);
          const altCorridors: string[] = [];
          for (const h of hit) {
            const lid = String(h.layer.id);
            if (lid !== "candidate" && lid !== "candidate-casing" && lid !== "candidate-mode") continue;
            const hid = String(h.properties?.id ?? "");
            const short = String(h.properties?.short || h.properties?.name || hid);
            if (hid && hid !== id && short && !altCorridors.includes(short)) altCorridors.push(short);
          }
          if (altCorridors.length) native.push({ label: "Koridor lain di sini", value: altCorridors.join(" · ") });
          const status = layerStatus(layer);
          const g = f.geometry;
          const coord: [number, number] = g && g.type === "Point" ? (g.coordinates as [number, number]) : [e.lngLat.lng, e.lngLat.lat];
          const role = isStopLayer(layer) ? "stop" : "line";
          const node = role === "stop" ? simNodeFrom(f as never, layer, coord) : null;
          if (role === "stop" && node && (st.pickMode === "destination" || st.pickMode === "origin")) {
            const r = st.beginSimFromStation(node);
            if (r === "ready") void navigate({ to: "/simulasi" });
            return;
          }
          setPopupStatus(status);
          setSelected(id);
          const title = String(f.properties.name || f.properties.route_name || f.properties.stop_name || "Fitur");
          setPopup({
            id: node?.id || id,
            title,
            x: e.point.x,
            y: e.point.y,
            rows: native,
            kind: "transport",
            role,
            statusKind: status,
            mode: inferMode(layer, f.properties as Record<string, unknown>),
            corridorId: String(f.properties.corridor_id || f.properties.route_id || f.properties.line_code || ""),
            routeId: String(f.properties.route_id || f.properties.corridor_id || f.properties.id || ""),
            coord,
            tabs: transportTabs(f.properties as Record<string, unknown>, layer, native),
          });
        } else {
          setSelected(null);
          setPopup(null);
        }
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [styleUrl, setMapStatus, setOverlayPhase, setLoadProgress, setPopup, setPopupStatus, setSelected, navigate]);

  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const onHome = () => {
      mapRef.current?.flyTo({ center: MAP_CENTER, zoom: MAP_ZOOM, duration: 800 });
    };
    const onFly = (ev: Event) => {
      const b = (ev as CustomEvent).detail?.bounds as number[] | undefined;
      if (!b || b.length < 4) return;
      try {
        mapRef.current?.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 72, duration: 800, maxZoom: 12 });
      } catch {
        /* ignore */
      }
    };
    window.addEventListener("cascade-home", onHome);
    window.addEventListener("cascade-fly", onFly as EventListener);
    const onSurveyRefresh = () => {
      const live = mapRef.current;
      if (!live) return;
      applySurveyOverlay(live, useCascade.getState().visibility, true);
    };
    window.addEventListener("cascade-survey-refresh", onSurveyRefresh);
    return () => {
      window.removeEventListener("cascade-home", onHome);
      window.removeEventListener("cascade-fly", onFly as EventListener);
      window.removeEventListener("cascade-survey-refresh", onSurveyRefresh);
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    applyOverlays(map, vis, appliedRef.current);
    applyPropertyOverlay(map, vis, propFilters);
    applySurveyOverlay(map, vis);
    if (vis.candidate) setOverlayPhase("siap");
    applyTjFilter(map, tjFilter);
    applyKrlFilter(map, krlFilter);
    applyLrtFilter(map, lrtFilter);
    applyMrtFilter(map, mrtFilter);
    applyMpFilter(map, mpMode, mpStatus, mpConf);
    applyCasFilter(map, casFilter);
    const paintSelected = () => {
      if (selectedFeature) {
        setData(map, "selected", { type: "FeatureCollection", features: [selectedFeature] });
        return;
      }
      if (!selectedId) {
        setData(map, "selected", emptyFC());
        return;
      }
      const sel = findSelectedFeature(map, selectedId);
      setData(map, "selected", sel ? { type: "FeatureCollection", features: [sel] } : emptyFC());
    };
    paintSelected();
    let timer = 0;
    const onData = () => {
      if (!selectedId) return;
      window.clearTimeout(timer);
      timer = window.setTimeout(paintSelected, 80);
    };
    map.on("sourcedata", onData);
    return () => {
      window.clearTimeout(timer);
      map.off("sourcedata", onData);
    };
  }, [tick, vis, groups, selectedId, selectedFeature, tjFilter, krlFilter, lrtFilter, mrtFilter, mpMode, mpStatus, mpConf, casFilter, propFilters, setOverlayPhase]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (map.getSource("identify-area")) setData(map, "identify-area", identifyBbox ? bboxPolygon(identifyBbox) : emptyFC());
    if (map.getSource("identify-hits")) setData(map, "identify-hits", identifyHits ?? emptyFC());
  }, [tick, identifyBbox, identifyHits]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getSource("sim-route")) return;
    const hubFc = simPath ? { type: "FeatureCollection" as const, features: simPath.features.filter((f) => f.geometry.type === "Point") } : emptyFC();
    paintSimCongestion(map, simPath, simCompare);
    if (map.getSource("sim-hubs")) setData(map, "sim-hubs", hubFc);
  }, [tick, simPath, simCompare, view]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getSource("sim-vehicle")) return;
    const coords = pathCoords(simPath);
    const track: AnimTrack | null = simPath ? buildAnimTrack(simResult, coords, simCompare) : null;
    const publish = (elapsed: number, cars: ReturnType<typeof consistAtTime>, fill: string) => {
      const head = cars[0];
      (window as unknown as { __CASCADE_ANIM?: unknown }).__CASCADE_ANIM = {
        duration: track?.duration ?? 0,
        totalM: track?.totalM ?? 0,
        elapsed,
        consistN: cars.length,
        vehicle: head?.vehicle,
        kind: head?.kind,
        fill,
        bn: animCursor.displayBn,
        mode: head?.mode,
        corridor: head?.corridorId,
        lng: head?.lng,
        lat: head?.lat,
        start: track?.samples[0] ? { lng: track.samples[0].lng, lat: track.samples[0].lat } : null,
        end: track?.samples.length ? { lng: track.samples[track.samples.length - 1].lng, lat: track.samples[track.samples.length - 1].lat } : null,
        iconSize: map.getLayer("sim-vehicle") ? map.getLayoutProperty("sim-vehicle", "icon-size") : null,
        trail: map.getLayer("sim-route") ? map.getPaintProperty("sim-route", "line-gradient") : null,
        shp: (window as unknown as { __CASCADE_CONGESTION?: unknown }).__CASCADE_CONGESTION ?? null,
        shpVis: map.getLayer("sim-route") ? map.getLayoutProperty("sim-route", "visibility") : "missing",
        shpOpacity: map.getLayer("sim-route") ? map.getPaintProperty("sim-route", "line-opacity") : 0,
        dualVis: map.getLayer("candidate") ? map.getLayoutProperty("candidate", "visibility") : "missing",
      };
      (window as unknown as { __CASCADE_ANIM_API?: unknown }).__CASCADE_ANIM_API = {
        sample: (sec: number) => (track ? consistAtTime(track, sec, map.getZoom()) : []),
        track,
        path: coords,
      };
    };
    const putConsist = (elapsed: number, dt = 0) => {
      if (!track) {
        setData(map, "sim-vehicle", emptyFC());
        return;
      }
      const cars = consistAtTime(track, elapsed, map.getZoom());
      const head = cars[0];
      if (head) {
        const k = dt > 0 ? Math.min(1, dt / 0.28) : 1;
        animCursor.displayBn += (head.bn - animCursor.displayBn) * k;
      }
      const fill = bnToHex(animCursor.displayBn);
      try {
        if (map.getLayer("sim-vehicle")) map.setPaintProperty("sim-vehicle", "icon-color", fill);
      } catch {
        /* style */
      }
      setData(map, "sim-vehicle", {
        type: "FeatureCollection",
        features: cars.map((s, i) => {
          const part = vehiclePart(s.vehicle, i, s.kind);
          return {
            type: "Feature" as const,
            id: `veh-${i}`,
            properties: {
              id: `veh-${i}`,
              body: vehicleBodyId(part),
              chrome: vehicleChromeId(part),
              bearing: s.bearing,
              mode: s.mode,
              corridor: s.corridorId,
            },
            geometry: { type: "Point" as const, coordinates: [s.lng, s.lat] },
          };
        }),
      });
      publish(elapsed, cars, fill);
    };
    if (map.getSource("sim-particles")) setData(map, "sim-particles", emptyFC());
    if (!simPath || !track) {
      setData(map, "sim-vehicle", emptyFC());
      return;
    }
    const cursor = animCursor;
    const pathKey = `${coords.length}:${coords[0]?.join(",")}:${coords[coords.length - 1]?.join(",")}:${track.totalM.toFixed(0)}`;
    if (cursor.key !== pathKey) {
      cursor.key = pathKey;
      cursor.elapsed = 0;
      cursor.displayBn = track.samples[0]?.bn ?? 0.35;
    }
    if (simPlaying && !simPaused && cursor.elapsed >= track.duration - 0.05) {
      cursor.elapsed = 0;
      cursor.displayBn = track.samples[0]?.bn ?? 0.35;
    }
    putConsist(cursor.elapsed);
    if (!simPlaying || simPaused) return;
    let raf = 0;
    const origin = performance.now() - cursor.elapsed * 1000;
    let lastElapsed = cursor.elapsed;
    const loop = (now: number) => {
      cursor.elapsed = Math.min(track.duration, (now - origin) / 1000);
      const dt = Math.max(0, cursor.elapsed - lastElapsed);
      lastElapsed = cursor.elapsed;
      if (cursor.elapsed >= track.duration) {
        cursor.elapsed = track.duration;
        putConsist(cursor.elapsed);
        useCascade.getState().setSimPlaying(false);
        return;
      }
      putConsist(cursor.elapsed, dt);
      raf = window.requestAnimationFrame(loop);
    };
    raf = window.requestAnimationFrame(loop);
    return () => window.cancelAnimationFrame(raf);
  }, [tick, simPath, simPlaying, simPaused, simCompare, simResult, view]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const onResize = () => {
      try {
        map.resize();
      } catch {
        /* */
      }
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("orientationchange", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("orientationchange", onResize);
    };
  }, [tick]);

  return <div ref={ref} className="absolute inset-0 h-full w-full" />;
}

function SurveyPhotos({ photos }: { photos?: string[] }) {
  const list = photos?.filter(Boolean) ?? [];
  const [i, setI] = useState(0);
  const [open, setOpen] = useState(false);
  if (!list.length) return <p className="mt-2 text-2xs text-muted">Bukti foto tidak tersedia</p>;
  const src = list[Math.min(i, list.length - 1)];
  return (
    <div className="mt-2">
      <button
        type="button"
        className="relative block w-full overflow-hidden rounded-[var(--radius-sm)] bg-subtle"
        onClick={() => setOpen((v) => !v)}
        aria-label="Lihat bukti foto"
      >
        <img src={src} alt="" className={open ? "survey-photo survey-photo-open" : "survey-photo"} loading="lazy" decoding="async" referrerPolicy="no-referrer" />
        {list.length > 1 && (
          <span className="absolute right-1.5 bottom-1.5 rounded-full bg-black/65 px-1.5 py-0.5 text-[0.58rem] text-white">
            {i + 1}/{list.length}
          </span>
        )}
      </button>
      {list.length > 1 && (
        <div className="mt-1 flex justify-between">
          <button type="button" className="h-8 px-1 text-2xs text-muted" onClick={() => setI((n) => (n - 1 + list.length) % list.length)}>
            Sebelumnya
          </button>
          <button type="button" className="h-8 px-1 text-2xs text-muted" onClick={() => setI((n) => (n + 1) % list.length)}>
            Berikutnya
          </button>
        </div>
      )}
    </div>
  );
}

function FeaturePopup() {
  const popup = useCascade((s) => s.popup);
  const setPopup = useCascade((s) => s.setPopup);
  const popupStatus = useCascade((s) => s.popupStatus);
  const setPopupStatus = useCascade((s) => s.setPopupStatus);
  const pickMode = useCascade((s) => s.pickMode);
  const begin = useCascade((s) => s.beginSimFromStation);
  const navigate = useNavigate();
  if (!popup) return null;
  const docked = !!popup.docked;
  const panelW = typeof window !== "undefined" && window.innerWidth >= 768 ? 272 : 0;
  const popW = 248;
  const left = docked
    ? Math.max(12, (typeof window !== "undefined" ? window.innerWidth : 400) - panelW - popW - 16)
    : Math.min(Math.max(12, popup.x + 14), (typeof window !== "undefined" ? window.innerWidth : 400) - popW - 12);
  const top = docked ? 84 : Math.min(Math.max(76, popup.y + 14), (typeof window !== "undefined" ? window.innerHeight : 600) - 240);
  const rows = popup.kind === "transport" && popup.tabs ? popup.tabs[popupStatus] : popup.rows;
  const tabs: { key: StatusKey; label: string }[] = [
    { key: "existing", label: "Existing" },
    { key: "masterplan", label: "Masterplan" },
    { key: "cascade", label: "CASCADE" },
  ];
  const canSim = popup.kind === "transport" && popup.role === "stop" && popup.coord;
  const cta = pickMode === "destination" ? "JADIKAN TUJUAN INI" : "SIMULASIKAN PERJALANAN DARI SINI";
  return (
    <div
      className="feature-popup cascade-panel absolute z-30 w-[15.5rem] max-h-[min(58vh,22rem)] overflow-auto p-2 text-left text-xs"
      style={{ left, top }}
      {...(popup.kind === "survey" ? { "data-survey-popup": "1" } : {})}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium">{popup.title}</p>
        <div className="flex items-center">
          {popup.kind === "transport" && (
            <button
              type="button"
              title="Unduh GeoJSON"
              aria-label="Unduh GeoJSON"
              className="flex size-11 items-center justify-center rounded-full text-muted hover:bg-subtle hover:text-fg"
              onClick={() => {
                void downloadFeatureGeoJSON({
                  id: popup.routeId || popup.corridorId || popup.id,
                  title: popup.title,
                  status: popup.statusKind || "cascade",
                  mode: popup.mode || "",
                  routeId: popup.routeId,
                  corridorId: popup.corridorId,
                });
              }}
            >
              <Download className="size-4" />
            </button>
          )}
          <button type="button" className="h-11 px-2 text-muted" onClick={() => setPopup(null)}>
            Tutup
          </button>
        </div>
      </div>
      {popup.kind === "transport" && (
        <div className="mt-2 grid grid-cols-3 gap-1" role="tablist" aria-label="Status koridor">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={popupStatus === t.key}
              className={`h-11 rounded-[var(--radius-sm)] px-1 text-2xs ${popupStatus === t.key ? "bg-subtle text-fg" : "text-muted"}`}
              onClick={() => setPopupStatus(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}
      {popup.kind === "property" && <p className="mt-1 text-2xs text-muted">Properti · bukan jaringan transportasi</p>}
      {popup.kind === "survey" && <p className="mt-1 text-2xs text-muted">Bukti survei · #geounjukkebolehan</p>}
      {popup.kind === "survey" && <SurveyPhotos photos={popup.photos} />}
      {popup.statusKind && (
        <p className="mt-2 text-2xs text-muted">
          {popup.statusKind} · {modeLabel(popup.mode) || "—"} · {popup.corridorId || popup.routeId || popup.id}
        </p>
      )}
      {rows.map((r) => (
        <p key={r.label} className="mt-1">
          <span className="text-muted">{r.label}</span> {r.value}
        </p>
      ))}
      {canSim && (
        <button
          type="button"
          className="mt-3 h-11 w-full rounded-[var(--radius-sm)] bg-accent text-sm font-medium text-accent-fg"
          onClick={() => {
            if (
              begin({
                id: popup.id,
                name: popup.title,
                coord: popup.coord!,
                status: popup.statusKind ?? "cascade",
                mode: popup.mode ?? "",
                corridorId: popup.corridorId ?? "",
                routeId: popup.routeId ?? popup.id,
              }) === "ready"
            )
              void navigate({ to: "/simulasi" });
          }}
        >
          {cta}
        </button>
      )}
      {popup.kind === "transport" && (
        <button
          type="button"
          className="mt-2 h-11 w-full rounded-[var(--radius-sm)] border border-border text-sm"
          onClick={() => {
            if (popup.routeId || popup.corridorId) useCascade.getState().setResearchId(popup.routeId || popup.corridorId || popup.id);
            setPopup(null);
            void navigate({ to: "/analisis" });
          }}
        >
          ANALISIS
        </button>
      )}
      {popup.mapsUrl && (
        <a href={popup.mapsUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex h-11 items-center text-sm text-accent">
          LIHAT DI GOOGLE MAPS
        </a>
      )}
      {popup.sourceUrl && (
        <a href={popup.sourceUrl} target="_blank" rel="noreferrer" className="mt-2 inline-block text-accent">
          Buka sumber
        </a>
      )}
    </div>
  );
}

export function MapCanvas() {
  const splash = useCascade((s) => s.splash);
  return (
    <>
      <GisMap />
      <IdentifyDrag />
      {!splash && <MapLegend />}
      {!splash && <FeaturePopup />}
    </>
  );
}

function IdentifyDrag() {
  const on = useCascade((s) => s.identifyMode);
  const setBox = useCascade((s) => s.setIdentifyBbox);
  const [rect, setRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  if (!on) return null;
  return (
    <div
      className="absolute inset-0 z-[15] cursor-crosshair"
      onPointerDown={(e) => {
        const host = e.currentTarget.getBoundingClientRect();
        start.current = { x: e.clientX - host.left, y: e.clientY - host.top };
        setRect({ x: start.current.x, y: start.current.y, w: 0, h: 0 });
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const host = e.currentTarget.getBoundingClientRect();
        const cx = e.clientX - host.left;
        const cy = e.clientY - host.top;
        const x = Math.min(start.current.x, cx);
        const y = Math.min(start.current.y, cy);
        setRect({ x, y, w: Math.abs(cx - start.current.x), h: Math.abs(cy - start.current.y) });
      }}
      onPointerUp={(e) => {
        const s = start.current;
        start.current = null;
        setRect(null);
        if (!s) return;
        const map = (window as unknown as { __CASCADE_MAP?: MapLibreMap }).__CASCADE_MAP;
        if (!map) return;
        const host = e.currentTarget.getBoundingClientRect();
        const p1 = map.unproject([s.x, s.y]);
        const p2 = map.unproject([e.clientX - host.left, e.clientY - host.top]);
        const bbox: [number, number, number, number] = [Math.min(p1.lng, p2.lng), Math.min(p1.lat, p2.lat), Math.max(p1.lng, p2.lng), Math.max(p1.lat, p2.lat)];
        if (Math.abs(bbox[2] - bbox[0]) < 1e-5 || Math.abs(bbox[3] - bbox[1]) < 1e-5) return;
        setBox(bbox);
      }}
    >
      {rect && <div className="pointer-events-none absolute border border-accent bg-accent/10" style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }} />}
    </div>
  );
}
