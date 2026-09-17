# CASCADE

**Corridor AI for Spatial Congestion, Advanced Data, and Expansion**

WebGIS Spatial Decision Support System for **mass-transport corridors in Jabodetabek**.

CASCADE is **decision support**. It is **not** an official BPTJ / Dishub / operator plan.

This GitHub tree is the **workspace zip**, remade from A→Z. Invented schematic stubs from earlier commits are gone.

| | |
|---|---|
| Status | product workspace export |
| Owner | [Arckzz](https://github.com/Arckzz) |
| Repo | [heavenplaceidn-spec/CASCADE](https://github.com/heavenplaceidn-spec/CASCADE) |
| License | [MIT](./LICENSE) |
| Integrity | [legal/ACADEMIC_INTEGRITY.md](./legal/ACADEMIC_INTEGRITY.md) |

---

## A — What you are looking at

Three views, one persistent MapLibre canvas, Bahasa Indonesia:

1. **Eksplorasi** `/` — layers, identify, buffer/property, survey
2. **Simulasi** `/simulasi` — playback along real LineStrings
3. **Analisis** `/analisis` — SDSS / compare / insight

Splash + mark: `public/cascade-mark.png`.

---


## 21–40% — data (lapisan ini)

Semua angka dari file, bukan karangan: [`docs/20-40/`](./docs/20-40/).

1. Lineage — [docs/20-40/01-LINEAGE.md](./docs/20-40/01-LINEAGE.md)
2. Existing TJ/KRL/MRT/LRT — [02-EXISTING-NETWORK.md](./docs/20-40/02-EXISTING-NETWORK.md)
3. Attachment → rebuild — [03-ATTACHMENTS-MAP.md](./docs/20-40/03-ATTACHMENTS-MAP.md)
4. 26 usulan CASCADE — [04-CORRIDOR-CATALOG.md](./docs/20-40/04-CORRIDOR-CATALOG.md)
5. Masterplan acuan — [05-MASTERPLAN.md](./docs/20-40/05-MASTERPLAN.md)
6. Properti — [06-PROPERTY.md](./docs/20-40/06-PROPERTY.md)
7. Indeks file — [07-FILE-INDEX.md](./docs/20-40/07-FILE-INDEX.md)

## 41–60% — tampilan dan proses (bahasa biasa)

Penjelasan ditulis dari kode, tidak meniru teks tugas. Inggris hanya untuk nama teknis.

Folder: [`docs/40-60/`](./docs/40-60/)

1. Tampilan (splash + tiga menu) — [01-TAMPILAN.md](./docs/40-60/01-TAMPILAN.md)
2. Peta MapLibre dan MAPID — [02-PETA.md](./docs/40-60/02-PETA.md)
3. Eksplorasi — [03-EKSPLORASI.md](./docs/40-60/03-EKSPLORASI.md)
4. Simulasi — [04-SIMULASI.md](./docs/40-60/04-SIMULASI.md)
5. Analisis / SDSS — [05-ANALISIS.md](./docs/40-60/05-ANALISIS.md)
6. Proses di belakang — [06-PROSES-BELAKANG.md](./docs/40-60/06-PROSES-BELAKANG.md)
7. Alur klik → popup — [07-ALUR.md](./docs/40-60/07-ALUR.md)

Ringkasnya: satu peta tidak di-reset saat pindah menu. Existing, masterplan, dan usulan CASCADE dibedakan dari **corak**, moda dari **warna**. AI hanya merangkum data yang sudah ada.

## B — Requirement source (cited, not rewritten as our paper)

## B — Requirement source (cited, not rewritten as our paper)

Assignment PRD:

`attachments/Geo Unjuk Kebolehan_PRD_CASCADE.pdf`

That PDF is **L1**. Code and GeoJSON in this repo are the implementation and usulan — they do not replace the PRD text.

Field log: `attachments/Log Geo unjuk kebolehan (1).xlsx`

---

## C — Data lineage (read this before the map)

Canonical table: [`public/data/sources.json`](./public/data/sources.json)

| Layer | Source | Status on map |
|---|---|---|
| TransJakarta 1–14 + halte | Jakarta Satu FeatureServer | **existing** |
| KRL / MRT NS / LRT Jabodebek | OpenStreetMap (ODbL) | **existing**, not operator GTFS |
| Roads | OSM named motorway/trunk/primary | context, not a corridor |
| CASCADE candidates | user GeoJSON in `attachments/` rebuilt by `scripts/rebuild-*.py` | **PROPOSED** |
| Masterplan | digitized planning refs | **acuan**, not existing, not CASCADE |
| Property | `public/data/property/` | corridor-area intelligence |

---

## D — User trase (attachments → public/data)

Raw drawn files live in [`attachments/`](./attachments/) (`CASTJ15`…`CASTJ26`, KRL, TREK MRT, LRT Dukuh Atas–Bandara, …).

Rebuild scripts snap those lines into `public/data/cascade/` and `public/data/*.geojson`.

Usulan inventory: [`public/data/cascade_existing.json`](./public/data/cascade_existing.json)  
Every row has `status: PROPOSED | CASCADE_PROPOSED | CASCADE_EXTENSION`.

---

## E — Front (tampilannya)

| File | Job |
|---|---|
| `src/features/splash.tsx` | landing |
| `src/features/app-shell.tsx` | persistent shell + 3-view nav |
| `src/features/map-canvas.tsx` | MapLibre, mode=hue, status=dash/casing |
| `src/features/explore-page.tsx` | layers / pick corridor |
| `src/features/simulate-page.tsx` | playhead |
| `src/features/analysis-page.tsx` | SDSS panel |
| `src/features/property-panel.tsx` | buffer property |
| `src/features/map-legend.tsx` | legend |

---

## F — Back (prosesnya)

| File | Job |
|---|---|
| `src/lib/cascade/static-data.ts` | load `/data/*.json` |
| `src/lib/cascade/graph.ts` | network / walk / routing graph |
| `src/lib/cascade/sdss.ts` | analysis envelope |
| `src/lib/cascade/carto.ts` | color + dash tokens |
| `src/lib/cascade/anim.ts` | vehicle playback |
| `src/lib/cascade/sim-route.ts` | simulation path |
| `src/lib/cascade/survey*.ts` | survey evidence |
| `src/lib/cascade/property*.ts` | property join |
| `src/lib/cascade/mapid.server.ts` | MAPID style proxy — **key from env only** |
| `src/lib/cascade/insight.ts` | fail-closed if no `XAI_API_KEY` |
| `src/lib/cascade/functions.ts` | server functions |
| `src/routes/api/**` | property, survey, MAPID tiles |

---

## G — How the process runs (A→Z)

```
PRD + user GeoJSON (attachments/)
        │
        ▼
scripts/rebuild-cascade-*.py     snap / stationize / validate
        │
        ▼
public/data/*.geojson            existing vs usulan vs masterplan
        │
        ▼
static-data.ts  →  MapLibre layers (map-canvas.tsx)
        │
        ├─ eksplorasi: toggle, identify WHAT/WHERE/STATUS/SOURCE
        ├─ simulasi:   anim.ts along LineString (no Null Island)
        └─ analisis:   sdss.ts + property buffer + insight fail-closed
```

QA: `scripts/p-*-verify.mjs` + `screenshots/`.

---

## H — Run

```bash
git clone https://github.com/heavenplaceidn-spec/CASCADE.git
cd CASCADE
npm install
# MAPID_API_KEY in the environment, never in git
npm run dev
```

Do **not** commit `.env` or `.grok/app-env.json`.

---

## I — What was deliberately left out of git

- Live MAPID / xAI keys (redacted from the zip)
- Grok App Builder skill packs (`.grok/skills`) — not CASCADE authorship
- `.vercel` build artifacts

Host contract file `AGENTS.md` is the App Builder runtime contract, not a thesis chapter.

---

## J — Cite

See [CITATION.cff](./CITATION.cff). OSM must be attributed when OSM layers are shown.
