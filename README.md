# CASCADE WebGIS

Repo **publik**. Kalau tautan privat tadi 404, buka yang ini.

## Tautan yang bisa dibuka

- Repo ini (publik): https://github.com/heavenplaceidn-spec/CASCADE
- Profil pemilik konektor Grok: https://github.com/heavenplaceidn-spec

Repo privat `cascade-webgis` dan `turbo-umbra-lagoon-crystal` **tetap ada**. GitHub sengaja mengembalikan 404 untuk repo privat jika kamu tidak login sebagai pemiliknya (`heavenplaceidn-spec`). Itu bukan repo hilang.

## Kenapa 404 di tautan privat?

Konektor GitHub di Grok memakai akun **heavenplaceidn-spec**.
Browser kamu kemungkinan:

1. belum login GitHub, atau
2. login akun lain (akun harianmu),

bukan akun `heavenplaceidn-spec`. GitHub menyembunyikan repo privat dari akun yang tidak punya akses — halaman yang muncul: 404.

## Cara buka repo privat

1. Buka https://github.com/login
2. Masuk dengan akun yang sama yang kamu otorisasi di Grok (username: `heavenplaceidn-spec`)
3. Baru buka:
   - https://github.com/heavenplaceidn-spec/cascade-webgis
   - https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal

Cek akun aktif: klik avatar kanan atas. Harus tertulis `heavenplaceidn-spec`.

Kalau kamu biasanya memakai username GitHub lain, kirim username itu. Repo privat perlu diundang sebagai kolaborator dari akun pemilik — dari sini belum ada tombol invite, jadi jalur tercepat adalah login sebagai `heavenplaceidn-spec` atau pakai repo publik ini.

## Source aplikasi

Kode yang dijalankan ada di repo privat:
`heavenplaceidn-spec/turbo-umbra-lagoon-crystal`

Clone hanya berhasil setelah login akun yang punya akses:

```bash
git clone https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal.git cascade
```

Tanpa akses, Git juga akan bilang `Repository not found` (sama artinya dengan 404).
