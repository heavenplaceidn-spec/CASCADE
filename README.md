# CASCADE WebGIS

Repo **publik** dokumen project CASCADE.
Akun konektor GitHub: [heavenplaceidn-spec](https://github.com/heavenplaceidn-spec).

## Repo

| Isi | Repo | Visibilitas |
|---|---|---|
| Dokumen project (ini) | https://github.com/heavenplaceidn-spec/CASCADE | publik |
| Salinan dokumen | https://github.com/heavenplaceidn-spec/cascade-webgis | privat |
| Source aplikasi (TanStack Start + PGLite + MapLibre) | https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal | privat |

Repo privat mengembalikan **404** jika browser tidak login sebagai `heavenplaceidn-spec`. Itu bukan repo hilang.

## Cara clone source aplikasi

```bash
# login dulu sebagai heavenplaceidn-spec
git clone https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal.git cascade
cd cascade
```

## Dokumen di repo ini

- [PROJECT_STATE.md](./PROJECT_STATE.md)
- [PASS5_CASCADE_BUILD_REPORT.md](./PASS5_CASCADE_BUILD_REPORT.md)
- [PASS6_CASCADE_VALIDATION_REPORT.md](./PASS6_CASCADE_VALIDATION_REPORT.md)
- PASS 1–4 (system comprehension, architecture, GIS spec, build blueprint) menyusul di commit berikutnya jika belum ada di tree.

## Stack host (ADR-09)

TanStack Start + PGLite GeoJSON-text + MapLibre. Logical stack tetap React + FastAPI + PostGIS — jangan mengarang GTFS resmi / MAPID / masterplan GIS.

## Status singkat

- PASS 6: audit + hardening. GIS tests 14/14 di folder Grok; di repo app PASS 7: GIS 18/18, E2E 21/21.
- Blocked: kunci MAPID, GTFS resmi, Jakarta Satu masterplan, Property Go / zoning / population, PostGIS / pgRouting.
