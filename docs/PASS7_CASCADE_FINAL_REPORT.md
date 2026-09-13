# CASCADE — FINAL VALIDATION REPORT

Tag: **CASCADE FINAL CANDIDATE**
Date: 2026-08-31

Architecture, schema, API envelope, GIS contracts, and MCDA weights are **frozen**.

Salinan dari repo aplikasi `heavenplaceidn-spec/turbo-umbra-lagoon-crystal`.

---

## RELEASE STATUS

**READY WITH DOCUMENTED LIMITATIONS**

Not READY FOR RELEASE: MAPID, official GTFS, and official masterplan GIS remain unavailable. No fabricated substitutes.

---

## PRD CONFORMANCE: PARTIAL

Core SDSS loop (map → corridor → buffer → analysis → priority → simulation → Insight) is implemented. Official datasets named in the PRD are not in the repository.

## PASS 1: PASS
## PASS 2: PASS (logical FastAPI+PostGIS; physical ADR-09 TanStack+PGLite)
## PASS 3: PARTIAL (MAPID/PostGIS/GTFS blocked; overlay cartography implemented)
## PASS 4: PASS (file-level contracts mapped onto host adapter)
## PASS 5: PASS (vertical slice, no fake Jakarta geoms)
## PASS 6: PASS (P1 code defects fixed; remaining P1 are data/API blockers)

---

## GIS STATUS: PASS (adapter) / BLOCKED (PostGIS)
Store/display EPSG:4326. Analysis EPSG:32748. Buffer 300–500 m metric. PIP in 32748. Unknown geom throws. Empty line throws. GIS tests 18/18.

## CARTOGRAPHIC STATUS: PASS with documented P2
Mode=hue, status=pattern. CASCADE casing + class encoding. Survey square, bottleneck diamond. Legend follows visibility+status. MAPID-missing banner + OSM ODbL. Popup WHAT/WHERE/STATUS/SOURCE/ACTION.

## DATABASE STATUS: PASS (frozen GeoJSON-text schema)
`migrations/0002_cascade.sql`. `candidate_corridors.created_at` present; **no `updated_at`** (frozen). No GiST. GPS accuracy not a column.

## FRONTEND STATUS: PASS
Three views, AppShell at root, Bahasa Indonesia, empty states honest.

## BACKEND STATUS: PASS (TanStack server functions)
Envelope `{ data, metadata, error }`. Structured logs with redaction.

## MAPID STATUS: BLOCKED
No keys. Empty GL style + overlay. Style switcher works on empty style.

## TRANSPORT STATUS: PARTIAL
OSM Overpass `supplemental_not_official`. Not GTFS.

## MASTERPLAN STATUS: BLOCKED_BY_DATA
Empty planning table. Dash language “acuan”. Never labeled operational.

## CASCADE STATUS: PARTIAL
PRD-named concepts stored as usulan. Geometry from network/OSRM, not LLM. Some concepts may lack LineString (`BLOCKED_BY_INFRASTRUCTURE`).

## SURVEY STATUS: PASS
Create → GPS → adjust → photo MIME/size → DB → map. Original vs adjusted preserved. E2E save passed.

## GPS STATUS: PASS
lon,lat order. 0,0 rejected. Accuracy shown at capture, **not persisted**.

## PROPERTY STATUS: BLOCKED
OSM POI proxy labeled. Property Go absent.

## BUFFER STATUS: PASS
300/400/500 m, metric, E2E profile visible.

## BOTTLENECK STATUS: PASS
Traceable to survey class; diamond mark.

## ACCESSIBILITY STATUS: PARTIAL
Network walk 5/10/15 min @ 75 m/min. Convex hull ≠ true isochrone (P2, documented).

## CLUSTERING STATUS: PASS
DBSCAN eps 300 m, minPts 4.

## HEATMAP STATUS: PASS
Density, not priority.

## MCDA STATUS: PASS
Weights 30/25/20/15/10 locked. Minmax. Regulation null → partial + renormalize. UI shows indicator, weight, normalized, contribution, raw, composite, rank, dataset_version.

## ROUTING STATUS: PARTIAL
ORS unused (no key) → OSRM. CASCADE LineString when corridor selected. Provider attributed. OD required unless corridor.

## SIMULATION STATUS: PASS
Playhead on returned geom; empty line does not teleport to Null Island.

## INSIGHT STATUS: PASS (fail-closed)
Allowlisted GIS facts. No `XAI_API_KEY` → facts returned, no invented scores. Prompt 4–500 chars.

---

## SECURITY: PASS
- Secret scan of `src/`, `docs/`, README: no live keys
- Keys only `process.env` on server; `hasSecret: false`
- Parameterized SQL
- Upload MIME/size; GPX cap
- Auth OFF: survey world-writable, non-personal (documented)
- Logs redact api_key/token/authorization/photo/data URLs
- No `Access-Control-Allow-Origin: *` API

## PERFORMANCE (measured)

| Step | Result |
|---|---|
| Document (warm) | HTTP 200, 9 ms, 7725 B |
| Full E2E path | 13.6 s (21/21) |
| Buffer 80-pt line | 15.38 ms |
| MCDA engine | 0.29 ms |
| DBSCAN n=40 | 1.4 ms |
| First Overpass | 15–40 s cold (cached after) |

Viewport tiling of all Jabodetabek roads is not implemented (P3; current payload acceptable).

## DATA QUALITY
OSM overlays validated (sane coords, types). Official GTFS/masterplan/Property Go/zoning/population **not present** — not substituted.

## DATA BLOCKERS
- Official GTFS / operator GIS (KRL, MRT, LRT, TransJakarta)
- Jakarta Satu / masterplan GIS
- Property Go, zoning, population
- PRD Outputs 1–5 files
- Two CASCADE concepts may lack network geometry

## API BLOCKERS
- MAPID_API_KEY + five style URLs
- ORS / Geoapify optional
- XAI_API_KEY for Insight prose

## INFRASTRUCTURE BLOCKERS
- PostGIS / pgRouting (host PGLite)
- Local `vite preview` + PGLite WASM historically unstable; deploy = Neon
- Backup/PITR not implemented as a product feature

---

## P0: none
## P1: none remaining in code. Data/API P1 = MAPID, official masterplan GIS, official GTFS (blocked, not faked).
## P2: accessibility hull ≠ true isochrone (documented, not faked)
## P3: no viewport-clipped road fetch; platform `npm test` template vs CASCADE title/`0002` migration; GPS accuracy not persisted (schema freeze)
## P4: host adapter comments vs FastAPI/PostGIS blueprint

## FIXES COMPLETED (this pass)
- Popup WHAT / WHERE / STATUS / SOURCE / ACTION (+ survey photo)
- MCDA contributions + norms + dataset_version in API and UI
- Structured logging with redaction
- Survey square / bottleneck diamond marks + legend
- GPS accuracy shown at capture
- Docs: README, GIS methodology, cartography, API, data dictionary, deployment, troubleshooting, env.example
- GIS tests 14 → 18 (popup, contributions, redact)
- E2E Playwright 21/21

## REGRESSION TESTS
`src/lib/cascade/gis.test.ts` **18/18 pass**. PASS 6 spatial tests still pass. `tsc --noEmit` clean. Dev server 8080 HTTP 200. Console filtered errors: 0.

## FINAL RELEASE DECISION

**READY WITH DOCUMENTED LIMITATIONS**

The system is a professional WebGIS + transport spatial-analysis platform on the host adapter. It is **not** production-authoritative until MAPID, official transport GIS/GTFS, and masterplan GIS are supplied. Insight cannot fabricate spatial facts. Schema/API/GIS contracts are frozen.

CASCADE FINAL CANDIDATE. No further speculative passes.
