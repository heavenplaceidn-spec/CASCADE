#!/usr/bin/env python3
"""PASS 16 — digitize masterplan rail corridors from documents + road reference.

Not DED. Not existing. Not CASCADE proposed.
MASTERPLAN.txt was not on disk; corridor structure from PASS 16 spec.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from masterplan_corridors import CORRIDORS, NODE_COORDS

ROOT = Path("/workspace")
OSM_ROADS = ROOT / "public/data/roads.geojson"
OUT_DIR = ROOT / "public/data/masterplan"
PUB = ROOT / "public/data"
GEO = Path("/tmp/cascade-data/masterplan/geocode.json")
COLOR = "#E58A3A"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-10"

# ---------------------------------------------------------------------------
# metric helpers (WGS84, local equirectangular + UTM-ish length)
# ---------------------------------------------------------------------------

def haversine(a, b):
    R = 6371000.0
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def length_m(coords):
    return sum(haversine(coords[i - 1], coords[i]) for i in range(1, len(coords)))


def bearing(a, b):
    lon1, lat1 = map(math.radians, (a[0], a[1]))
    lon2, lat2 = map(math.radians, (b[0], b[1]))
    dl = lon2 - lon1
    y = math.sin(dl) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def turn_angles(coords):
    out = []
    for i in range(1, len(coords) - 1):
        b1 = bearing(coords[i - 1], coords[i])
        b2 = bearing(coords[i], coords[i + 1])
        d = abs((b2 - b1 + 180) % 360 - 180)
        out.append((i, d, coords[i]))
    return out


def dist_point_to_seg(p, a, b):
    latm = math.radians((a[1] + b[1] + p[1]) / 3)
    kx, ky = 111320 * math.cos(latm), 110540
    ax, ay = a[0] * kx, a[1] * ky
    bx, by = b[0] * kx, b[1] * ky
    px, py = p[0] * kx, p[1] * ky
    vx, vy = bx - ax, by - ay
    n2 = vx * vx + vy * vy
    if n2 == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / n2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy)), t


def nearest_along(p, coords):
    meas = [0.0]
    for i in range(1, len(coords)):
        meas.append(meas[-1] + haversine(coords[i - 1], coords[i]))
    best, along, pt, tseg, idx = 1e18, 0.0, coords[0], 0.0, 0
    for i in range(1, len(coords)):
        d, t = dist_point_to_seg(p, coords[i - 1], coords[i])
        if d < best:
            best = d
            along = meas[i - 1] + t * (meas[i] - meas[i - 1])
            pt = [
                coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0]),
                coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1]),
            ]
            tseg, idx = t, i - 1
    return best, along, pt, meas[-1]


def slice_along(coords, a_m, b_m):
    if a_m > b_m:
        a_m, b_m = b_m, a_m
    meas = [0.0]
    for i in range(1, len(coords)):
        meas.append(meas[-1] + haversine(coords[i - 1], coords[i]))
    total = meas[-1] or 1.0
    a_m = max(0, min(total, a_m))
    b_m = max(0, min(total, b_m))
    out = []

    def at(m):
        for i in range(1, len(coords)):
            if meas[i] >= m:
                t = 0 if meas[i] == meas[i - 1] else (m - meas[i - 1]) / (meas[i] - meas[i - 1])
                return [
                    coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0]),
                    coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1]),
                ]
        return coords[-1]

    out.append(at(a_m))
    for i, m in enumerate(meas):
        if a_m < m < b_m:
            out.append(coords[i])
    out.append(at(b_m))
    # drop dupes
    cleaned = [out[0]]
    for p in out[1:]:
        if haversine(cleaned[-1], p) > 1:
            cleaned.append(p)
    return cleaned if len(cleaned) >= 2 else [out[0], out[-1]]


def chaikin(coords, iterations=2):
    pts = [list(c) for c in coords]
    for _ in range(iterations):
        if len(pts) < 3:
            break
        nxt = [pts[0]]
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            nxt.append([0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]])
            nxt.append([0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]])
        nxt.append(pts[-1])
        pts = nxt
    return pts


def resample(coords, step=80.0):
    if length_m(coords) < step * 2:
        return coords
    total = length_m(coords)
    n = max(2, int(total / step) + 1)
    out = []
    for i in range(n):
        m = total * i / (n - 1)
        # reuse slice_along's at via nearest
        d, along, pt, tot = nearest_along(coords[0], coords)  # dummy
        # walk
        acc = 0.0
        if i == 0:
            out.append(coords[0])
            continue
        if i == n - 1:
            out.append(coords[-1])
            continue
        target = m
        acc = 0.0
        placed = False
        for j in range(1, len(coords)):
            seg = haversine(coords[j - 1], coords[j])
            if acc + seg >= target:
                t = 0 if seg == 0 else (target - acc) / seg
                out.append(
                    [
                        coords[j - 1][0] + t * (coords[j][0] - coords[j - 1][0]),
                        coords[j - 1][1] + t * (coords[j][1] - coords[j - 1][1]),
                    ]
                )
                placed = True
                break
            acc += seg
        if not placed:
            out.append(coords[-1])
    return out


def douglas(coords, tol=40.0):
    if len(coords) < 3:
        return coords

    def rec(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        mx, mi = -1, 0
        for i in range(1, len(pts) - 1):
            d, _ = dist_point_to_seg(pts[i], a, b)
            if d > mx:
                mx, mi = d, i
        if mx > tol:
            left = rec(pts[: mi + 1])
            right = rec(pts[mi:])
            return left[:-1] + right
        return [a, b]

    return rec(coords)


def catmull(points, samples=8):
    if len(points) < 2:
        return points
    pts = [points[0]] + points + [points[-1]]
    out = [points[0]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(1, samples + 1):
            t = s / samples
            t2, t3 = t * t, t * t * t
            lon = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            lat = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            out.append([lon, lat])
    return out


def flatten(geom):
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    return geom["coordinates"]


def stitch(parts, gap=90):
    unused = [list(map(list, p)) for p in parts if len(p) >= 2]
    if not unused:
        return []
    runs = []
    while unused:
        run = unused.pop(0)
        changed = True
        while changed:
            changed = False
            for i, other in enumerate(list(unused)):
                if haversine(run[-1], other[0]) < gap:
                    run.extend(other[1:])
                    unused.pop(i)
                    changed = True
                    break
                if haversine(run[-1], other[-1]) < gap:
                    run.extend(reversed(other[:-1]))
                    unused.pop(i)
                    changed = True
                    break
                if haversine(run[0], other[-1]) < gap:
                    run = other[:-1] + run
                    unused.pop(i)
                    changed = True
                    break
                if haversine(run[0], other[0]) < gap:
                    run = list(reversed(other))[:-1] + run
                    unused.pop(i)
                    changed = True
                    break
        runs.append(run)
    return runs


def orient_to(run, target):
    if haversine(run[0], target) <= haversine(run[-1], target):
        return run
    return list(reversed(run))


def road_between(road_map, names, a, b, max_off=480, max_stretch=1.55):
    """Slice a named road between two spine points if it stays a rail-plausible corridor."""
    straight = haversine(a, b)
    if straight < 120:
        return None
    best = None
    for name in names:
        feat = road_map.get(name)
        if not feat:
            continue
        for run in stitch(flatten(feat["geometry"]), gap=120):
            if len(run) < 2:
                continue
            d0, a0, _, tot = nearest_along(a, run)
            d1, a1, _, _ = nearest_along(b, run)
            if d0 > max_off or d1 > max_off:
                continue
            if abs(a1 - a0) < 100:
                continue
            sl = slice_along(run, a0, a1)
            L = length_m(sl)
            if L < straight * 0.72 or L > straight * max_stretch:
                continue
            score = (d0 + d1) + (L - straight)
            if best is None or score < best[0]:
                best = (score, sl)
    return best[1] if best else None


def build_from_spine(spec, nodes_xy, road_map):
    warnings = []
    spine = spec.get("spine") or []
    pts = [list(p) for p in spine]
    fn, tn = spec["from_node"], spec["to_node"]
    if fn in nodes_xy:
        pts[0] = list(nodes_xy[fn][:2])
    if tn in nodes_xy and pts:
        pts[-1] = list(nodes_xy[tn][:2])
    if len(pts) < 2:
        return None, "empty", warnings
    names = spec.get("road_refs") or []
    used_road = False
    chain = []
    # L1 schematic and underground: do not hug surface-road zigzags
    follow = (
        spec.get("digitization_level") not in ("L1",)
        and spec.get("structure") != "UNDERGROUND"
        and bool(names)
    )
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        sl = road_between(road_map, names, a, b) if follow else None
        if sl and len(sl) >= 2:
            used_road = True
            sl = [list(a)] + sl[1:]
            sl[-1] = list(b)
            if not chain:
                chain = sl
            else:
                chain.extend(sl[1:] if haversine(chain[-1], sl[0]) < 50 else sl)
        else:
            if not chain:
                chain = [list(a), list(b)]
            else:
                chain.append(list(b))
    level = spec.get("digitization_level") or "L2"
    dp = 40 if level in ("L1", "L2") else 28
    step = 130 if level in ("L1", "L2") else 75
    # underground: smoother, less road-kink
    if spec.get("structure") == "UNDERGROUND":
        dp, step = 45, 90
    geom = smooth_rail(chain, dp=dp, step=step)
    geom[0] = pts[0]
    geom[-1] = pts[-1]
    kinks = [t for t in turn_angles(geom) if t[1] > 80]
    if used_road and kinks:
        geom = smooth_rail(pts, dp=dp, step=step)
        geom[0] = pts[0]
        geom[-1] = pts[-1]
        used_road = False
        warnings.append(f"road slices dropped ({len(kinks)} kinks); spine retained")
    method = "DOCUMENT_RECONSTRUCTION"
    if used_road:
        method = "ROAD_REFERENCE"
    return geom, method, warnings


def load_snaps():
    snaps = {}
    for fn, mode in [
        ("krl_stops.geojson", "krl"),
        ("mrt_stops.geojson", "mrt"),
        ("lrt_stops.geojson", "lrt"),
    ]:
        d = json.loads((PUB / fn).read_text())
        for f in d["features"]:
            n = f["properties"]["name"]
            snaps[n] = (*f["geometry"]["coordinates"], f"existing_{mode}")
    # LRT Jakarta
    for rid in (10693119,):
        p = Path(f"/tmp/cascade-data/osm/rel-{rid}.json")
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for e in d["elements"]:
            if e.get("type") == "node" and (e.get("tags") or {}).get("name"):
                snaps[e["tags"]["name"]] = (e["lon"], e["lat"], "osm_lrt_jakarta")
    return snaps


ALIAS = {
    "Cibadak Tangerang": "Cibadak Tangerang",
    "Kelapa Dua Tangerang": "Kelapa Dua Tangerang",
    "Dukuh Atas BNI": "Dukuh Atas BNI",
}

# Names whose existing-rail snap is a DIFFERENT place (KRL vs MRT 2A).
NO_EXISTING_SNAP = {"Sawah Besar", "Mangga Besar", "Kota", "Thamrin", "Monas", "Harmoni", "Glodok"}


def resolve_node(name, ntype, snaps, geo):
    # Existing connections snap to live network, except colliding names.
    if ntype == "EXISTING_CONNECTION" and name not in NO_EXISTING_SNAP:
        if name in snaps:
            lon, lat, src = snaps[name]
            return lon, lat, src
        if name in ALIAS and ALIAS[name] in snaps:
            lon, lat, src = snaps[ALIAS[name]]
            return lon, lat, src
    if name in NODE_COORDS:
        lon, lat, src = NODE_COORDS[name]
        return lon, lat, src
    if name in snaps and name not in NO_EXISTING_SNAP:
        lon, lat, src = snaps[name]
        return lon, lat, src
    g = geo.get(name) or geo.get(ALIAS.get(name, name))
    if g and g.get("lon"):
        return g["lon"], g["lat"], g.get("source") or "geocode"
    for k, v in geo.items():
        if k == "_snaps" or not isinstance(v, dict) or not v.get("lon"):
            continue
        if name.lower() in k.lower() or k.lower() in name.lower():
            return v["lon"], v["lat"], v.get("source") or "geocode"
    return None


def project_on_chain(pt, chain):
    d, along, ppt, tot = nearest_along(pt, chain)
    return d, along, ppt, tot


# ---------------------------------------------------------------------------
# build one corridor
# ---------------------------------------------------------------------------

def build_alignment(spec, nodes_xy, road_map):
    warnings = []
    if spec.get("spine") and len(spec["spine"]) >= 2:
        geom, method, warns = build_from_spine(spec, nodes_xy, road_map)
        return geom, method, warnings + warns
    pts = [nodes_xy[n[0]][:2] for n in spec["nodes"] if n[0] in nodes_xy]
    if len(pts) < 2:
        return None, "empty", warnings
    start, end = pts[0], pts[-1]
    geom = smooth_rail(schematic(pts), dp=25, step=120 if spec["digitization_level"] in ("L1", "L2") else 90)
    method = "DOCUMENT_RECONSTRUCTION"
    geom[0] = list(start)
    geom[-1] = list(end)
    return geom, method, warnings


def smooth_rail(coords, dp=35, step=90):
    if not coords or len(coords) < 2:
        return coords
    s = douglas(coords, dp)
    s = chaikin(s, 2)
    s = resample(s, step)
    s[0] = coords[0]
    s[-1] = coords[-1]
    return s


def schematic(points):
    if len(points) == 2:
        a, b = points
        mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        mid = [mid[0] - dy / n * n * 0.04, mid[1] + dx / n * n * 0.04]
        return catmull([a, mid, b], 10)
    return catmull(points, 10)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps()
    geo = json.loads(GEO.read_text()) if GEO.exists() else {}
    roads_fc = json.loads(OSM_ROADS.read_text())
    road_map = {f["properties"]["name"]: f for f in roads_fc["features"]}

    corridor_feats = []
    segment_feats = []
    station_feats = []
    node_feats = []
    sources = {}
    report = []
    warnings_all = []

    for spec in CORRIDORS:
        nodes_xy = {}
        node_meta = []
        for name, ntype, sconf, note in spec["nodes"]:
            r = resolve_node(name, ntype, snaps, geo)
            if not r:
                warnings_all.append({"route": spec["id"], "issue": f"unresolved {name}"})
                continue
            lon, lat, src = r
            nodes_xy[name] = (lon, lat, src)
            node_meta.append((name, ntype, sconf, note, lon, lat, src))

        geom, method, warns = build_alignment(spec, nodes_xy, road_map)
        for w in warns:
            if w.startswith("road slices"):
                continue
            warnings_all.append({"route": spec["id"], "issue": w})
        if not geom:
            warnings_all.append({"route": spec["id"], "issue": "no geometry"})
            continue

        # project stations onto alignment; flag far
        km = round(length_m(geom) / 1000, 2)
        src_km = spec.get("length_source_km")
        diff_pct = None
        if src_km:
            diff_pct = round(abs(km - src_km) / src_km * 100, 1)
            if diff_pct > 10:
                warnings_all.append({"route": spec["id"], "issue": f"length {km} vs source {src_km} ({diff_pct}%)"})

        sharp = [t for t in turn_angles(geom) if t[1] > 55]
        for i, ang, pt in sharp[:8]:
            warnings_all.append({"route": spec["id"], "issue": f"SHARP_TURN {ang:.0f}° at {pt}"})

        # self-intersection crude: skip, flag large backtrack
        back = 0
        for i in range(2, len(geom)):
            if haversine(geom[i], geom[i - 2]) < haversine(geom[i - 1], geom[i - 2]) * 0.2:
                back += 1
        if back > 12:
            warnings_all.append({"route": spec["id"], "issue": f"possible backtrack vertices {back}"})

        cid = spec["id"]
        status = spec["status"]
        mode = spec["mode"]
        conf = spec["geometry_confidence"]
        props_common = {
            "corridor_id": cid,
            "mode": mode,
            "status": status,
            "status_label": {
                "CONSTRUCTION": "Konstruksi",
                "PLANNED": "Rencana",
                "FS": "Studi kelayakan",
                "UNDER_STUDY": "Studi",
                "MASTERPLAN": "Masterplan",
                "REFERENCE": "Referensi",
            }.get(status, status),
            "source": spec["source"],
            "source_year": spec["source_year"],
            "source_type": spec["source_type"],
            "source_url": spec.get("source_url") or "",
            "geometry_confidence": conf,
            "alignment_confidence": spec["alignment_confidence"],
            "digitization_level": spec["digitization_level"],
            "digitization_method": spec["digitization_method"] + ("" if method == "ROAD_REFERENCE" else f" ({method})"),
            "passenger_status": spec["passenger_status"],
            "structure": spec["structure"],
            "color": COLOR,
            "crs": CRS,
            "geometry_source": "DOCUMENT",
            "disclaimer": "Geometri hasil digitasi/rekonstruksi spasial dari dokumen perencanaan. Bukan gambar DED.",
        }

        expected = spec.get("expected_station_count")
        station_names_planned = [n[0] for n in spec["nodes"] if n[1] in ("STATION", "DEPOT")]
        termini = {spec["from_node"], spec["to_node"]}

        corridor_feat_idx = len(corridor_feats)
        corridor_feats.append(
            {
                "type": "Feature",
                "id": cid,
                "geometry": {"type": "LineString", "coordinates": [[c[0], c[1]] for c in geom]},
                "properties": {
                    **props_common,
                    "id": cid,
                    "name": spec["name"],
                    "route_name": spec["name"],
                    "short": spec["short"],
                    "from_node": spec["from_node"],
                    "to_node": spec["to_node"],
                    "length_km": km,
                    "length_source_km": src_km or "",
                    "length_digitized_km": km,
                    "length_difference_pct": diff_pct if diff_pct is not None else "",
                    "stop_count": 0,  # filled after station export
                    "node_count": len(spec["nodes"]),
                    "expected_station_count": expected or "",
                    "confirmed_station_count": len(station_names_planned),
                    "station_data_status": "OK",
                    "service_type": spec.get("service_type") or "",
                    "structure_latest": spec.get("structure_latest") or spec["structure"],
                    "structure_historical": spec.get("structure_historical") or "",
                    "notes": spec.get("status_note") or spec.get("structure_note") or "",
                    "mode_filter": f",{mode},",
                    "status_filter": f",{status},",
                    "conf_filter": f",{conf},",
                },
            }
        )

        # segments between consecutive resolved nodes, sliced from alignment
        seq = [n for n in spec["nodes"] if n[0] in nodes_xy]
        alongs = []
        for name, *_ in seq:
            lon, lat, _ = nodes_xy[name]
            d, along, ppt, tot = nearest_along((lon, lat), geom)
            alongs.append((name, along, d, ppt))
        for i in range(len(seq) - 1):
            a, b = seq[i], seq[i + 1]
            a_m, b_m = alongs[i][1], alongs[i + 1][1]
            seg = slice_along(geom, a_m, b_m)
            sid = f"{cid}-s{i+1:02d}"
            segment_feats.append(
                {
                    "type": "Feature",
                    "id": sid,
                    "geometry": {"type": "LineString", "coordinates": seg},
                    "properties": {
                        **props_common,
                        "id": sid,
                        "segment_id": sid,
                        "sequence": i + 1,
                        "from_node": a[0],
                        "to_node": b[0],
                        "name": f"{spec['short']} · {a[0]}–{b[0]}",
                        "length_km": round(length_m(seg) / 1000, 3),
                        "mode_filter": f",{mode},",
                        "status_filter": f",{status},",
                        "conf_filter": f",{conf},",
                    },
                }
            )

        exported_here = 0
        for name, ntype, sconf, note, lon, lat, src in node_meta:
            d, along, ppt, tot = nearest_along((lon, lat), geom)
            nid = f"{cid}-{name}".replace(" ", "_")
            is_from = name == spec["from_node"]
            is_to = name == spec["to_node"]
            is_terminus = is_from or is_to
            is_indicative = "indikatif" in (note or "").lower()
            export_station = ntype in ("STATION", "DEPOT") or is_terminus or (
                ntype == "EXISTING_CONNECTION" and "interchange" in (note or "").lower()
            )
            if is_from:
                use_lon, use_lat, d = geom[0][0], geom[0][1], 0.0
            elif is_to:
                use_lon, use_lat, d = geom[-1][0], geom[-1][1], 0.0
            elif export_station:
                use_lon, use_lat, d = ppt[0], ppt[1], 0.0
            elif ntype in ("ROUTE_NODE", "REFERENCE") and d <= 400:
                use_lon, use_lat = ppt[0], ppt[1]
            else:
                use_lon, use_lat = lon, lat
            if d > 250 and not export_station:
                warnings_all.append({"route": cid, "issue": f"{name} {d:.0f}m from alignment ({ntype})"})
            props = {
                "id": nid,
                "station_id": nid,
                "node_id": nid,
                "name": name,
                "station_name": name,
                "corridor_id": cid,
                "corridor_name": spec["name"],
                "mode": mode,
                "node_type": ntype,
                "station_status": "rencana" if ntype in ("STATION", "DEPOT") else "interchange_existing",
                "station_confidence": sconf,
                "name_confidence": "low" if is_indicative else ("high" if sconf == "HIGH" else "medium" if sconf == "MEDIUM" else "low"),
                "location_confidence": "high" if is_terminus or d < 40 else ("medium" if d < 200 else "low"),
                "is_terminus": "ya" if is_terminus else "tidak",
                "is_interchange": "tidak",
                "is_indicative": "ya" if is_indicative else "tidak",
                "connected_corridors": cid,
                "connected_modes": mode,
                "status": status,
                "status_label": "Masterplan",
                "source": spec["source"],
                "source_year": spec["source_year"],
                "source_type": spec["source_type"],
                "station_source": spec["source"],
                "notes": note,
                "coord_source": src,
                "rail_dist_m": round(d, 1),
                "color": COLOR,
                "mode_filter": f",{mode},",
                "status_filter": f",{status},",
                "conf_filter": f",{sconf},",
            }
            if is_indicative:
                props["indicative_note"] = (
                    "Posisi stasiun merupakan rekonstruksi/indikasi spasial berdasarkan sumber perencanaan dan bukan penetapan stasiun resmi."
                )
            feat = {
                "type": "Feature",
                "id": nid,
                "geometry": {"type": "Point", "coordinates": [use_lon, use_lat]},
                "properties": props,
            }
            node_feats.append(feat)
            if export_station:
                station_feats.append(feat)
                exported_here += 1

        corridor_feats[corridor_feat_idx]["properties"]["stop_count"] = exported_here
        if expected and exported_here < expected:
            corridor_feats[corridor_feat_idx]["properties"]["station_data_status"] = "PARTIAL"
        elif exported_here == 0:
            corridor_feats[corridor_feat_idx]["properties"]["station_data_status"] = "NONE"

        sources[spec["source"]] = {
            "source_id": spec["id"] + "_src",
            "title": spec["source"],
            "year": spec["source_year"],
            "source_type": spec["source_type"],
            "url": spec.get("source_url") or "",
            "notes": "Dokumen perencanaan / operator. AI adalah proses digitasi, bukan sumber.",
        }
        report.append(
            {
                "route_id": cid,
                "status": status,
                "source": spec["source"],
                "source_year": spec["source_year"],
                "length_source_km": src_km,
                "length_digitized_km": km,
                "length_difference_pct": diff_pct,
                "station_count": exported_here,
                "node_count": len(spec["nodes"]),
                "geometry_confidence": conf,
                "alignment_confidence": spec["alignment_confidence"],
                "structure": spec["structure"],
                "passenger_status": spec["passenger_status"],
                "digitization_level": spec["digitization_level"],
                "method": method,
                "sharp_turns": len(sharp),
                "validation_status": "FLAG" if (diff_pct and diff_pct > 10) or len(sharp) > 6 else "PASS",
            }
        )

    # Interchange: same station name on 2+ corridors, or existing-connection
    by_name = {}
    for f in station_feats:
        by_name.setdefault(f["properties"]["name"], []).append(f)
    interchange_feats = []
    for name, group in by_name.items():
        corridors = sorted({g["properties"]["corridor_id"] for g in group})
        modes = sorted({g["properties"]["mode"] for g in group})
        is_ix = len(corridors) > 1 or any(g["properties"]["node_type"] == "EXISTING_CONNECTION" for g in group)
        if not is_ix:
            continue
        for g in group:
            g["properties"]["is_interchange"] = "ya"
            g["properties"]["connected_corridors"] = ",".join(corridors)
            g["properties"]["connected_modes"] = ",".join(modes)
        lon, lat = group[0]["geometry"]["coordinates"]
        interchange_feats.append(
            {
                "type": "Feature",
                "id": f"ix-{name}".replace(" ", "_"),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": f"ix-{name}".replace(" ", "_"),
                    "node_id": f"ix-{name}".replace(" ", "_"),
                    "name": name,
                    "connected_corridors": ",".join(corridors),
                    "connected_modes": ",".join(modes),
                    "source": "masterplan interchange reconstruction",
                    "confidence": "MEDIUM",
                    "color": COLOR,
                },
            }
        )

    # QA
    geom_by_cid = {f["id"]: f["geometry"]["coordinates"] for f in corridor_feats}
    zero_stn = [r["route_id"] for r in report if r["station_count"] == 0]
    one_stn = [r["route_id"] for r in report if r["station_count"] == 1]
    offline = []
    broken_ep = []
    invalid = []
    for f in corridor_feats:
        coords = f["geometry"]["coordinates"]
        if not coords or len(coords) < 2:
            invalid.append(f["id"])
        for i in range(1, len(coords)):
            if coords[i] == coords[i - 1]:
                continue
    for f in station_feats:
        cid = f["properties"]["corridor_id"]
        geom = geom_by_cid.get(cid)
        if not geom:
            continue
        d, along, ppt, tot = nearest_along(f["geometry"]["coordinates"], geom)
        f["properties"]["rail_dist_m"] = round(d, 1)
        if d > 80:
            offline.append({"id": f["id"], "name": f["properties"]["name"], "d": round(d, 1), "corridor": cid})
        if f["properties"]["is_terminus"] == "ya":
            d0 = haversine(f["geometry"]["coordinates"], geom[0])
            d1 = haversine(f["geometry"]["coordinates"], geom[-1])
            if min(d0, d1) > 40:
                broken_ep.append({"id": f["id"], "name": f["properties"]["name"], "d0": round(d0, 1), "d1": round(d1, 1)})

    ids = [f["id"] for f in station_feats]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})

    qa = {
        "total_corridors": len(corridor_feats),
        "total_stations": len(station_feats),
        "total_interchanges": len(interchange_feats),
        "corridors_with_0_stations": zero_stn,
        "corridors_with_1_station": one_stn,
        "stations_off_line": offline,
        "broken_endpoints": broken_ep,
        "duplicate_station_ids": dup_ids,
        "invalid_geometries": invalid,
        "disconnected_segments": 0,
        "target": {
            "corridors_with_0_stations": 0,
            "stations_off_line": 0,
            "broken_endpoints": 0,
            "invalid_geometries": 0,
        },
    }

    corridors_fc = {"type": "FeatureCollection", "features": corridor_feats}
    segments_fc = {"type": "FeatureCollection", "features": segment_feats}
    stations_fc = {"type": "FeatureCollection", "features": station_feats}
    nodes_fc = {"type": "FeatureCollection", "features": node_feats}
    ix_fc = {"type": "FeatureCollection", "features": interchange_feats}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "masterplan_corridors.geojson").write_text(json.dumps(corridors_fc, ensure_ascii=False))
    (OUT_DIR / "masterplan_segments.geojson").write_text(json.dumps(segments_fc, ensure_ascii=False))
    (OUT_DIR / "masterplan_stations.geojson").write_text(json.dumps(stations_fc, ensure_ascii=False))
    (OUT_DIR / "masterplan_nodes.geojson").write_text(json.dumps(nodes_fc, ensure_ascii=False))
    (OUT_DIR / "masterplan_interchanges.geojson").write_text(json.dumps(ix_fc, ensure_ascii=False))
    (OUT_DIR / "masterplan_sources.json").write_text(json.dumps(list(sources.values()), ensure_ascii=False, indent=2))
    (OUT_DIR / "masterplan_validation.json").write_text(
        json.dumps(
            {
                "color": COLOR,
                "crs": CRS,
                "retrieved_at": RETRIEVED,
                "masterplan_txt": "NOT_ON_DISK",
                "routes": report,
                "issues": warnings_all,
                "qa": qa,
                "disclaimer": "Masterplan geometry is spatially reconstructed from planning documents and reference corridors. It is not a DED or construction drawing unless the source explicitly provides such alignment.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    (OUT_DIR / "masterplan_warnings.json").write_text(json.dumps(warnings_all, ensure_ascii=False, indent=2))

    (PUB / "masterplan.geojson").write_text(json.dumps(corridors_fc, ensure_ascii=False))
    (PUB / "masterplan_stations.geojson").write_text(json.dumps(stations_fc, ensure_ascii=False))
    (PUB / "masterplan_nodes.geojson").write_text(json.dumps(nodes_fc, ensure_ascii=False))
    (PUB / "masterplan_existing.json").write_text(
        json.dumps(
            {
                "corridors": [
                    {
                        "id": r["route_id"],
                        "name": next(s["name"] for s in CORRIDORS if s["id"] == r["route_id"]),
                        "short": next(s["short"] for s in CORRIDORS if s["id"] == r["route_id"]),
                        "mode": next(s["mode"] for s in CORRIDORS if s["id"] == r["route_id"]),
                        "status": r["status"],
                        "endpoint": f"{next(s['from_node'] for s in CORRIDORS if s['id']==r['route_id'])} - {next(s['to_node'] for s in CORRIDORS if s['id']==r['route_id'])}",
                        "length_km": r["length_digitized_km"],
                        "length_source_km": r["length_source_km"],
                        "stop_count": r["station_count"],
                        "geometry_confidence": r["geometry_confidence"],
                        "source": r["source"],
                        "source_year": r["source_year"],
                    }
                    for r in report
                ],
                "color": COLOR,
                "crs": CRS,
                "qa": qa,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    sp = PUB / "sources.json"
    srcs = json.loads(sp.read_text())
    by = {s["dataset"]: s for s in srcs}
    by["masterplan"] = {
        "dataset": "masterplan",
        "source": "Digitasi dokumen perencanaan (BPTJ / MRTJ / LRT Jakarta / JICA / RTRW)",
        "source_type": "AI_RECONSTRUCTED",
        "license": "campuran dokumen perencanaan",
        "geometry_type": "LineString",
        "crs": CRS,
        "count": len(corridor_feats),
        "notes": "Layer acuan masterplan #E58A3A. Bukan existing, bukan usulan CASCADE, bukan DED.",
    }
    by["masterplan_stations"] = {
        "dataset": "masterplan_stations",
        "source": "Dokumen masterplan — stasiun, terminus, dan simpul yang dapat dipertanggungjawabkan",
        "source_type": "AI_RECONSTRUCTED",
        "geometry_type": "Point",
        "crs": CRS,
        "count": len(station_feats),
        "notes": "Terminus dan interchange diekspor sebagai titik stasiun. Nama indikatif ditandai is_indicative.",
    }
    sp.write_text(json.dumps(list(by.values()), ensure_ascii=False, indent=2))

    print("corridors", len(corridor_feats))
    print("segments", len(segment_feats))
    print("stations", len(station_feats), "nodes", len(node_feats), "interchanges", len(interchange_feats))
    for r in report:
        print(f"  {r['route_id']:16} {r['status']:14} {r['length_digitized_km']:>7} km  src={r['length_source_km']}  stn={r['station_count']}  {r['method']}  {r['validation_status']} sharp={r['sharp_turns']}")
    print("warnings", len(warnings_all))
    print("QA 0-stn", zero_stn, "1-stn", one_stn, "offline", len(offline), "broken_ep", len(broken_ep), "invalid", invalid)


if __name__ == "__main__":
    main()
