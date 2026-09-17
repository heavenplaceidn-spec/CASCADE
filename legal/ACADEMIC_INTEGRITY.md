# Academic integrity

This repository is the **workspace export of the CASCADE WebGIS**
(Geo Unjuk Kebolehan). It is original project work plus **cited** third-party
data. It is **not** an official BPTJ / Dishub / operator plan.

## Original (ours)

- `src/features/` — map-first UI: splash, eksplorasi, simulasi, analisis
- `src/lib/cascade/` — cartography, graph, SDSS, survey, property, animation
- `src/routes/` — three views + property/survey/MAPID proxy APIs
- `scripts/rebuild-cascade-*.py`, `scripts/p-*-verify.mjs` — rebuild + QA
- `public/data/cascade*` — usulan CASCADE (trase user GeoJSON, labeled PROPOSED)
- `screenshots/` — visual QA of this app
- Brand: `public/cascade-mark.png`, landing/hero

## Cited, not invented as official

| Asset | Source | How labeled |
|---|---|---|
| Assignment PRD PDF | Geo Unjuk Kebolehan / Departemen Geografi UI | L1 spec — not our paper |
| TransJakarta routes/stops | Jakarta Satu FeatureServer | `source_type: official` in `public/data/sources.json` |
| KRL / MRT / LRT existing | OpenStreetMap | ODbL; `supplemental` / OSM notes |
| Roads | OSM motorway/trunk/primary | ODbL, context only |
| MAPID | vendor basemap | key **not** in git; proxy `/api/mapid` |
| TanStack / MapLibre / PGLite | OSS host | ADR-09 host adapter |

## Forbidden (we do not do this)

- Claim OSM or Jakarta Satu geometries as operator GTFS we surveyed
- Paste another student's repo as ours
- Commit API keys
- Let an LLM silently rewrite corridor LineStrings as “official”
- Call CASCADE lines **existing**

Every CASCADE candidate in `cascade_existing.json` carries `status: PROPOSED`
or `CASCADE_PROPOSED` / `CASCADE_EXTENSION`.
