import { useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Compass } from "lucide-react";
import { COLOR } from "@/lib/cascade/carto";
import { SURVEY_COLOR } from "@/lib/cascade/survey";
import { MAPID_STYLE_KEYS, MAPID_STYLE_LABELS, type MapidStyleKey } from "@/lib/cascade/mapid";
import { loadCatalog } from "@/lib/cascade/static-data";
import { useCascade } from "@/lib/cascade/store";
import { carriageCount, legendConsistUrl } from "@/lib/cascade/vehicle-icons";

export function MapLegend() {
  const styleKey = useCascade((s) => s.styleKey);
  const setStyle = useCascade((s) => s.setStyle);
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: loadCatalog, staleTime: 60_000 });
  const c = catalog.data;
  return (
    <div
      className="pointer-events-none absolute left-3 z-20 flex w-[11.25rem] max-h-[28vh] max-w-[calc(100%-1.5rem)] flex-col gap-1.5 top-[4.75rem] md:top-20 md:bottom-20 md:w-[12.5rem] md:max-h-none md:max-w-[13.25rem] lg:w-[13.25rem]"
      data-legend-stack
      onWheel={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="cascade-panel pointer-events-auto flex min-h-0 flex-1 flex-col overflow-hidden px-2.5 py-2 text-2xs text-fg">
        <p className="mb-1 shrink-0 text-[0.62rem] font-medium tracking-wide text-muted">LEGENDA</p>
        <div className="legend-scroll min-h-0 flex-1">
          <div className="space-y-1">
            <p className="text-[0.62rem] tracking-wide text-muted">STATUS JALUR</p>
            <StatusRow solid label="Existing" hint="Sudah tersedia / beroperasi" />
            <StatusRow dashed label="Masterplan" hint="Rencana / referensi" />
            <StatusRow dashed label="CASCADE" hint="Usulan hasil analisis" />
          </div>
          <LegendGroup title="Existing" note="garis solid">
            <DualLine left="var(--color-existing)" right="var(--color-tj)" label="TransJakarta" />
            <DualLine left="var(--color-existing)" right="var(--color-krl)" label="KRL" />
            <DualLine left="var(--color-existing)" right="var(--color-lrt)" label="LRT" />
            <DualLine left="var(--color-existing)" right="var(--color-mrt)" label="MRT" />
          </LegendGroup>
          <LegendGroup title="Masterplan" note="garis putus-putus">
            <DualLine left="var(--color-masterplan)" right="var(--color-tj)" dashed label="TransJakarta" />
            <DualLine left="var(--color-masterplan)" right="var(--color-krl)" dashed label="KRL" />
            <DualLine left="var(--color-masterplan)" right="var(--color-lrt)" dashed label="LRT" />
            <DualLine left="var(--color-masterplan)" right="var(--color-mrt)" dashed label="MRT" />
          </LegendGroup>
          <LegendGroup title="CASCADE" note="garis putus-putus">
            <DualLine left="var(--color-cascade)" right="var(--color-tj)" dashed label="TransJakarta" />
            <DualLine left="var(--color-cascade)" right="var(--color-krl)" dashed label="KRL" />
            <DualLine left="var(--color-cascade)" right="var(--color-lrt)" dashed label="LRT" />
            <DualLine left="var(--color-cascade)" right="var(--color-mrt)" dashed label="MRT" />
          </LegendGroup>
          <div className="legend-section">
            <p className="mb-1 text-[0.62rem] tracking-wide text-muted">MODE SIMULASI</p>
            <p className="mb-1 text-[0.58rem] leading-snug text-muted">Bentuk moda, sama dengan animasi. Warna di peta mengikuti segmen jalur.</p>
            <div className="flex flex-col gap-1">
              <SimModePreview vehicle="bus" label="TJ" fill={COLOR.tj} />
              <SimModePreview vehicle="krl" label="KRL" fill={COLOR.krl} />
              <SimModePreview vehicle="lrt" label="LRT" fill={COLOR.lrt} />
              <SimModePreview vehicle="mrt" label="MRT" fill={COLOR.mrt} />
            </div>
          </div>
          <div className="legend-section">
            <p className="mb-1 text-[0.62rem] tracking-wide text-muted">KONDISI JALUR</p>
            <p className="mb-1 text-[0.58rem] leading-snug text-muted">Warna SHP per segmen, bukan identitas moda.</p>
            <div className="flex flex-col gap-0.5">
              <BnLine klass="low" label="Lancar" />
              <BnLine klass="mid" label="Sedang" />
              <BnLine klass="high" label="Macet" />
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-muted">
              <span className="legend-dot bg-fg" /> halte
            </div>
          </div>
          <div className="legend-section">
            <p className="mb-1 text-[0.62rem] tracking-wide text-muted">TITIK DATA</p>
            <span className="flex items-center gap-1.5">
              <span className="legend-dot" style={{ background: SURVEY_COLOR }} data-survey-legend />
              <span className="leading-tight">
                Titik Survei
                <span className="mt-0.5 block text-[0.58rem] text-muted">MAPID Survey Activity</span>
              </span>
            </span>
          </div>
          <div className="legend-section">
            <p className="mb-1 text-[0.62rem] tracking-wide text-muted">KETERANGAN</p>
            <p className="text-[0.58rem] leading-snug text-muted">Garis solid = layanan existing. Garis putus-putus = Masterplan atau CASCADE, belum beroperasi.</p>
            {c && (
              <p className="mt-1 text-[0.58rem] leading-snug text-muted">
                Jaringan transportasi: {c.krl} lini KRL · {c.transjakarta} koridor TransJakarta · {c.lrt} LRT · {c.mrt} MRT · {c.masterplan}{" "}
                masterplan · {c.candidates} koridor usulan
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="pointer-events-auto cascade-panel flex shrink-0 items-end gap-1.5 px-2 py-1.5">
        <label className="min-w-0 flex-1 text-2xs text-muted">
          Tampilan Peta
          <select
            className="mt-1 h-9 w-full rounded-[var(--radius-sm)] border border-border bg-subtle px-2 text-sm text-fg"
            value={styleKey}
            onChange={(e) => setStyle(e.target.value as MapidStyleKey)}
            aria-label="Tampilan Peta"
          >
            {MAPID_STYLE_KEYS.map((k) => (
              <option key={k} value={k}>
                {MAPID_STYLE_LABELS[k]}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="flex size-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-border text-fg"
          aria-label="Kembali ke tampilan awal"
          onClick={() => window.dispatchEvent(new Event("cascade-home"))}
        >
          <Compass className="size-4" />
        </button>
      </div>
    </div>
  );
}

function SimModePreview({ vehicle, label, fill }: { vehicle: "bus" | "krl" | "lrt" | "mrt"; label: string; fill: string }) {
  const [url, setUrl] = useState("");
  const cars = carriageCount(vehicle);
  useEffect(() => {
    setUrl(legendConsistUrl(vehicle, fill));
  }, [vehicle, fill]);
  return (
    <span className="flex items-center gap-1.5">
      {url ? (
        <img src={url} alt="" className="legend-consist" data-sim-mode={vehicle} data-cars={String(cars)} />
      ) : (
        <span className="legend-consist" data-sim-mode={vehicle} data-cars={String(cars)} />
      )}
      <span className="leading-tight">{label}</span>
    </span>
  );
}

function StatusRow({ solid, dashed, label, hint }: { solid?: boolean; dashed?: boolean; label: string; hint: string }) {
  return (
    <span className="flex items-start gap-1.5">
      <span className={`legend-status ${dashed || !solid ? "legend-status-dash" : "legend-status-solid"}`} aria-hidden />
      <span className="min-w-0 leading-tight">
        <span className="font-medium">{label}</span>
        <span className="mt-0.5 block text-[0.58rem] text-muted">{hint}</span>
      </span>
    </span>
  );
}

function LegendGroup({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <div className="mt-1.5">
      <p className="mb-0.5 text-[0.62rem] tracking-wide text-muted">
        {title}
        <span className="ml-1 font-normal">· {note}</span>
      </p>
      <div className="flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function DualLine({ left, right, label, dashed }: { left: string; right: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="legend-dual" aria-hidden>
        <span style={{ borderTopColor: left, borderTopStyle: dashed ? "dashed" : "solid" }} />
        <span style={{ borderTopColor: right, borderTopStyle: dashed ? "dashed" : "solid" }} />
      </span>
      {label}
    </span>
  );
}

function BnLine({ klass, label }: { klass: "low" | "mid" | "high"; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`legend-line legend-bn-line-${klass}`} aria-hidden />
      {label}
    </span>
  );
}
