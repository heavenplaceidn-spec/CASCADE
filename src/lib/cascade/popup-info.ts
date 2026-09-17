import { featureBbox, type Feature } from "./geojson";
import { flyBounds } from "./static-data";
import { useCascade, type PopupInfo, type PopupRow, type StatusKey } from "./store";

function str(v: unknown) {
  return v == null ? "" : String(v).trim();
}

export function modeLabel(mode?: string) {
  const m = String(mode || "").toLowerCase();
  if (m === "krl") return "KRL";
  if (m === "mrt") return "MRT";
  if (m === "lrt") return "LRT";
  if (m.includes("transjakarta") || m === "brt" || m === "bus") return "TransJakarta";
  if (m === "rail") return "Rel / outer ring";
  return mode || "";
}

function confLabel(c: unknown) {
  const v = String(c || "").toUpperCase();
  if (v === "HIGH") return "Tinggi";
  if (v === "MEDIUM") return "Sedang";
  if (v === "LOW") return "Rendah";
  return v;
}

function addRow(rows: PopupRow[], label: string, value: unknown) {
  const v = str(value);
  if (!v || v === "—" || v === "null" || v === "undefined") return;
  rows.push({ label, value: v });
}

export function layerForStatus(status: StatusKey, mode: string, role: "line" | "stop" = "line") {
  if (status === "cascade") return role === "stop" ? "cascade-stop" : "candidate";
  if (status === "masterplan") return role === "stop" ? "masterplan-stop" : "masterplan-line";
  if (mode === "krl") return role === "stop" ? "krl-existing-stop" : "krl-existing-line";
  if (mode === "mrt") return role === "stop" ? "mrt-existing-stop" : "mrt-existing-line";
  if (mode === "lrt") return role === "stop" ? "lrt-existing-stop" : "lrt-existing-line";
  return role === "stop" ? "tj-existing-stop" : "tj-existing-line";
}

export function popupRowsFromLine(props: Record<string, unknown>, status: StatusKey): PopupRow[] {
  const rows: PopupRow[] = [];
  if (status === "cascade") {
    addRow(rows, "Koridor", props.route_id || props.id);
    addRow(rows, "Dari", props.from_name);
    addRow(rows, "Ke", props.to_name);
    addRow(rows, "Panjang", props.length_km != null ? `${props.length_km} km` : "");
    addRow(rows, "Jumlah halte", props.stop_count);
    addRow(rows, "Tipe jaringan", String(props.mode) === "lrt" ? "LRT usulan" : String(props.mode) === "mrt" ? "MRT usulan" : String(props.mode) === "krl" ? "KRL usulan" : "BRT trunk usulan");
    addRow(rows, "Status", props.status_label || "Usulan CASCADE");
    addRow(rows, "Kepercayaan geometri", confLabel(props.geometry_confidence));
    addRow(rows, "Sumber", props.source);
    addRow(rows, "Keterangan", String(props.disclaimer || "Usulan CASCADE. Bukan rute resmi. Bukan DED."));
  } else if (status === "masterplan") {
    addRow(rows, "Moda", modeLabel(String(props.mode || "")));
    addRow(rows, "Koridor", props.short || props.route_name);
    addRow(rows, "Dari – ke", props.from_node && props.to_node ? `${props.from_node} – ${props.to_node}` : "");
    addRow(rows, "Jumlah stasiun", props.stop_count);
    addRow(rows, "Status", props.status_label || "Masterplan / acuan");
    addRow(rows, "Sumber", props.source);
    addRow(rows, "Keterangan", String(props.disclaimer || "Geometri hasil digitasi dokumen perencanaan. Bukan gambar DED."));
  } else {
    addRow(rows, "Moda", modeLabel(String(props.mode || "")));
    addRow(rows, "Koridor", props.corridor_id || props.koridor_label || props.route_id);
    addRow(rows, "Endpoint", props.endpoint);
    addRow(rows, "Status", props.status_label || "Jaringan saat ini");
    addRow(rows, "Panjang", props.length_km != null ? `${props.length_km} km` : "");
    addRow(rows, "Jumlah halte", props.stop_count);
    addRow(rows, "Sumber", props.source);
  }
  return rows;
}

export function transportTabsFrom(status: StatusKey, native: PopupRow[]) {
  return {
    existing: status === "existing" ? native : [{ label: "Status", value: "Bukan jaringan yang sedang beroperasi." }],
    masterplan: status === "masterplan" ? native : [{ label: "Status", value: "Bukan koridor masterplan resmi." }],
    cascade: status === "cascade" ? native : [{ label: "Status", value: "Bukan usulan koridor CASCADE." }],
  };
}

export function buildLinePopup(opts: {
  feature: Feature;
  status: StatusKey;
  mode: string;
  docked?: boolean;
}): PopupInfo {
  const p = (opts.feature.properties ?? {}) as Record<string, unknown>;
  const id = str(p.route_id || p.id || opts.feature.id);
  const native = popupRowsFromLine(p, opts.status);
  const title = str(p.name || p.route_name || p.short || p.corridor_name || id || "Koridor");
  return {
    id,
    title,
    x: 0,
    y: 0,
    rows: native,
    kind: "transport",
    role: "line",
    statusKind: opts.status,
    mode: opts.mode,
    corridorId: str(p.corridor_id || p.route_id || id),
    routeId: str(p.route_id || p.corridor_id || id),
    docked: opts.docked ?? true,
    tabs: transportTabsFrom(opts.status, native),
  };
}

/** Pilih koridor analisis: highlight geometri exact, terbang ke bbox, buka popup unduhan. */
export function openAnalysisCorridor(opts: {
  id: string;
  status: StatusKey;
  mode: string;
  name: string;
  feature: Feature;
}) {
  const st = useCascade.getState();
  st.setResearchId(opts.id);
  st.setSelected(opts.id, opts.feature);
  st.setPopupStatus(opts.status);
  st.setPopup(buildLinePopup({ feature: opts.feature, status: opts.status, mode: opts.mode, docked: true }));
  flyBounds(featureBbox(opts.feature));
}
