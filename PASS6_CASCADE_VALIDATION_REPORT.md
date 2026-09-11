# CASCADE PASS 6 — VALIDATION REPORT

Audit of PASS 5 against PRD + PASS 1–5. No product redesign. No fabricated GIS.

**OVERALL: READY WITH LIMITATIONS**
**READY FOR PASS 7: NO** (MAPID, official masterplan GIS, and official GTFS remain BLOCKED BY DATA/API)

---

## 1. EXECUTIVE STATUS

The vertical slice is functionally, spatially (adapter), and cartographically usable on OSM-context overlays. It is **not** production-authoritative: MAPID basemap is absent, masterplan GIS is empty, transport is supplemental OSM, property/zoning/population are missing. No P0. P1 implementation bugs found in this pass were fixed. Remaining P1s are data/API blockers, not code defects.

## 2. BUGS FOUND → FIXED

| ID | Sev | Issue | Root cause | Fix | Regression |
|---|---|---|---|---|---|
| B1 | P1 | Map destroyed on Eksplorasi↔Simulasi↔Analisis | Each route remounted `AppShell` | Lift `AppShell` to root `Outlet` | Visual: camera/overlays persist across views |
| B2 | P1 | Unknown geom buffered as a fake Jakarta point | `bufferGeometryM` fallback | Throw `unsupported_geometry` | gis.test “unknown geometry…” |
| B3 | P1 | Empty line `pointAlong` returned `[0,0]` | Sentinel Null Island | Throw `empty_line`; playhead catch | gis.test “rejects 0,0…” |
| B4 | P1 | Search hit Nominatim every keystroke | No debounce | 400 ms debounce + 60s stale | code |
| B5 | P1 | Simulasi routed Jakarta defaults without picks | Silent OD fallback | Require origin+dest unless corridor selected; server rejects <25 m | code |
| B6 | P2 | Buffer intersection tested in 4326 plane | PIP on lng/lat | PIP in EPSG:32748 | gis.test “400m buffer membership…” |
| B7 | P2 | Legend omitted analysis layers / ignored status filter | Incomplete legend | Legend tracks vis + status; labels “usulan/acuan” | visual |
| B8 | P2 | CASCADE `recommendation_class` not encoded | Single solid style | Refine dash `[4,2]`; new_corridor double casing; rank-1 width | visual |
| B9 | P2 | GPS/photo/GPX failed silently | No error UX / no GPX size cap | Messages + MIME/size; server GPX 1.5 MB + sane coords | code |
| B10 | P2 | Survey category / insane coords accepted | Weak validator | Allowlist + `isSaneLngLat` + bbox flag | code |
| B11 | P2 | Insight unbounded prompt | No cap | 500-char slice, min 4 | code |
| B12 | P3 | Station labels missing when MAPID empty | Empty GL style had no glyphs | Overlay glyphs + stops-label z≥12 | visual |
| B13 | P3 | MCDA 3-decimal false precision | `toFixed(3)` | `toFixed(2)` | visual |

## 3. REQUIREMENT MATRIX (abbrev.)

Status: PASS / PARTIAL / FAIL / BLOCKED

| REQ | Source | Requirement | Impl | Status | Evidence |
|---|---|---|---|---|---|
| R1 | PRD/P3 | MAPID primary basemap, never Google | `getMapSession` | **BLOCKED** | no keys; empty GL style; banner honest |
| R2 | PRD | Existing ⟂ Masterplan ⟂ CASCADE | independent sources/layers | **PASS** | filters + compare overlay/swipe/split |
| R3 | PRD | Roads ≠ PT corridors | `road_edges` vs `transport_routes` | **PASS** | |
| R4 | PRD | Survey = raw evidence | form + original GPS | **PASS** | original preserved; adjusted separate |
| R5 | PRD | Insight ≠ GIS engine | allowlisted facts → grok-4.5 | **PASS** | verified insufficient-evidence |
| R6 | P3 | Metric buffer 300–500 m EPSG:32748 | `buffer.ts` | **PASS** | tests 3,4,5,6,13 |
| R7 | P3 | MCDA 30/25/20/15/10 minmax | `mcda.ts` | **PASS** | tests 7,8; UI |
| R8 | P3 | Routing ORS→OSRM; CASCADE geom for transit | `routePath` | **PARTIAL** | ORS unused (no key); OSRM + CASCADE LineString |
| R9 | P3 | Network accessibility not Euclidean | graph reachable + hull | **PARTIAL** | network walk; hull ≠ true isochrone polygon |
| R10 | P3 | DBSCAN 300 m / minPts 4 | `dbscan.ts` | **PASS** | test 9 |
| R11 | P3 | Heatmap ≠ DBSCAN | separate sources | **PASS** | |
| R12 | P3 | Mode=hue, status=pattern | carto + layers | **PASS** | existing solid, MP [8,4], refine [4,2] |
| R13 | P3 | Recommendation classes | properties + paint | **PASS** | |
| R14 | L3 | Official GTFS KRL/MRT/LRT/TJ | OSM Overpass | **BLOCKED** | `supplemental_not_official` |
| R15 | L3 | Masterplan GIS | placeholder row | **BLOCKED** | `BLOCKED_BY_DATA` |
| R16 | L3 | Property Go | OSM POI proxy | **BLOCKED** | labeled note |
| R17 | P3 | PostGIS GiST / ST_Buffer | PGLite GeoJSON-text | **BLOCKED** | host ADR-09; TS 32748 adapter |
| R18 | P3 | Survey 0,0 reject | `isSaneLngLat` | **PASS** | |
| R19 | P4 | Envelope API | `envelope.ts` | **PASS** | |
| R20 | P5 | Three views BI | routes + panels | **PASS** | |
| R21 | P6 | Map persists across views | root AppShell | **PASS** | p6-simulasi no splash remount |
| R22 | P3 | Stop labels z≥12 | `stops-label` | **PARTIAL** | overlay glyphs; MAPID glyphs untested |
| R23 | P6 | Legend = visible layers | Legend() | **PASS** | |
| R24 | P3 | Corridor LineString native | `candidate_corridors.geom_json` | **PARTIAL** | 6/8 have geom; 2 BLOCKED_BY_INFRASTRUCTURE |
| R25 | Security | No secrets in source | scan | **PASS** | env-only names |
| R26 | Security | Parameterized SQL | tagged `sql` | **PASS** | |
| R27 | Security | Upload MIME/size | photo+GPX | **PASS** | |
| R28 | Perf | No infinite retry | timeout 8–24s | **PASS** | |
| R29 | P3 | Viewport bbox fetch | full overlay load | **PARTIAL** | small post-prune payload; no moveend bbox |
| R30 | A11y | Keyboard / contrast / non-color | nav+width+dash | **PARTIAL** | filters keyboard; map canvas pointer |

## 4. GIS AUDIT

| Topic | Result |
|---|---|
| CRS | Store/display 4326; analysis 32748 via proj4. Roundtrip <1e-6°. |
| Buffer | Metric; area ≈ πr² (ratio 0.85–1.15); radius clamp 300–500. |
| Intersection | Now 32748 PIP. 200 m inside / 520 m outside of 400 m buffer. |
| Network | Dijkstra on OSM roads; length 1–5 km on 3-node test. |
| Accessibility | 5/10/15 min @ 75 m/min; convex hull of reachable nodes. |
| Service gap | POI outside 15 min hull. Population **BLOCKED**. |
| DBSCAN | eps 300 m, minPts 4; noise=0. |
| MCDA | Weights sum 1; deterministic; regulation null → partial=true. |
| Routing | Invalid/same-point rejected; CASCADE uses stored LineString. |
| Geometry validity | Ingest drops 0,0 / non-finite; unknown buffer types throw. |
| Spatial index | **N/A** — no PostGIS. B-tree on mode columns only. |

Measured: line buffer 80 vertices **15.3 ms**; DBSCAN n=40 **1.5 ms**; MCDA **0.24 ms**; 0.01° lon in Jakarta **1107 m**.

## 5. CARTOGRAPHIC AUDIT

- Hierarchy: roads → existing PT (solid, width by mode) → masterplan dash [8,4] → CASCADE casing + class encoding → buffer/analysis → evidence → selection.
- CASCADE labeled **usulan**; masterplan **acuan**. Does not share solid-without-casing with existing.
- Scale: stops z≥11, labels z≥12, POI z≥13, zoom 8–18.
- Legend follows visibility + status filter.
- Attribution: MAPID-missing banner + OSM ODbL.
- Two PRD corridors remain empty (honest `geom kosong`).

## 6. SECURITY

- No live keys in src, docs, README, screenshots.
- Server-only `process.env` for MAPID/ORS/XAI.
- SQL parameterized.
- Photo MIME allowlist + size; GPX size + sane coords; filename sanitized.
- Same-origin app; no `Access-Control-Allow-Origin: *` API.
- Auth off: survey world-writable (documented; not personal data).

## 7. PERFORMANCE

| Step | Result |
|---|---|
| Dev document | 200, ~2 s to splash |
| GIS buffer 80-pt | 15.3 ms |
| Corridor+buffer UI | ~1.2 s (POI join in TS) |
| MCDA UI | previously 8 s (POI×corridor); engine 0.24 ms |
| First Overpass ingest | 15–40 s (cold); then skipped |
| Console | 0 errors (smoke + interactive) |

## 8. DATA / API BLOCKERS

- MAPID_API_KEY + five style URLs
- Official GTFS / operator GIS
- Jakarta Satu / masterplan GIS
- Property Go, zoning, population
- ORS / Geoapify (optional; OSRM/Nominatim used)
- PostGIS/pgRouting (host PGLite)
- PRD Outputs 1–5 files

## 9. REMAINING TECHNICAL ISSUES (real)

- Accessibility hull is a simplification of a true network isochrone (P2, documented)
- Full-road GeoJSON not viewport-clipped (P3)
- Survey/bottleneck symbols are circles, not square/diamond (P3)
- Two CASCADE concepts lack network geometry (data, not fake)
- Local `vite preview` + PGLite WASM historically unstable; deploy path is Neon
- Platform `npm test` template assertions vs extra `0002` migration / CASCADE title (not GIS)

## 10. FINAL GATE vs §90

| Gate | Met? |
|---|---|
| no unresolved P0 | YES |
| no unresolved **code** P1 | YES |
| core map works | YES (overlay; MAPID blocked) |
| MAPID works | **NO** — keys absent |
| transport works | PARTIAL — OSM supplemental |
| Masterplan works | **NO** — BLOCKED_BY_DATA |
| CASCADE works | PARTIAL — 6/8 geoms |
| Survey works | YES |
| GIS analysis works | YES (adapter) |
| priority works | YES |
| routing works | YES (OSRM/CASCADE) |
| Insight grounding | YES |
| security | YES |
| cartographic QA | YES with listed P3 |

Therefore **NOT READY FOR PASS 7**.
