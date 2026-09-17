# 03 — Skrip verify (Playwright)

Hampir semua file `scripts/p-*-verify.mjs` membuka aplikasi di peramban, menekan **Mulai Eksplorasi** (beberapa skrip lama masih mencari tulisan `EKSPLOR`), lalu memeriksa layer MapLibre lewat `window.__CASCADE_MAP`.

Kalau tes gagal, yang dicetak daftar `fail`. Kalau lulus, daftar `ok`. Screenshot sering disimpan ke `screenshots/`.

## Cek per koridor / moda

| Skrip | Yang dicek, dengan kata biasa |
|---|---|
| `p-tj-verify.mjs` / `p-tj-b-verify.mjs` | usulan TransJakarta tampil, existing tidak hilang |
| `p-tj-cas21-verify.mjs` | CASTJ21 (Cibubur–Blok M) |
| `p-tj-c20-verify.mjs` | CASTJ20 |
| `p-tj-c22-26-verify.mjs` | CASTJ22–26 |
| `p-tj-ext-2-3-14-verify.mjs` | perpanjangan koridor 2, 3, 14 |
| `p-tj0607-verify.mjs` | CAS-TJ06 / 07 |
| `p-tj-names-verify.mjs` | nama halte tidak acak |
| `p-krl-c04-verify.mjs` | KRL-C04, termasuk Dramaga |
| `p-west-verify.mjs` | cabang Tangerang (C03-N/S) |
| `p-mrt-verify.mjs` / `p-mrt-trek-verify.mjs` | trase MRT user |
| `p-mrt-east-verify.mjs` / `p-mrt-intent-verify.mjs` | cabang timur / niat koridor terkunci |
| `p-lrt-verify.mjs` / `p-mrt-lrt-verify.mjs` | LRT usulan vs LRT existing |

## Cek tampilan (bukan geom baru)

| Skrip | Yang dicek |
|---|---|
| `p-patch24-brand.mjs` | logo / hero CASCADE |
| `p-patch25-verify.mjs` | teks panel (misalnya tidak ada label lama yang membingungkan) |
| `p-patch26-verify.mjs` / `p-patch26-1-verify.mjs` | layer ganda warna moda + status |
| `p-patch27-verify.mjs` / `p-patch27b-verify.mjs` | legenda, termasuk “STATUS GARIS” |
| `p-patch28-verify.mjs` | desktop + HP (360 / 390 / 412) |
| `p-patch29-verify.mjs` | warna bottleneck (hijau–kuning–merah) |
| `p-patch30-survey.mjs` | survei tampil, **kunci API tidak bocor ke halaman** |
| `p-property-verify.mjs` | API properti menjawab, geom koridor tidak ikut berubah |
| `p-visual-dl-verify.mjs` | unduh GeoJSON dari kartu |
| `p-final-verify.mjs` / `p-overhaul-verify.mjs` | hash beku + peta siap |

Perlu dicatat: skrip ini **bukan** tes resmi MAPID. Itu tes kami sendiri supaya regresi kelihatan sebelum dikumpulkan.
