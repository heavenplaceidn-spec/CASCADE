# 03 — Eksplorasi

File: `src/features/explore-page.tsx`

Ini menu default. Tujuannya: **melihat dan membandingkan lapisan**, bukan langsung menghitung skor.

## Tiga kelompok layer

Panel kiri/atas bertuliskan Existing · Masterplan · CASCADE.

Tiap kelompok bisa:

- dicentang (tampil / disembunyikan)
- dibuka, lalu dipilih modanya (KRL, MRT, LRT, TransJakarta)

Kalau pengguna membuka moda CASCADE, peta bisa `fly` mendekati bbox koridor itu. Perintahnya ada di `static-data.ts` (`flyCascadeKrl`, `flyCorridorId`).

Mohon dibedakan: mencentang **Existing TransJakarta** tidak sama dengan mencentang **CASCADE TransJakarta**. Yang pertama rute 1–14 yang sudah jalan. Yang kedua usulan.

## Klik di peta

Klik garis atau halte membuka kartu singkat. Dari kartu itu pengguna bisa:

- melihat status (existing / masterplan / usulan)
- unduh **GeoJSON** satu fitur (`geojson-download.ts`)
- menuju analisis koridor yang sama

Unduhan melewati saringan supaya **kunci API** dan data pribadi tidak ikut tertulis di file.

## Properti dan survei

Panel properti (`property-panel.tsx`) menempel di eksplorasi. Titik listing hanya asking price, bukan nilai transaksi.

Titik survei memakai kategori yang sudah diizinkan (`survey-allowlist.ts`). Keterangan bebas yang menyinggung orang tidak disimpan.
