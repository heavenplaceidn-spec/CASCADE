export type PropCategory = "TANAH" | "RUKO" | "APARTEMEN/KOS";
export type PriceClass = "MURAH" | "SEDANG" | "MAHAL";
export type CorridorType = "existing" | "masterplan" | "cascade";

export type PropertyRecord = {
  property_id: string;
  source: string;
  source_url?: string | null;
  source_type?: string | null;
  category: PropCategory;
  sub_category?: string | null;
  title: string;
  property_name?: string | null;
  latitude: number;
  longitude: number;
  address?: string | null;
  district?: string | null;
  city?: string | null;
  price?: number | null;
  price_min?: number | null;
  price_max?: number | null;
  price_unit?: string | null;
  area_land_m2?: number | null;
  area_building_m2?: number | null;
  price_per_m2?: number | null;
  listing_type?: string | null;
  sale_or_rent: "jual" | "sewa";
  bedroom?: number | null;
  confidence_score?: string | null;
  geometry_source?: string | null;
  corridor_id?: string | null;
  corridor_type?: CorridorType | null;
  distance_to_corridor?: number | null;
  distance_to_station?: number | null;
  nearest_station?: string | null;
  existing_corridor_id?: string | null;
  existing_distance_m?: number | null;
  masterplan_corridor_id?: string | null;
  masterplan_distance_m?: number | null;
  cascade_corridor_id?: string | null;
  cascade_distance_m?: number | null;
  local_price_index?: number | null;
  price_class?: PriceClass | null;
  price_label?: string | null;
  date_updated?: string | null;
  note?: string | null;
};

export type CorridorPropertySummary = {
  corridor_id: string;
  corridor_name: string;
  corridor_type: string;
  mode: string;
  buffer_m: number;
  property_count: number;
  tanah: number;
  ruko: number;
  apartemen_kos: number;
  median_price: number | null;
  median_price_per_m2: number | null;
  murah_pct: number;
  sedang_pct: number;
  mahal_pct: number;
  nearest_m: number;
  max_price: number | null;
  min_price: number | null;
  insight: string;
  data_sufficient: boolean;
};

export const PROP_COLOR = { MURAH: "#4FAF86", SEDANG: "#E5A13A", MAHAL: "#D62F7F" } as const;
export const PROP_RELATE_M = 1000;

export type PropFilterState = {
  tanah: boolean;
  ruko: boolean;
  apt: boolean;
  murah: boolean;
  sedang: boolean;
  mahal: boolean;
  existing: boolean;
  masterplan: boolean;
  cascade: boolean;
  jual: boolean;
  sewa: boolean;
};

export function formatIdr(n?: number | null) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  if (v >= 1_000_000_000) return `Rp${(v / 1_000_000_000).toLocaleString("id-ID", { maximumFractionDigits: 2 })} M`;
  if (v >= 1_000_000) return `Rp${Math.round(v / 1_000_000).toLocaleString("id-ID")} jt`;
  return `Rp${Math.round(v).toLocaleString("id-ID")}`;
}

function num(v: unknown): number | null {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function propertyMatchesFilters(p: Record<string, unknown>, f: PropFilterState): boolean {
  const cat = String(p.category ?? "");
  if (cat === "TANAH" && !f.tanah) return false;
  if (cat === "RUKO" && !f.ruko) return false;
  if (cat === "APARTEMEN/KOS" && !f.apt) return false;
  const cls = String(p.price_class ?? "");
  if (cls === "MURAH" && !f.murah) return false;
  if (cls === "SEDANG" && !f.sedang) return false;
  if (cls === "MAHAL" && !f.mahal) return false;
  const sale = String(p.sale_or_rent ?? "");
  if (sale === "jual" && !f.jual) return false;
  if (sale === "sewa" && !f.sewa) return false;
  const ex = num(p.existing_distance_m);
  const mp = num(p.masterplan_distance_m);
  const cas = num(p.cascade_distance_m);
  const hitEx = f.existing && ex != null && ex <= PROP_RELATE_M;
  const hitMp = f.masterplan && mp != null && mp <= PROP_RELATE_M;
  const hitCas = f.cascade && cas != null && cas <= PROP_RELATE_M;
  return hitEx || hitMp || hitCas;
}

export function filterPropertyFeatures<T extends { properties?: object | null }>(
  features: T[],
  f: PropFilterState,
): T[] {
  return features.filter((feat) => propertyMatchesFilters((feat.properties ?? {}) as Record<string, unknown>, f));
}

function distLabel(v: unknown): string {
  const n = num(v);
  if (n == null) return "";
  if (n < 10) return `${n.toFixed(0)} m`;
  return `${Math.round(n)} m`;
}

export function propertyPopupRows(p: Record<string, unknown>): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [];
  const add = (label: string, value: unknown) => {
    const v = value == null ? "" : String(value).trim();
    if (!v || v === "—" || v === "null" || v === "undefined") return;
    rows.push({ label, value: v });
  };
  const sale = String(p.sale_or_rent ?? "");
  add("Kategori", p.category);
  add("Status", sale === "sewa" ? "Disewakan" : sale === "jual" ? "Dijual" : p.listing_type);
  if (sale === "sewa") {
    add("Sewa", `${formatIdr(num(p.price))}${p.price_unit && p.price_unit !== "total" ? ` / ${p.price_unit}` : " / bulan"}`);
  } else {
    if (p.price_min != null && p.price_max != null && p.price == null) {
      add("Kisaran", `${formatIdr(num(p.price_min))} – ${formatIdr(num(p.price_max))}`);
    } else {
      add("Harga", formatIdr(num(p.price)));
    }
  }
  const land = num(p.area_land_m2);
  const bld = num(p.area_building_m2);
  if (land) add("Luas tanah", `${land} m²`);
  if (bld) add("Luas bangunan", `${bld} m²`);
  if (sale !== "sewa") add("Harga/m²", formatIdr(num(p.price_per_m2)));
  add("Kelas harga", p.price_class ? `${p.price_class} (benchmark lokal)` : "");
  add("Dasar kelas", p.price_class ? "Median harga kecamatan per kategori (tanah / ruko / apartemen-kos)" : "");
  add("Label harga", p.price_label);
  add("Indeks lokal", num(p.local_price_index) != null ? Number(p.local_price_index).toFixed(2) : "");
  add("Kawasan", [p.district, p.city].filter(Boolean).join(", ") || p.address);
  add("Sumber", p.source);
  add("Tipe sumber", p.source_type);
  add("Update", p.date_updated || p.data_timestamp);
  add("Kepercayaan", p.confidence_score);
  add("Koridor terdekat", p.corridor_id);
  const ctype = String(p.corridor_type ?? "");
  add(
    "Jenis koridor",
    ctype === "cascade" ? "Usulan CASCADE" : ctype === "masterplan" ? "Masterplan" : ctype === "existing" ? "Existing" : "",
  );
  add("Jarak koridor", distLabel(p.distance_to_corridor));
  add("Stasiun terdekat", p.nearest_station);
  add("Jarak stasiun", distLabel(p.distance_to_station));
  if (p.existing_corridor_id) add("Existing terdekat", `${p.existing_corridor_id} · ${distLabel(p.existing_distance_m)}`);
  if (p.masterplan_corridor_id) add("Masterplan terdekat", `${p.masterplan_corridor_id} · ${distLabel(p.masterplan_distance_m)}`);
  if (p.cascade_corridor_id) add("CASCADE terdekat", `${p.cascade_corridor_id} · ${distLabel(p.cascade_distance_m)}`);
  add("Catatan", p.note);
  return rows;
}
