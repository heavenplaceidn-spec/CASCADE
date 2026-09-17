import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { BarChart3, ChevronUp, MapPinned, Route } from "lucide-react";
import { useCascade, type ViewId } from "@/lib/cascade/store";
import { MapCanvas } from "./map-canvas";
import { LandingPage } from "./splash";

const VIEW_LABEL: Record<ViewId, string> = {
  eksplorasi: "Eksplorasi",
  simulasi: "Simulasi",
  analisis: "Analisis",
};

export function AppShell({ children }: { children?: React.ReactNode }) {
  const splash = useCascade((s) => s.splash);
  const mapError = useCascade((s) => s.mapError);
  const setView = useCascade((s) => s.setView);
  const pickMode = useCascade((s) => s.pickMode);
  const simOrigin = useCascade((s) => s.simOrigin);
  const path = useRouterState({ select: (s) => s.location.pathname });
  const view: ViewId = path.startsWith("/simulasi") ? "simulasi" : path.startsWith("/analisis") ? "analisis" : "eksplorasi";
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    setView(view);
  }, [view, setView]);

  useEffect(() => {
    setSheetOpen(view !== "eksplorasi");
  }, [view]);

  const panelWide = view === "analisis";

  return (
    <div className="cascade-app relative h-dvh w-full overflow-hidden bg-bg text-fg">
      <MapCanvas />
      {splash ? (
        <LandingPage />
      ) : (
        <>
          <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 px-3 pb-2 pt-[max(0.25rem,env(safe-area-inset-top))]">
            <img
              src="/cascade-mark.png?v=user1"
              alt="CASCADE — Corridor AI for Spatial Congestion, Advanced Data, and Expansion"
              className="cascade-mark"
              width={2048}
              height={682}
            />
            <nav className="pointer-events-auto cascade-panel hidden p-1 md:flex" aria-label="Tampilan">
              <NavBtn to="/" active={view === "eksplorasi"} icon={<MapPinned className="size-4" />} label="Eksplorasi" />
              <NavBtn to="/simulasi" active={view === "simulasi"} icon={<Route className="size-4" />} label="Simulasi" />
              <NavBtn to="/analisis" active={view === "analisis"} icon={<BarChart3 className="size-4" />} label="Analisis" />
            </nav>
          </header>
          {mapError && (
            <div className="absolute inset-x-3 top-20 z-30 rounded-[var(--radius-md)] border border-danger bg-surface px-3 py-2 text-xs text-danger">
              {mapError}
            </div>
          )}
          {pickMode === "destination" && simOrigin && view === "eksplorasi" && (
            <div className="pointer-events-none absolute left-1/2 top-20 z-20 max-w-[min(20rem,calc(100vw-2rem))] -translate-x-1/2 rounded-full border border-border bg-surface px-4 py-2 text-xs text-fg">
              Asal: {simOrigin.name}. Pilih stasiun tujuan di peta.
            </div>
          )}
          <aside
            data-work-panel
            data-collapsed={sheetOpen ? "false" : "true"}
            className={`pointer-events-none absolute z-20 flex flex-col inset-x-3 max-h-[42vh] bottom-[calc(4.35rem+env(safe-area-inset-bottom,0px))] md:inset-x-auto md:right-3 md:top-20 md:bottom-5 md:h-auto md:max-h-none md:w-[14.5rem] lg:bottom-20 ${sheetOpen ? "max-md:h-[42vh]" : ""} ${panelWide ? "lg:w-[17rem]" : "lg:w-[15.5rem]"}`}
          >
            <div
              className="pointer-events-auto cascade-panel flex min-h-0 flex-1 flex-col overflow-hidden"
              onWheel={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                className="flex h-11 w-full shrink-0 items-center justify-between px-3 text-sm md:hidden"
                aria-expanded={sheetOpen}
                aria-label={sheetOpen ? "Tutup panel" : "Buka panel"}
                onClick={() => setSheetOpen((v) => !v)}
              >
                <span className="font-medium">{VIEW_LABEL[view]}</span>
                <ChevronUp className={`size-4 text-muted ${sheetOpen ? "" : "rotate-180"}`} />
              </button>
              <div className={`min-h-0 flex-1 overflow-hidden ${sheetOpen ? "max-md:block" : "max-md:hidden"}`}>{children}</div>
            </div>
          </aside>
          <nav
            className="pointer-events-auto cascade-panel absolute inset-x-2 z-30 flex p-1 md:hidden bottom-[max(0.4rem,env(safe-area-inset-bottom))]"
            aria-label="Tampilan"
            data-mobile-nav
          >
            <NavBtn to="/" active={view === "eksplorasi"} icon={<MapPinned className="size-4" />} label="Eksplorasi" compact />
            <NavBtn to="/simulasi" active={view === "simulasi"} icon={<Route className="size-4" />} label="Simulasi" compact />
            <NavBtn to="/analisis" active={view === "analisis"} icon={<BarChart3 className="size-4" />} label="Analisis" compact />
          </nav>
        </>
      )}
    </div>
  );
}

function NavBtn({
  to,
  active,
  icon,
  label,
  compact,
}: {
  to: string;
  active: boolean;
  icon: ReactNode;
  label: string;
  compact?: boolean;
}) {
  return (
    <Link
      to={to}
      className={`flex min-h-11 items-center justify-center gap-1 rounded-[var(--radius-sm)] px-2 text-xs ${compact ? "h-12 flex-1 flex-col gap-0.5 px-1" : "h-11 gap-2 px-3"} ${active ? "bg-subtle text-fg" : "text-muted"}`}
    >
      {icon}
      {label}
    </Link>
  );
}
