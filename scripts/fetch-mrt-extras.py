#!/usr/bin/env python3
"""Nominatim extras for CAS-MRT-C01 road backbone. Writes extra_roads_mrt.geojson + nodes_mrt.json."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("/workspace/public/data/cascade")
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-mrt)"}
SLEEP = 1.15

ROAD_Q = [
    "Jalan Raya Ciputat, Tangerang Selatan",
    "Jalan Ciputat Raya, Jakarta",
    "Jalan Raya Parung, Bogor",
    "Jalan Raya Parung-Ciputat",
    "Jalan Raya Sawangan, Depok",
    "Jalan Cinere Raya, Depok",
    "Jalan Raya Cinere, Depok",
    "Jalan Limo Raya, Depok",
    "Jalan Andara, Jakarta Selatan",
    "Jalan Krukut Raya, Depok",
    "Jalan Margonda Raya, Depok",
    "Jalan Tole Iskandar, Depok",
    "Jalan Raya Condet, Jakarta",
    "Jalan Tanah Merdeka, Ciracas",
    "Jalan Palakali, Depok",
    "Jalan Lebak Bulus Raya, Jakarta",
    "Jalan Ir Haji Juanda, Depok",
    "Jalan Arif Rahman Hakim, Depok",
    "Jalan Parung Bingung, Depok",
    "Jalan Dewi Sartika, Cililitan",
    "Jalan Proklamasi, Jakarta",
    "Jalan Pegangsaan Timur, Jakarta",
    "Jalan Minangkabau, Jakarta",
    "Jalan Sultan Agung, Menteng",
    "Jalan Angkasa, Kemayoran",
    "Jalan Ancol Barat, Jakarta",
    "Jalan Gunung Sahari Raya, Jakarta",
    "Jalan Lodan Raya, Jakarta",
    "Jalan Benyamin Sueb, Jakarta",
    "Jalan Raya Bogor, Cimanggis",
    "Jalan RS Fatmawati, Jakarta",
    "Jalan Raden Ajeng Kartini, Cilandak",
    "Jalan TB Simatupang, Cilandak",
    "Jalan Alternative Cibubur, Ciracas",
    "Jalan Raya Centex, Ciracas",
    "Jalan Kayu Manis, Condet",
    "Jalan Batu Ampar, Condet",
    "Jalan Moch Kahfi I, Cipedak",
    "Jalan Nusantara Raya, Depok",
    "Jalan Raya Limo, Depok",
]

PLACE_Q = {
    "Lebak Bulus": "Stasiun MRT Lebak Bulus, Jakarta",
    "Ciputat": "Ciputat, Tangerang Selatan",
    "Parung": "Parung, Kabupaten Bogor",
    "Parung Bingung": "Parung Bingung, Sawangan, Depok",
    "Sawangan": "Sawangan, Depok",
    "Cinere": "Cinere, Depok",
    "Krukut": "Krukut, Limo, Depok",
    "Andara": "Jalan Andara, Cilandak, Jakarta",
    "Cilandak": "Cilandak Town Square, Jakarta",
    "Fatmawati": "Stasiun MRT Fatmawati, Jakarta",
    "Depok Baru": "Stasiun Depok Baru",
    "Margonda": "Margonda, Depok",
    "Cimanggis": "Cimanggis, Depok",
    "Cibubur": "Cibubur Junction, Jakarta",
    "Ciracas": "Ciracas, Jakarta Timur",
    "Pasar Rebo": "Pasar Rebo, Jakarta Timur",
    "Tanah Merdeka": "Jalan Tanah Merdeka, Ciracas",
    "Kampung Rambutan": "Terminal Kampung Rambutan, Jakarta",
    "PGC": "PGC Cililitan, Jakarta",
    "Condet": "Condet, Balekambang, Jakarta",
    "Kampung Melayu": "Terminal Kampung Melayu, Jakarta",
    "Tebet": "Stasiun Tebet, Jakarta",
    "Manggarai": "Stasiun Manggarai, Jakarta",
    "Salemba": "Salemba, Jakarta Pusat",
    "Senen": "Stasiun Pasar Senen, Jakarta",
    "Kemayoran": "Stasiun Kemayoran, Jakarta",
    "Ancol": "Stasiun Ancol, Jakarta",
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
    feats = []
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
            props = f.get("properties") or {}
            name = props.get("display_name", "").split(",")[0].strip() or q.split(",")[0]
            if g["type"] in ("LineString", "MultiLineString"):
                feats.append(
                    {
                        "type": "Feature",
                        "properties": {"name": name, "query": q, "source": "nominatim_mrt", "osm_id": props.get("osm_id")},
                        "geometry": g if g["type"] == "MultiLineString" else {"type": "LineString", "coordinates": parts[0]},
                    }
                )
                n += 1
        print(f"  road {q[:40]:40s} +{n}")
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
            nodes[key] = [lon, lat, data[0].get("display_name", "")[:80]]
            print(f"  place {key:20s} {lon:.5f},{lat:.5f}")
        else:
            print("  MISS place", key)
        time.sleep(SLEEP)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "extra_roads_mrt.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False)
    )
    (OUT / "nodes_mrt.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2))
    print("wrote", len(feats), "road parts", len(nodes), "places")


if __name__ == "__main__":
    main()
