import { useQuery } from "@tanstack/react-query";
import { formatIdr, type CorridorPropertySummary } from "@/lib/cascade/property";
import { fetchJson } from "@/lib/cascade/static-data";
import { useCascade, type PropFilters } from "@/lib/cascade/store";

const CAT: { key: keyof PropFilters; label: string; glyph: "tanah" | "ruko" | "apt" }[] = [
  { key: "tanah", label: "Tanah", glyph: "tanah" },
  { key: "ruko", label: "Ruko", glyph: "ruko" },
  { key: "apt", label: "Apartemen/kos", glyph: "apt" },
];
const CLS: { key: keyof PropFilters; label: string; color: string }[] = [
  { key: "murah", label: "Murah", color: "var(--color-prop-murah)" },
  { key: "sedang", label: "Sedang", color: "var(--color-prop-sedang)" },
  { key: "mahal", label: "Mahal", color: "var(--color-prop-mahal)" },
];
const SALE: { key: keyof PropFilters; label: string }[] = [
  { key: "jual", label: "Jual" },
  { key: "sewa", label: "Sewa" },
];

function Glyph({ kind }: { kind: "tanah" | "ruko" | "apt" }) {
  return (
    <svg viewBox="0 0 16 16" className="size-3.5 shrink-0 text-muted" aria-hidden>
      {kind === "tanah" && <rect x="2" y="2" width="12" height="12" rx="1" fill="currentColor" />}
      {kind === "ruko" && <path d="M8 1.5 14 7v8H2V7Z" fill="currentColor" />}
      {kind === "apt" && (
        <g fill="currentColor">
          <rect x="1" y="5" width="4" height="10" />
          <rect x="6" y="1.5" width="4" height="13.5" />
          <rect x="11" y="6.5" width="4" height="8.5" />
        </g>
      )}
    </svg>
  );
}

function Check({
  k,
  label,
  color,
  glyph,
}: {
  k: keyof PropFilters;
  label: string;
  color?: string;
  glyph?: "tanah" | "ruko" | "apt";
}) {
  const on = useCascade((s) => s.propFilters[k]);
  const set = useCascade((s) => s.setPropFilter);
  return (
    <label className="flex min-h-11 items-center gap-2 rounded-[var(--radius-sm)] px-1 py-1 text-sm hover:bg-subtle">
      <input type="checkbox" checked={on} onChange={() => set(k, !on)} />
      {glyph && <Glyph kind={glyph} />}
      {color && <span className="inline-block size-2 rounded-full" style={{ background: color }} />}
      <span>{label}</span>
    </label>
  );
}

export function PropertyPanel() {
  const vis = useCascade((s) => s.visibility);
  const toggle = useCascade((s) => s.toggle);
  const selectedId = useCascade((s) => s.selectedId);
  const casFilter = useCascade((s) => s.casFilter);
  const summaries = useQuery({
    queryKey: ["property-summaries"],
    queryFn: () => fetchJson<CorridorPropertySummary[]>("/data/property/corridor_summaries.json"),
    staleTime: 120_000,
  });
  const meta = useQuery({
    queryKey: ["property-meta"],
    queryFn: () => fetchJson<{ count?: number; disclaimer?: string }>("/data/property/meta.json"),
    staleTime: 120_000,
  });
  const list = summaries.data ?? [];
  const match =
    list.find((s) => s.corridor_id === selectedId) ||
    list.find((s) => casFilter !== "all" && s.corridor_id === casFilter) ||
    null;
  return (
    <div className="mt-4 border-t border-border pt-4">
      <p className="text-[11px] tracking-wide text-muted">PROPERTI</p>
      <p className="mt-1 text-sm font-medium">Harga di sekitar koridor</p>
      <label className="mt-2 flex min-h-11 items-center gap-2 rounded-[var(--radius-sm)] px-1 py-1.5 text-sm hover:bg-subtle">
        <input type="checkbox" checked={vis.property} onChange={() => toggle("property")} />
        <span>Lapisan properti</span>
      </label>
      <p className="mt-3 text-[11px] text-muted">Kategori</p>
      {CAT.map((c) => (
        <Check key={c.key} k={c.key} label={c.label} glyph={c.glyph} />
      ))}
      <p className="mt-3 text-[11px] text-muted">Kelas harga</p>
      {CLS.map((c) => (
        <Check key={c.key} k={c.key} label={c.label} color={c.color} />
      ))}
      <p className="mt-3 text-[11px] text-muted">Jenis listing</p>
      {SALE.map((c) => (
        <Check key={c.key} k={c.key} label={c.label} />
      ))}
      {match ? (
        <SummaryCard s={match} />
      ) : (
        <p className="mt-3 text-[11px] text-subtle-fg">Pilih koridor untuk melihat ringkasan harga properti di sekitar koridor.</p>
      )}
      <p className="mt-3 text-[11px] leading-relaxed text-subtle-fg">
        {meta.data?.disclaimer ||
          "Harga mengacu pada asking price dari listing publik dan kisaran kawasan tahun 2026. Angka ini bukan nilai transaksi."}
      </p>
    </div>
  );
}

function SummaryCard({ s }: { s: CorridorPropertySummary }) {
  const typeLabel =
    s.corridor_type === "cascade" ? "Usulan CASCADE" : s.corridor_type === "masterplan" ? "Masterplan" : "Jaringan saat ini";
  return (
    <div className="mt-3 rounded-[var(--radius-md)] border border-border bg-subtle p-3 text-xs">
      <p className="font-medium text-sm">{s.corridor_name}</p>
      <p className="mt-0.5 text-[11px] text-muted">
        {typeLabel}
        {" · "}buffer {s.buffer_m} m
      </p>
      {!s.data_sufficient ? (
        <p className="mt-2 text-muted">Data belum mencukupi untuk ringkasan harga.</p>
      ) : (
        <>
          <p className="mt-2">
            {s.property_count} properti · Tanah {s.tanah} · Ruko {s.ruko} · Apt/kos {s.apartemen_kos}
          </p>
          <p className="mt-1">Median jual {formatIdr(s.median_price)}</p>
          <p>Median /m² {formatIdr(s.median_price_per_m2)}</p>
          <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-border" aria-hidden>
            <span className="bg-prop-murah" style={{ width: `${s.murah_pct}%` }} />
            <span className="bg-prop-sedang" style={{ width: `${s.sedang_pct}%` }} />
            <span className="bg-prop-mahal" style={{ width: `${s.mahal_pct}%` }} />
          </div>
          <p className="mt-1">
            Murah {s.murah_pct}% · Sedang {s.sedang_pct}% · Mahal {s.mahal_pct}%
          </p>
          <p className="mt-1 text-muted">
            Terdekat {Math.round(s.nearest_m)} m · {formatIdr(s.min_price)} – {formatIdr(s.max_price)}
          </p>
        </>
      )}
      <p className="mt-2 leading-relaxed text-muted">{s.insight}</p>
    </div>
  );
}
