# Vehicle animation assets

CASCADE simulation vehicles are original canvas sprites drawn for this WebGIS.

MapLibre + MAPID vector styles do not expose a native GLB/GLTF model layer.
3D GLB packs (including Quaternius Modular Train Pack, CC0 / public domain)
were evaluated and are not loaded at runtime so that:

- vehicles stay snapped to GeoJSON centerline
- basemap style switches keep working
- the map does not become a pitched 3D game camera

Silhouettes follow common public-transport proportions (single urban bus vs
multi-carriage commuter / LRT / metro consists). They are not copies of
TravelBoast, Quaternius, or other third-party meshes.

License of these sprites: original work for CASCADE, free to keep with the app.

Reference (not bundled):
- Quaternius Modular Train Pack — https://poly.pizza/bundle/Modular-Train-Pack-jYEybkFVr1 — CC0
- Quaternius Public Transport Pack — https://quaternius.com/packs/publictransport.html — CC0
