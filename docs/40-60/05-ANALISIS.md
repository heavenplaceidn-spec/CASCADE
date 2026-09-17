# 05 — Analisis

File: `src/features/analysis-page.tsx`  
Hitung: `src/lib/cascade/sdss.ts`

## Untuk apa menu ini

Eksplorasi = melihat.  
Analisis = **membandingkan koridor di suatu wilayah** lalu memberi urutan prioritas.

Pengguna bisa mengaktifkan mode identify, menarik **bbox** di peta, lalu sistem mengumpulkan garis yang terpotong kotak itu.

## Faktor yang dijumlahkan

Bobot ada di kode (jumlah 1,00):

| Faktor | Bobot |
|---|---:|
| congestion | 0,28 |
| accessibility | 0,18 |
| connectivity | 0,16 |
| coverage_gap | 0,14 |
| property | 0,14 |
| planning | 0,10 |

Hasilnya skor plus label prioritas: tinggi / sedang / rendah.  
Alasan tertulis di `why` (kalimat pendek dari data, bukan esai).

Properti yang menempel ke skor diambil dari `corridor_summaries.json`. Perlu dicatat: itu asking price 2026, bukan NJOP dan bukan harga transaksi.

## Teks AI (Insight)

Tombol AI memanggil `explainCorridor` di `insight.ts`.

Aturan yang kami pasang:

1. Hanya memakai konteks yang dikirim (id, skor, stasiun, catatan properti).
2. Dilarang menambah angka baru.
3. Bahasa Indonesia, dipotong kira-kira 50 kata (`clip50`).
4. Jika `XAI_API_KEY` tidak ada, jawaban jujur: *AI tidak tersedia di lingkungan ini.*
5. Jika data kurang, model diminta mengaku data belum cukup — bukan mengarang.

Jadi AI **bukan** sumber geometri. Geometri tetap dari GeoJSON lapisan 21–40%.
