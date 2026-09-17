import { useEffect, useState } from "react";
import { prefetchOverlays } from "@/lib/cascade/static-data";
import { useCascade } from "@/lib/cascade/store";

const STAGE: Record<number, string> = {
  10: "Menyiapkan aplikasi",
  20: "Menyiapkan peta",
  30: "Memuat basemap",
  40: "Memuat data transportasi",
  50: "Memuat jaringan existing",
  60: "Memuat masterplan",
  70: "Memuat CASCADE",
  80: "Memuat stasiun/halte",
  90: "Menyusun layer peta",
  100: "Peta siap",
};

export function LandingPage() {
  const dismiss = useCascade((s) => s.dismissSplash);
  const progress = useCascade((s) => s.loadProgress);
  const mapStatus = useCascade((s) => s.mapStatus);
  const mapError = useCascade((s) => s.mapError);
  const [shown, setShown] = useState(0);
  const mapReady = mapStatus === "ready" && progress >= 100;
  const uiReady = shown >= 100 && mapReady;
  useEffect(() => {
    prefetchOverlays();
  }, []);
  useEffect(() => {
    const id = window.setInterval(() => {
      setShown((s) => {
        if (s >= 100) return 100;
        const next = s + 10;
        if (next < 100) return next;
        return mapReady ? 100 : 90;
      });
    }, 220);
    return () => window.clearInterval(id);
  }, [mapReady]);
  return (
    <div className="landing-root">
      <img src="/cascade-hero.png" alt="" className="landing-hero" width={1671} height={941} />
      <div className="landing-ui">
        <div className="w-full max-w-xs">
          <div className="h-1.5 overflow-hidden rounded-full bg-white/20">
            <div className="h-full bg-white transition-[width] duration-200" style={{ width: `${Math.max(4, shown)}%` }} />
          </div>
          <p className="mt-2 text-center text-2xs text-white/85">
            {uiReady ? "Peta siap" : `Memuat peta ${shown || 10}%`}
          </p>
          <p className="mt-1 text-center text-2xs text-white/60">{STAGE[shown] || STAGE[10]}</p>
        </div>
        {mapError && <p className="mt-3 max-w-xs text-center text-2xs text-red-300">{mapError}</p>}
        <button
          type="button"
          disabled={!uiReady}
          onClick={dismiss}
          className="mt-5 h-11 rounded-full border border-white/40 bg-white/95 px-8 text-sm font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Mulai Eksplorasi
        </button>
      </div>
    </div>
  );
}
