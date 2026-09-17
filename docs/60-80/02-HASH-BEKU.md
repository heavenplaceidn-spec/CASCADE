# 02 — Hash yang dibekukan

Beberapa skrip `p-*-verify.mjs` dan `p-overhaul-verify.mjs` menyimpan **cuplikan SHA-256** koordinat. Tujuannya sederhana: kalau ada yang “ rapikan” garis tanpa disadari, tes gagal.

Contoh yang tertulis di `p-final-verify.mjs` (12 karakter pertama hash geometri):

| Id koridor | Hash singkat |
|---|---|
| `CAS-MRT-C01` | `7f4818d71be3` |
| `CAS-MRT-C01-A` | `ae3767b7fef3` |
| `KRL-C03-N` | `711afcad81d6` |

`p-overhaul-verify.mjs` juga membekukan **seluruh file** existing, misalnya `krl_routes.geojson`, `transjakarta_routes.geojson`, `masterplan.geojson`. Artinya: usulan baru tidak boleh menimpa berkas existing.

`rebuild-cascade-tj06-07.py` menyebut CAS-TJ07 dibekukan di hash `86db51d43844`.

Kalau geometri memang harus diubah (user mengirim trase baru), langkah yang sopan:

1. ganti GeoJSON di `attachments/`
2. jalankan **satu** skrip rebuild yang relevan
3. jalankan verify yang sama
4. **perbarui hash** di skrip verify, jangan dihapus diam-diam

Ini bagian anti-plagiasi praktis: jejak perubahan ada di git, bukan “tiba-tiba beda di peta”.
