# 04 — Simulasi

File: `src/features/simulate-page.tsx`  
Jalur: `src/lib/cascade/sim-route.ts`  
Gerak kendaraan: `src/lib/cascade/anim.ts`  
Graf jaringan: `src/lib/cascade/graph.ts`

## Apa yang disimulasikan

Pengguna memilih **stasiun asal** dan **stasiun tujuan**. Pencarian nama memakai `searchStations`. Hasilnya titik yang benar-benar ada di data, bukan nama karangan.

Jaringan bisa dipilih: Existing, Masterplan, atau CASCADE. Percampuran disengaja terlihat di label titik (misalnya “Existing” vs “CASCADE”) supaya tidak tertukar.

Tombol menjalankan `buildSimPath`. Kalau graf tidak menemukan jalan, yang tampil pesan gagal — **bukan** garis lurus ke tengah laut.

## Playhead

Setelah jalur ada, titik kendaraan berjalan di atas **LineString** itu. Waktu animasi dihitung di `anim.ts`. Ikon moda disiapkan di `vehicle-icons.ts`.

Yang tidak kami lakukan:

- mengisi geom kosong dengan koordinat 0,0
- membuat jalan baru hanya karena AI “merasa” ada jalan
- menyamakan usulan dengan rute existing tanpa label

## Bottleneck

Sepanjang jalur, skor ramai-tidaknya ruas diambil dari `bottleneck.ts` (warna hijau–kuning–merah di peta). Angka ini indikator di dalam aplikasi, bukan data Macet resmi Dishub.
