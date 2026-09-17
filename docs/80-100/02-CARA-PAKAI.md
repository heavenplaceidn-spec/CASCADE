# 02 — Cara memakai repo ini

Langkah untuk teman satu kelompok atau penguji yang meng-clone GitHub.

## 1. Ambil kode

```bash
git clone https://github.com/heavenplaceidn-spec/CASCADE.git
cd CASCADE
npm install
```

## 2. Kunci basemap

Salin `.env.example`. Isi `MAPID_API_KEY` di lingkungan kerja, **jangan** di-commit.  
Kalau Insight AI dipakai, `XAI_API_KEY` juga dari lingkungan, bukan dari berkas data.

## 3. Jalankan

```bash
npm run dev
```

Buka alamat yang dicetak di terminal. Bahasa antarmuka Indonesia. Judul: `CASCADE | MAPID WebGIS Competition 2026`.

## 4. Tiga menu

1. Tunggu splash sampai tombol **Mulai Eksplorasi** aktif.
2. **Eksplorasi** — nyalakan Existing / Masterplan / CASCADE, klik garis, baca popup.
3. **Simulasi** — ketik nama stasiun (≥ 2 huruf), pilih asal dan tujuan, jalankan playhead.
4. **Analisis** — kotak wilayah atau koridor terpilih, baca skor SDSS.

Peta tidak di-reset saat pindah menu. Zoom yang sudah diatur tetap.

## 5. Unduh GeoJSON

Dari kartu popup atau panel, unduhan lewat `geojson-download.ts`. File hasil tidak boleh berisi kunci API.

## 6. Ubah trase (opsional)

Ikuti [docs/60-80/05-CARA-JALANKAN.md](../60-80/05-CARA-JALANKAN.md): satu skrip rebuild, lalu satu skrip verify yang sesuai.
