# 07 — Alur dari A ke Z (sekali klik)

Contoh paling umum: pengguna ingin melihat usulan CASTJ21.

1. Splash selesai → `AppShell` menampilkan peta.
2. Overlay CASCADE dimuat dari `/data/cascade_candidates.geojson` (dan meta di `cascade_existing.json`).
3. Di Eksplorasi, kelompok CASCADE dibuka, moda TransJakarta dicentang.
4. MapLibre menggambar layer `candidate` (ungu, dash) plus `cascade-stop`.
5. Pengguna klik garis. `map-canvas` membaca `id` fitur.
6. `popup-info.ts` merakit baris: nama, status usulan, moda, sumber.
7. Kartu muncul. Tombol unduh menulis GeoJSON satu koridor, sudah disaring.
8. Jika lanjut Analisis, `sdss.ts` menghitung skor di bbox atau koridor terpilih.
9. Jika tombol AI ditekan, `insight.ts` hanya merangkum konteks itu. Tanpa kunci: pesan “tidak tersedia”.
10. Jika lanjut Simulasi, `graph.ts` mencari stasiun di garis yang sama, `anim.ts` menggerakkan ikon di koordinat yang sudah ada.

Kalau salah satu langkah data kosong, alur **berhenti dengan pesan**. Tidak ada garis darurat ke koordinat 0,0.

```
[GeoJSON di public/data]
        → static-data / fetch
        → layer MapLibre
        → klik
        → popup
        → (opsional) SDSS / simulasi / AI
```
