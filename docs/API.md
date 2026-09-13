# CASCADE — API (server functions)

Salinan dari repo aplikasi. TanStack `createServerFn`. Envelope:

```
{ data, metadata: { crs: "EPSG:4326", source, timestamp, analysis_version, empty_reason }, error }
```

## Read

`bootstrap`, `getMapSession`, `getCatalog`, `getTransport`, `getRoads`, `getStops`, `getMasterplan`, `getCorridors`, `getCorridorBuffer`, `getSurveys`, `getSurveyDetail`, `getBottlenecks`, `getPoi`, `getGpsTracks`, `getMcda`, `getAccessibility`, `getHeatmap`, `getServiceGap`, `getClusterLayer`, `compareTrio`, `searchPlaces`.

## Write (auth off)

`createSurvey`, `ingestGpx`, `runMcda`, `routePath`, `insightQuery`.

## Error codes

`VALIDATION_ERROR` `GEOMETRY_INVALID` `NOT_FOUND` `ANALYSIS_FAILED` `ROUTING_UNAVAILABLE` `INSIGHT_UNAVAILABLE`

Keys never returned (`hasSecret: false`).
