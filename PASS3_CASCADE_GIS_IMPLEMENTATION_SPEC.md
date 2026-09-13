# CASCADE PASS 3 — GIS IMPLEMENTATION SPECIFICATION
GIS implementation bible. Status: COMPLETED.

Berkas lengkap (28 KB) ada di folder Grok artifacts. Kontrak yang diikat ke GitHub:

## CRS
Simpan/tampil EPSG:4326. Analisis EPSG:32748 (UTM 48S).
Buffer wajib `ST_Transform` → `ST_Buffer(meter)` → kembali 4326. Di host adapter: `src/lib/cascade/crs.ts` + `buffer.ts`.

## Non-negotiable
MAPID primer. Existing ⟂ Masterplan ⟂ CASCADE. Jalan ≠ PT. Survei mentah. Insight bukan GIS. Tidak ada buffer derajat. Tidak ada geom fiktif.

## Engines
Buffer, interchange (bukan crossing garis saja), masterplan force-status, candidate ≤3 alt, property intersect, survey/GPS, geocode Nominatim→Geoapify, routing ORS→OSRM, accessibility jaringan (bukan lingkaran), service gap, bottleneck, DBSCAN 300 m/4, heatmap ≠ cluster, MCDA, comparison overlay/swipe/split, popup WHAT/WHERE/STATUS/SOURCE/ACTION.

## Next
PASS 4 blueprint. Implementasi ada di repo source `turbo-umbra-lagoon-crystal`.
