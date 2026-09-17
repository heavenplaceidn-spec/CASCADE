# 02 — Peta

File utama: `src/features/map-canvas.tsx`  
Aturan warna: `src/lib/cascade/carto.ts`

## Basemap

Basemap wajib dari **MAPID**, bukan Google.  
Kunci API **tidak** disimpan di GitHub. Server membaca kunci dari lingkungan, lalu peta meminta gaya lewat **proxy** `/api/mapid/...`.

Pilihan gaya (nama teknis tetap): `basic`, `street_2d` (Street), `satellite`, `dark`, `light`.

Jika MAPID gagal, yang tampil bukan peta dunia kosong di koordinat 0,0. Ada gaya cadangan gelap (`EMPTY_MAP_STYLE`) dan pesan kesalahan di layar. Overlay GeoJSON tetap bisa dicoba.

Worker MapLibre dipanggil dari `/maplibre/maplibre-gl-worker.mjs`.

## Cara membedakan garis

Kami tidak memakai banyak warna acak. Aturannya sederhana:

| Yang dibedakan | Cara di peta |
|---|---|
| Moda (KRL, MRT, LRT, TransJakarta) | **warna** garis/titik |
| Status (existing, masterplan, usulan CASCADE) | **corak**: existing lebih tegas, masterplan putus-putus oranye, CASCADE ungu + dash |
| Jalan konteks | abu-abu, bukan koridor |

Nilai warna di kode:

- KRL `#DC2626`
- MRT `#247A67`
- LRT `#4FAF86`
- TransJakarta `#5865C7`
- usulan CASCADE `#7C3AED`
- masterplan `#E58A3A`
- existing (kelompok) `#C9A227`

Nama stasiun tidak ditampilkan dari zoom jauh. Titik mulai kira-kira zoom 12, label zoom 14. Ini supaya peta tidak penuh tulisan.

## Overlay

Garis dan titik diambil dari `/data/...` (lihat lapisan 21–40%).  
`map-canvas` memasang banyak **layer** MapLibre (contoh: `tj-existing-line`, `candidate`, `cascade-stop`, `property-point`). Klik di peta dicek ke daftar layer itu, lalu isi **popup**.

Popup disusun di `src/lib/cascade/popup-info.ts`. Isinya nama, status, sumber, moda — bukan paragraf panjang dari AI.
