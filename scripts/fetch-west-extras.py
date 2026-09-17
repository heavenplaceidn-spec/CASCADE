#!/usr/bin/env python3
"""Nominatim extras for CASCADE KRL-C03 + MRT BR02. Appends extra_roads_west.geojson."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("/workspace/public/data/cascade/extra_roads_west.geojson")
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-west-fix)"}
SLEEP = 1.2

ROAD_Q = [
    "Jalan Gatot Subroto, Kota Tangerang",
    "Jalan Gatot Subroto, Cimone, Tangerang",
    "Jalan Raya Serang, Pasar Kemis",
    "Jalan Raya Serang, Tangerang",
    "Jalan Raya Kutabumi, Pasar Kemis",
    "Jalan Raya Rajeg, Rajeg, Tangerang",
    "Jalan Raya Mauk, Mauk, Tangerang",
    "Jalan Raya Mauk, Rajeg, Tangerang",
    "Jalan Raya Curug, Curug, Tangerang",
    "Jalan Raya Curug, Bitung, Tangerang",
    "Jalan Raya Bitung, Curug",
    "Jalan Raya Legok, Legok, Tangerang",
    "Jalan Raya Parung Panjang, Tangerang",
    "Jalan Raya Parung Panjang, Legok",
    "Jalan Siliwangi, Pamulang",
    "Jalan Siliwangi, Serpong",
    "Jalan Raya Serpong, Serpong",
    "Jalan Raya Serpong, Tangerang Selatan",
    "Jalan Pelayangan, BSD City",
    "Jalan Pelayangan, Serpong",
    "Jalan BSD Grand Boulevard, BSD",
    "Jalan Pahlawan Seribu, BSD",
    "Jalan Letnan Sutopo, Serpong",
    "Jalan Tekno Widya, BSD",
    "Jalan Taman Tekno, Serpong",
    "Jalan BSD Raya Utama, BSD",
    "Jalan Ciater Raya, Serpong",
    "Jalan Buaran Raya, Serpong",
    "Jalan Imam Bonjol, Kota Tangerang",
    "Jalan Raya PLP Curug, Curug",
]

PLACE_Q = {
    "Taman Kota 2 BSD": "Taman Kota 2 BSD, Serpong",
    "Jalan Pelayangan BSD": "Jalan Pelayangan, BSD City, Serpong",
    "ICE BSD": "Indonesia Convention Exhibition, BSD",
    "The Breeze BSD": "The Breeze, BSD City",
    "Rajeg": "Rajeg, Kabupaten Tangerang",
    "Mauk": "Mauk, Kabupaten Tangerang",
    "Pasar Kemis": "Pasar Kemis, Tangerang",
    "Kutabumi": "Kutabumi, Pasar Kemis",
    "Cimone": "Cimone, Kota Tangerang",
    "Bitung Curug": "Bitung, Curug, Tangerang",
    "Legok": "Legok, Kabupaten Tangerang",
    "Pamulang": "Pamulang Barat, Tangerang Selatan",
    "Siliwangi Serpong": "Jalan Siliwangi, Serpong, Tangerang Selatan",
}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def flatten_geom(g):
    if not g:
        return []
    t = g.get("type")
    c = g.get("coordinates")
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return c
    if t == "GeometryCollection":
        out = []
        for x in g.get("geometries") or []:
            out.extend(flatten_geom(x))
        return out
    return []


def main():
    existing = json.loads(OUT.read_text()) if OUT.exists() else {"type": "FeatureCollection", "features": []}
    seen = set()
    for f in existing["features"]:
        oid = (f.get("properties") or {}).get("osm_id")
        if oid is not None:
            seen.add(str(oid))
    feats = list(existing["features"])
    added = 0
    for q in ROAD_Q:
        url = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode(
                {
                    "q": q,
                    "format": "geojson",
                    "polygon_geojson": 1,
                    "limit": 8,
                    "countrycodes": "id",
                    "viewbox": "106.48,-6.36,106.76,-6.04",
                    "bounded": 0,
                }
            )
        )
        try:
            data = get(url)
        except Exception as e:
            print("FAIL road", q, e)
            time.sleep(SLEEP)
            continue
        n = 0
        for f in data.get("features") or []:
            g = f.get("geometry") or {}
            parts = flatten_geom(g)
            if not parts:
                continue
            if g["type"] not in ("LineString", "MultiLineString"):
                continue
            props = f.get("properties") or {}
            oid = props.get("osm_id")
            if oid is not None and str(oid) in seen:
                continue
            name = props.get("display_name", "").split(",")[0].strip() or q.split(",")[0]
            feats.append(
                {
                    "type": "Feature",
                    "properties": {"name": name, "query": q, "source": "nominatim_west_fix", "osm_id": oid},
                    "geometry": g if g["type"] == "MultiLineString" else {"type": "LineString", "coordinates": parts[0]},
                }
            )
            if oid is not None:
                seen.add(str(oid))
            n += 1
            added += 1
        print(f"  road {q[:48]:48s} +{n}")
        time.sleep(SLEEP)

    nodes = {}
    for key, q in PLACE_Q.items():
        url = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({"q": q, "format": "json", "limit": 3, "countrycodes": "id"})
        )
        try:
            data = get(url)
        except Exception as e:
            print("FAIL place", q, e)
            time.sleep(SLEEP)
            continue
        hits = []
        for row in data or []:
            hits.append(
                {
                    "lon": float(row["lon"]),
                    "lat": float(row["lat"]),
                    "name": row.get("display_name"),
                    "type": row.get("type"),
                    "cls": row.get("class"),
                }
            )
        nodes[key] = hits
        if hits:
            h = hits[0]
            print(f"  place {key:22s} {h['lon']:.5f},{h['lat']:.5f}  {str(h['name'])[:70]}")
        else:
            print(f"  place {key:22s} MISS")
        time.sleep(SLEEP)

    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    Path("/workspace/public/data/cascade/nodes_west.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2))
    print(f"wrote {OUT} features={len(feats)} added={added}")


if __name__ == "__main__":
    main()
