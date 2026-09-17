# 05 — Cara menjalankan (urutan sopan)

Aplikasi sudah jalan di mesin kerja. Skrip verify menganggap alamat pratinjau itu hidup.

Contoh, setelah mengubah CASTJ26 saja:

```bash
python3 scripts/add-castj22-26.py
node scripts/p-tj-c22-26-verify.mjs
```

Contoh, setelah mengubah KRL-C04:

```bash
python3 scripts/rebuild-cascade-krl-user.py
node scripts/p-krl-c04-verify.mjs
```

Contoh, cek tampilan HP:

```bash
node scripts/p-patch28-verify.mjs
```

Contoh, cek kunci tidak bocor + survei:

```bash
node scripts/p-patch30-survey.mjs
```

Jangan menjalankan **semua** `rebuild-*.py` berurutan tanpa baca docstring. Beberapa skrip lama menulis ulang koridor yang sudah diganti trase user.

Kalau Playwright tidak terpasang di mesin orang lain, folder `screenshots/` tetap bisa dibuka sebagai bukti yang sudah kami simpan.
