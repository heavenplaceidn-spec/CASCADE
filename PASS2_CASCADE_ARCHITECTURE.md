# CASCADE PASS 2 — ARCHITECTURE
Status: COMPLETED.

Berkas lengkap (54 KB) ada di folder Grok artifacts. Ringkasan yang diikat ke GitHub:

## Logical stack
React + FastAPI + PostGIS + MapLibre + MAPID GL styles.

## Physical host adapter (ADR-09)
TanStack Start + PGLite GeoJSON-text + MapLibre.
Operasi metrik di TypeScript EPSG:32748 karena PGLite tidak memuat PostGIS.

## ADR kunci
- Envelope API `{ data, metadata, error }`
- Isolasi provider (MAPID/ORS/Nominatim/Insight) di server
- Empat moda independen (KRL/MRT/LRT/TJ)
- MCDA bobot 30/25/20/15/10
- Buffer 300–500 m metrik

## Next
PASS 3 GIS bible. Lihat [PASS3_CASCADE_GIS_IMPLEMENTATION_SPEC.md](./PASS3_CASCADE_GIS_IMPLEMENTATION_SPEC.md).
