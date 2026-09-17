import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ChevronDown, ChevronRight, Download } from "lucide-react";
import { flyCascadeKrl, flyCorridorId, flyMeta, loadCascadeMeta, loadKrlMeta, loadLrtMeta, loadMasterplanMeta, loadMrtMeta, loadTjMeta } from "@/lib/cascade/static-data";
import { downloadFeatureGeoJSON, downloadLayerGeoJSON } from "@/lib/cascade/geojson-download";
import {
  MODE_KEYS,
  MODE_LABEL,
  STATUS_LABEL,
  useCascade,
  type CasFilter,
  type ModeKey,
  type StatusKey,
} from "@/lib/cascade/store";
import { SURVEY_COLOR, SURVEY_HASHTAG_LABEL } from "@/lib/cascade/survey";
import { PropertyPanel } from "./property-panel";

const MODE_SWATCH: Record<ModeKey, string> = {
  mrt: "bg-mrt",
  lrt: "bg-lrt",
  transjakarta: "bg-tj",
  krl: "bg-krl",
};
const GROUP_SWATCH: Record<StatusKey, string> = {
  cascade: "bg-cascade",
  existing: "bg-existing",
  masterplan: "bg-masterplan",
};

export function ExplorePage() {
  const groups = useCascade((s) => s.groups);
  const openGroup = useCascade((s) => s.openGroup);
  const toggleGroup = useCascade((s) => s.toggleGroup);
  const toggleMode = useCascade((s) => s.toggleMode);
  const toggleOpenGroup = useCascade((s) => s.toggleOpenGroup);
  const openMode = useCascade((s) => s.openMode);
  const setOpenMode = useCascade((s) => s.setOpenMode);
  const [layerNote, setLayerNote] = useState<string | null>(null);

  const setCasFilter = useCascade((s) => s.setCasFilter);
  const onModeRow = (g: StatusKey, m: ModeKey) => {
    const next = openMode?.g === g && openMode.m === m ? null : { g, m };
    setOpenMode(next);
    if (next?.g === "cascade" && (next.m === "krl" || next.m === "mrt" || next.m === "lrt" || next.m === "transjakarta")) {
      setCasFilter(next.m);
      void flyCascadeKrl(next.m);
    }
  };

  return (
    <div className="cascade-scroll flex h-full flex-col overflow-auto p-2">
      <p className="text-2xs tracking-wide text-muted">LAPISAN</p>
      <p className="mt-1 text-sm font-medium">Existing · Masterplan · CASCADE</p>
      <ul className="mt-3 space-y-1">
        {(["cascade", "existing", "masterplan"] as StatusKey[]).map((g) => {
          const open = openGroup[g];
          const grp = groups[g];
          return (
            <li key={g} className="rounded-[var(--radius-sm)] bg-subtle/40">
              <div className="flex items-center gap-1 px-1">
                <button
                  type="button"
                  className="flex min-h-11 flex-1 items-center gap-2 px-1 text-left text-sm font-medium"
                  onClick={() => toggleOpenGroup(g)}
                  aria-expanded={open}
                >
                  {open ? <ChevronDown className="size-4 text-muted" /> : <ChevronRight className="size-4 text-muted" />}
                  <span className={`size-2 rounded-full ${GROUP_SWATCH[g]}`} />
                  {STATUS_LABEL[g]}
                </button>
                <label className="flex size-11 items-center justify-center">
                  <input type="checkbox" checked={grp.on} onChange={() => toggleGroup(g)} aria-label={`Tampilkan ${STATUS_LABEL[g]}`} />
                </label>
              </div>
              {open && (
                <ul className="border-t border-border px-1 pb-2">
                  {MODE_KEYS.map((m) => {
                    const modeOpen = openMode?.g === g && openMode.m === m;
                    return (
                      <li key={m}>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            className="flex min-h-11 flex-1 items-center gap-2 px-2 text-left text-sm"
                            onClick={() => onModeRow(g, m)}
                            aria-expanded={modeOpen}
                          >
                            {modeOpen ? <ChevronDown className="size-3.5 text-muted" /> : <ChevronRight className="size-3.5 text-muted" />}
                            <span className={`size-2 rounded-full ${MODE_SWATCH[m]}`} />
                            {MODE_LABEL[m]}
                          </button>
                          <button
                            type="button"
                            title="Unduh GeoJSON"
                            aria-label={`Unduh GeoJSON ${STATUS_LABEL[g]} ${MODE_LABEL[m]}`}
                            className="flex size-9 items-center justify-center rounded-full text-muted hover:bg-subtle hover:text-fg"
                            onClick={() => {
                              setLayerNote(null);
                              void downloadLayerGeoJSON({ status: g, mode: m })
                                .then((ok) => setLayerNote(ok ? "GeoJSON berhasil diunduh." : "Gagal menyiapkan GeoJSON."))
                                .catch(() => setLayerNote("Gagal menyiapkan GeoJSON."));
                            }}
                          >
                            <Download className="size-3.5" />
                          </button>
                          <label className="flex size-11 items-center justify-center">
                            <input
                              type="checkbox"
                              checked={grp[m]}
                              onChange={() => toggleMode(g, m)}
                              aria-label={`${STATUS_LABEL[g]} ${MODE_LABEL[m]}`}
                            />
                          </label>
                        </div>
                        {modeOpen && <ModeCorridors status={g} mode={m} />}
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
      {layerNote && <p className="mt-1 text-2xs text-muted">{layerNote}</p>}
      <SurveyLayerPanel />
      <PropertyPanel />
    </div>
  );
}

function SurveyLayerPanel() {
  const vis = useCascade((s) => s.visibility);
  const toggle = useCascade((s) => s.toggle);
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["survey-activities"],
    queryFn: async () => {
      const res = await fetch("/api/survey-activities");
      return res.json() as Promise<{ ok: boolean; count: number; message: string }>;
    },
    staleTime: 120_000,
  });
  const count = q.data?.count ?? 0;
  return (
    <div className="mt-4 border-t border-border pt-4">
      <p className="text-[11px] tracking-wide text-muted">TITIK STRATEGIS & KEMACETAN</p>
      <p className="mt-1 text-sm font-medium">Bukti survei lapangan</p>
      <label className="mt-2 flex min-h-11 items-center gap-2 rounded-[var(--radius-sm)] px-1 py-1.5 text-sm hover:bg-subtle">
        <input type="checkbox" checked={vis.survey} onChange={() => toggle("survey")} data-survey-toggle />
        <span className="inline-block size-2.5 shrink-0 rounded-full" style={{ background: SURVEY_COLOR }} />
        <span>Bukti survei</span>
      </label>
      <p className="mt-1 px-1 text-[11px] leading-relaxed text-muted" data-survey-count>
        {SURVEY_HASHTAG_LABEL} · MAPID Survey Activity
        {q.data ? ` · ${count} titik` : ""}
      </p>
      {q.data && !q.data.ok && <p className="mt-1 px-1 text-[11px] text-muted">{q.data.message}</p>}
      {q.isError && <p className="mt-1 px-1 text-[11px] text-muted">Titik survei tidak dapat dimuat.</p>}
      <button
        type="button"
        className="mt-1 h-9 px-1 text-[11px] text-muted hover:text-fg"
        onClick={() => {
          void fetch("/api/survey-activities?refresh=1").then(() => {
            void qc.invalidateQueries({ queryKey: ["survey-activities"] });
            window.dispatchEvent(new Event("cascade-survey-refresh"));
          });
        }}
      >
        Muat ulang
      </button>
    </div>
  );
}

function ModeCorridors({ status, mode }: { status: StatusKey; mode: ModeKey }) {
  const setSelected = useCascade((s) => s.setSelected);
  const setCasFilter = useCascade((s) => s.setCasFilter);
  const setTjFilter = useCascade((s) => s.setTjFilter);
  const setKrlFilter = useCascade((s) => s.setKrlFilter);
  const setLrtFilter = useCascade((s) => s.setLrtFilter);
  const setMpMode = useCascade((s) => s.setMpMode);
  const casFilter = useCascade((s) => s.casFilter);
  const selectedId = useCascade((s) => s.selectedId);
  const toggleGroup = useCascade((s) => s.toggleGroup);
  const toggleMode = useCascade((s) => s.toggleMode);
  const groups = useCascade((s) => s.groups);
  const krl = useQuery({ queryKey: ["krl-existing"], queryFn: loadKrlMeta, staleTime: 60_000 });
  const lrt = useQuery({ queryKey: ["lrt-existing"], queryFn: loadLrtMeta, staleTime: 60_000 });
  const mrt = useQuery({ queryKey: ["mrt-existing"], queryFn: loadMrtMeta, staleTime: 60_000 });
  const mp = useQuery({ queryKey: ["masterplan-existing"], queryFn: loadMasterplanMeta, staleTime: 60_000 });
  const tj = useQuery({ queryKey: ["tj-existing"], queryFn: loadTjMeta, staleTime: 60_000 });
  const cascade = useQuery({ queryKey: ["cascade-existing", "tj28"], queryFn: loadCascadeMeta, staleTime: 60_000 });

  const ensure = () => {
    if (!groups[status].on) toggleGroup(status);
    if (!groups[status][mode]) toggleMode(status, mode);
  };

  const rows: { id: string; title: string; sub: string; onClick: () => void; active: boolean }[] = [];

  if (status === "cascade") {
    const list = cascade.data?.corridors ?? [];
    const pred =
      mode === "mrt"
        ? (id: string) => id.startsWith("CAS-MRT") || id.startsWith("MRT-CASCADE")
        : mode === "lrt"
          ? (id: string) => id.startsWith("CAS-LRT") || id.startsWith("LRT-CASCADE")
          : mode === "krl"
            ? (id: string) => id.startsWith("KRL-C") || id.startsWith("CAS-KRL")
            : (id: string) => id.startsWith("CAS-TJ") || id.startsWith("CASTJ");
    for (const m of list.filter((x) => pred(String(x.id)))) {
      rows.push({
        id: m.id,
        title: m.short || m.name,
        sub: `${m.endpoint} · ${m.length_km} km · ${m.stop_count ?? 0}`,
        active: selectedId === m.id || casFilter === m.id,
        onClick: () => {
          ensure();
          setCasFilter(m.id as CasFilter);
          setSelected(m.id);
          flyMeta(m);
          void flyCorridorId(m.id);
        },
      });
    }
  } else if (status === "existing") {
    if (mode === "krl") {
      for (const m of (krl.data?.corridors ?? []).filter((x) => x.filter_key !== "B-nambo")) {
        rows.push({
          id: m.id,
          title: m.short,
          sub: `${m.endpoint} · ${m.stop_count} stasiun`,
          active: selectedId === m.id,
          onClick: () => {
            ensure();
            setKrlFilter(m.line_code as "B" | "R" | "C" | "T" | "TP");
            setSelected(m.id);
            flyMeta(m);
          },
        });
      }
    } else if (mode === "lrt") {
      for (const m of lrt.data?.corridors ?? []) {
        rows.push({
          id: m.id,
          title: m.short,
          sub: `${m.endpoint} · ${m.stop_count} stasiun`,
          active: selectedId === m.id,
          onClick: () => {
            ensure();
            setLrtFilter(m.line_code as "CB" | "BK");
            setSelected(m.id);
            flyMeta(m);
          },
        });
      }
    } else if (mode === "mrt") {
      for (const m of mrt.data?.corridors ?? []) {
        rows.push({
          id: m.id,
          title: m.short,
          sub: `${m.endpoint} · ${m.stop_count} stasiun`,
          active: selectedId === m.id,
          onClick: () => {
            ensure();
            setSelected(m.id);
            flyMeta(m);
          },
        });
      }
    } else {
      for (const m of [...(tj.data?.corridors ?? [])].sort((a, b) => a.corridor_no - b.corridor_no)) {
        rows.push({
          id: m.id,
          title: m.name,
          sub: `${m.endpoint} · ${m.length_km} km · ${m.stop_count} halte`,
          active: selectedId === m.id,
          onClick: () => {
            ensure();
            setTjFilter(m.corridor_no);
            setSelected(m.id);
            flyMeta(m);
          },
        });
      }
    }
  } else {
    const want = mode === "krl" ? ["krl", "rail"] : [mode];
    for (const m of (mp.data?.corridors ?? []).filter((x) => want.includes(String(x.mode).toLowerCase()))) {
      rows.push({
        id: m.id,
        title: m.short || m.name,
        sub: `${m.endpoint} · ${m.length_km} km`,
        active: selectedId === m.id,
        onClick: () => {
          ensure();
          setMpMode(mode === "krl" ? "rail" : mode === "transjakarta" ? "all" : mode);
          setSelected(m.id);
          flyMeta(m);
        },
      });
    }
  }

  if (!rows.length) {
    return <p className="px-3 pb-2 text-2xs text-muted">Tidak ada koridor pada moda ini.</p>;
  }
  return (
    <ul className="space-y-0.5 px-1 pb-1">
      {rows.map((r) => (
        <li key={r.id} className="flex items-stretch gap-0.5">
          <button
            type="button"
            className={`min-w-0 flex-1 rounded-[var(--radius-sm)] px-2 py-2 text-left text-sm ${r.active ? "bg-subtle" : "hover:bg-subtle"}`}
            onClick={r.onClick}
          >
            <span className="block font-medium">{r.title}</span>
            <span className="text-2xs text-muted">{r.sub}</span>
          </button>
          <button
            type="button"
            title="Unduh GeoJSON"
            aria-label={`Unduh GeoJSON ${r.id}`}
            className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-full text-muted hover:bg-subtle hover:text-fg"
            onClick={() => {
              void downloadFeatureGeoJSON({
                id: r.id,
                title: r.title,
                status,
                mode,
                routeId: r.id,
                corridorId: r.id,
              });
            }}
          >
            <Download className="size-3.5" />
          </button>
        </li>
      ))}
    </ul>
  );
}
