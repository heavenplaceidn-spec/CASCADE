# 03 — Attachments → rebuild → `public/data`

Trase digambar user (GeoJSON) di `attachments/`. Script `scripts/rebuild-*.py` dan `add-*.py` menuliskan hasil ke `public/data/`.

| Attachment (zip) | Script | Keluaran |
|---|---|---|
| `CASTJ15_Petojo-Pulogebang Via BKT.geojson` | `rebuild-cascade-tj-cas15-21.py` | CASTJ15 |
| `CASTJ16_Pinang Ranti -Lebak Bulus via Pasar Rebo.geojson` | same | CASTJ16 |
| `CASTJ17_… Marunda Center.geojson` | same | CASTJ17 |
| `CASTJ18_… Tanjung Priok.geojson` | same | CASTJ18 |
| `CASTJ19_UI-Galunggung Via Pasar Minggu.geojson` | same | CASTJ19 |
| `KORIDOR 20 … & KORIDOR 21 ….geojson` | `patch-castj20.py` / cas15-21 | CASTJ20, CASTJ21 |
| `CASTJ22_SAWANGAN-BLOK M….geojson` | `add-castj22-26.py` | CASTJ22 |
| `CASTJ23_PONDOK LABU - KALIDERES….geojson` | same | CASTJ23 |
| `CASTJ24_CBD CILEDUG - MONAS….geojson` | same | CASTJ24 |
| `CASTJ25_PURI BETA - MONAS….geojson` | same | CASTJ25 |
| `CASTJ26_KOJA - CENGKARENG….geojson` | same | CASTJ26 |
| `CASTJ07_PERPANJANGAN KORIDOR 7….geojson` | `rebuild-cascade-tj06-07.py` | CASTJ07-EXT |
| `PERPANJANGAN KORIDOR 2 ARAH HARAPAN INDAH.geojson` | `add-castj-ext-2-3-14.py` | CASTJ02-EXT |
| `PERPANJANGAN KORIDOR 3 ARAH BANDARA 3B.geojson` | same | CASTJ03-EXT |
| `PERPANJANGAN KORIDOR 14 JIS-MARUNDA….geojson` | same | CASTJ14-EXT |
| `KRL_TANGERANG_ARAH_UTARA_VIA_MAUK.geojson` | `rebuild-cascade-krl-user.py` | KRL-C03-N |
| `KRL_TANGERANG_ARAH_SELATAN_VIA_BITUNG.geojson` | same | KRL-C03-S |
| `KRL_SENTUL_JASINGA_MAJA.geojson` | same | KRL-C04 (Dramaga IPB wajib) |
| `TREKMRT.geojson` + `TREK MRT LEBAK BULUS….geojson` | `rebuild-cascade-mrt-trek.py` / mrt-lrt-user | MRT-CASCADE-01..04 |
| `LRT DUKUH ATAS BANDARA.geojson` | `rebuild-cascade-mrt-lrt-user.py` | LRT-CASCADE-NEW-01 |
| Jakarta Satu FeatureServer | `rebuild-tj-existing.py` | `transjakarta_*.geojson` |
| OSM KRL/MRT/LRT | `rebuild-krl-existing.py`, `rebuild-lrt-mrt-existing.py` | `krl_*`, `mrt_*`, `lrt_*` |
| dokumen perencanaan | `rebuild-masterplan.py` | `masterplan/*` |

Existing TJ/KRL/MRT/LRT **tidak** ditulis ulang dari attachment usulan.

`cascade_existing.json` field `deleted` mencatat identitas lama yang **sengaja** diganti (bukan dihapus diam-diam).
