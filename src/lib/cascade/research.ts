import type { CascadeMeta } from "./functions";
import type { CorridorPropertySummary } from "./property";
import { HOTSPOTS } from "./bottleneck";

export type CostRange = { loT: number; hiT: number; label: string; note: string };

function modeKey(mode?: string, id?: string) {
  const m = String(mode || id || "").toLowerCase();
  if (m.includes("mrt")) return "mrt";
  if (m.includes("lrt")) return "lrt";
  if (m.includes("krl") || m.includes("rail")) return "krl";
  return "transjakarta";
}

/** Order-of-magnitude, bukan RAB/DED. Satuan triliun rupiah. */
export function costRange(id: string, mode: string | undefined, km: number, stops: number, extra?: { elevatedKm?: number; widening?: string; costLabel?: string }): CostRange {
  if (extra?.costLabel) {
    return {
      loT: 0,
      hiT: 0,
      label: extra.costLabel,
      note: "Angka bersifat indikatif untuk perbandingan awal dan bukan RAB/DED.",
    };
  }
  const mk = modeKey(mode, id);
  const elevated = extra?.elevatedKm || (id.includes("CASTJ21") ? 9 : 0);
  const perKm = mk === "mrt" ? [0.7, 1.15] : mk === "lrt" ? [0.18, 0.38] : mk === "krl" ? [0.1, 0.22] : [0.03, 0.07];
  const perStop = mk === "transjakarta" ? [0.004, 0.012] : [0.04, 0.09];
  let lo = km * perKm[0] + stops * perStop[0];
  let hi = km * perKm[1] + stops * perStop[1];
  if (elevated) {
    lo += elevated * 0.4;
    hi += elevated * 0.8;
  }
  const loT = Number(Math.max(0.15, lo).toFixed(1));
  const hiT = Number(Math.max(loT + 0.2, hi).toFixed(1));
  return {
    loT,
    hiT,
    label: `Rp ${loT}–${hiT} T`,
    note: "Angka bersifat indikatif untuk perbandingan awal dan bukan RAB/DED.",
  };
}

export function lineHitsBbox(coords: [number, number][], b: [number, number, number, number]) {
  let overlap = 0;
  for (let i = 0; i < coords.length; i++) {
    const [x, y] = coords[i];
    if (x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) overlap++;
  }
  if (overlap) return overlap;
  const minX = Math.min(...coords.map((c) => c[0]));
  const maxX = Math.max(...coords.map((c) => c[0]));
  const minY = Math.min(...coords.map((c) => c[1]));
  const maxY = Math.max(...coords.map((c) => c[1]));
  const hit = !(maxX < b[0] || minX > b[2] || maxY < b[1] || minY > b[3]);
  return hit ? 1 : 0;
}

export function googleMapsUrl(lng: number, lat: number) {
  return `https://www.google.com/maps?q=${lat},${lng}`;
}

export type DecisionRow = {
  id: string;
  name: string;
  score: number;
  why: string[];
  cost: CostRange;
  mode: string;
  km: number;
  stops: number;
};

export function rankCorridors(cas: CascadeMeta[], summaries: CorridorPropertySummary[]): DecisionRow[] {
  const propBy = Object.fromEntries(summaries.map((s) => [s.corridor_id, s]));
  const rows: DecisionRow[] = cas.map((m) => {
    const km = m.length_km || 1;
    const stops = m.stop_count || 0;
    const mk = modeKey(m.mode, m.id);
    const modeW = mk === "mrt" ? 1 : mk === "lrt" ? 0.86 : mk === "krl" ? 0.8 : 0.62;
    const coverage = Math.min(1, km / 45);
    const access = Math.min(1, stops / 28);
    const ps = propBy[m.id];
    const prop = ps ? Math.min(1, ps.property_count / 40) : 0.2;
    const box = m.bbox;
    let bn = 0.4;
    if (box && box.length === 4) {
      const hits = HOTSPOTS.filter((h) => h.lng >= box[0] && h.lng <= box[2] && h.lat >= box[1] && h.lat <= box[3]);
      bn = hits.length ? Math.min(1, hits.reduce((a, h) => a + h.peak, 0) / hits.length) : 0.4;
    }
    const extra = m as CascadeMeta & { elevated_km?: number; cost_label?: string; insight?: string; widening_level?: string };
    const score = Math.round(100 * (0.28 * bn + 0.18 * access + 0.16 * coverage + 0.14 * prop + 0.14 * modeW + 0.1 * Math.min(1, stops / km / 0.7)));
    const why: string[] = [];
    if (bn >= 0.7) why.push("potensi mengurai kemacetan tinggi");
    else if (bn >= 0.5) why.push("melewati kawasan padat");
    if (access >= 0.55) why.push("jangkauan pelayanan tinggi");
    if (coverage >= 0.5) why.push("cakupan koridor panjang");
    if (prop >= 0.45) why.push("konteks properti di buffer");
    if (mk === "mrt" || mk === "lrt") why.push("konektivitas jaringan rel");
    if (extra.widening_level === "VERY HIGH" || extra.widening_level === "HIGH") why.push(`pelebaran jalan ${extra.widening_level.toLowerCase()}`);
    if ((extra.elevated_km || 0) > 0) why.push("ada skenario elevated konseptual");
    if (!why.length) why.push("melengkapi celah layanan");
    return {
      id: m.id,
      name: m.short || m.name,
      score: Math.max(12, Math.min(96, score)),
      why: why.slice(0, 3),
      cost: costRange(m.id, m.mode, km, stops, { elevatedKm: extra.elevated_km, costLabel: extra.cost_label }),
      mode: mk,
      km,
      stops,
    };
  });
  return rows.sort((a, b) => b.score - a.score);
}

export function fallbackInsight(row: DecisionRow) {
  const specific: Record<string, string> = {
    CASTJ15: "Petojo–Pulo Gebang mengikat pusat kota ke simpul timur. Bottleneck Otista/Jatinegara; pelebaran sedang, bukan elevated.",
    CASTJ16: "Pinang Ranti–Lebak Bulus via Pasar Rebo menyambung MRT Lebak Bulus. Celah selatan-timur; interchange MRT di ujung barat.",
    "CASTJ07-EXT": "Perpanjangan Koridor 7 Trikora–UI via Kelapa Dua. Interchange KRL di UI. Pelebaran tinggi di Condet–Cimanggis.",
    CASTJ17: "Pinang Ranti–Marunda via Pulo Gebang mengisi akses timur-utara. Pelebaran tinggi di Cakung–Cilincing.",
    CASTJ18: "Pinang Ranti–Tanjung Priok via Jatiwaringin dan Koja. Konektivitas timur-utara; bottleneck Kelapa Gading–Koja.",
    CASTJ19: "UI–Galunggung via Pasar Minggu menumpang catchment KRL UI dan simpul Galunggung. Properti Margonda aktif.",
    "CASTJ06-EXT": "Perpanjangan Koridor 6 Ragunan–Jagakarsa. Geometry pendek sesuai GeoJSON, tanpa trase ke Galunggung.",
    CASTJ20: "Jagakarsa–Kemang paling ketat ROW-nya sehingga pelebaran VERY HIGH. Senayan–Grogol lebih arterial, interchange MRT/TJ.",
    CASTJ21: "Cibubur–Ciracas: skenario elevated konseptual karena ROW sempit. Kemang at-grade. Interchange MRT Blok M dan LRT Cibubur.",
    CASTJ22: "Sawangan–Blok M via UPN Veteran mengisi selatan-barat. Geometry GeoJSON; transfer Blok M hanya jika spasial bertemu.",
    CASTJ23: "Pondok Labu–Kalideres via Puri Indah. Shared node TJ existing hanya jika garis benar-benar bertemu.",
    CASTJ24: "CBD Ciledug–Monas via Joglo. Terpisah dari CASTJ25 meski Ciledug/Monas bisa berbagi halte.",
    CASTJ25: "Ciledug–Monas via Meruya. Overlap dengan CASTJ24 bukan alasan merge; trek GeoJSON tetap berbeda.",
    CASTJ26: "Koja–CBC via Plumpang dan Kapuk. Interchange utara hanya jika spasial bertemu TJ existing.",
    "CASTJ03-EXT": "Perpanjangan Koridor 3 Kalideres–Bandara. Shared Kalideres jika berimpit; geometry GeoJSON tidak digeser.",
    "CASTJ02-EXT": "Perpanjangan Koridor 2 Pulo Gadung–Harapan Indah. Bukan pengganti 2B; shared node hanya jika spasial.",
    "CASTJ14-EXT": "Perpanjangan Koridor 14 JIS–Marunda via Cilincing. Parent JIS–Senen utuh. Endpoint mengikuti GeoJSON.",
  };
  const text = specific[row.id] || `Koridor ${row.id} (${row.mode}) diprioritaskan karena ${row.why.join(", ")}. Estimasi indikatif ${row.cost.label}, bukan RAB/DED.`;
  return clip50(text);
}

export function clip50(text: string) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length <= 50) return words.join(" ");
  return `${words.slice(0, 50).join(" ")}`;
}
