# 01 — Peta folder

Ini isi repo yang sengaja dipublikasikan. Nama Inggris hanya untuk folder teknis.

```
CASCADE/
├── README.md                 pengantar
├── LICENSE                   MIT
├── CITATION.cff              sitasi perangkat lunak
├── SOURCE_MAP.md             zip → git
├── legal/                    keaslian + atribusi OSM / Jakarta Satu
├── docs/
│   ├── 20-40/                data dan lineage
│   ├── 40-60/                tampilan dan proses
│   ├── 60-80/                rebuild, tes, screenshot
│   └── 80-100/               cara pakai (lapisan ini)
├── attachments/              trase user + PRD (disitasi)
├── public/
│   ├── data/                 GeoJSON yang dibaca peta
│   ├── cascade-mark.png      logo
│   └── maplibre/             worker MapLibre
├── screenshots/              bukti layar tes
├── scripts/                  rebuild-*.py dan p-*-verify.mjs
├── src/
│   ├── features/             splash, peta, tiga menu
│   ├── lib/cascade/          proses di belakang
│   └── routes/               alamat halaman + API
├── migrations/               skema simpan (auth host)
├── package.json
└── .env.example              nama variabel saja, tanpa nilai
```

Yang **tidak** di git: `node_modules`, hasil build, dan file yang berisi kunci MAPID.
