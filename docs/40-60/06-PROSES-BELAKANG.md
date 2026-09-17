# 06 — Proses di belakang

Folder: `src/lib/cascade/`

Tidak semua file “menggambar”. Sebagian hanya menyiapkan data, menyaring, atau menjaga basemap.

| File | Tugas, dengan kata sederhana |
|---|---|
| `static-data.ts` | mengambil JSON di `/data/...` |
| `store.ts` | ingatan UI: layer nyala, stasiun asal, bbox, error peta |
| `geojson.ts` | bentuk Feature / FeatureCollection |
| `geojson-download.ts` | unduh aman (tanpa rahasia) |
| `carto.ts` | warna dan dash |
| `mapid.ts` + `mapid.server.ts` | proxy gaya MAPID, kunci hanya di server |
| `graph.ts` | graf transit: cari stasiun, rute |
| `sim-route.ts` | menyusun jalur simulasi |
| `anim.ts` | posisi kendaraan per waktu |
| `bottleneck.ts` | indikator ramai di ruas |
| `sdss.ts` | skor analisis |
| `property.ts` / `property.server.ts` | listing dan ringkasan koridor |
| `survey.ts` / `survey.server.ts` | titik survei |
| `survey-allowlist.ts` | kategori yang boleh |
| `popup-info.ts` | isi kartu klik |
| `insight.ts` | teks AI, gagal tertutup jika tanpa kunci |
| `research.ts` | pemotong teks, kisaran biaya indikatif |
| `functions.ts` | server function cadangan / meta koridor |
| `vehicle-icons.ts` | ikon kereta/bus di peta |
| `crs.ts` | pusat peta dan zoom awal |

## API di `src/routes/api/`

| Alamat | Kegunaan |
|---|---|
| `/api/mapid/*` | meneruskan tile/gaya MAPID, kunci tidak ke browser |
| `/api/properties` dan `/api/properties/$id` | baca listing |
| `/api/corridors/$id/properties` | properti di sekitar koridor |
| `/api/corridors/$id/property-summary` | ringkasan |
| `/api/corridors/$id/price-distribution` | sebaran kelas harga |
| `/api/property-price-zones` | zona |
| `/api/property-ai-insights` | insight properti yang sudah disiapkan |
| `/api/survey-activities` | kegiatan survei |

Auth dimatikan. Data ini data perencanaan, bukan akun pengguna.

## Yang tidak dikerjakan di belakang layar

- menulis kunci MAPID ke GeoJSON
- mengisi masterplan seolah-olah existing
- membiarkan AI menambahkan halte yang tidak ada di file
