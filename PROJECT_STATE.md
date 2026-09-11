# CASCADE — PROJECT STATE
Last updated: 2026-09-11. GitHub connected.

## SOURCE OF TRUTH
- L1 PRD; L2 Outputs 1–5 ABSENT; L3 files ABSENT
- PASS 1–6 artifacts in Grok project folder + this public repo
- Host adapter ADR-09: TanStack Start + PGLite GeoJSON (not PostGIS)

## GITHUB
- Account: heavenplaceidn-spec
- Public docs: https://github.com/heavenplaceidn-spec/CASCADE
- Private docs: https://github.com/heavenplaceidn-spec/cascade-webgis
- App source: https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal

## PASS 6
Audit + hardening. AppShell lifted to root (map persists). Metric PIP. No Jakarta fallback geoms. Search debounce. Routing/survey/Insight validation. Cartographic class encoding + legend. GIS tests 14/14.

## PASS 7
Lives in the app repo (CASCADE FINAL CANDIDATE). GIS tests 18/18. E2E 21/21.

## BLOCKED (unchanged)
- MAPID keys/styles
- Official GTFS / Jakarta Satu masterplan GIS
- Property Go, zoning, population
- PostGIS / pgRouting
