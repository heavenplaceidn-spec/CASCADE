# 01 — Skrip rebuild

File-file ini **Python**. Tugasnya satu: membaca sumber (Jakarta Satu, OSM, atau GeoJSON gambar user), lalu menulis ulang `public/data/`. Bukan merapikan tampilan.

## Jaringan yang sudah jalan (existing)

| Skrip | Hasil | Sumber yang disitasi |
|---|---|---|
| `rebuild-tj-existing.py` | TransJakarta koridor 1–14 | Jakarta Satu |
| `rebuild-krl-existing.py` | 6 jalur KRL + stasiun | OSM, ODbL |
| `rebuild-lrt-mrt-existing.py` | MRT Fase 1 + LRT Jabodebek | OSM, ODbL |
| `rebuild-masterplan.py` | 14 garis acuan | dokumen perencanaan yang didigitasi |

Existing **tidak** ditulis dari file CASTJ di `attachments/`. Itu aturan kami, supaya usulan tidak menimpa rute yang sudah operasi.

## Usulan CASCADE (dari gambar user)

| Skrip | Yang disentuh | Yang tidak disentuh |
|---|---|---|
| `rebuild-cascade-tj-cas15-21.py` | CASTJ15–21 + perpanjangan 6/7 | moda lain |
| `add-castj22-26.py` | CASTJ22–26 | CASTJ06–21 |
| `add-castj-ext-2-3-14.py` | CASTJ02-EXT, 03-EXT, 14-EXT | CASTJ06–26 |
| `patch-castj20.py` | hanya CASTJ20 | CASTJ21 dan yang lain |
| `rebuild-cascade-tj06-07.py` | CAS-TJ06 | CAS-TJ07 dibekukan hash |
| `rebuild-cascade-krl-user.py` | KRL-C03-N, C03-S, C04 | KRL existing |
| `rebuild-cascade-mrt-trek.py` / `rebuild-cascade-mrt-lrt-user.py` | MRT-CASCADE-01…04 + LRT Dukuh Atas–Bandara | MRT/LRT existing |
| `rebuild-cascade-lrt.py` | CAS-LRT-C02 (dan C04 jika ada) | Harjamukti–Baranangsiang (itu masterplan) |

Skrip lama (`rebuild-cascade.py`, `rebuild-cascade-tj.py`) adalah jejak langkah awal. Yang dipakai untuk trase user yang sekarang adalah baris `*-user.py`, `*-cas15-21.py`, dan `add-*.py`.

## Bantuan lain

- `cascade_corridors.py` / `masterplan_corridors.py` — daftar node/koridor untuk skrip lama
- `fetch-*-extras.py` — potongan jalan OSM di sekitar trase, konteks saja
- `rename-cascade-tj-stops.py` — rapikan nama halte, bukan memindah titik
- `build-property-intelligence.py` — ringkasan listing, bukan geom koridor

Mohon diingat: menjalankan rebuild **mengubah file data**. Itu baru sah jika skrip verify di langkah 03 masih lulus.
