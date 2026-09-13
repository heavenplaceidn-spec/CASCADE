# CASCADE WebGIS

Repo **publik** dokumen project CASCADE (semua PASS + peta tautan source).

WebGIS Spatial Decision Support System untuk prioritas koridor angkutan massal Jabodetabek.
CASCADE **bukan otoritas rencana resmi**.

Tag implementasi: **CASCADE FINAL CANDIDATE** (PASS 7).
Status rilis: **READY WITH DOCUMENTED LIMITATIONS**.

## Peta repo

| Isi | Repo | Visibilitas |
|---|---|---|
| Dokumen PASS 1–7 (repo ini) | https://github.com/heavenplaceidn-spec/CASCADE | publik — bisa dibuka akun Arckzz |
| Salinan dokumen | https://github.com/heavenplaceidn-spec/cascade-webgis | privat |
| Source aplikasi (TanStack Start + PGLite + MapLibre) | https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal | privat |
| Akun pemilik harian | https://github.com/Arckzz | — |

Repo privat mengembalikan **404** jika browser tidak login sebagai `heavenplaceidn-spec` atau belum diundang sebagai kolaborator.

## Semua PASS

| Pass | File | Isi |
|---|---|---|
| State | [PROJECT_STATE.md](./PROJECT_STATE.md) | peta repo + status beku |
| 1 | [PASS1_CASCADE_SYSTEM_COMPREHENSION.md](./PASS1_CASCADE_SYSTEM_COMPREHENSION.md) | ingest PRD + pemahaman sistem |
| 2 | [PASS2_CASCADE_ARCHITECTURE.md](./PASS2_CASCADE_ARCHITECTURE.md) | arsitektur + ADR |
| 3 | [PASS3_CASCADE_GIS_IMPLEMENTATION_SPEC.md](./PASS3_CASCADE_GIS_IMPLEMENTATION_SPEC.md) | spesifikasi GIS |
| 4 | [PASS4_CASCADE_BUILD_BLUEPRINT.md](./PASS4_CASCADE_BUILD_BLUEPRINT.md) | blueprint file-level |
| 5 | [PASS5_CASCADE_BUILD_REPORT.md](./PASS5_CASCADE_BUILD_REPORT.md) | laporan build |
| 6 | [PASS6_CASCADE_VALIDATION_REPORT.md](./PASS6_CASCADE_VALIDATION_REPORT.md) | audit + validasi |
| 7 | [docs/PASS7_CASCADE_FINAL_REPORT.md](./docs/PASS7_CASCADE_FINAL_REPORT.md) | kandidat final |

Dokumen aplikasi tambahan (GIS methodology, kartografi, API, deploy) ada di repo source:
https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal/tree/main/docs

## Clone dokumen (akun Arckzz boleh)

```bash
git clone https://github.com/heavenplaceidn-spec/CASCADE.git
cd CASCADE
```

## Clone source aplikasi (perlu akses privat)

```bash
git clone https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal.git cascade
cd cascade
npm install
npm run dev
```

## Stack host (ADR-09)

TanStack Start + PGLite GeoJSON-text + MapLibre.
Logical stack tetap React + FastAPI + PostGIS — jangan mengarang GTFS resmi / MAPID / masterplan GIS.

## Status singkat

- PASS 6: GIS tests 14/14 di folder Grok.
- PASS 7 di repo app: GIS 18/18, E2E 21/21.
- Blocked: kunci MAPID, GTFS resmi, Jakarta Satu masterplan, Property Go / zoning / population, PostGIS / pgRouting.
