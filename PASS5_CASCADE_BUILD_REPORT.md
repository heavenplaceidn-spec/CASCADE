# CASCADE PASS 5 — BUILD REPORT

Host adapter (ADR-09): TanStack Start + PGLite GeoJSON-text implements PASS 4 contracts. Logical stack remains React + FastAPI + PostGIS. Metric ops run in TypeScript EPSG:32748 because PGLite cannot load PostGIS.

Do not start PASS 6 until the owner sends PASS 6.

---

## STATUS

**COMPLETE WITH BLOCKERS.** Vertical slices 1–5 run in the live preview. Official GIS files, MAPID keys, and property/zoning/population dumps remain absent and are labeled empty — never fabricated.

## BUILT

- MapLibre canvas, independent KRL / MRT / LRT / TransJakarta overlays
- CASCADE proposal corridors (PRD-named, network/OSRM aligned, provenance `prd_concept`)
- Survey create + original GPS preserved + photo MIME/size validation + popup
- GPX track ingest
- Metric buffer 300 / 400 / 500 m in EPSG:32748
- MCDA weights 30 / 25 / 20 / 15 / 10, minmax, regulation-null renormalize
- Routing ORS → OSRM, CASCADE geom when a corridor is selected
- Simulation along-line playback
- Insight (grok-4.5) grounded on allowlisted GIS facts, fail-closed
- Compare overlay / swipe / side-by-side
- Heatmap, network walk isochrone 5/10/15 min @ 75 m/min, service gap (POI outside 15 min), DBSCAN
- Search (internal + Nominatim), stacked filters, legend, popups
- Honest empty states (`BLOCKED_BY_DATA`, `PROVIDER_UNAVAILABLE`, `geom kosong`)

## PARTIAL

- Masterplan layer exists as a placeholder row (`empty_reason = BLOCKED_BY_DATA`)
- Property profile uses OSM POI as labeled proxy (not Go dump)
- Two PRD corridors still lack network geometry (Nambo–Parung Panjang, Harjamukti–Mekarsari)
- Local production preview (`vite preview`) is unstable with PGLite WASM assets; deploy path is Neon `DATABASE_URL`
- Unnamed OSM heavy-rail ways are pruned for cartography; named routes + stations remain

## BLOCKED

- MAPID basemap (no `MAPID_API_KEY` / style URLs) — dark empty canvas + overlays
- Official GTFS / operator KRL, MRT, LRT, TransJakarta
- Jakarta Satu / official masterplan GIS
- Property Go dump, zoning, population rasters
- ORS / Geoapify keys (ORS skipped; OSRM + Nominatim + Overpass used)
- PostGIS / pgRouting (host has PGLite)

---

## FRONTEND

TanStack Start, three views (`/` Eksplorasi, `/simulasi`, `/analisis`), Bahasa Indonesia chrome, MapLibre, zustand, layer panel, splash, survey form, MCDA + Insight panel. MAPID style switcher is wired; without keys it no-ops honestly.

## BACKEND

Server functions in `src/lib/cascade/functions.ts` (envelope `{ data, metadata, error }`). No FastAPI process on this host. Auth off; survey rows unowned (world-writable demo).

## DATABASE

`migrations/0002_cascade.sql` — GeoJSON text columns, dataset lineage (`data_sources`), MCDA tables, survey original vs adjusted GPS, photos, GPS tracks, buffers, insight results, geocode cache.

## GIS

`buffer.ts` / `graph.ts` / `dbscan.ts` / `mcda.ts` / `crs.ts` (EPSG:32748). Ingest Overpass roads + named rails + TJ relations + POI; proposals via Dijkstra on road graph then OSRM.

## MAPID

Interface implemented. Runtime: `mapid_unavailable` empty GL style. Never replaced with Google or OSM raster as the primary basemap.

## TRANSPORT

Independent mode layers. Source `osm_overpass`, quality `supplemental_not_official`. Unnamed `OSM krl N` ways pruned so the map is readable.

## MASTERPLAN

Schema + dashed cartography + empty placeholder. **BLOCKED_BY_DATA.**

## CASCADE

Eight PRD concepts stored. Six have network/OSRM geometry marked proposal, not operational. Two remain `geom kosong` / `BLOCKED_BY_INFRASTRUCTURE`.

## SURVEY

Form: category, description, GPS, map point, optional adjusted point, photo, GPX. Original GPS is never overwritten.

## GPS

GPX parser (lat/lon attribute orders), LINESTRING store, dashed overlay. Distinct from route simulation.

## PROPERTY

Intersection against OSM POI inside metric buffer. Official Go property: **BLOCKED.**

## BUFFER

300–500 m only; active distance shown; polygon persisted in `corridor_buffers`.

## BOTTLENECK

Created from survey category `kemacetan`; mapped by severity. Empty until field evidence exists.

## ACCESSIBILITY

Network walk graph, convex-hull isochrones, not Euclidean circles.

## MCDA

Locked weights, stored run + scores + rank. Regulation null when zoning absent.

## ROUTING

Backend abstraction. ORS if keyed, else OSRM. CASCADE scenario uses candidate LineString, not driving-car as fake MRT.

## SIMULATION

Playhead along returned geometry (8 s loop). Defaults origin/destination only if the user has not picked points — still a real route, not a straight fake line.

## INSIGHT

Intent → GIS facts JSON → grok-4.5 with “do not invent coordinates/scores”. Verified: admits congestion evidence is insufficient; cites ranking from accessibility/demand proxies.

---

## TESTS

| Suite | Result |
|---|---|
| GIS (`src/lib/cascade/gis.test.ts`) | **11/11 pass** (CRS, metric distance, point/line buffer area, 300–500 reject, intersects, MCDA deterministic + null regulation, DBSCAN, pointAlong, network Dijkstra) |
| `tsc --noEmit` | pass |
| `npm run build` | pass |
| Dev smoke 1280×800 + 390×844 | pass, 0 console/page errors |
| Interactive: splash, explore, corridor+buffer, survey form, MCDA names, Insight, route enable | pass |
| `npm test` (platform scripts) | 9 template failures (PWA injector title CASCADE; `0002_cascade.sql` present vs empty-migrations assertion) — not GIS regressions |
| Local `vite preview` :8081 | fail (PGLite WASM path in nitro bundle) |

## CARTOGRAPHIC QA

- Mode = hue (KRL navy, MRT gold, LRT teal, TJ red); status = dash (masterplan [8,4])
- CASCADE casing + mode stroke; selected highlight
- After pruning unnamed rails, existing transport is a readable figure against road context
- Legend tracks visible layers
- MAPID-missing banner + OSM ODbL attribution
- Zoom 8–18; stops from z11; POI from z13
- Swipe / side-by-side implemented; overlay default

## SECURITY

- No secrets in source, README, or API responses
- `docs/env.example` placeholders only; no `.env` committed
- MAPID / ORS / xAI keys read server-side only
- `XAI_API_KEY` used only on user-initiated Insight
- Survey photo MIME + size checked before insert
- 0,0 coordinates rejected

## PERFORMANCE

- First Overpass ingest 15–40 s (splash + “Mengimpor jaringan OSM…”)
- Catalog polling stops once roads/candidates exist (was hammering Overpass every 8 s — fixed)
- Geocode cache short-circuits Overpass when ≥12 named places cached
- Proposal generation skipped when all PRD corridors already have geometry
- MapLibre GeoJSON sources, not DOM markers
- Client MapLibre chunk ~989 kB gzip 257 kB — acceptable for a WebGIS

---

## REMAINING DATA

1. Official GTFS / shapefiles: KRL, MRT Jakarta, LRT Jabodebek, TransJakarta
2. Masterplan GIS (Jakarta Satu / RTRW / official corridor plans)
3. Property Go dump
4. Zoning / land use
5. Population (kelurahan or grid)
6. Outputs 1–5 from the PRD (absent)

## REMAINING API

1. `MAPID_API_KEY` + five style URLs
2. `ORS_API_KEY` (optional; OSRM fallback live)
3. `GEOAPIFY_API_KEY` (optional; Nominatim + Overpass live)
4. Deploy `DATABASE_URL` (Neon) for production PostGIS-less Postgres

## REMAINING GIS PROCESSING

1. Align remaining two empty corridors once named places resolve (Nambo, Mekarsari)
2. Swap TS buffer/isochrone for `ST_Transform` + `ST_Buffer` + pgRouting when PostGIS is available
3. Official masterplan overlay ingest
4. Population catchment / service-gap with census, not POI proxy

---

## CRITICAL ISSUES

1. **MAPID absent** — map is overlay-on-empty, not a full basemap product.
2. **No official transport/masterplan GIS** — OSM is supplemental and labeled as such.
3. **PGLite ≠ PostGIS** — spatial engine is TypeScript 32748; production with Neon still has no PostGIS unless the owner provisions it.
4. **Survey is public unowned** because auth is off (host rule). Do not store sensitive field photos in this mode.
5. **Two CASCADE concepts have no geometry** — UI shows `geom kosong`, not fake lines.

## PASS 5 STATUS

**COMPLETE WITH BLOCKERS**

## READY FOR VALIDATION

**YES** — live preview runs the five vertical slices; blockers are explicit empty states, not fake GIS.

## PASS 6

Do not start until the owner sends PASS 6.
