#!/usr/bin/env python3
"""PASS 15 — rebuild LRT Jabodebek + MRT Jakarta existing from OSM rail relations.

MRT&LRT.txt was not on disk; station order / topology is the PASS 15 lock:
  LRT = 18 unique stations, 2 branches + 1 shared trunk, Cawang merge.
  MRT = 13 stations, 12 edges, linear Lebak Bulus → Bundaran HI.
LRT Jakarta (Kelapa Gading–Velodrome) is excluded. MRT Phase 2 is excluded.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

OSM = Path("/tmp/cascade-data/osm")
OUT = Path("/workspace/public/data")
LRT_COLOR = "#4FAF86"
MRT_COLOR = "#247A67"
SRC = "OpenStreetMap route relations"
SRC_TYPE = "osm"
LICENSE = "ODbL"
SRC_URL = "https://www.openstreetmap.org"
RETRIEVED = "2026-09-10"
STOP_TOL_M = 120.0

LRT_CB_REL = 16036441  # Cibubur Line Harjamukti → Dukuh Atas
LRT_BK_REL = 16079478  # Bekasi Line Jatimulya → Dukuh Atas
MRT_REL = 9200637  # NS railways Lebak Bulus → Bundaran HI

# Canonical names from PASS 15 / MRT&LRT.txt structure.
LRT_CIBUBUR_FULL = [
    "Harjamukti",
    "Ciracas",
    "Kampung Rambutan",
    "TMII",
    "Cawang",
    "Ciliwung",
    "Cikoko",
    "Pancoran",
    "Kuningan",
    "Rasuna Said",
    "Setiabudi",
    "Dukuh Atas BNI",
]
LRT_BEKASI_FULL = [
    "Jatimulya",
    "Bekasi Barat",
    "Cikunir 2",
    "Cikunir 1",
    "Jatibening Baru",
    "Halim",
    "Cawang",
    "Ciliwung",
    "Cikoko",
    "Pancoran",
    "Kuningan",
    "Rasuna Said",
    "Setiabudi",
    "Dukuh Atas BNI",
]
LRT_CIBUBUR_BRANCH = ["Harjamukti", "Ciracas", "Kampung Rambutan", "TMII", "Cawang"]
LRT_BEKASI_BRANCH = [
    "Jatimulya",
    "Bekasi Barat",
    "Cikunir 2",
    "Cikunir 1",
    "Jatibening Baru",
    "Halim",
    "Cawang",
]
LRT_SHARED_TRUNK = [
    "Cawang",
    "Ciliwung",
    "Cikoko",
    "Pancoran",
    "Kuningan",
    "Rasuna Said",
    "Setiabudi",
    "Dukuh Atas BNI",
]
MRT_SEQ = [
    "Lebak Bulus",
    "Fatmawati",
    "Cipete Raya",
    "Haji Nawi",
    "Blok A",
    "Blok M",
    "ASEAN",
    "Senayan",
    "Istora",
    "Bendungan Hilir",
    "Setiabudi",
    "Dukuh Atas",
    "Bundaran HI",
]

LRT_NAME_ALIAS = {
    "taman mini": "TMII",
    "tmii": "TMII",
    "dukuh atas bank syariah indonesia": "Dukuh Atas BNI",
    "dukuh atas bni": "Dukuh Atas BNI",
    "dukuh atas bsi": "Dukuh Atas BNI",
    "kampung rambutan": "Kampung Rambutan",
    "jatibening baru": "Jatibening Baru",
    "bekasi barat": "Bekasi Barat",
    "cikunir 2": "Cikunir 2",
    "cikunir 1": "Cikunir 1",
    "rasuna said": "Rasuna Said",
}
MRT_NAME_ALIAS = {
    "lebak bulus bank syariah indonesia": "Lebak Bulus",
    "lebak bulus grab": "Lebak Bulus",
    "lebak bulus": "Lebak Bulus",
    "fatmawati indomaret": "Fatmawati",
    "fatmawati": "Fatmawati",
    "cipete raya tuku": "Cipete Raya",
    "cipete raya": "Cipete Raya",
    "haji nawi": "Haji Nawi",
    "blok a visa": "Blok A",
    "blok a": "Blok A",
    "blok m bca": "Blok M",
    "blok m": "Blok M",
    "asean headquarters": "ASEAN",
    "asean": "ASEAN",
    "senayan mastercard": "Senayan",
    "senayan": "Senayan",
    "istora mandiri": "Istora",
    "istora": "Istora",
    "bendungan hilir": "Bendungan Hilir",
    "setiabudi astra": "Setiabudi",
    "setiabudi": "Setiabudi",
    "dukuh atas bni": "Dukuh Atas",
    "dukuh atas bank syariah indonesia": "Dukuh Atas",
    "dukuh atas": "Dukuh Atas",
    "bundaran hi bank jakarta": "Bundaran HI",
    "bundaran hi": "Bundaran HI",
}
MRT_NAMING_RIGHTS = {
    "Lebak Bulus": "Grab / Bank Syariah Indonesia",
    "Fatmawati": "Indomaret",
    "Cipete Raya": "TUKU",
    "Blok A": "VISA",
    "Blok M": "BCA",
    "ASEAN": "Headquarters",
    "Senayan": "Mastercard",
    "Istora": "Mandiri",
    "Setiabudi": "Astra",
    "Dukuh Atas": "BNI",
    "Bundaran HI": "Bank Jakarta",
}
LRT_NAMING_RIGHTS = {
    "TMII": "Taman Mini",
    "Dukuh Atas BNI": "Bank Syariah Indonesia",
}
LRT_CODES = {
    "Harjamukti": "HJM",
    "Ciracas": "CRC",
    "Kampung Rambutan": "KPR",
    "TMII": "TMI",
    "Cawang": "CWG",
    "Ciliwung": "CLW",
    "Cikoko": "CKK",
    "Pancoran": "PNC",
    "Kuningan": "KNG",
    "Rasuna Said": "RSS",
    "Setiabudi": "STB",
    "Dukuh Atas BNI": "DKA",
    "Jatimulya": "JTM",
    "Bekasi Barat": "BKB",
    "Cikunir 2": "CK2",
    "Cikunir 1": "CK1",
    "Jatibening Baru": "JBB",
    "Halim": "HLM",
}
MRT_CODES = {
    "Lebak Bulus": "S13",
    "Fatmawati": "S12",
    "Cipete Raya": "S11",
    "Haji Nawi": "S10",
    "Blok A": "S09",
    "Blok M": "S08",
    "ASEAN": "S07",
    "Senayan": "S06",
    "Istora": "S05",
    "Bendungan Hilir": "S04",
    "Setiabudi": "S03",
    "Dukuh Atas": "S02",
    "Bundaran HI": "S01",
}
# Verified multimodal hubs only — not inferred from Jakarta-wide proximity.
LRT_INTERCHANGE = {
    "Cawang": ["TransJakarta"],
    "Cikoko": ["KRL", "TransJakarta"],
    "Halim": ["KA Bandara"],
    "Dukuh Atas BNI": ["MRT", "KRL", "TransJakarta", "KA Bandara"],
    "Kampung Rambutan": ["TransJakarta"],
}
MRT_INTERCHANGE = {
    "Lebak Bulus": ["TransJakarta"],
    "Blok M": ["TransJakarta"],
    "Senayan": ["TransJakarta"],
    "Istora": ["TransJakarta"],
    "Bendungan Hilir": ["TransJakarta"],
    "Dukuh Atas": ["LRT Jabodebek", "KRL", "TransJakarta"],
    "Bundaran HI": ["TransJakarta"],
}

# Names that must never appear in existing layers.
LRT_JAKARTA_EXCLUDE = {
    "kelapa gading",
    "velodrome",
    "equestrian",
    "pulomas",
    "boulevard selatan",
    "boulevard utara",
}
MRT_PHASE2_EXCLUDE = {
    "monas",
    "harmoni",
    "sawah besar",
    "mangga besar",
    "kota",
    "glodok",
    "ancol marina",
    "ancol",
}


def canon_lrt(name: str | None) -> str | None:
    if not name:
        return None
    key = " ".join(name.strip().split()).lower()
    if key in LRT_JAKARTA_EXCLUDE:
        return None
    return LRT_NAME_ALIAS.get(key, " ".join(name.strip().split()))


def canon_mrt(name: str | None) -> str | None:
    if not name:
        return None
    key = " ".join(name.strip().split()).lower()
    if key in MRT_PHASE2_EXCLUDE:
        return None
    return MRT_NAME_ALIAS.get(key, " ".join(name.strip().split()))


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
    if not geom:
        return 0.0
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    s = 0.0
    for part in parts:
        for i in range(1, len(part)):
            s += haversine(part[i - 1][:2], part[i][:2])
    return s


def max_jump(geom):
    mx = 0.0
    if not geom:
        return mx
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    for part in parts:
        for i in range(1, len(part)):
            mx = max(mx, haversine(part[i - 1][:2], part[i][:2]))
    return mx


def dist_point_to_seg(p, a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    latm = math.radians((lat1 + lat2 + p[1]) / 3)
    ax, ay = lon1 * 111320 * math.cos(latm), lat1 * 110540
    bx, by = lon2 * 111320 * math.cos(latm), lat2 * 110540
    px, py = p[0] * 111320 * math.cos(latm), p[1] * 110540
    vx, vy = bx - ax, by - ay
    n2 = vx * vx + vy * vy
    if n2 == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / n2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy)), t


def dist_to_geom(p, geom):
    if not geom:
        return 1e18
    parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
    best = 1e18
    for part in parts:
        for i in range(1, len(part)):
            d, _ = dist_point_to_seg(p, part[i - 1][:2], part[i][:2])
            best = min(best, d)
    return best


def load_rel(rid: int):
    return json.loads((OSM / f"rel-{rid}.json").read_text())


def index_rel(data, rid: int):
    nodes = {}
    ways = {}
    rel = None
    for e in data["elements"]:
        if e["type"] == "node" and "lat" in e:
            nodes[e["id"]] = (e["lon"], e["lat"], e.get("tags") or {})
        elif e["type"] == "way":
            ways[e["id"]] = e
        elif e["type"] == "relation" and e.get("id") == rid:
            rel = e
    if rel is None:
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
    if only_ids is not None and not parts:
        for wid in only_ids:
            w = ways.get(wid)
            if not w:
                continue
            coords = way_coords(w, nodes)
            if len(coords) >= 2:
                parts.append(coords)
    if not parts:
        return None
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


def unique_way_ids(rel):
    return {m["ref"] for m in (rel.get("members") or []) if m["type"] == "way"}


def flatten_line(geom):
    if not geom:
        return []
    if geom["type"] == "LineString":
        return [c[:2] for c in geom["coordinates"]]
    parts = [[c[:2] for c in p] for p in geom["coordinates"]]
    if not parts:
        return []
    run = list(parts[0])
    used = [True] + [False] * (len(parts) - 1)
    changed = True
    while changed:
        changed = False
        for j, o in enumerate(parts):
            if used[j]:
                continue
            if haversine(run[-1], o[0]) < 40:
                run.extend(o[1:])
                used[j] = True
                changed = True
            elif haversine(run[-1], o[-1]) < 40:
                run.extend(reversed(o[:-1]))
                used[j] = True
                changed = True
            elif haversine(run[0], o[-1]) < 40:
                run = o[:-1] + run
                used[j] = True
                changed = True
            elif haversine(run[0], o[0]) < 40:
                run = list(reversed(o))[:-1] + run
                used[j] = True
                changed = True
    return run


def measures(coords):
    m = [0.0]
    for i in range(1, len(coords)):
        m.append(m[-1] + haversine(coords[i - 1], coords[i]))
    return m


def nearest_along(p, coords, meas):
    best = 1e18
    along = 0.0
    hit = list(coords[0]) if coords else [p[0], p[1]]
    for i in range(1, len(coords)):
        d, t = dist_point_to_seg(p, coords[i - 1], coords[i])
        if d < best:
            best = d
            along = meas[i - 1] + t * (meas[i] - meas[i - 1])
            lon = coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0])
            lat = coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1])
            hit = [lon, lat]
    return best, along, hit


def interpolate_at(coords, meas, along):
    if not coords:
        return None
    if along <= 0:
        return list(coords[0])
    if along >= meas[-1]:
        return list(coords[-1])
    for i in range(1, len(coords)):
        if meas[i] >= along:
            span = meas[i] - meas[i - 1]
            t = 0.0 if span == 0 else (along - meas[i - 1]) / span
            return [
                coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0]),
                coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1]),
            ]
    return list(coords[-1])


def slice_line(coords, meas, a, b):
    if not coords or a is None or b is None:
        return None
    lo, hi = (a, b) if a <= b else (b, a)
    if hi - lo < 5:
        pa = interpolate_at(coords, meas, lo)
        pb = interpolate_at(coords, meas, hi)
        if pa and pb:
            return {"type": "LineString", "coordinates": [pa, pb]}
        return None
    out = [interpolate_at(coords, meas, lo)]
    for i, c in enumerate(coords):
        if lo < meas[i] < hi:
            out.append(list(c))
    end = interpolate_at(coords, meas, hi)
    if end:
        out.append(end)
    cleaned = []
    for c in out:
        if not c:
            continue
        if not cleaned or haversine(cleaned[-1], c) > 0.4:
            cleaned.append(c)
    if len(cleaned) < 2:
        return None
    return {"type": "LineString", "coordinates": cleaned}


def line_codes_str(codes):
    return "," + ",".join(sorted(set(codes))) + ","


def fc(features):
    return {"type": "FeatureCollection", "features": features}


def stop_members(rel, nodes, canon):
    out = []
    for m in rel.get("members") or []:
        if m["type"] != "node":
            continue
        role = m.get("role") or ""
        if "stop" not in role and "platform" not in role:
            continue
        n = nodes.get(m["ref"])
        if not n:
            continue
        lon, lat, tags = n
        name = canon(tags.get("name") or tags.get("name:id"))
        if not name:
            continue
        out.append({"osm_id": m["ref"], "name": name, "lon": lon, "lat": lat, "tags": tags})
    return out


def named_rail_nodes(nodes, canon):
    out = []
    for nid, (lon, lat, tags) in nodes.items():
        railway = tags.get("railway")
        if railway not in {"stop", "station", "halt"} and tags.get("public_transport") not in {
            "stop_position",
            "station",
        }:
            continue
        name = canon(tags.get("name") or tags.get("name:id"))
        if not name:
            continue
        out.append({"osm_id": nid, "name": name, "lon": lon, "lat": lat, "tags": tags})
    return out


def station_type_lrt(name, lines):
    if name == "Cawang":
        return "branching"
    if name in {"Harjamukti", "Jatimulya"}:
        return "terminus"
    if name == "Dukuh Atas BNI":
        return "terminus"
    if name in LRT_INTERCHANGE:
        return "interchange"
    return "intermediate"


def station_type_mrt(name):
    if name in {"Lebak Bulus", "Bundaran HI"}:
        return "terminus"
    if name == "Dukuh Atas":
        return "interchange"
    if name in MRT_INTERCHANGE:
        return "interchange"
    return "intermediate"


def type_label(station_type, name=None):
    if station_type == "branching" or name == "Cawang":
        return "Simpul penggabungan"
    if station_type == "interchange":
        return "Simpul pertukaran"
    if station_type == "terminus":
        return "Terminus"
    return "Stasiun antara"


def way_profile(ways, nodes, ids):
    elevated = 0.0
    underground = 0.0
    other = 0.0
    for wid in ids:
        w = ways.get(wid)
        if not w:
            continue
        coords = way_coords(w, nodes)
        if len(coords) < 2:
            continue
        km = 0.0
        for i in range(1, len(coords)):
            km += haversine(coords[i - 1], coords[i])
        tags = w.get("tags") or {}
        if tags.get("tunnel") == "yes":
            underground += km
        elif tags.get("bridge") == "yes":
            elevated += km
        else:
            other += km
    return {
        "elevated_km": round(elevated / 1000, 2),
        "underground_km": round(underground / 1000, 2),
        "other_km": round(other / 1000, 2),
    }


def make_edges(seq, stations, geom, segment_type, line_code, mode, operator, color, prefix):
    coords = flatten_line(geom)
    meas = measures(coords) if coords else []
    along = {}
    for name in seq:
        st = stations.get(name)
        if not st or not coords:
            along[name] = None
            continue
        _d, al, _hit = nearest_along((st["lon"], st["lat"]), coords, meas)
        along[name] = al
    edges = []
    issues = []
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        g = None
        src_geom = "osm_rail_relation"
        if along.get(a) is not None and along.get(b) is not None and coords:
            g = slice_line(coords, meas, along[a], along[b])
        if not g:
            sa, sb = stations.get(a), stations.get(b)
            if sa and sb:
                g = {
                    "type": "LineString",
                    "coordinates": [[sa["lon"], sa["lat"]], [sb["lon"], sb["lat"]]],
                }
                src_geom = "SIMPLIFIED"
                issues.append({"edge": f"{a}→{b}", "issue": "simplified fallback"})
        eid = f"{prefix}-{i + 1:02d}"
        edges.append(
            {
                "type": "Feature",
                "id": eid,
                "geometry": g,
                "properties": {
                    "id": eid,
                    "edge_id": eid,
                    "from_station": a,
                    "to_station": b,
                    "line": "Cibubur Line"
                    if line_code == "CB"
                    else ("Bekasi Line" if line_code == "BK" else "MRT North-South Line"),
                    "line_code": line_code,
                    "line_codes": line_codes_str([line_code] if line_code != "SHARED" else ["CB", "BK"]),
                    "mode": mode,
                    "segment_type": segment_type,
                    "active_2026": True,
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "operator": operator,
                    "source": SRC,
                    "source_type": SRC_TYPE,
                    "source_url": SRC_URL,
                    "license": LICENSE,
                    "retrieved_at": RETRIEVED,
                    "geometry_source": src_geom,
                    "length_km": round(length_m(g) / 1000, 3) if g else None,
                    "color": color,
                },
            }
        )
    return edges, issues


def line_feature(fid, name, short, endpoint, from_name, to_name, line_code, codes, geom, stop_count, operator, color, extra):
    props = {
        "id": fid,
        "line_id": fid,
        "line_name": name,
        "name": name,
        "route_name": name,
        "short": short,
        "from_name": from_name,
        "to_name": to_name,
        "endpoint": endpoint,
        "line_code": line_code,
        "line_codes": line_codes_str(codes),
        "mode": extra.get("mode"),
        "status": "existing",
        "status_label": "Jaringan saat ini",
        "active_2026": True,
        "color": color,
        "operator": operator,
        "source": SRC,
        "source_type": SRC_TYPE,
        "source_url": SRC_URL,
        "license": LICENSE,
        "retrieved_at": RETRIEVED,
        "geometry_source": extra.get("geometry_source", "osm_rail_relation"),
        "length_km": round(length_m(geom) / 1000, 2) if geom else None,
        "stop_count": stop_count,
        "segment_type": extra.get("segment_type", ""),
        "osm_relation": extra.get("osm_relation", ""),
    }
    return {"type": "Feature", "id": fid, "geometry": geom, "properties": props}


def main():
    issues = []
    cb_data = load_rel(LRT_CB_REL)
    bk_data = load_rel(LRT_BK_REL)
    mrt_data = load_rel(MRT_REL)
    cb_rel, cb_nodes, cb_ways = index_rel(cb_data, LRT_CB_REL)
    bk_rel, bk_nodes, bk_ways = index_rel(bk_data, LRT_BK_REL)
    mrt_rel, mrt_nodes, mrt_ways = index_rel(mrt_data, MRT_REL)

    cb_ids = unique_way_ids(cb_rel)
    bk_ids = unique_way_ids(bk_rel)
    shared_ids = cb_ids & bk_ids
    cb_only = cb_ids - shared_ids
    bk_only = bk_ids - shared_ids
    union_ids = cb_ids | bk_ids

    lrt_nodes = dict(cb_nodes)
    lrt_nodes.update(bk_nodes)
    lrt_ways = dict(cb_ways)
    lrt_ways.update(bk_ways)

    geom_cb = assemble_ways(cb_rel, cb_nodes, cb_ways, cb_ids)
    geom_bk = assemble_ways(bk_rel, bk_nodes, bk_ways, bk_ids)
    dummy = {"members": [{"type": "way", "ref": i} for i in shared_ids]}
    geom_shared = assemble_ways(dummy, lrt_nodes, lrt_ways, shared_ids)
    dummy_cb = {"members": [{"type": "way", "ref": i} for i in cb_only]}
    geom_cb_branch = assemble_ways(dummy_cb, lrt_nodes, lrt_ways, cb_only)
    dummy_bk = {"members": [{"type": "way", "ref": i} for i in bk_only]}
    geom_bk_branch = assemble_ways(dummy_bk, lrt_nodes, lrt_ways, bk_only)
    dummy_net = {"members": [{"type": "way", "ref": i} for i in union_ids]}
    geom_lrt_net = assemble_ways(dummy_net, lrt_nodes, lrt_ways, union_ids)
    geom_mrt = assemble_ways(mrt_rel, mrt_nodes, mrt_ways, unique_way_ids(mrt_rel))

    for key, g in [
        ("cibubur", geom_cb),
        ("bekasi", geom_bk),
        ("shared", geom_shared),
        ("cb_branch", geom_cb_branch),
        ("bk_branch", geom_bk_branch),
        ("lrt_net", geom_lrt_net),
        ("mrt", geom_mrt),
    ]:
        if not g:
            issues.append({"part": key, "issue": "empty geometry"})
        else:
            jmp = max_jump(g)
            if jmp > 800:
                issues.append({"part": key, "issue": f"max vertex jump {jmp:.0f} m"})

    # --- LRT stations (unique 18) ---
    osm_lrt = {}
    for s in stop_members(cb_rel, cb_nodes, canon_lrt) + stop_members(bk_rel, bk_nodes, canon_lrt):
        osm_lrt.setdefault(s["name"], s)
    wanted_lrt = {}
    for name in LRT_CIBUBUR_FULL:
        wanted_lrt.setdefault(name, {"name": name, "lines": []})
        wanted_lrt[name]["lines"].append("CB")
    for name in LRT_BEKASI_FULL:
        wanted_lrt.setdefault(name, {"name": name, "lines": []})
        if "BK" not in wanted_lrt[name]["lines"]:
            wanted_lrt[name]["lines"].append("BK")

    lrt_station_objs = {}
    lrt_station_feats = []
    missing_lrt = []
    far_lrt = []
    for name, meta in wanted_lrt.items():
        s = osm_lrt.get(name)
        if not s:
            missing_lrt.append(name)
            continue
        lon, lat = s["lon"], s["lat"]
        drail = dist_to_geom((lon, lat), geom_lrt_net)
        if drail > STOP_TOL_M:
            far_lrt.append({"name": name, "dist_m": round(drail, 1)})
        codes = sorted(set(meta["lines"]))
        stype = station_type_lrt(name, codes)
        interchange = name in LRT_INTERCHANGE or len(codes) > 1
        modes = LRT_INTERCHANGE.get(name, [])
        sid = f"lrt-{LRT_CODES.get(name, name).lower()}"
        line_name = " / ".join(x for x in ["Cibubur Line" if "CB" in codes else "", "Bekasi Line" if "BK" in codes else ""] if x)
        branch = "shared" if set(codes) == {"BK", "CB"} else ("cibubur" if codes == ["CB"] else "bekasi")
        if name == "Cawang":
            branch = "merge"
        obj = {
            "id": sid,
            "name": name,
            "lon": lon,
            "lat": lat,
            "osm_id": s["osm_id"],
            "code": LRT_CODES.get(name, ""),
            "lines": codes,
            "station_type": stype,
        }
        lrt_station_objs[name] = obj
        lrt_station_feats.append(
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
                    "station_code": LRT_CODES.get(name, ""),
                    "stop_code": LRT_CODES.get(name, ""),
                    "naming_rights": LRT_NAMING_RIGHTS.get(name, ""),
                    "mode": "LRT Jabodebek",
                    "line": line_name,
                    "line_name": line_name,
                    "line_code": codes[0],
                    "line_codes": line_codes_str(codes),
                    "branch": branch,
                    "station_type": stype,
                    "station_type_label": type_label(stype, name),
                    "interchange": interchange,
                    "interchange_label": type_label(stype, name) if interchange or stype in {"branching", "terminus"} else "",
                    "interchange_mode": " / ".join(modes),
                    "active_2026": True,
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "operator": "LRT Jabodebek / KAI",
                    "latitude": lat,
                    "longitude": lon,
                    "source": SRC,
                    "source_type": SRC_TYPE,
                    "source_url": SRC_URL,
                    "license": LICENSE,
                    "retrieved_at": RETRIEVED,
                    "geometry_source": "osm_station",
                    "osm_id": s["osm_id"],
                    "color": LRT_COLOR,
                    "rail_dist_m": round(drail, 1),
                },
            }
        )

    # --- MRT stations (13, from named stop nodes on the railway relation) ---
    osm_mrt = {}
    for s in named_rail_nodes(mrt_nodes, canon_mrt):
        if s["name"] in MRT_SEQ:
            osm_mrt.setdefault(s["name"], s)
    mrt_station_objs = {}
    mrt_station_feats = []
    missing_mrt = []
    far_mrt = []
    for i, name in enumerate(MRT_SEQ, 1):
        s = osm_mrt.get(name)
        if not s:
            missing_mrt.append(name)
            continue
        lon, lat = s["lon"], s["lat"]
        drail = dist_to_geom((lon, lat), geom_mrt)
        if drail > STOP_TOL_M:
            far_mrt.append({"name": name, "dist_m": round(drail, 1)})
        stype = station_type_mrt(name)
        interchange = name in MRT_INTERCHANGE
        modes = MRT_INTERCHANGE.get(name, [])
        sid = f"mrt-{MRT_CODES.get(name, name).lower()}"
        obj = {
            "id": sid,
            "name": name,
            "lon": lon,
            "lat": lat,
            "osm_id": s["osm_id"],
            "code": MRT_CODES.get(name, ""),
            "station_type": stype,
        }
        mrt_station_objs[name] = obj
        mrt_station_feats.append(
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
                    "station_code": MRT_CODES.get(name, ""),
                    "stop_code": MRT_CODES.get(name, ""),
                    "naming_rights": MRT_NAMING_RIGHTS.get(name, ""),
                    "mode": "MRT",
                    "line": "MRT North-South Line",
                    "line_name": "MRT North-South Line",
                    "line_code": "NS",
                    "line_codes": ",NS,",
                    "station_order": i,
                    "station_type": stype,
                    "station_type_label": type_label(stype, name),
                    "interchange": interchange,
                    "interchange_label": "Simpul pertukaran" if interchange else ("Terminus" if stype == "terminus" else ""),
                    "interchange_mode": " / ".join(modes),
                    "active_2026": True,
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "operator": "PT MRT Jakarta",
                    "latitude": lat,
                    "longitude": lon,
                    "source": SRC,
                    "source_type": SRC_TYPE,
                    "source_url": SRC_URL,
                    "license": LICENSE,
                    "retrieved_at": RETRIEVED,
                    "geometry_source": "osm_station",
                    "osm_id": s["osm_id"],
                    "color": MRT_COLOR,
                    "rail_dist_m": round(drail, 1),
                },
            }
        )

    # --- LRT route features (unique network + per-line; never draw shared trunk twice) ---
    lrt_line_feats = []
    lrt_line_feats.append(
        line_feature(
            "lrt-network",
            "Jaringan LRT Jabodebek",
            "Semua",
            "Harjamukti / Jatimulya - Dukuh Atas BNI",
            "Harjamukti / Jatimulya",
            "Dukuh Atas BNI",
            "ALL",
            ["CB", "BK"],
            geom_lrt_net,
            len(lrt_station_feats),
            "LRT Jabodebek / KAI",
            LRT_COLOR,
            {
                "mode": "LRT Jabodebek",
                "geometry_source": "osm_rail_unique_ways",
                "segment_type": "NETWORK",
                "osm_relation": f"{LRT_CB_REL},{LRT_BK_REL}",
            },
        )
    )
    lrt_line_feats.append(
        line_feature(
            "lrt-CB",
            "Cibubur Line",
            "Cibubur",
            "Harjamukti - Dukuh Atas BNI",
            "Harjamukti",
            "Dukuh Atas BNI",
            "CB",
            ["CB"],
            geom_cb,
            len(LRT_CIBUBUR_FULL),
            "LRT Jabodebek / KAI",
            LRT_COLOR,
            {
                "mode": "LRT Jabodebek",
                "segment_type": "CIBUBUR_FULL",
                "osm_relation": LRT_CB_REL,
            },
        )
    )
    lrt_line_feats.append(
        line_feature(
            "lrt-BK",
            "Bekasi Line",
            "Bekasi",
            "Jatimulya - Dukuh Atas BNI",
            "Jatimulya",
            "Dukuh Atas BNI",
            "BK",
            ["BK"],
            geom_bk,
            len(LRT_BEKASI_FULL),
            "LRT Jabodebek / KAI",
            LRT_COLOR,
            {
                "mode": "LRT Jabodebek",
                "segment_type": "BEKASI_FULL",
                "osm_relation": LRT_BK_REL,
            },
        )
    )

    mrt_line_feats = [
        line_feature(
            "mrt-NS",
            "MRT North-South Line",
            "Utara-Selatan",
            "Lebak Bulus - Bundaran HI",
            "Lebak Bulus",
            "Bundaran HI",
            "NS",
            ["NS"],
            geom_mrt,
            len(mrt_station_feats),
            "PT MRT Jakarta",
            MRT_COLOR,
            {
                "mode": "MRT",
                "segment_type": "LINEAR",
                "osm_relation": MRT_REL,
            },
        )
    ]

    # Unique edges only: branch edges + one shared trunk (not 12+14).
    cb_branch_edges, e1 = make_edges(
        LRT_CIBUBUR_BRANCH,
        lrt_station_objs,
        geom_cb_branch or geom_cb,
        "CIBUBUR_BRANCH",
        "CB",
        "LRT Jabodebek",
        "LRT Jabodebek / KAI",
        LRT_COLOR,
        "lrt-e-cb",
    )
    bk_branch_edges, e2 = make_edges(
        LRT_BEKASI_BRANCH,
        lrt_station_objs,
        geom_bk_branch or geom_bk,
        "BEKASI_BRANCH",
        "BK",
        "LRT Jabodebek",
        "LRT Jabodebek / KAI",
        LRT_COLOR,
        "lrt-e-bk",
    )
    shared_edges, e3 = make_edges(
        LRT_SHARED_TRUNK,
        lrt_station_objs,
        geom_shared or geom_cb,
        "SHARED_TRUNK",
        "SHARED",
        "LRT Jabodebek",
        "LRT Jabodebek / KAI",
        LRT_COLOR,
        "lrt-e-tr",
    )
    mrt_edges, e4 = make_edges(
        MRT_SEQ,
        mrt_station_objs,
        geom_mrt,
        "LINEAR",
        "NS",
        "MRT",
        "PT MRT Jakarta",
        MRT_COLOR,
        "mrt-e",
    )
    issues.extend(e1 + e2 + e3 + e4)
    lrt_edges = cb_branch_edges + bk_branch_edges + shared_edges

    lrt_profile = way_profile(lrt_ways, lrt_nodes, union_ids)
    mrt_profile = way_profile(mrt_ways, mrt_nodes, unique_way_ids(mrt_rel))

    # Topology checks
    unique_lrt = sorted(wanted_lrt)
    if len(lrt_station_feats) != 18:
        issues.append({"part": "lrt_stations", "issue": f"count {len(lrt_station_feats)} != 18"})
    if len(mrt_station_feats) != 13:
        issues.append({"part": "mrt_stations", "issue": f"count {len(mrt_station_feats)} != 13"})
    if len(mrt_edges) != 12:
        issues.append({"part": "mrt_edges", "issue": f"count {len(mrt_edges)} != 12"})
    if len(lrt_edges) != 17:
        issues.append({"part": "lrt_edges", "issue": f"count {len(lrt_edges)} != 17 (4+6+7)"})
    leak_lrt = [f["properties"]["name"] for f in lrt_station_feats if canon_lrt(f["properties"]["name"]) is None]
    leak_mrt = [
        f["properties"]["name"]
        for f in mrt_station_feats
        if " ".join(f["properties"]["name"].lower().split()) in MRT_PHASE2_EXCLUDE
    ]
    if leak_lrt:
        issues.append({"part": "lrt", "issue": f"LRT Jakarta leak {leak_lrt}"})
    if leak_mrt:
        issues.append({"part": "mrt", "issue": f"phase 2 leak {leak_mrt}"})

    lrt_graph = {
        "nodes": [
            {
                "id": o["id"],
                "name": n,
                "type": o["station_type"],
                "lines": o["lines"],
            }
            for n, o in lrt_station_objs.items()
        ],
        "edges": [
            {
                "id": e["id"],
                "from": e["properties"]["from_station"],
                "to": e["properties"]["to_station"],
                "segment_type": e["properties"]["segment_type"],
                "length_km": e["properties"]["length_km"],
            }
            for e in lrt_edges
        ],
    }
    mrt_graph = {
        "nodes": [
            {"id": o["id"], "name": n, "type": o["station_type"]}
            for n, o in mrt_station_objs.items()
        ],
        "edges": [
            {
                "id": e["id"],
                "from": e["properties"]["from_station"],
                "to": e["properties"]["to_station"],
                "length_km": e["properties"]["length_km"],
            }
            for e in mrt_edges
        ],
    }

    lrt_stats = {
        "unique_stations": len(lrt_station_feats),
        "total_edges": len(lrt_edges),
        "cibubur_branch_km": round(length_m(geom_cb_branch) / 1000, 2) if geom_cb_branch else None,
        "bekasi_branch_km": round(length_m(geom_bk_branch) / 1000, 2) if geom_bk_branch else None,
        "shared_trunk_km": round(length_m(geom_shared) / 1000, 2) if geom_shared else None,
        "harjamukti_dukuh_atas_km": round(length_m(geom_cb) / 1000, 2) if geom_cb else None,
        "jatimulya_dukuh_atas_km": round(length_m(geom_bk) / 1000, 2) if geom_bk else None,
        "network_km": round(length_m(geom_lrt_net) / 1000, 2) if geom_lrt_net else None,
        "profile": lrt_profile,
    }
    mrt_stats = {
        "total_stations": len(mrt_station_feats),
        "total_edges": len(mrt_edges),
        "terminus": 2,
        "interchange": sum(1 for f in mrt_station_feats if f["properties"]["interchange"]),
        "network_km": round(length_m(geom_mrt) / 1000, 2) if geom_mrt else None,
        "profile": mrt_profile,
    }

    lrt_corridors = [
        {
            "id": "lrt-CB",
            "line_code": "CB",
            "filter_key": "CB",
            "name": "Cibubur Line",
            "short": "Cibubur",
            "endpoint": "Harjamukti - Dukuh Atas BNI",
            "from_name": "Harjamukti",
            "to_name": "Dukuh Atas BNI",
            "branch": "cibubur",
            "stations": LRT_CIBUBUR_FULL,
            "stop_count": len(LRT_CIBUBUR_FULL),
            "length_km": lrt_stats["harjamukti_dukuh_atas_km"],
            "source": SRC,
            "source_type": SRC_TYPE,
        },
        {
            "id": "lrt-BK",
            "line_code": "BK",
            "filter_key": "BK",
            "name": "Bekasi Line",
            "short": "Bekasi",
            "endpoint": "Jatimulya - Dukuh Atas BNI",
            "from_name": "Jatimulya",
            "to_name": "Dukuh Atas BNI",
            "branch": "bekasi",
            "stations": LRT_BEKASI_FULL,
            "stop_count": len(LRT_BEKASI_FULL),
            "length_km": lrt_stats["jatimulya_dukuh_atas_km"],
            "source": SRC,
            "source_type": SRC_TYPE,
        },
    ]
    mrt_corridors = [
        {
            "id": "mrt-NS",
            "line_code": "NS",
            "filter_key": "NS",
            "name": "MRT North-South Line",
            "short": "Utara-Selatan",
            "endpoint": "Lebak Bulus - Bundaran HI",
            "from_name": "Lebak Bulus",
            "to_name": "Bundaran HI",
            "branch": "",
            "stations": MRT_SEQ,
            "stop_count": len(MRT_SEQ),
            "length_km": mrt_stats["network_km"],
            "source": SRC,
            "source_type": SRC_TYPE,
        }
    ]

    lrt_validation = {
        "unique_stations": len(lrt_station_feats),
        "expected_stations": 18,
        "station_names": [f["properties"]["name"] for f in lrt_station_feats],
        "cibubur_sequence": LRT_CIBUBUR_FULL,
        "bekasi_sequence": LRT_BEKASI_FULL,
        "shared_trunk": LRT_SHARED_TRUNK,
        "cawang_merge": "Cawang" in lrt_station_objs and set(lrt_station_objs["Cawang"]["lines"]) == {"BK", "CB"},
        "missing": missing_lrt,
        "far_from_rail": far_lrt,
        "edges": len(lrt_edges),
        "stats": lrt_stats,
        "max_jump_m": {
            "network": round(max_jump(geom_lrt_net), 1) if geom_lrt_net else None,
            "cibubur": round(max_jump(geom_cb), 1) if geom_cb else None,
            "bekasi": round(max_jump(geom_bk), 1) if geom_bk else None,
            "shared": round(max_jump(geom_shared), 1) if geom_shared else None,
        },
        "shared_way_count": len(shared_ids),
        "cibubur_unique_ways": len(cb_only),
        "bekasi_unique_ways": len(bk_only),
        "excluded": "LRT Jakarta Kelapa Gading–Velodrome (OSM rel 10693119/10693160/10693161) tidak dimasukkan.",
        "issues": issues,
        "crs": "EPSG:4326",
        "color": LRT_COLOR,
        "notes": [
            "MRT&LRT.txt tidak ada di disk; urutan stasiun dari dokumen PASS 15.",
            "Geometri: OSM light_rail relation ways, bukan garis lurus antarstasiun.",
            "Shared trunk digambar sekali (union unique ways saat filter semua).",
            "Bukan data resmi operator LRT Jabodebek.",
        ],
    }
    mrt_validation = {
        "stations": len(mrt_station_feats),
        "expected_stations": 13,
        "edges": len(mrt_edges),
        "expected_edges": 12,
        "sequence": MRT_SEQ,
        "missing": missing_mrt,
        "far_from_rail": far_mrt,
        "stats": mrt_stats,
        "max_jump_m": round(max_jump(geom_mrt), 1) if geom_mrt else None,
        "excluded": "MRT Fase 2 Bundaran HI–Kota–Ancol tidak dimasukkan.",
        "issues": [i for i in issues if str(i.get("part", "")).startswith("mrt") or "mrt" in str(i.get("edge", ""))],
        "crs": "EPSG:4326",
        "color": MRT_COLOR,
        "notes": [
            "MRT&LRT.txt tidak ada di disk; 13 stasiun Fase 1 dari dokumen PASS 15.",
            "Nama inti tanpa hak penamaan sponsor; naming_rights disimpan terpisah.",
            "Geometri: OSM subway relation 9200637, bukan data resmi MRTJ.",
            "Tidak ada cabang, loop, atau perpanjangan utara.",
        ],
    }

    # Write datasets. Keep lrt_stops/mrt_stops as the files the app already reads.
    (OUT / "lrt_routes.geojson").write_text(json.dumps(fc(lrt_line_feats), ensure_ascii=False))
    (OUT / "lrt_stops.geojson").write_text(json.dumps(fc(lrt_station_feats), ensure_ascii=False))
    (OUT / "lrt_stations.geojson").write_text(json.dumps(fc(lrt_station_feats), ensure_ascii=False))
    (OUT / "lrt_edges.geojson").write_text(json.dumps(fc(lrt_edges), ensure_ascii=False))
    (OUT / "lrt_existing.json").write_text(
        json.dumps(
            {
                "corridors": lrt_corridors,
                "graph": lrt_graph,
                "stats": lrt_stats,
                "color": LRT_COLOR,
                "crs": "EPSG:4326",
                "source": SRC,
                "source_type": SRC_TYPE,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    (OUT / "lrt_validation.json").write_text(json.dumps(lrt_validation, ensure_ascii=False, indent=2))
    (OUT / "lrt_network_graph.json").write_text(json.dumps(lrt_graph, ensure_ascii=False, indent=2))

    (OUT / "mrt_routes.geojson").write_text(json.dumps(fc(mrt_line_feats), ensure_ascii=False))
    (OUT / "mrt_stops.geojson").write_text(json.dumps(fc(mrt_station_feats), ensure_ascii=False))
    (OUT / "mrt_stations.geojson").write_text(json.dumps(fc(mrt_station_feats), ensure_ascii=False))
    (OUT / "mrt_edges.geojson").write_text(json.dumps(fc(mrt_edges), ensure_ascii=False))
    (OUT / "mrt_existing.json").write_text(
        json.dumps(
            {
                "corridors": mrt_corridors,
                "graph": mrt_graph,
                "stats": mrt_stats,
                "color": MRT_COLOR,
                "crs": "EPSG:4326",
                "source": SRC,
                "source_type": SRC_TYPE,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    (OUT / "mrt_validation.json").write_text(json.dumps(mrt_validation, ensure_ascii=False, indent=2))
    (OUT / "mrt_network_graph.json").write_text(json.dumps(mrt_graph, ensure_ascii=False, indent=2))

    sources_path = OUT / "sources.json"
    sources = json.loads(sources_path.read_text())
    by = {s["dataset"]: s for s in sources}
    by["lrt_routes"] = {
        "dataset": "lrt_routes",
        "source": "OpenStreetMap LRT Jabodebek Cibubur + Bekasi route relations",
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "LineString/MultiLineString",
        "crs": "EPSG:4326",
        "count": 2,
        "notes": "LRT Jabodebek existing. 2 branch + 1 shared trunk. Warna #4FAF86. Bukan LRT Jakarta. OSM, bukan data resmi operator.",
    }
    by["lrt_stops"] = {
        "dataset": "lrt_stops",
        "source": "OpenStreetMap LRT Jabodebek stop members",
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "Point",
        "crs": "EPSG:4326",
        "count": len(lrt_station_feats),
        "notes": "18 stasiun unik. Cawang merge. Shared trunk tidak diduplikasi.",
    }
    by["mrt_routes"] = {
        "dataset": "mrt_routes",
        "source": "OpenStreetMap MRT Jakarta North-South Line",
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "LineString",
        "crs": "EPSG:4326",
        "count": 1,
        "notes": "MRT Jakarta Fase 1 Lebak Bulus–Bundaran HI. Warna #247A67. Bukan data resmi MRTJ. Fase 2 tidak termasuk.",
    }
    by["mrt_stops"] = {
        "dataset": "mrt_stops",
        "source": "OpenStreetMap MRT Jakarta stop positions on NS railway relation",
        "url": SRC_URL,
        "source_type": SRC_TYPE,
        "license": LICENSE,
        "geometry_type": "Point",
        "crs": "EPSG:4326",
        "count": len(mrt_station_feats),
        "notes": "13 stasiun existing. Nama inti tanpa sponsor. Satu titik per stasiun.",
    }
    sources_path.write_text(json.dumps(list(by.values()), ensure_ascii=False, indent=2))

    print("LRT stations", len(lrt_station_feats), "expected 18")
    print("LRT edges", len(lrt_edges), "expected 17")
    print("LRT names", [f["properties"]["name"] for f in lrt_station_feats])
    print("LRT missing", missing_lrt, "far", far_lrt)
    print("LRT stats", json.dumps(lrt_stats))
    print("MRT stations", len(mrt_station_feats), "expected 13")
    print("MRT edges", len(mrt_edges), "expected 12")
    print("MRT names", [f["properties"]["name"] for f in mrt_station_feats])
    print("MRT missing", missing_mrt, "far", far_mrt)
    print("MRT stats", json.dumps(mrt_stats))
    print("issues", issues)
    print("geom types", {
        "cb": geom_cb["type"] if geom_cb else None,
        "bk": geom_bk["type"] if geom_bk else None,
        "shared": geom_shared["type"] if geom_shared else None,
        "net": geom_lrt_net["type"] if geom_lrt_net else None,
        "mrt": geom_mrt["type"] if geom_mrt else None,
    })


if __name__ == "__main__":
    main()
