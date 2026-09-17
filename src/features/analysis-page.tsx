import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { explainCorridor } from "@/lib/cascade/insight";
import { searchStations } from "@/lib/cascade/graph";
import { openAnalysisCorridor } from "@/lib/cascade/popup-info";
import type { CorridorPropertySummary } from "@/lib/cascade/property";
import { clip50, fallbackInsight } from "@/lib/cascade/research";
import { analyzeIdentifyArea, factorRows, priorityHint, priorityLabel, type SdssRow } from "@/lib/cascade/sdss";
import { fetchJson } from "@/lib/cascade/static-data";
import { STATUS_LABEL, useCascade } from "@/lib/cascade/store";

const MODE_ID: Record<string, string> = {
  transjakarta: "TransJakarta",
  krl: "KRL",
  lrt: "LRT",
  mrt: "MRT",
};

export function AnalysisPage() {
  const navigate = useNavigate();
  const props = useQuery({
    queryKey: ["property-summaries"],
    queryFn: () => fetchJson<CorridorPropertySummary[]>("/data/property/corridor_summaries.json"),
    staleTime: 120_000,
  });
  const identifyMode = useCascade((s) => s.identifyMode);
  const setIdentifyMode = useCascade((s) => s.setIdentifyMode);
  const bbox = useCascade((s) => s.identifyBbox);
  const setIdentifyBbox = useCascade((s) => s.setIdentifyBbox);
  const setIdentifyHits = useCascade((s) => s.setIdentifyHits);
  const researchId = useCascade((s) => s.researchId);
  const setResearchId = useCascade((s) => s.setResearchId);
  const origin = useCascade((s) => s.simOrigin);
  const dest = useCascade((s) => s.simDest);
  const sim = useCascade((s) => s.simResult);
  const ai = useCascade((s) => s.insightText);
  const aiErr = useCascade((s) => s.insightErr);
  const setInsight = useCascade((s) => s.setInsight);
  const [aiBusy, setAiBusy] = useState(false);
  const [openStops, setOpenStops] = useState<Record<string, boolean>>({});
  const [openScore, setOpenScore] = useState<Record<string, boolean>>({});
  const [simBusy, setSimBusy] = useState(false);

  const identify = useQuery({
    queryKey: ["identify-sdss", bbox, sim?.km, sim?.bottleneckBefore, (props.data ?? []).length],
    enabled: !!bbox,
    staleTime: 20_000,
    placeholderData: (prev) => prev,
    queryFn: () => analyzeIdentifyArea(bbox!, { summaries: props.data ?? [], sim }),
  });

  useEffect(() => {
    if (!identify.data) return;
    setIdentifyHits(identify.data.hits);
  }, [identify.data, setIdentifyHits]);

  const rows = identify.data?.rows ?? [];
  const selected = rows.find((r) => r.id === researchId) || null;

  const askAi = async (row: SdssRow) => {
    setAiBusy(true);
    setInsight(null, null);
    const payload = {
      corridor_id: row.id,
      corridor_name: row.name,
      score: row.score,
      priority: row.priority,
      congestion_indicators: row.factors.congestion,
      accessibility: row.factors.accessibility,
      connectivity: row.factors.connectivity,
      property_context: row.propertyNote,
      station_list: row.stations.slice(0, 12),
      indicative_cost: row.cost.label,
      constraints: row.why,
      status: row.status,
    };
    try {
      const res = await explainCorridor({ data: { id: row.id, context: JSON.stringify(payload) } });
      if (res.ok) setInsight(clip50(res.text), null);
      else setInsight(clip50(row.why.join(". ")), res.error);
    } catch {
      setInsight(clip50(row.why.join(". ")), "AI tidak tersedia.");
    } finally {
      setAiBusy(false);
    }
  };

  const seedSim = async (row: SdssRow) => {
    const first = row.stations[0];
    const last = row.stations[row.stations.length - 1];
    if (!first || !last) {
      void navigate({ to: "/simulasi" });
      return;
    }
    setSimBusy(true);
    try {
      const [aHits, bHits] = await Promise.all([searchStations(first, 10), searchStations(last, 10)]);
      const pick = (hits: typeof aHits, name: string) =>
        hits.find((s) => s.routeId === row.id || s.corridorId === row.id) ||
        hits.find((s) => s.name.toLowerCase() === name.toLowerCase() && s.status === row.status) ||
        hits[0];
      const a = pick(aHits, first);
      const b = pick(bHits, last);
      if (a && b && a.id !== b.id) {
        useCascade.setState({
          simOrigin: a,
          origin: a.coord,
          simDest: b,
          destination: b.coord,
          simNetwork: row.status,
          simCompare: row.status,
          pickMode: "none",
          simPath: null,
          simResult: null,
          simPlaying: false,
          simPaused: false,
        });
      }
      void navigate({ to: "/simulasi" });
    } finally {
      setSimBusy(false);
    }
  };

  const clear = () => {
    setIdentifyBbox(null);
    setIdentifyHits(null);
    setIdentifyMode(false);
    setInsight(null, null);
    setResearchId(null);
  };

  return (
    <div className="cascade-scroll h-full overflow-auto p-2">
      <p className="text-2xs tracking-wide text-muted">ANALISIS</p>
      <p className="mt-0.5 text-sm font-medium">Decision Support spasial</p>
      <p className="mt-1 text-2xs leading-relaxed text-muted">
        Prioritas indikatif dari irisan area peta, bukan keputusan pembangunan resmi.
      </p>

      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" variant={identifyMode ? "default" : "outline"} onClick={() => setIdentifyMode(!identifyMode)}>
          {identifyMode ? "Seret kotak di peta…" : "Seret untuk pilih area"}
        </Button>
        {bbox && (
          <Button size="sm" variant="ghost" onClick={clear}>
            Hapus area
          </Button>
        )}
      </div>
      {identifyMode && (
        <p className="mt-2 text-2xs text-muted">Seret kotak di peta. Koridor yang beririsan akan dihitung skor SDSS-nya.</p>
      )}

      {bbox && (
        <div className="mt-2 rounded-[var(--radius-sm)] bg-subtle px-2 py-1.5">
          <p className="text-2xs tracking-wide text-muted">AREA TERPILIH</p>
          {identify.isLoading && <p className="mt-1 text-2xs text-muted">Menghitung irisan spasial…</p>}
          {identify.data && identify.data.candidateCount === 0 && (
            <p className="mt-1 text-2xs text-muted">Tidak ada koridor transportasi yang teridentifikasi pada area ini.</p>
          )}
          {identify.data && identify.data.candidateCount > 0 && (
            <p className="mt-1 text-2xs text-muted">
              {identify.data.candidateCount} koridor beririsan. Menampilkan hingga 3 koridor yang paling relevan pada area terpilih.
            </p>
          )}
        </div>
      )}

      {rows.map((r, i) => (
        <SdssCard
          key={`${r.status}-${r.id}`}
          row={r}
          index={i + 1}
          active={selected?.id === r.id && selected.status === r.status}
          openStops={!!openStops[r.id]}
          openScore={!!openScore[r.id]}
          onOpen={() => openAnalysisCorridor({ id: r.id, status: r.status, mode: r.mode, name: r.name, feature: r.feature })}
          onStops={() => setOpenStops((s) => ({ ...s, [r.id]: !s[r.id] }))}
          onScore={() => setOpenScore((s) => ({ ...s, [r.id]: !s[r.id] }))}
        />
      ))}

      {selected && (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" disabled={aiBusy} onClick={() => void askAi(selected)}>
            {aiBusy ? "Menyusun…" : "Ringkas dengan AI"}
          </Button>
          <Button size="sm" variant="outline" disabled={simBusy} onClick={() => void seedSim(selected)}>
            {simBusy ? "Menyiapkan…" : "Lihat di Simulasi"}
          </Button>
        </div>
      )}
      {(ai || aiErr) && selected && (
        <p className="mt-2 text-2xs leading-relaxed text-muted">
          {ai || fallbackInsight({ id: selected.id, name: selected.name, score: selected.score, why: selected.why, cost: selected.cost, mode: selected.mode, km: selected.km, stops: selected.stops })}
          {aiErr ? ` (${aiErr})` : ""}
        </p>
      )}

      {sim && origin && dest && (
        <p className="mt-3 text-2xs text-muted">
          Hasil simulasi dipakai sebagai konteks: {origin.name} → {dest.name} ({sim.km} km).
        </p>
      )}
    </div>
  );
}

function SdssCard({
  row,
  index,
  active,
  openStops,
  openScore,
  onOpen,
  onStops,
  onScore,
}: {
  row: SdssRow;
  index: number;
  active: boolean;
  openStops: boolean;
  openScore: boolean;
  onOpen: () => void;
  onStops: () => void;
  onScore: () => void;
}) {
  const tone = row.priority === "tinggi" ? "text-bn-high" : row.priority === "sedang" ? "text-bn-mid" : "text-bn-low";
  const shown = openStops ? row.stations : row.stations.slice(0, 6);
  return (
    <article
      className={`mt-2 rounded-[var(--radius-sm)] border px-2 py-1.5 ${active ? "border-accent bg-subtle" : "border-border hover:border-accent/70"}`}
    >
      <button type="button" className="w-full cursor-pointer text-left" onClick={onOpen} aria-label={`Lihat koridor ${row.id}`}>
        <p className="text-2xs tracking-wide text-muted">
          Koridor {String(index).padStart(2, "0")} · {STATUS_LABEL[row.status]} · {MODE_ID[row.mode] || row.mode}
        </p>
        <p className="mt-0.5 text-sm font-medium">
          {row.id} · {row.name}
        </p>
        <p className={`mt-1 text-2xs font-medium ${tone}`}>
          {priorityLabel(row.priority)} · {row.score}/100
        </p>
        <p className="mt-0.5 text-2xs text-muted">{priorityHint(row.priority)}</p>
        <p className="mt-1 text-2xs text-accent">Klik untuk melihat koridor di peta</p>
      </button>

      <p className="mt-1.5 text-2xs tracking-wide text-muted">Halte / stasiun</p>
      {row.stations.length ? (
        <>
          <ol className="mt-0.5 max-h-28 space-y-0.5 overflow-auto text-2xs">
            {shown.map((n, i) => (
              <li key={`${n}-${i}`}>
                {String(i + 1).padStart(2, "0")} {n}
              </li>
            ))}
          </ol>
          {row.stations.length > 6 && (
            <button type="button" className="mt-1 min-h-10 text-2xs text-accent" onClick={onStops}>
              {openStops ? "Sembunyikan" : `Lihat seluruh halte (${row.stations.length})`}
            </button>
          )}
        </>
      ) : (
        <p className="mt-0.5 text-2xs text-muted">Data halte/stasiun belum tersedia.</p>
      )}

      <p className="mt-1.5 text-2xs tracking-wide text-muted">Perkiraan biaya indikatif</p>
      <p className="mt-0.5 text-sm">{row.cost.label}</p>
      <p className="text-2xs text-muted">
        Dihitung dari panjang koridor dan jumlah halte/stasiun dengan satuan indikatif per moda. Angka bersifat indikatif untuk perbandingan
        awal dan bukan RAB/DED.
      </p>

      <p className="mt-1.5 text-2xs tracking-wide text-muted">Alasan analisis</p>
      <ul className="mt-0.5 list-disc space-y-0.5 pl-4 text-2xs text-muted">
        {row.why.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>

      <p className="mt-1.5 text-2xs tracking-wide text-muted">Konteks properti</p>
      <p className="mt-0.5 text-2xs text-muted">{row.propertyNote}</p>

      <button type="button" className="mt-1.5 min-h-10 text-2xs text-accent" onClick={onScore}>
        {openScore ? "Sembunyikan dasar penilaian" : "Dasar penilaian"}
      </button>
      {openScore && (
        <ul className="mt-0.5 space-y-0.5 text-2xs text-muted">
          {factorRows(row.factors).map((f) => (
            <li key={f.k} className="flex justify-between">
              <span>{f.k}</span>
              <span>{f.v}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
