import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { hotspotsAlong, meanScore } from "@/lib/cascade/bottleneck";
import { searchStations } from "@/lib/cascade/graph";
import { flyBounds } from "@/lib/cascade/static-data";
import { buildSimPath, pathBbox, pathCoords } from "@/lib/cascade/sim-route";
import { STATUS_LABEL, useCascade, type SimNode, type StatusKey } from "@/lib/cascade/store";

const NETS: { key: StatusKey; label: string }[] = [
  { key: "existing", label: "Existing" },
  { key: "masterplan", label: "Masterplan" },
  { key: "cascade", label: "CASCADE" },
];

function StationField({
  label,
  value,
  placeholder,
  onPick,
}: {
  label: string;
  value: SimNode | null;
  placeholder: string;
  onPick: (n: SimNode) => void;
}) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SimNode[]>([]);
  useEffect(() => {
    let live = true;
    if (q.trim().length < 2) {
      setHits([]);
      return;
    }
    void searchStations(q, 8).then((rows) => {
      if (live) setHits(rows);
    });
    return () => {
      live = false;
    };
  }, [q]);
  return (
    <label className="mt-3 block text-2xs text-muted">
      {label}
      <input
        className="mt-1 h-11 w-full rounded-[var(--radius-sm)] border border-border bg-subtle px-2 text-sm text-fg"
        value={q}
        placeholder={value ? value.name : placeholder}
        onChange={(e) => setQ(e.target.value)}
        aria-label={label}
      />
      {value && !q ? <span className="mt-1 block text-2xs text-fg">{value.name}</span> : null}
      {hits.length ? (
        <ul className="mt-1 max-h-40 overflow-auto rounded-[var(--radius-sm)] border border-border bg-surface">
          {hits.map((h) => (
            <li key={`${h.id}-${h.routeId}`}>
              <button
                type="button"
                className="flex min-h-11 w-full flex-col items-start px-2 py-1.5 text-left text-sm text-fg hover:bg-subtle"
                onClick={() => {
                  onPick(h);
                  setQ("");
                  setHits([]);
                }}
              >
                <span>{h.name}</span>
                <span className="text-2xs text-muted">
                  {h.routeId || h.corridorId} · {h.status === "cascade" ? "CASCADE" : h.status === "masterplan" ? "Masterplan" : "Existing"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </label>
  );
}

export function SimulatePage() {
  const origin = useCascade((s) => s.simOrigin);
  const dest = useCascade((s) => s.simDest);
  const network = useCascade((s) => s.simNetwork);
  const compare = useCascade((s) => s.simCompare);
  const playing = useCascade((s) => s.simPlaying);
  const paused = useCascade((s) => s.simPaused);
  const result = useCascade((s) => s.simResult);
  const simPath = useCascade((s) => s.simPath);
  const networkReady = useCascade((s) => s.networkReady);
  const setNetwork = useCascade((s) => s.setSimNetwork);
  const setPlaying = useCascade((s) => s.setSimPlaying);
  const setPaused = useCascade((s) => s.setSimPaused);
  const setPath = useCascade((s) => s.setSimPath);
  const begin = useCascade((s) => s.beginSimFromStation);
  const clearSim = useCascade((s) => s.clearSim);
  const [busy, setBusy] = useState(false);
  const coords = pathCoords(simPath);
  const liveSpots = coords.length ? hotspotsAlong(coords, compare) : result?.hotspots ?? [];
  const bnExisting = coords.length ? meanScore(coords, "existing") : result?.bottleneckBefore ?? 0;
  const bnNow = coords.length ? meanScore(coords, compare) : result?.bottleneckAfter ?? 0;
  const hasRoute = !!(simPath && coords.length > 1 && result && result.km > 0);

  const play = async () => {
    if (!origin || !dest) return;
    setBusy(true);
    try {
      const { fc, result: res } = await buildSimPath(origin, dest, network);
      setPath(fc.features.length ? fc : null, res);
      const box = pathBbox(pathCoords(fc));
      if (box) flyBounds(box);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cascade-scroll h-full overflow-auto p-2">
      <p className="text-2xs tracking-wide text-muted">SIMULASI</p>
      <p className="mt-0.5 text-sm font-medium">Aliran di sepanjang koridor</p>
      <p className="mt-1 text-2xs leading-relaxed text-muted">Putaran penuh ~20 detik. Jalur SHP tetap merah/kuning/hijau sesuai kemacetan segmen; kendaraan berjalan di atasnya dan warna badan mengikuti segmen yang dilewati. TJ = satu bus; KRL, LRT, dan MRT = 3 gerbong rapat dengan siluet berbeda.</p>
      {!networkReady && <p className="mt-1 text-2xs text-muted">Menyiapkan jaringan transit…</p>}

      <StationField
        label="Asal"
        value={origin}
        placeholder="Ketik nama stasiun, mis. Koja"
        onPick={(n) => begin(n)}
      />
      <StationField
        label="Tujuan"
        value={dest}
        placeholder="Ketik stasiun tujuan, mis. Cengkareng Business City"
        onPick={(n) => {
          if (!origin) begin(n);
          else useCascade.setState({ simDest: n, destination: n.coord, pickMode: "none" });
        }}
      />
      <label className="mt-2 block text-2xs text-muted">
        Mode jaringan
        <select
          className="mt-1 h-11 w-full rounded-[var(--radius-sm)] border border-border bg-subtle px-2 text-sm text-fg"
          value={network}
          onChange={(e) => setNetwork(e.target.value as StatusKey)}
          aria-label="Mode jaringan simulasi"
        >
          {NETS.map((n) => (
            <option key={n.key} value={n.key}>
              {n.label}
            </option>
          ))}
        </select>
      </label>

      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" disabled={!origin || !dest || busy || !networkReady} onClick={() => void play()}>
          {busy ? "Menghitung…" : "Jalankan"}
        </Button>
        {playing && hasRoute && (
          <Button size="sm" variant="outline" onClick={() => setPaused(true)}>
            Jeda
          </Button>
        )}
        {paused && hasRoute && (
          <Button size="sm" variant="outline" onClick={() => setPlaying(true)}>
            Lanjut
          </Button>
        )}
        {(origin || dest) && (
          <Button size="sm" variant="ghost" onClick={clearSim}>
            Reset
          </Button>
        )}
      </div>

      {result && (
        <div className="mt-3 space-y-1 text-sm">
          {result.km > 0 ? (
            <>
              <p>
                <span className="text-muted">Jarak</span> {result.km} km
              </p>
              <p>
                <span className="text-muted">Estimasi waktu</span> {result.minutes} mnt
              </p>
              <p>
                <span className="text-muted">Bottleneck rute</span> existing {bnExisting.toFixed(2)} / {STATUS_LABEL[compare].toLowerCase()}{" "}
                {bnNow.toFixed(2)}
              </p>
              <p className="text-2xs text-muted">{result.hops.join(" → ")}</p>
              {result.segments?.length ? (
                <p className="text-2xs text-muted">
                  Segmen: {result.segments.map((s) => (s.kind === "transfer" ? `pindah ${s.toName}` : `${s.routeId || s.mode}`)).join(" · ")}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-2xs text-muted">{result.note || "Rute belum terhubung pada jaringan yang tersedia."}</p>
          )}
          {result.km > 0 && result.note ? <p className="text-2xs text-muted">{result.note}</p> : null}
          {liveSpots.length ? (
            <ul className="mt-2 space-y-1 text-2xs">
              {liveSpots.map((h) => (
                <li key={h.name} className="flex justify-between rounded-[var(--radius-sm)] bg-subtle px-2 py-1.5">
                  <span>{h.name}</span>
                  <span className={h.klass === "tinggi" ? "text-bn-high" : h.klass === "sedang" ? "text-bn-mid" : "text-bn-low"}>
                    {h.klass} · {h.score}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}

      <Link to="/analisis" className="mt-3 inline-flex h-11 items-center text-sm text-accent">
        Buka analisis
      </Link>
    </div>
  );
}