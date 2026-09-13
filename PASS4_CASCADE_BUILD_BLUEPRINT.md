# CASCADE PASS 4 — FILE-LEVEL IMPLEMENTATION BLUEPRINT
Status: COMPLETED. Blueprint only.

Berkas lengkap (32 KB) ada di folder Grok artifacts. Yang diikat ke GitHub:

## Logical tree
`frontend/` (Next.js/React + MapLibre) + `backend/` (FastAPI) + `database/` (PostGIS) + `gis/`.

## Host mapping (PASS 5+)
Kontrak yang sama di TanStack Start:
- `src/lib/cascade/functions.ts` — server functions / envelope
- `src/lib/cascade/{crs,buffer,graph,dbscan,mcda,ingest,popup}.ts`
- `migrations/0002_cascade.sql`
- tiga view: `/` Eksplorasi, `/simulasi`, `/analisis`
- AppShell di root agar peta persist

## Jangan
GTFS URL karangan, koridor palsu, kunci di frontend, `turf.buffer` derajat, ORS driving sebagai MRT.

## Next
PASS 5 build report + PASS 7 final di `docs/PASS7_CASCADE_FINAL_REPORT.md`.
