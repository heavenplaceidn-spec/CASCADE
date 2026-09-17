#!/usr/bin/env python3
"""Nominatim extras for CAS-MRT-C01 eastern road backbone (Depok–Condet–Senen–Ancol)."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("/workspace/public/data/cascade")
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-mrt-east)"}
SLEEP = 1.15

ROAD_Q = [
    "Jalan Margonda Raya, Depok",
    "Jalan Kelapa Dua Raya, Depok",
    "Jalan Akses UI, Depok",
    "Jalan Komjen Pol M Jasin, Depok",
    "Jalan RA Fadilah, Cijantung",
    "Jalan RA Fadillah, Jakarta Timur",
    "Jalan R.A. Fadillah, Cijantung",
    "Jalan Kesehatan, Cijantung",
    "Jalan Kesehatan, Kramat Jati",
    "Jalan Kesehatan, Pasar Rebo",
    "Jalan TB Simatupang, Cijantung",
    "Jalan TB Simatupang, Tanjung Barat",
    "Jalan T.B. Simatupang, Kramat Jati",
    "Jalan Raya Condet, Jakarta",
    "Jalan Condet Raya, Jakarta",
    "Jalan Dewi Sartika, Cililitan",
    "Jalan Otto Iskandar Dinata, Jakarta",
    "Jalan Jatinegara Barat, Jakarta",
    "Jalan Jatinegara Barat Raya, Jakarta",
    "Jalan Matraman Raya, Jakarta",
    "Jalan Pramuka, Jakarta",
    "Jalan Pramuka Raya, Jakarta",
    "Jalan Kramat Raya, Jakarta",
    "Jalan Pasar Senen, Jakarta",
    "Jalan Gunung Sahari Raya, Jakarta",
    "Jalan Gunung Sahari, Jakarta",
    "Jalan Letnan Jenderal Suprapto, Jakarta",
    "Jalan Lodan Raya, Jakarta",
    "Jalan Benyamin Sueb, Jakarta",
]

PLACE_Q = {
    "Kelapa Dua Depok": "Kelapa Dua, Cimanggis, Depok",
    "Akses UI": "Jalan Akses UI, Cimanggis, Depok",
    "Tugu Kostrad Cijantung": "Tugu Kostrad Cijantung, Jakarta",
    "RA Fadilah": "Jalan RA Fadilah, Cijantung, Jakarta",
    "Graha Cijantung": "Mall Graha Cijantung, Jakarta",
    "Jalan Kesehatan Cijantung": "Jalan Kesehatan, Cijantung, Jakarta",
    "TB Simatupang Cijantung": "Jalan TB Simatupang, Cijantung, Jakarta",
    "Condet": "Condet, Balekambang, Jakarta",
    "PGC": "PGC Cililitan, Jakarta",
    "Otista": "Jalan Otto Iskandar Dinata, Jakarta",
    "Jatinegara Barat": "Jalan Jatinegara Barat, Jakarta",
    "Matraman": "Matraman, Jakarta",
    "Pramuka": "Halte Pramuka, Jakarta",
    "Kramat Raya": "Jalan Kramat Raya, Jakarta",
    "Senen": "Stasiun Pasar Senen, Jakarta",
    "Gunung Sahari": "Jalan Gunung Sahari Raya, Jakarta",
    "Ancol": "Stasiun Ancol, Jakarta",
    "Margonda": "Margonda, Depok",
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
    extra_path = OUT / "extra_roads_mrt_east.geojson"
    feats = []
    seen = set()
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
                    "viewbox": "106.80,-6.42,106.90,-6.10",
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
            osm_id = props.get("osm_id")
            if osm_id in seen:
                continue
            seen.add(osm_id)
            name = props.get("display_name", "").split(",")[0].strip() or q.split(",")[0]
            feats.append(
                {
                    "type": "Feature",
                    "properties": {"name": name, "query": q, "source": "nominatim_mrt_east", "osm_id": osm_id},
                    "geometry": g if g["type"] == "MultiLineString" else {"type": "LineString", "coordinates": parts[0]},
                }
            )
            n += 1
        print(f"  road {q[:48]:48s} +{n}")
        time.sleep(SLEEP)

    extra_path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    print("wrote", extra_path, "features", len(feats))

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
            nodes[key] = {"lon": lon, "lat": lat, "display": data[0].get("display_name", "")}
            print(f"  place {key:28s} {lon:.5f},{lat:.5f}  {data[0].get('display_name','')[:90]}")
        else:
            print(f"  place {key:28s} MISS")
        time.sleep(SLEEP)
    (OUT / "nodes_mrt_east.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
