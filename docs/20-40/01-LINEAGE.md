# 01 — Lineage (`public/data/sources.json`)

| Dataset | Tipe | n | Lisensi / catatan |
|---|---|---:|---|
| `transjakarta_routes` | official | 14 | BRT koridor 1–14 existing. Satu geometri per koridor. Bukan usulan CASCADE. |
| `transjakarta_stops` | official | 255 | Hanya halte koridor BRT, difilter spasial <150 m dari jaringan 1–14. |
| `transjakarta_segments` | official | 207 | Jakarta Satu / Jaklingko Rute_TJ FeatureServer |
| `roads` | osm | 310 | Konteks jalan abu-abu. Bukan jaringan TransJakarta. |
| `krl_routes` | osm | 6 | Jaringan fisik KRL existing. Warna CASCADE #D83A72. OSM rel, bukan data resmi KAI. |
| `krl_stops` | osm | 83 | Stasiun KRL existing sesuai struktur Bogor/Nambo/Rangkasbitung/Cikarang/Tangerang/Tanjung Priok. Satu titik per stasiun. |
| `mrt_routes` | osm | 1 | MRT Jakarta Fase 1 Lebak Bulus–Bundaran HI. Warna #247A67. Bukan data resmi MRTJ. Fase 2 tidak termasuk. |
| `mrt_stops` | osm | 13 | 13 stasiun existing. Nama inti tanpa sponsor. Satu titik per stasiun. |
| `lrt_routes` | osm | 2 | LRT Jabodebek existing. 2 branch + 1 shared trunk. Warna #4FAF86. Bukan LRT Jakarta. OSM, bukan data resmi operator. |
| `lrt_stops` | osm | 18 | 18 stasiun unik. Cawang merge. Shared trunk tidak diduplikasi. |
| `cascade_candidates` | AI_RECONSTRUCTED | 20 | CAS-TJ01..11 + CAS-LRT + CAS-MRT + KRL-C03-N/S + KRL-C04. KRL CASCADE = trase user GeoJSON, stasiun desa per 2 km, Dramaga IPB wajib. |
| `cascade_stops` | AI_RECONSTRUCTED | 410 | Halte/stasiun usulan. Nama desa setempat. Bukan stasiun resmi. |
| `masterplan` | AI_RECONSTRUCTED | 14 | Layer acuan masterplan #E58A3A. Bukan existing, bukan usulan CASCADE, bukan DED. |
| `masterplan_stations` | AI_RECONSTRUCTED | 107 | Terminus dan interchange diekspor sebagai titik stasiun. Nama indikatif ditandai is_indicative. |

## Aturan status

- `official` / existing TransJakarta = **operasi**. Bukan usulan.
- `osm` = **existing fisik**, ODbL, **bukan** GTFS operator.
- `AI_RECONSTRUCTED` + usulan CASCADE = **PROPOSED**. Bukan DED.
- Masterplan = **acuan perencanaan**. Bukan existing, bukan CASCADE.

CRS simpan/tampil: **EPSG:4326** (`lng,lat`).
