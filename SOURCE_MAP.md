# Source map (zip → this repo)

Workspace zip exported 2026-09-17. Secrets stripped. Platform `.grok/skills`
and `.vercel` build are **not** published (not CASCADE work; keys live there).

| Zip path | GitHub | Role |
|---|---|---|
| `attachments/*.geojson` | `attachments/` | User-drawn trase (CASTJ, KRL, MRT, LRT) |
| `attachments/*PRD*.pdf` | `attachments/` | Assignment PRD (L1, cited) |
| `public/data/**` | same | Existing + usulan + property GeoJSON |
| `public/data/sources.json` | same | Lineage table |
| `src/features/*.tsx` | same | Front |
| `src/lib/cascade/*.ts` | same | Back / GIS / SDSS |
| `src/routes/**` | same | Views + API |
| `scripts/rebuild-*.py` | same | How GeoJSON was rebuilt |
| `scripts/p-*-verify.mjs` | same | How it was checked |
| `screenshots/` | same | Visual proof |
| `.grok/app-env.json` | **omitted** | contained live MAPID key |
