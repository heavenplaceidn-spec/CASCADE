# 41–60% — tampilan dan proses di belakang peta

Bagian ini menjelaskan **cara aplikasi dipakai** dan **apa yang terjadi setelah tombol diklik**.  
Bahasa di sini ditulis ulang dari kode, bukan meniru teks tugas.

Istilah Inggris hanya dipakai kalau memang nama teknis: MapLibre, GeoJSON, layer, API, proxy, popup, store, playhead, bbox, overlay.

| Urutan | File | Isi singkat |
|---|---|---|
| 1 | [01-TAMPILAN.md](./01-TAMPILAN.md) | layar awal, kerangka, tiga menu |
| 2 | [02-PETA.md](./02-PETA.md) | MapLibre, warna, basemap MAPID |
| 3 | [03-EKSPLORASI.md](./03-EKSPLORASI.md) | menyalakan layer, klik garis, unduh GeoJSON |
| 4 | [04-SIMULASI.md](./04-SIMULASI.md) | pilih stasiun, jalur, animasi kendaraan |
| 5 | [05-ANALISIS.md](./05-ANALISIS.md) | SDSS, properti, teks AI yang dibatasi |
| 6 | [06-PROSES-BELAKANG.md](./06-PROSES-BELAKANG.md) | file `src/lib/cascade` dan API |
| 7 | [07-ALUR.md](./07-ALUR.md) | dari klik sampai popup |

Peta **tidak dibuat ulang** setiap pindah menu. Satu kanvas MapLibre di `AppShell`, panel kanan yang berganti.
