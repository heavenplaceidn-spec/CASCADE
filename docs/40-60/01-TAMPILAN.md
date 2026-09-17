# 01 — Tampilan yang dilihat pengguna

Aplikasi dibuka dalam bahasa Indonesia. Judul halaman: `CASCADE | MAPID WebGIS Competition 2026`.

## Layar awal

File: `src/features/splash.tsx`

Saat pertama buka, yang tampil bukan peta kosong, melainkan layar pembuka dengan persentase. Tulisannya mengikuti langkah nyata:

- menyiapkan aplikasi
- menyiapkan peta
- memuat basemap
- memuat data transportasi
- existing, masterplan, lalu CASCADE
- stasiun/halte
- menyusun layer

Tombol **Mulai Eksplorasi** baru terasa “siap” setelah peta benar-benar `ready`. Ini supaya pengguna tidak mengira peta sudah lengkap padahal overlay masih loading.

## Kerangka (shell)

File: `src/features/app-shell.tsx`

Setelah splash ditutup:

1. Logo `cascade-mark.png` di kiri atas.
2. Menu **Eksplorasi · Simulasi · Analisis** di kanan atas (di HP menu ini pindah ke bawah).
3. Kanvas peta memenuhi layar.
4. Panel kerja di kanan (di HP jadi lembar dari bawah, bisa dilipat).

Peta tetap hidup ketika menu diganti. Yang berganti hanya isi panel. Itu sengaja: zoom dan layer tidak boleh “reset” hanya karena pengguna buka Simulasi.

| Alamat | Menu | File panel |
|---|---|---|
| `/` | Eksplorasi | `explore-page.tsx` |
| `/simulasi` | Simulasi | `simulate-page.tsx` |
| `/analisis` | Analisis | `analysis-page.tsx` |

Router ada di `src/routes/`. Root (`__root.tsx`) yang membungkus `AppShell`.
