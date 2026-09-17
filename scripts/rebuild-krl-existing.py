#!/usr/bin/env python3
"""PASS 14 — rebuild KRL existing network from OSM rail relations + KRL.txt structure."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

OSM = Path("/tmp/cascade-data/osm")
OUT = Path("/workspace/public/data")
COLOR = "#D83A72"
SRC = "OpenStreetMap route relations KAI Commuter"
SRC_TYPE = "osm"
LICENSE = "ODbL"
SRC_URL = "https://www.openstreetmap.org"
RETRIEVED = "2026-09-04"
STOP_TOL_M = 120.0

# Canonical structure from KRL.txt (station order is source of truth).
LINES = {
    "B": {
        "line_id": "krl-B",
        "line_name": "Commuter Line Bogor",
        "line_code": "B",
        "short": "Bogor",
        "from_name": "Jakarta Kota",
        "to_name": "Bogor",
        "endpoint": "Jakarta Kota - Bogor",
        "rel": 16877210,
        "stations": [
            "Jakarta Kota",
            "Jayakarta",
            "Mangga Besar",
            "Sawah Besar",
            "Juanda",
            "Gondangdia",
            "Cikini",
            "Manggarai",
            "Tebet",
            "Cawang",
            "Duren Kalibata",
            "Pasar Minggu Baru",
            "Pasar Minggu",
            "Tanjung Barat",
            "Lenteng Agung",
            "Universitas Pancasila",
            "Universitas Indonesia",
            "Pondok Cina",
            "Depok Baru",
            "Depok",
            "Citayam",
            "Bojong Gede",
            "Cilebut",
            "Bogor",
        ],
        "terminus": ["Jakarta Kota", "Bogor"],
        "branch_node": "Citayam",
    },
    "B-nambo": {
        "line_id": "krl-B-nambo",
        "line_name": "Commuter Line Bogor — cabang Nambo",
        "line_code": "B",
        "short": "Nambo",
        "from_name": "Citayam",
        "to_name": "Nambo",
        "endpoint": "Citayam - Nambo",
        "rel": 16877211,
        "unique_vs": 16877210,
        "branch": "nambo",
        "parent": "B",
        "stations": ["Citayam", "Pondok Rajeg", "Cibinong", "Nambo"],
        "terminus": ["Nambo"],
        "branch_node": "Citayam",
    },
    "R": {
        "line_id": "krl-R",
        "line_name": "Commuter Line Rangkasbitung",
        "line_code": "R",
        "short": "Rangkasbitung",
        "from_name": "Tanah Abang",
        "to_name": "Rangkasbitung",
        "endpoint": "Tanah Abang - Rangkasbitung",
        "rel": 15094546,
        "stations": [
            "Tanah Abang",
            "Palmerah",
            "Kebayoran",
            "Pondok Ranji",
            "Jurangmangu",
            "Sudimara",
            "Rawa Buntu",
            "Serpong",
            "Cisauk",
            "Cicayur",
            "Jatake",
            "Parung Panjang",
            "Cilejit",
            "Daru",
            "Tenjo",
            "Tigaraksa",
            "Cikoya",
            "Maja",
            "Citeras",
            "Rangkasbitung",
        ],
        "terminus": ["Tanah Abang", "Rangkasbitung"],
    },
    "C": {
        "line_id": "krl-C",
        "line_name": "Commuter Line Cikarang",
        "line_code": "C",
        "short": "Cikarang",
        "from_name": "Cikarang",
        "to_name": "Kampung Bandan",
        "endpoint": "Cikarang - Jatinegara - Kampung Bandan (loop)",
        "rel": 15094545,
        "extra_rels": [2922163],
        "stations": [
            "Cikarang",
            "Metland Telagamurni",
            "Cibitung",
            "Tambun",
            "Bekasi Timur",
            "Bekasi",
            "Kranji",
            "Cakung",
            "Klender Baru",
            "Buaran",
            "Klender",
            "Jatinegara",
            "Matraman",
            "Manggarai",
            "Sudirman",
            "Karet",
            "Tanah Abang",
            "Duri",
            "Angke",
            "Kampung Bandan",
            "Pondok Jati",
            "Kramat",
            "Gang Sentiong",
            "Pasar Senen",
            "Kemayoran",
            "Rajawali",
        ],
        "loop_manggarai": [
            "Jatinegara",
            "Matraman",
            "Manggarai",
            "Sudirman",
            "Karet",
            "Tanah Abang",
            "Duri",
            "Angke",
            "Kampung Bandan",
        ],
        "loop_senen": [
            "Jatinegara",
            "Pondok Jati",
            "Kramat",
            "Gang Sentiong",
            "Pasar Senen",
            "Kemayoran",
            "Rajawali",
            "Kampung Bandan",
        ],
        "terminus": ["Cikarang"],
        "loop_nodes": ["Jatinegara", "Kampung Bandan"],
    },
    "T": {
        "line_id": "krl-T",
        "line_name": "Commuter Line Tangerang",
        "line_code": "T",
        "short": "Tangerang",
        "from_name": "Duri",
        "to_name": "Tangerang",
        "endpoint": "Duri - Tangerang",
        "rel": 17193463,
        "stations": [
            "Duri",
            "Grogol",
            "Pesing",
            "Taman Kota",
            "Bojong Indah",
            "Rawa Buaya",
            "Kalideres",
            "Poris",
            "Batu Ceper",
            "Tanah Tinggi",
            "Tangerang",
        ],
        "terminus": ["Duri", "Tangerang"],
    },
    "TP": {
        "line_id": "krl-TP",
        "line_name": "Commuter Line Tanjung Priok",
        "line_code": "TP",
        "short": "Tanjung Priok",
        "from_name": "Jakarta Kota",
        "to_name": "Tanjung Priok",
        "endpoint": "Jakarta Kota - Tanjung Priok",
        "rel": 17193008,
        "stations": ["Jakarta Kota", "Kampung Bandan", "Ancol", "Tanjung Priok"],
        "terminus": ["Jakarta Kota", "Tanjung Priok"],
    },
}

NAME_ALIAS = {
    "bojonggede": "Bojong Gede",
    "bojong gede": "Bojong Gede",
    "parungpanjang": "Parung Panjang",
    "parung panjang": "Parung Panjang",
    "tanjung priuk": "Tanjung Priok",
    "tanjung priok": "Tanjung Priok",
    "jurang mangu": "Jurangmangu",
    "jurangmangu": "Jurangmangu",
    "pasar minggu baru": "Pasar Minggu Baru",
    "universitas pancasila": "Universitas Pancasila",
    "universitas indonesia": "Universitas Indonesia",
    "metland telaga murni": "Metland Telagamurni",
    "pondok cina": "Pondok Cina",
    "pondok rajeg": "Pondok Rajeg",
}

# Extra stations that OSM route members omitted. Coordinates from OSM/Nominatim.
EXTRA_STATIONS = {
    "Pondok Rajeg": {"lon": 106.8242960, "lat": -6.4607829, "osm_id": 1228345121, "code": "B22A"},
    "Cikoya": {"lon": 106.4116547, "lat": -6.3357385, "osm_id": 5310716224, "code": "R17"},
    "Karet": {"lon": 106.8160036, "lat": -6.2008624, "osm_id": 605535396, "code": "C09A"},
}

EXCLUDE = {"bni city", "jakarta international stadium", "gunung putri", "bendungan hilir"}

CODES = {
    "Jakarta Kota": "JAKK",
    "Jayakarta": "JYK",
    "Mangga Besar": "MGB",
    "Sawah Besar": "SWB",
    "Juanda": "JUA",
    "Gondangdia": "GOD",
    "Cikini": "CKI",
    "Manggarai": "MRI",
    "Tebet": "TEB",
    "Cawang": "CW",
    "Duren Kalibata": "DRN",
    "Pasar Minggu Baru": "PSMB",
    "Pasar Minggu": "PSM",
    "Tanjung Barat": "TJB",
    "Lenteng Agung": "LNA",
    "Universitas Pancasila": "UP",
    "Universitas Indonesia": "UI",
    "Pondok Cina": "POC",
    "Depok Baru": "DPB",
    "Depok": "DP",
    "Citayam": "CTA",
    "Bojong Gede": "BJD",
    "Cilebut": "CLT",
    "Bogor": "BOO",
    "Pondok Rajeg": "PDRG",
    "Cibinong": "CBN",
    "Nambo": "NMO",
    "Tanah Abang": "THB",
    "Palmerah": "PLM",
    "Kebayoran": "KBY",
    "Pondok Ranji": "PDJ",
    "Jurangmangu": "JRG",
    "Sudimara": "SDM",
    "Rawa Buntu": "RU",
    "Serpong": "SRP",
    "Cisauk": "CSK",
    "Cicayur": "CC",
    "Jatake": "JTK",
    "Parung Panjang": "PRP",
    "Cilejit": "CJT",
    "Daru": "DAR",
    "Tenjo": "TJO",
    "Tigaraksa": "TGS",
    "Cikoya": "CKY",
    "Maja": "MJ",
    "Citeras": "CTR",
    "Rangkasbitung": "RK",
    "Cikarang": "CKR",
    "Metland Telagamurni": "MTM",
    "Cibitung": "CIT",
    "Tambun": "TB",
    "Bekasi Timur": "BKT",
    "Bekasi": "BKS",
    "Kranji": "KRI",
    "Cakung": "CUK",
    "Klender Baru": "KLDB",
    "Buaran": "BUA",
    "Klender": "KLD",
    "Jatinegara": "JNG",
    "Matraman": "MTR",
    "Sudirman": "SUD",
    "Karet": "KAT",
    "Duri": "DU",
    "Angke": "AK",
    "Kampung Bandan": "KPB",
    "Pondok Jati": "POK",
    "Kramat": "KMT",
    "Gang Sentiong": "GST",
    "Pasar Senen": "PSE",
    "Kemayoran": "KMO",
    "Rajawali": "RJW",
    "Grogol": "GGL",
    "Pesing": "PSG",
    "Taman Kota": "TKO",
    "Bojong Indah": "BOI",
    "Rawa Buaya": "RW",
    "Kalideres": "KDS",
    "Poris": "PI",
    "Batu Ceper": "BPR",
    "Tanah Tinggi": "TTI",
    "Tangerang": "TNG",
    "Ancol": "AC",
    "Tanjung Priok": "TPK",
}


def canon(name: str | None) -> str | None:
    if not name:
        return None
    key = " ".join(name.strip().split()).lower()
    if key in EXCLUDE:
        return None
    return NAME_ALIAS.get(key, " ".join(name.strip().split()))


def haversine(a, b):
    R = 6371000.0
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def length_m(geom):
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    s = 0.0
    for part in parts:
        for i in range(1, len(part)):
            s += haversine(part[i - 1][:2], part[i][:2])
    return s


def max_jump(geom):
    mx = 0.0
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    for part in parts:
        for i in range(1, len(part)):
            mx = max(mx, haversine(part[i - 1][:2], part[i][:2]))
    return mx


def dist_point_to_seg(p, a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    # local equirectangular metres
    latm = math.radians((lat1 + lat2 + p[1]) / 3)
    ax, ay = lon1 * 111320 * math.cos(latm), lat1 * 110540
    bx, by = lon2 * 111320 * math.cos(latm), lat2 * 110540
    px, py = p[0] * 111320 * math.cos(latm), p[1] * 110540
    vx, vy = bx - ax, by - ay
    n2 = vx * vx + vy * vy
    if n2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / n2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def dist_to_geom(p, geom):
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    best = 1e18
    for part in parts:
        for i in range(1, len(part)):
            best = min(best, dist_point_to_seg(p, part[i - 1][:2], part[i][:2]))
    return best


def load_rel(rid: int):
    return json.loads((OSM / f"rel-{rid}.json").read_text())


def index_rel(data):
    nodes = {}
    ways = {}
    rel = None
    for e in data["elements"]:
        if e["type"] == "node" and "lat" in e:
            nodes[e["id"]] = (e["lon"], e["lat"], e.get("tags") or {})
        elif e["type"] == "way":
            ways[e["id"]] = e
        elif e["type"] == "relation" and e.get("id"):
            if rel is None or e["id"] == data["elements"][-1].get("id"):
                rel = e
    # prefer the relation whose id matches file
    for e in data["elements"]:
        if e["type"] == "relation":
            rel = e
            break
    return rel, nodes, ways


def way_coords(way, nodes):
    coords = []
    for nid in way.get("nodes") or []:
        if nid in nodes:
            lon, lat, _ = nodes[nid]
            coords.append([lon, lat])
    return coords


def assemble_ways(rel, nodes, ways, only_ids=None):
    parts = []
    for m in rel.get("members") or []:
        if m["type"] != "way":
            continue
        if only_ids is not None and m["ref"] not in only_ids:
            continue
        w = ways.get(m["ref"])
        if not w:
            continue
        coords = way_coords(w, nodes)
        if len(coords) >= 2:
            parts.append(coords)
    if not parts:
        return None
    # stitch connected runs
    used = [False] * len(parts)
    runs = []
    for i, part in enumerate(parts):
        if used[i]:
            continue
        run = list(part)
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, other in enumerate(parts):
                if used[j]:
                    continue
                o = list(other)
                if haversine(run[-1], o[0]) < 25:
                    run.extend(o[1:])
                    used[j] = True
                    changed = True
                elif haversine(run[-1], o[-1]) < 25:
                    run.extend(reversed(o[:-1]))
                    used[j] = True
                    changed = True
                elif haversine(run[0], o[-1]) < 25:
                    run = o[:-1] + run
                    used[j] = True
                    changed = True
                elif haversine(run[0], o[0]) < 25:
                    run = list(reversed(o))[:-1] + run
                    used[j] = True
                    changed = True
        runs.append(run)
    if len(runs) == 1:
        return {"type": "LineString", "coordinates": [[c[0], c[1]] for c in runs[0]]}
    return {"type": "MultiLineString", "coordinates": [[[c[0], c[1]] for c in r] for r in runs]}


def unique_way_ids(rel, extra=None):
    ids = {m["ref"] for m in (rel.get("members") or []) if m["type"] == "way"}
    if extra:
        ids |= extra
    return ids


def stop_members(rel, nodes):
    out = []
    for m in rel.get("members") or []:
        if m["type"] != "node":
            continue
        role = m.get("role") or ""
        if "stop" not in role:
            continue
        n = nodes.get(m["ref"])
        if not n:
            continue
        lon, lat, tags = n
        name = canon(tags.get("name") or tags.get("name:id"))
        if not name:
            continue
        out.append(
            {
                "osm_id": m["ref"],
                "name": name,
                "lon": lon,
                "lat": lat,
                "code": tags.get("ref") or tags.get("uic_ref") or CODES.get(name, ""),
                "railway": tags.get("railway"),
            }
        )
    return out


def geom_bbox(geom):
    pts = []
    if geom["type"] == "LineString":
        pts = geom["coordinates"]
    else:
        for p in geom["coordinates"]:
            pts.extend(p)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def line_codes_str(codes):
    return "," + ",".join(sorted(set(codes))) + ","


def main():
    issues = []
    # Load relations
    loaded = {}
    for key, spec in LINES.items():
        rids = [spec["rel"]] + spec.get("extra_rels", [])
        for rid in rids:
            if rid not in loaded:
                data = load_rel(rid)
                rel, nodes, ways = index_rel(data)
                # pick relation with matching id
                rel = next((e for e in data["elements"] if e["type"] == "relation" and e["id"] == rid), rel)
                loaded[rid] = (rel, nodes, ways)

    # Assemble per-line geometry
    line_geoms = {}
    line_way_ids = {}
    for key, spec in LINES.items():
        rel, nodes, ways = loaded[spec["rel"]]
        only = None
        if spec.get("unique_vs"):
            parent_rel, _, _ = loaded[spec["unique_vs"]]
            parent_ids = unique_way_ids(parent_rel)
            only = unique_way_ids(rel) - parent_ids
        if spec.get("extra_rels"):
            ids = unique_way_ids(rel)
            extra_nodes = dict(nodes)
            extra_ways = dict(ways)
            for erid in spec["extra_rels"]:
                erel, enodes, eways = loaded[erid]
                ids |= unique_way_ids(erel)
                extra_nodes.update(enodes)
                extra_ways.update(eways)
            # merge node/way dicts onto first rel for assemble
            nodes, ways = extra_nodes, extra_ways
            only = ids
            # dummy rel members in any order of unique ways
            rel = {"members": [{"type": "way", "ref": i} for i in only]}
        geom = assemble_ways(rel, nodes, ways, only)
        if not geom:
            issues.append({"line": key, "issue": "empty geometry"})
            continue
        line_geoms[key] = geom
        line_way_ids[key] = only if only is not None else unique_way_ids(loaded[spec["rel"]][0])
        jmp = max_jump(geom)
        if jmp > 800:
            issues.append({"line": key, "issue": f"max vertex jump {jmp:.0f} m"})

    # Physical network = unique ways across all lines
    all_ids = set()
    all_nodes = {}
    all_ways = {}
    for rid, (rel, nodes, ways) in loaded.items():
        all_ids |= unique_way_ids(rel)
        all_nodes.update(nodes)
        all_ways.update(ways)
    net_rel = {"members": [{"type": "way", "ref": i} for i in all_ids]}
    network_geom = assemble_ways(net_rel, all_nodes, all_ways, all_ids)

    # Stations: OSM members + extras, restricted to KRL.txt names
    wanted = {}
    for key, spec in LINES.items():
        for i, name in enumerate(spec["stations"], 1):
            wanted.setdefault(name, {"name": name, "lines": [], "orders": {}, "branch": None})
            wanted[name]["lines"].append(spec["line_code"])
            wanted[name]["orders"][spec["line_code"] if key != "B-nambo" else "B-nambo"] = i
            if spec.get("branch") and name in spec["stations"][1:]:
                wanted[name]["branch"] = spec["branch"]
            if name == spec.get("branch_node"):
                wanted[name]["branch"] = wanted[name].get("branch") or "junction"

    # Collect coords from OSM stop members
    osm_pts = defaultdict(list)
    for key, spec in LINES.items():
        rel, nodes, ways = loaded[spec["rel"]]
        for s in stop_members(rel, nodes):
            osm_pts[s["name"]].append(s)
        for erid in spec.get("extra_rels", []):
            erel, enodes, _ = loaded[erid]
            for s in stop_members(erel, enodes):
                osm_pts[s["name"]].append(s)

    station_feats = []
    missing = []
    far = []
    for name, meta in wanted.items():
        samples = osm_pts.get(name) or []
        if samples:
            # pick median-ish first stop node
            s = samples[0]
            lon, lat = s["lon"], s["lat"]
            osm_id = s["osm_id"]
            code = CODES.get(name) or s.get("code") or ""
            src = SRC
            src_type = SRC_TYPE
        elif name in EXTRA_STATIONS:
            ex = EXTRA_STATIONS[name]
            lon, lat, osm_id = ex["lon"], ex["lat"], ex["osm_id"]
            code = CODES.get(name) or ex.get("code") or ""
            src = "OpenStreetMap / Nominatim"
            src_type = "osm"
        else:
            missing.append(name)
            continue
        codes = sorted(set(meta["lines"]))
        interchange = len(codes) > 1
        station_type = "terminus" if name in {
            "Jakarta Kota", "Bogor", "Nambo", "Rangkasbitung", "Cikarang", "Tangerang", "Tanjung Priok"
        } else ("interchange" if interchange or name in {"Manggarai", "Jatinegara", "Kampung Bandan", "Citayam", "Tanah Abang", "Duri", "Pasar Senen"} else "station")
        if name == "Citayam":
            station_type = "branching"
        if name == "Jatinegara":
            station_type = "loop"
        if name == "Kampung Bandan":
            station_type = "loop"
        orders = meta["orders"]
        primary = codes[0]
        drail = dist_to_geom((lon, lat), network_geom) if network_geom else 9999
        if drail > STOP_TOL_M:
            far.append({"name": name, "dist_m": round(drail, 1)})
        sid = f"krl-{CODES.get(name, name).lower()}"
        station_feats.append(
            {
                "type": "Feature",
                "id": sid,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": sid,
                    "station_id": sid,
                    "station_name": name,
                    "stop_name": name,
                    "name": name,
                    "station_code": code,
                    "stop_code": code,
                    "line_name": " / ".join(
                        LINES[k]["short"] for k in ("B", "R", "C", "T", "TP") if LINES[k]["line_code"] in codes
                    ),
                    "line_code": codes[0],
                    "line_codes": line_codes_str(codes),
                    "station_order": orders.get(primary) or min(orders.values()),
                    "station_type": station_type,
                    "interchange": interchange,
                    "interchange_label": "Simpul pertukaran" if interchange or station_type in ("loop", "branching", "interchange") else "",
                    "branch": meta.get("branch") or "",
                    "active": True,
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "mode": "KRL",
                    "operator": "KAI Commuter",
                    "latitude": lat,
                    "longitude": lon,
                    "source": src,
                    "source_type": src_type,
                    "source_url": SRC_URL,
                    "license": LICENSE,
                    "geometry_source": "osm_station",
                    "osm_id": osm_id,
                    "color": COLOR,
                    "rail_dist_m": round(drail, 1),
                },
            }
        )

    # Line features
    line_feats = []
    for key, spec in LINES.items():
        geom = line_geoms.get(key)
        if not geom:
            continue
        km = round(length_m(geom) / 1000, 2)
        stops_n = len(spec["stations"])
        codes = [spec["line_code"]]
        line_feats.append(
            {
                "type": "Feature",
                "id": spec["line_id"],
                "geometry": geom,
                "properties": {
                    "id": spec["line_id"],
                    "line_id": spec["line_id"],
                    "line_name": spec["line_name"],
                    "name": spec["line_name"],
                    "route_name": spec["line_name"],
                    "line_code": spec["line_code"],
                    "line_codes": line_codes_str(codes),
                    "short": spec["short"],
                    "from_name": spec["from_name"],
                    "to_name": spec["to_name"],
                    "endpoint": spec["endpoint"],
                    "terminus": " - ".join(spec.get("terminus") or []),
                    "branch": spec.get("branch") or "",
                    "parent": spec.get("parent") or "",
                    "mode": "KRL",
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "color": COLOR,
                    "operator": "KAI Commuter",
                    "source": SRC,
                    "source_type": SRC_TYPE,
                    "source_url": SRC_URL,
                    "license": LICENSE,
                    "retrieved_at": RETRIEVED,
                    "geometry_source": "osm_rail_relation",
                    "length_km": km,
                    "stop_count": stops_n,
                    "osm_relation": spec["rel"],
                },
            }
        )

    # Physical network feature (no duplicate shared rails)
    net_feat = {
        "type": "Feature",
        "id": "krl-network",
        "geometry": network_geom,
        "properties": {
            "id": "krl-network",
            "line_id": "krl-network",
            "line_name": "Jaringan KRL",
            "name": "Jaringan KRL",
            "route_name": "Jaringan KRL",
            "line_code": "ALL",
            "line_codes": ",B,C,R,T,TP,",
            "short": "Semua",
            "endpoint": "Jabodetabek",
            "mode": "KRL",
            "status": "existing",
            "status_label": "Jaringan saat ini",
            "color": COLOR,
            "operator": "KAI Commuter",
            "source": SRC,
            "source_type": SRC_TYPE,
            "source_url": SRC_URL,
            "license": LICENSE,
            "retrieved_at": RETRIEVED,
            "geometry_source": "osm_rail_unique_ways",
            "length_km": round(length_m(network_geom) / 1000, 2) if network_geom else 0,
            "stop_count": len(station_feats),
        },
    }

    # Segments between consecutive stations (straight only as topology record, geometry clipped from rail if possible)
    segments = []
    seg_id = 0
    for key, spec in LINES.items():
        geom = line_geoms.get(key)
        names = spec["stations"]
        for i in range(len(names) - 1):
            a, b = names[i], names[i + 1]
            seg_id += 1
            segments.append(
                {
                    "type": "Feature",
                    "id": f"krl-seg-{seg_id}",
                    "geometry": geom if geom else {"type": "LineString", "coordinates": []},
                    "properties": {
                        "id": f"krl-seg-{seg_id}",
                        "segment_id": f"krl-seg-{seg_id}",
                        "from_station": a,
                        "to_station": b,
                        "line_id": spec["line_id"],
                        "line_code": spec["line_code"],
                        "branch": spec.get("branch") or "",
                        "source": SRC,
                        "source_type": SRC_TYPE,
                    },
                }
            )
    # segments file would duplicate full line geom — store topology-only JSON instead
    topo_segments = []
    for key, spec in LINES.items():
        names = spec["stations"]
        for i in range(len(names) - 1):
            topo_segments.append(
                {
                    "segment_id": f"{spec['line_id']}-{i+1}",
                    "from_station": names[i],
                    "to_station": names[i + 1],
                    "line_id": spec["line_id"],
                    "line_code": spec["line_code"],
                    "branch": spec.get("branch") or "",
                }
            )

    routes_fc = {"type": "FeatureCollection", "features": [net_feat] + line_feats}
    stops_fc = {"type": "FeatureCollection", "features": station_feats}

    corridors_meta = []
    for key, spec in LINES.items():
        geom = line_geoms.get(key)
        corridors_meta.append(
            {
                "id": spec["line_id"],
                "line_code": spec["line_code"],
                "filter_key": key,
                "name": spec["line_name"],
                "short": spec["short"],
                "endpoint": spec["endpoint"],
                "from_name": spec["from_name"],
                "to_name": spec["to_name"],
                "branch": spec.get("branch") or "",
                "stations": spec["stations"],
                "stop_count": len(spec["stations"]),
                "length_km": round(length_m(geom) / 1000, 2) if geom else None,
                "source": SRC,
                "source_type": SRC_TYPE,
            }
        )

    validation = {
        "lines": {k: {
            "geom": line_geoms[k]["type"] if k in line_geoms else None,
            "length_km": round(length_m(line_geoms[k]) / 1000, 2) if k in line_geoms else None,
            "max_jump_m": round(max_jump(line_geoms[k]), 1) if k in line_geoms else None,
            "stations_expected": len(v["stations"]),
        } for k, v in LINES.items()},
        "stations": {
            "expected": len(wanted),
            "built": len(station_feats),
            "missing": missing,
            "far_from_rail": far,
        },
        "network_km": round(length_m(network_geom) / 1000, 2) if network_geom else None,
        "issues": issues,
        "crs": "EPSG:4326",
        "color": COLOR,
        "notes": [
            "KRL.txt tidak ada di disk; struktur stasiun/branch/loop dari dokumen PASS 14.",
            "Geometri rel: OSM relation ways, bukan garis lurus antarstasiun.",
            "Cabang Nambo: ways unik rel 16877211 vs Bogor (Citayam–Nambo).",
            "Cikarang: ways unik rel via Manggarai + via Pasar Senen (loop, tidak flatten).",
            "Jatake ada di rel Green OSM. Cikoya dan Pondok Rajeg dan Karet ditambah dari OSM/Nominatim.",
            "BNI City, JIS, Gunung Putri tidak dirender sebagai stasiun KRL aktif.",
        ],
    }

    (OUT / "krl_routes.geojson").write_text(json.dumps(routes_fc, ensure_ascii=False))
    (OUT / "krl_stops.geojson").write_text(json.dumps(stops_fc, ensure_ascii=False))
    (OUT / "krl_existing.json").write_text(json.dumps({
        "corridors": corridors_meta,
        "segments": topo_segments,
        "color": COLOR,
        "crs": "EPSG:4326",
        "source": SRC,
        "source_type": SRC_TYPE,
    }, ensure_ascii=False, indent=2))
    (OUT / "krl_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2))

    # update sources.json in place
    sources_path = OUT / "sources.json"
    sources = json.loads(sources_path.read_text())
    by = {s["dataset"]: s for s in sources}
    by["krl_routes"] = {
        "dataset": "krl_routes",
        "source": SRC,
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "LineString/MultiLineString",
        "crs": "EPSG:4326",
        "count": len(line_feats),
        "notes": "Jaringan fisik KRL existing. Warna CASCADE #D83A72. OSM rel, bukan data resmi KAI.",
    }
    by["krl_stops"] = {
        "dataset": "krl_stops",
        "source": SRC,
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "Point",
        "crs": "EPSG:4326",
        "count": len(station_feats),
        "notes": "Stasiun KRL existing sesuai struktur Bogor/Nambo/Rangkasbitung/Cikarang/Tangerang/Tanjung Priok. Satu titik per stasiun.",
    }
    sources_path.write_text(json.dumps(list(by.values()), ensure_ascii=False, indent=2))

    print("routes", len(line_feats), "network", 1, "stops", len(station_feats))
    print("missing", missing)
    print("far", far)
    print("issues", issues)
    for k, v in validation["lines"].items():
        print(k, v)


if __name__ == "__main__":
    main()
