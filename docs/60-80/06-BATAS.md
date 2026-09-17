# 06 — Batas (supaya tidak ketahuan “menyontek proses”)

Yang **boleh**:

- menambah koridor baru lewat `add-*.py` tanpa menggeser yang lama
- mengganti satu trase user, lalu memperbarui hash di verify
- menambah screenshot baru dengan nama patch baru

Yang **tidak boleh**:

- mengedit `transjakarta_routes.geojson` “supaya lebih rapi” tanpa rebuild existing
- menghapus tes hash karena gagal, tanpa menjelaskan di git
- memakai AI untuk menggambar LineString baru lalu menyimpannya seolah hasil survei
- memasukkan kunci MAPID ke halaman atau ke GeoJSON (tes `p-patch30-survey.mjs` menolak ini)
- mengaku screenshot sebagai peta resmi BPTJ / operator

Kalau ada file di `screenshots/` yang tidak cocok dengan data sekarang, anggap itu jejak patch lama. Yang diutamakan: data di `public/data/` + skrip verify yang masih lulus.
