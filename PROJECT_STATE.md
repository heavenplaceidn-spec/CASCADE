# CASCADE — PROJECT STATE
Last updated: 2026-09-13. All PASS docs linked on public GitHub.

## SOURCE OF TRUTH
- L1 PRD; L2 Outputs 1–5 ABSENT; L3 files ABSENT
- PASS 1–6 artifacts originate in the Grok project folder
- PASS 7 + application source live in turbo-umbra-lagoon-crystal
- Host adapter ADR-09: TanStack Start + PGLite GeoJSON (not PostGIS)

## GITHUB MAP
| Role | Repo | Visibility |
|---|---|---|
| Docs PASS 1–7 (this repo) | https://github.com/heavenplaceidn-spec/CASCADE | public |
| Docs mirror | https://github.com/heavenplaceidn-spec/cascade-webgis | private |
| App source PASS 7 | https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal | private |
| Owner personal | https://github.com/Arckzz | — |

Connector account: heavenplaceidn-spec. Collaborator invite to Arckzz must be done in GitHub UI.

## PASS STATUS
| Pass | Artifact | Status |
|---|---|---|
| 1 | PASS1_CASCADE_SYSTEM_COMPREHENSION.md | COMPLETED (analysis) |
| 2 | PASS2_CASCADE_ARCHITECTURE.md | COMPLETED (architecture) |
| 3 | PASS3_CASCADE_GIS_IMPLEMENTATION_SPEC.md | COMPLETED (GIS bible) |
| 4 | PASS4_CASCADE_BUILD_BLUEPRINT.md | COMPLETED (blueprint) |
| 5 | PASS5_CASCADE_BUILD_REPORT.md | COMPLETE WITH BLOCKERS |
| 6 | PASS6_CASCADE_VALIDATION_REPORT.md | READY WITH LIMITATIONS |
| 7 | docs/PASS7_CASCADE_FINAL_REPORT.md | FINAL CANDIDATE |

## BLOCKED (unchanged)
- MAPID keys/styles
- Official GTFS / Jakarta Satu masterplan GIS
- Property Go, zoning, population
- PostGIS / pgRouting

## NEXT
Do not fabricate missing GIS. Do not start PASS 8.
