# CASCADE — Data dictionary

Salinan dari repo aplikasi. Host adapter: GeoJSON text (`geom_json`), SRID 4326, no PostGIS geometry type.

Schema freeze PASS 7: `candidate_corridors` has `created_at`, no `updated_at`. GPS accuracy is not a column.

Core tables: data_sources, transport_modes, transport_routes, transport_stops, road_edges, masterplan_corridors, candidate_corridors, poi, survey_observations, survey_photos, gps_tracks, bottlenecks, corridor_buffers, mcda_weight_config, mcda_runs, corridor_scores, analysis_results, insight_results, geocode_cache.

Empty reasons: NOT_INGESTED | PROVIDER_UNAVAILABLE | BLOCKED_BY_DATA | BLOCKED_BY_INFRASTRUCTURE | FILTERED_EMPTY.
