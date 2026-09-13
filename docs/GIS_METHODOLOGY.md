# CASCADE — GIS methodology (frozen)

Salinan dari repo aplikasi. Authoritative methods: PRD + PASS 3. This file records what the code actually does.

## CRS

| Role | CRS | Notes |
|---|---|---|
| Data / store | EPSG:4326 | GeoJSON `lon, lat`. Column `source_crs` / `geom_json`. |
| Display | EPSG:4326 | MapLibre |
| Analysis | EPSG:32748 | UTM 48S via proj4 (`src/lib/cascade/crs.ts`) |

Round-trip 4326→32748→4326 stays within 1e-6°. A 0.01° longitude step in Jakarta is ~1107 m. `isSaneLngLat` rejects `0,0`. Working bbox is Jabodetabek.

PostGIS production must use `ST_Transform(geom, 32748)`. Host adapter: TypeScript because PGLite has no PostGIS.

## Geometry rules

- Point (stops, survey, POI, bottleneck), LineString (routes, corridors, GPS), Polygon (buffer, hull).
- Empty LineString interpolation throws `empty_line` (never Null Island).
- Unknown buffer geometry throws `unsupported_geometry` (never a fake Jakarta point).
- Ingest drops non-finite / 0,0 coordinates.

## Provenance

```
SOURCE → VERSION → PROCESSING → PARAMETERS → ANALYSIS → RESULT
```

## Transport / Masterplan / CASCADE

- Existing PT: OSM Overpass, `supplemental_not_official`. Not official GTFS. Roads never merged into PT corridors.
- Masterplan: empty until official GIS imported. Dash `[8,4]`, label “acuan”.
- CASCADE: PRD concepts; geometry from graph/OSRM, never LLM-drawn. Classes: existing_extension / masterplan_refinement / new_corridor. Schema freeze: `created_at`, no `updated_at`.

## Buffer / accessibility / MCDA

- Buffer 300/400/500 m in EPSG:32748. PIP in 32748.
- Walk network 5/10/15 min @ 75 m/min; convex hull of reachable nodes (not true isochrone).
- DBSCAN eps 300 m, minPts 4.
- MCDA weights 30/25/20/15/10 locked. Minmax. Null regulation → partial + renormalize.

## Routing / Insight / Survey

- ORS → OSRM. Transit sim uses CASCADE LineString.
- Insight: allowlisted GIS facts; fail-closed without XAI key.
- Survey: original GPS preserved; accuracy shown, not persisted.
