import { create } from "zustand";
import type { MapidStyleKey } from "./mapid";
import type { Feature, FeatureCollection } from "./geojson";

export type ViewId = "eksplorasi" | "simulasi" | "analisis";
export type StatusKey = "existing" | "masterplan" | "cascade";
export type ModeKey = "mrt" | "lrt" | "transjakarta" | "krl";

export type GroupState = { on: boolean } & Record<ModeKey, boolean>;

export type LayerGroups = {
  existing: GroupState;
  masterplan: GroupState;
  cascade: GroupState;
};

export type Visibility = {
  krl: boolean;
  mrt: boolean;
  lrt: boolean;
  transjakarta: boolean;
  masterplan: boolean;
  candidate: boolean;
  roads: boolean;
  stops: boolean;
  property: boolean;
  survey: boolean;
};

export type OverlayPhase = "basemap" | "jaringan" | "siap";

export type PopupRow = { label: string; value: string };

export type PopupInfo = {
  id: string;
  title: string;
  x: number;
  y: number;
  rows: PopupRow[];
  notes?: string;
  kind?: "transport" | "property" | "survey";
  role?: "stop" | "line" | "property" | "survey";
  statusKind?: StatusKey;
  mode?: string;
  corridorId?: string;
  routeId?: string;
  coord?: [number, number];
  sourceUrl?: string | null;
  mapsUrl?: string | null;
  photos?: string[];
  docked?: boolean;
  tabs?: {
    existing: PopupRow[];
    masterplan: PopupRow[];
    cascade: PopupRow[];
  };
};

export type SimNode = {
  id: string;
  name: string;
  coord: [number, number];
  status: StatusKey;
  mode: string;
  corridorId: string;
  routeId: string;
};

export type SimVehicle = "bus" | "krl" | "lrt" | "mrt";

export type SimSegment = {
  corridorId: string;
  routeId: string;
  mode: string;
  status: StatusKey;
  kind: "ride" | "transfer";
  coords: [number, number][];
  meters: number;
  fromName: string;
  toName: string;
  vehicle: SimVehicle;
  stops: { name: string; coord: [number, number]; atM: number }[];
};

export type SimResult = {
  km: number;
  minutes: number;
  bottleneckBefore: number;
  bottleneckAfter: number;
  flowChange: number;
  hops: string[];
  note: string;
  hotspots: { name: string; score: number; klass: "tinggi" | "sedang" | "rendah" }[];
  transfers: { name: string; coord: [number, number] }[];
  segments?: SimSegment[];
};

export type PropFilters = {
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

export type TjFilter = "all" | number;
export type KrlFilter = "all" | "B" | "R" | "C" | "T" | "TP";
export type LrtFilter = "all" | "CB" | "BK";
export type MrtFilter = "all" | "NS";
export type MpMode = "all" | "rail" | "mrt" | "lrt";
export type MpStatus = "all" | "CONSTRUCTION" | "PLANNED" | "FS" | "UNDER_STUDY" | "MASTERPLAN";
export type MpConf = "all" | "HIGH" | "MEDIUM" | "LOW";
export type CasFilter = "all" | string;

export const MODE_KEYS: ModeKey[] = ["mrt", "lrt", "transjakarta", "krl"];
export const MODE_LABEL: Record<ModeKey, string> = {
  mrt: "MRT",
  lrt: "LRT",
  transjakarta: "TransJakarta",
  krl: "KRL",
};
export const STATUS_LABEL: Record<StatusKey, string> = {
  existing: "EXISTING",
  masterplan: "MASTERPLAN",
  cascade: "CASCADE",
};

const ALL_ON: GroupState = { on: true, mrt: true, lrt: true, transjakarta: true, krl: true };

export function enabledModes(g: GroupState): ModeKey[] {
  return MODE_KEYS.filter((m) => g[m]);
}

function visFromGroups(g: LayerGroups, roads: boolean, property: boolean, survey: boolean): Visibility {
  return {
    krl: g.existing.on && g.existing.krl,
    mrt: g.existing.on && g.existing.mrt,
    lrt: g.existing.on && g.existing.lrt,
    transjakarta: g.existing.on && g.existing.transjakarta,
    masterplan: g.masterplan.on,
    candidate: g.cascade.on,
    roads,
    stops: g.existing.on,
    property,
    survey,
  };
}

type CascadeState = {
  view: ViewId;
  styleKey: MapidStyleKey;
  groups: LayerGroups;
  openGroup: { existing: boolean; masterplan: boolean; cascade: boolean };
  visibility: Visibility;
  selectedId: string | null;
  selectedFeature: Feature | null;
  tjFilter: TjFilter;
  krlFilter: KrlFilter;
  lrtFilter: LrtFilter;
  mrtFilter: MrtFilter;
  mpMode: MpMode;
  mpStatus: MpStatus;
  mpConf: MpConf;
  casFilter: CasFilter;
  propFilters: PropFilters;
  popupStatus: StatusKey;
  splash: boolean;
  loadProgress: number;
  mapStatus: "boot" | "loading" | "ready" | "error";
  overlayPhase: OverlayPhase;
  mapError: string | null;
  popup: PopupInfo | null;
  origin: [number, number] | null;
  destination: [number, number] | null;
  pickMode: "none" | "origin" | "destination";
  simOrigin: SimNode | null;
  simDest: SimNode | null;
  simNetwork: StatusKey;
  simCompare: StatusKey;
  simPlaying: boolean;
  simPaused: boolean;
  simResult: SimResult | null;
  simPath: FeatureCollection | null;
  networkReady: boolean;
  identifyMode: boolean;
  identifyBbox: [number, number, number, number] | null;
  identifyHits: FeatureCollection | null;
  researchId: string | null;
  openMode: { g: StatusKey; m: ModeKey } | null;
  insightText: string | null;
  insightErr: string | null;
  setView: (v: ViewId) => void;
  setStyle: (s: MapidStyleKey) => void;
  toggle: (k: keyof Visibility) => void;
  toggleGroup: (g: StatusKey) => void;
  toggleMode: (g: StatusKey, m: ModeKey) => void;
  toggleOpenGroup: (g: StatusKey) => void;
  setSelected: (id: string | null, feature?: Feature | null) => void;
  setTjFilter: (f: TjFilter) => void;
  setKrlFilter: (f: KrlFilter) => void;
  setLrtFilter: (f: LrtFilter) => void;
  setMrtFilter: (f: MrtFilter) => void;
  setMpMode: (f: MpMode) => void;
  setMpStatus: (f: MpStatus) => void;
  setMpConf: (f: MpConf) => void;
  setCasFilter: (f: CasFilter) => void;
  setPropFilter: (k: keyof PropFilters, v: boolean) => void;
  setPopupStatus: (s: CascadeState["popupStatus"]) => void;
  dismissSplash: () => void;
  setLoadProgress: (n: number) => void;
  setMapStatus: (s: CascadeState["mapStatus"], error?: string | null) => void;
  setOverlayPhase: (p: OverlayPhase) => void;
  setPopup: (p: PopupInfo | null) => void;
  setOrigin: (c: [number, number] | null) => void;
  setDest: (c: [number, number] | null) => void;
  setPick: (p: CascadeState["pickMode"]) => void;
  setSimNetwork: (n: StatusKey) => void;
  setSimCompare: (n: StatusKey) => void;
  setSimPlaying: (on: boolean) => void;
  setSimPaused: (on: boolean) => void;
  setSimPath: (fc: FeatureCollection | null, result?: SimResult | null) => void;
  setNetworkReady: (on: boolean) => void;
  beginSimFromStation: (node: SimNode) => "need-dest" | "ready";
  clearSim: () => void;
  setIdentifyMode: (on: boolean) => void;
  setIdentifyBbox: (b: [number, number, number, number] | null) => void;
  setIdentifyHits: (fc: FeatureCollection | null) => void;
  setResearchId: (id: string | null) => void;
  setOpenMode: (v: { g: StatusKey; m: ModeKey } | null) => void;
  setInsight: (text: string | null, err?: string | null) => void;
};

function patchVis(s: CascadeState, groups: LayerGroups, extra?: Partial<CascadeState>): Partial<CascadeState> {
  return { groups, visibility: visFromGroups(groups, s.visibility.roads, s.visibility.property, s.visibility.survey), ...extra };
}

export const useCascade = create<CascadeState>((set, get) => ({
  view: "eksplorasi",
  styleKey: "basic",
  groups: {
    existing: { ...ALL_ON },
    masterplan: { ...ALL_ON, on: false },
    cascade: { ...ALL_ON },
  },
  openGroup: { existing: false, masterplan: false, cascade: true },
  visibility: visFromGroups(
    { existing: { ...ALL_ON }, masterplan: { ...ALL_ON, on: false }, cascade: { ...ALL_ON } },
    false,
    false,
    true,
  ),
  selectedId: null,
  selectedFeature: null,
  tjFilter: "all",
  krlFilter: "all",
  lrtFilter: "all",
  mrtFilter: "all",
  mpMode: "all",
  mpStatus: "all",
  mpConf: "all",
  casFilter: "all",
  propFilters: {
    tanah: true,
    ruko: true,
    apt: true,
    murah: true,
    sedang: true,
    mahal: true,
    existing: true,
    masterplan: true,
    cascade: true,
    jual: true,
    sewa: true,
  },
  popupStatus: "cascade",
  splash: true,
  loadProgress: 0,
  mapStatus: "boot",
  overlayPhase: "basemap",
  mapError: null,
  popup: null,
  origin: null,
  destination: null,
  pickMode: "none",
  simOrigin: null,
  simDest: null,
  simNetwork: "cascade",
  simCompare: "cascade",
  simPlaying: false,
  simPaused: false,
  simResult: null,
  simPath: null,
  networkReady: false,
  identifyMode: false,
  identifyBbox: null,
  identifyHits: null,
  researchId: null,
  openMode: { g: "cascade", m: "mrt" },
  insightText: null,
  insightErr: null,
  setView: (view) => set({ view }),
  setStyle: (styleKey) => set({ styleKey }),
  toggle: (k) =>
    set((s) => {
      if (k === "candidate") return patchVis(s, { ...s.groups, cascade: { ...s.groups.cascade, on: !s.groups.cascade.on } });
      if (k === "masterplan") return patchVis(s, { ...s.groups, masterplan: { ...s.groups.masterplan, on: !s.groups.masterplan.on } });
      if (k === "krl" || k === "mrt" || k === "lrt" || k === "transjakarta") {
        return patchVis(s, { ...s.groups, existing: { ...s.groups.existing, [k]: !s.groups.existing[k] } });
      }
      if (k === "roads" || k === "property" || k === "stops" || k === "survey") {
        const visibility = { ...s.visibility, [k]: !s.visibility[k] };
        return { visibility };
      }
      return {};
    }),
  toggleGroup: (g) => set((s) => patchVis(s, { ...s.groups, [g]: { ...s.groups[g], on: !s.groups[g].on } })),
  toggleMode: (g, m) => set((s) => patchVis(s, { ...s.groups, [g]: { ...s.groups[g], [m]: !s.groups[g][m] } })),
  toggleOpenGroup: (g) => set((s) => ({ openGroup: { ...s.openGroup, [g]: !s.openGroup[g] } })),
  setSelected: (selectedId, feature) =>
    set({
      selectedId,
      selectedFeature: selectedId == null ? null : feature === undefined ? null : feature,
    }),
  setTjFilter: (tjFilter) => set({ tjFilter, selectedId: null, selectedFeature: null, popup: null }),
  setKrlFilter: (krlFilter) => set({ krlFilter, selectedId: null, selectedFeature: null, popup: null }),
  setLrtFilter: (lrtFilter) => set({ lrtFilter, selectedId: null, selectedFeature: null, popup: null }),
  setMrtFilter: (mrtFilter) => set({ mrtFilter, selectedId: null, selectedFeature: null, popup: null }),
  setMpMode: (mpMode) => set({ mpMode, selectedId: null, selectedFeature: null, popup: null }),
  setMpStatus: (mpStatus) => set({ mpStatus, selectedId: null, selectedFeature: null, popup: null }),
  setMpConf: (mpConf) => set({ mpConf, selectedId: null, selectedFeature: null, popup: null }),
  setCasFilter: (casFilter) => set({ casFilter, selectedId: null, selectedFeature: null, popup: null }),
  setPropFilter: (k, v) => set((s) => ({ propFilters: { ...s.propFilters, [k]: v } })),
  setPopupStatus: (popupStatus) => set({ popupStatus }),
  dismissSplash: () => {
    if (get().loadProgress < 100 || get().mapStatus !== "ready") return;
    set({ splash: false });
  },
  setLoadProgress: (n) => set((s) => ({ loadProgress: Math.max(s.loadProgress, Math.min(100, Math.round(n))) })),
  setMapStatus: (mapStatus, mapError = null) => set({ mapStatus, mapError }),
  setOverlayPhase: (overlayPhase) => set({ overlayPhase }),
  setPopup: (popup) => set({ popup }),
  setOrigin: (origin) => set({ origin }),
  setDest: (destination) => set({ destination }),
  setPick: (pickMode) => set({ pickMode }),
  setSimNetwork: (simNetwork) => set({ simNetwork, simCompare: simNetwork, simPlaying: false, simPaused: false }),
  setSimCompare: (simCompare) => set({ simCompare }),
  setSimPlaying: (simPlaying) => set({ simPlaying, simPaused: simPlaying ? false : get().simPaused }),
  setSimPaused: (simPaused) => set({ simPaused, simPlaying: simPaused ? false : get().simPlaying }),
  setSimPath: (simPath, simResult = null) =>
    set({ simPath, simResult, simPlaying: !!simPath?.features.length, simPaused: false }),
  setNetworkReady: (networkReady) => set({ networkReady }),
  beginSimFromStation: (node) => {
    const s = get();
    const samePoint =
      s.simOrigin &&
      Math.abs(s.simOrigin.coord[0] - node.coord[0]) < 1e-5 &&
      Math.abs(s.simOrigin.coord[1] - node.coord[1]) < 1e-5;
    if (s.pickMode === "destination" && s.simOrigin && !samePoint) {
      set({
        simDest: node,
        destination: node.coord,
        pickMode: "none",
        popup: null,
      });
      return "ready";
    }
    set({
      simOrigin: node,
      origin: node.coord,
      simDest: null,
      destination: null,
      simPath: null,
      simResult: null,
      simPlaying: false,
      simPaused: false,
      simNetwork: node.status,
      simCompare: node.status,
      pickMode: "destination",
      popup: null,
    });
    return "need-dest";
  },
  clearSim: () =>
    set({
      simOrigin: null,
      simDest: null,
      origin: null,
      destination: null,
      simPlaying: false,
      simPaused: false,
      simPath: null,
      simResult: null,
      pickMode: "none",
    }),
  setIdentifyMode: (identifyMode) => set({ identifyMode }),
  setIdentifyBbox: (identifyBbox) => set({ identifyBbox, identifyHits: null }),
  setIdentifyHits: (identifyHits) => set({ identifyHits }),
  setResearchId: (researchId) => set({ researchId }),
  setOpenMode: (openMode) => set({ openMode }),
  setInsight: (insightText, insightErr = null) => set({ insightText, insightErr }),
}));

if (typeof window !== "undefined") {
  (window as unknown as { __CASCADE?: typeof useCascade }).__CASCADE = useCascade;
}
