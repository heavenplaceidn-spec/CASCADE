#!/usr/bin/env python3
"""Nominatim extras for MRT corridor intent: Cijantung, RA Fadillah, Matraman, Pramuka, Gunung Sahari."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("/workspace/public/data/cascade")
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-mrt-intent)"}
SLEEP = 1.15

ROAD_Q = [
    "Jalan RA Fadillah, Cijantung, Jakarta",
    "Jalan R.A. Fadillah, Pasar Rebo",
    "Jalan Pendidikan, Cijantung, Jakarta",
    "Jalan Kesehatan, Cijantung, Jakarta",
    "Jalan Raya Bogor, Cijantung",
    "Jalan Raya Bogor, Kramat Jati",
    "Jalan Condet Raya, Jakarta",
    "Jalan Dewi Sartika, Cililitan",
    "Jalan Otto Iskandar Dinata, Jakarta",
    "Jalan Otista Raya, Jakarta",
    "Jalan Matraman Raya, Jakarta",
    "Jalan Pramuka, Jakarta Timur",
    "Jalan Letjen Suprapto, Jakarta",
    "Jalan Kwitang, Jakarta",
    "Jalan Gunung Sahari Raya, Jakarta",
    "Jalan Salemba Raya, Jakarta",
    "Jalan Sultan Agung, Jakarta",
    "Jalan Raya Parung—Ciputat",
    "Jalan Raya Parung, Bogor",
    "Jalan Raya Sawangan, Depok",
    "Jalan Arif Rahman Hakim, Depok",
    "Jalan Margonda Raya, Depok",
    "Jalan Tole Iskandar, Depok",
    "Jalan Cinere Raya, Depok",
    "Jalan Raya Limo, Depok",
    "Jalan Andara, Jakarta Selatan",
]

PLACE_Q = {
    "Cijantung Mall": "Mal Cijantung, Jakarta",
    "RA Fadillah": "Jalan RA Fadillah, Cijantung",
    "Matraman KRL": "Stasiun Matraman, Jakarta",
    "Matraman TJ": "Halte Matraman, Transjakarta",
    "Pramuka": "Jalan Pramuka, Jakarta Timur",
    "Gunung Sahari": "Jalan Gunung Sahari Raya, Jakarta",
    "Parung Bingung": "Parung Bingung, Sawangan, Depok",
    "Pondok Cabe": "Pondok Cabe, Tangerang Selatan",
    "Bojongsari": "Bojongsari, Depok",
    "Otista": "Jalan Otto Iskandar Dinata, Jatinegara",
    "Pademangan": "Pademangan, Jakarta Utara",
}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def flatten_geom(g):
    if not g:
        return []
    t = g.get("type")
    if t == "LineString":
        return [g.get("coordinates") or []]
    if t == "MultiLineString":
        return g.get("coordinates") or []
    if t == "GeometryCollection":
        out = []
        for x in g.get("geometries") or []:
            out.extend(flatten_geom(x))
        return out
    return []


def main():
    extra_path = OUT / "extra_roads_mrt.geojson"
    existing = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}
    have = set()
    for f in existing.get("features") or []:
        g = f.get("geometry") or {}
        have.add((g.get("type"), json.dumps(g.get("coordinates"), separators=(",", ":"))))

    feats = list(existing.get("features") or [])
    added = 0
    for q in ROAD_Q:
        url = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode(
                {
                    "q": q,
                    "format": "geojson",
                    "polygon_geojson": 1,
                    "limit": 6,
                    "countrycodes": "id",
                    "viewbox": "106.70,-6.45,106.92,-6.10",
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
            key = (g.get("type"), json.dumps(g.get("coordinates"), separators=(",", ":")))
            if key in have:
                continue
            props = f.get("properties") or {}
            name = props.get("display_name", "").split(",")[0].strip() or q.split(",")[0]
            if g["type"] not in ("LineString", "MultiLineString"):
                continue
            feats.append(
                {
                    "type": "Feature",
                    "properties": {
                        "name": name,
                        "query": q,
                        "source": "nominatim_mrt_intent",
                        "osm_id": props.get("osm_id"),
                    },
                    "geometry": g if g["type"] == "MultiLineString" else {"type": "LineString", "coordinates": parts[0]},
                }
            )
            have.add(key)
            n += 1
            added += 1
        print(f"  road {q[:48]:48s} +{n}")
        time.sleep(SLEEP)

    nodes = {}
    for key, q in PLACE_Q.items():
        url = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "id"})
        )
        try:
            data = get(url)
        except Exception as e:
            print("FAIL place", key, e)
            time.sleep(SLEEP)
            continue
        if data:
            lon, lat = float(data[0]["lon"]), float(data[0]["lat"])
            nodes[key] = [lon, lat, (data[0].get("display_name") or "")[:90]]
            print(f"  place {key:22s} {lon:.5f},{lat:.5f}  {nodes[key][2][:70]}")
        else:
            print(f"  place {key:22s} MISS")
        time.sleep(SLEEP)

    extra_path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    (OUT / "nodes_mrt_intent.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2))
    print(f"wrote {extra_path} features={len(feats)} added={added}")


if __name__ == "__main__":
    main()
