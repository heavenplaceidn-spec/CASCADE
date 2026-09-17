# 61–80% — rebuild, cek otomatis, bukti gambar

Lapisan 21–40 menjelaskan **data apa**.  
Lapisan 41–60 menjelaskan **tampilan**.  
Lapisan ini menjelaskan **bagaimana data itu dicek ulang** supaya tidak berubah diam-diam.

Bahasa di sini ditulis dari nama file dan isi skrip, bukan meniru teks tugas.

| Urutan | File | Isi |
|---|---|---|
| 1 | [01-REBUILD.md](./01-REBUILD.md) | skrip Python yang menulis GeoJSON |
| 2 | [02-HASH-BEKU.md](./02-HASH-BEKU.md) | hash SHA-256 supaya geometri tidak “geser” |
| 3 | [03-VERIFY.md](./03-VERIFY.md) | skrip `p-*-verify.mjs` (Playwright) |
| 4 | [04-SCREENSHOT.md](./04-SCREENSHOT.md) | 46 gambar di `screenshots/` |
| 5 | [05-CARA-JALANKAN.md](./05-CARA-JALANKAN.md) | urutan yang kami pakai |
| 6 | [06-BATAS.md](./06-BATAS.md) | apa yang tidak boleh dilakukan saat memperbaiki |

Gambar ada di folder [`screenshots/`](../../screenshots/). Skrip ada di [`scripts/`](../../scripts/).
