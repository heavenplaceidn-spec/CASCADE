#!/usr/bin/env python3
"""Rebuild CAS-TJ06 only. CAS-TJ07 is frozen (hash 86db51d43844). Other corridors untouched.

CAS-TJ06 backbone (user 2026-09-12):
Monas → Medan Merdeka Barat → Abdul Muis → Fachrudin → Palmerah Utara →
Palmerah Barat → Kemanggisan Utama Raya → Budi Raya → Kebon Jeruk Raya →
Raya Kebon Jeruk → Meruya Selatan/Udik (connector) → Meruya Ilir Raya →
Puri Kencana → Puri Indah Raya → Puri Indah
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path("/workspace")
sys.path.insert(0, str(ROOT / "scripts"))

PUB = ROOT / "public/data"
OUT_DIR = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-12"
SOURCE = "CASCADE.txt + user road-intent 2026-09-12 (TJ06 ruas: Medan Merdeka Barat–Abdul Muis–Fachrudin–Palmerah–Kemanggisan Utama–Kebon Jeruk Raya–Meruya Ilir Raya–Puri Kencana–Puri Indah)"
TJ07_HASH = "86db51d43844"

spec = importlib.util.spec_from_file_location("tja", ROOT / "scripts/rebuild-cascade-tj.py")
tja = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tja)
rc = tja.rc

haversine = tja.haversine
length_m = tja.length_m
feat_line = tja.feat_line
feat_pt = tja.feat_pt
fc = tja.fc
densify = tja.rc.densify
densify_line = tja.rc.densify_line
clean_chain = tja.clean_chain
flatten = tja.rc.flatten
stitch = tja.rc.stitch
nearest_along = tja.rc.nearest_along
slice_along = tja.rc.slice_along
snap_to_named = tja.snap_to_named

SKIP_EXTRA_SRC = {
    "constructed_budi_rawa",
    "constructed_parman_west",
    "constructed_pengumben_parman",
}


def geom_hash(coords):
    raw = json.dumps(coords, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


NODES = {
    "Monas": (106.82271, -6.17641),
    "Medan Merdeka Barat": (106.82240, -6.17850),
    "Medan Merdeka Selatan": (106.82180, -6.18020),
    "Abdul Muis Utara": (106.82080, -6.17680),
    "Abdul Muis Selatan": (106.81720, -6.18120),
    "Fachrudin Utara": (106.81580, -6.18250),
    "Fachrudin": (106.81450, -6.18650),
    "Tanah Abang": (106.81380, -6.18840),
    "Jatibaru": (106.81170, -6.18880),
    "Tubun Tengah": (106.80711, -6.18890),
    "Tubun Barat": (106.79980, -6.20150),
    "Palmerah Utara": (106.79680, -6.20400),
    "Palmerah Barat": (106.79430, -6.20760),
    "Palmerah Barat Barat": (106.78796, -6.20762),
    "Palmerah Barat Ujung": (106.78318, -6.20698),
    "Rawa Belong": (106.78285, -6.20180),
    "Rawa Belong Utara": (106.78232, -6.19884),
    "Kemanggisan Raya Utara": (106.78659, -6.18904),
    "Kemanggisan": (106.78659, -6.18904),
    "Kemanggisan Utama Barat": (106.78330, -6.18831),
    "Budi Selatan": (106.78225, -6.19322),
    "Kebon Jeruk Raya Timur": (106.78232, -6.19884),
    "Kebon Jeruk": (106.76887, -6.19431),
    "Kebon Jeruk Raya Barat": (106.76550, -6.19800),
    "Meruya Ilir Timur": (106.76441, -6.19773),
    "Meruya Ilir": (106.75300, -6.19820),
    "Meruya Ilir Barat": (106.74246, -6.19890),
    "Meruya Selatan Utara": (106.74188, -6.19877),
    "Puri Kencana": (106.74241, -6.19105),
    "Puri Indah Jalan": (106.74006, -6.19124),
    "Puri Indah": (106.73390, -6.18830),
    # frozen TJ07 nodes kept so snaps don't break if referenced
    "Gang Jengkol": (106.72996, -6.21897),
    "Puri Beta": (106.72602, -6.23060),
}


SPECS = [
    dict(
        id="CAS-TJ06",
        route_order=6,
        name="Monas – Puri Indah",
        short="Monas – Puri Indah",
        from_name="Monas",
        to_name="Puri Indah",
        direction="Monas → Puri Indah",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note=(
            "CAS-TJ06 Monas–Puri Indah. Backbone: Medan Merdeka Barat–Abdul Muis–Fachrudin–"
            "Palmerah Utara–Palmerah Barat–Kemanggisan Utama Raya–Budi Raya–Kebon Jeruk Raya–"
            "Raya Kebon Jeruk–Meruya Ilir Raya–Puri Kencana–Puri Indah Raya–Puri Indah. "
            "Bukan Puri Beta. Bukan Joglo. Bukan Daan Mogot. Bukan Lingkar Luar Barat/JORR."
        ),
        osm_alias={
            "Jl Abdul Muis": "Jalan Abdul Muis",
            "Jl Fachrudin": "Jalan Fakhrudin / Jalan Kyai Haji Fakhrudin / Jalan Haji Fachrudin",
            "Jl Kemanggisan Utama Raya": "Jalan Kemanggisan Utama",
            "Jl Kebon Jeruk Raya": "Jalan Kebon Jeruk Raya",
            "Jl Raya Kebon Jeruk": "Jalan Kebon Jeruk Raya + Jalan Panjang Raya (ruas Kedoya)",
            "Jl Meruya Ilir Raya": "Jalan Meruya Ilir",
            "Jl Puri Indah Raya": "Jalan Puri Indah Raya / Jalan Puri Indah (bukan JORR Lingkar Luar Barat)",
        },
        legs=[
            ("Monas", "Medan Merdeka Selatan", ["Jalan Medan Merdeka Barat"]),
            ("Medan Merdeka Selatan", "Abdul Muis Selatan", ["Jalan Abdul Muis", "Jalan Medan Merdeka Barat"]),
            ("Abdul Muis Selatan", "Fachrudin", ["Jalan Abdul Muis", "Jalan Kyai Haji Fakhrudin", "Jalan Fakhrudin"]),
            ("Fachrudin", "Tanah Abang", ["Jalan Fakhrudin", "Jalan Kyai Haji Fakhrudin", "Jalan Haji Fachrudin"]),
            ("Tanah Abang", "Jatibaru", ["Jalan Haji Fachrudin", "Jalan Jatibaru", "Jalan Fakhrudin"]),
            ("Jatibaru", "Tubun Tengah", ["Jalan Jatibaru", "Jalan Aipda Karel Satsuit Tubun"]),
            ("Tubun Tengah", "Tubun Barat", ["Jalan Aipda Karel Satsuit Tubun"]),
            ("Tubun Barat", "Palmerah Utara", ["Jalan Palmerah Utara", "Jalan Aipda Karel Satsuit Tubun"]),
            ("Palmerah Utara", "Palmerah Barat", ["Jalan Palmerah Utara", "Jalan Palmerah Barat"]),
            ("Palmerah Barat", "Palmerah Barat Barat", ["Jalan Palmerah Barat"]),
            ("Palmerah Barat Barat", "Palmerah Barat Ujung", ["Jalan Palmerah Barat"]),
            ("Palmerah Barat Ujung", "Rawa Belong", ["Jalan Rawa Belong"]),
            ("Rawa Belong", "Rawa Belong Utara", ["Jalan Rawa Belong"]),
            ("Rawa Belong Utara", "Kemanggisan", ["Jalan Kemanggisan Raya"]),
            ("Kemanggisan", "Kemanggisan Utama Barat", ["Jalan Kemanggisan Utama"]),
            ("Kemanggisan Utama Barat", "Budi Selatan", ["Jalan Budi Raya", "Jalan Kemanggisan Utama"]),
            ("Budi Selatan", "Kebon Jeruk Raya Timur", ["Jalan Kemanggisan Raya"]),
            ("Kebon Jeruk Raya Timur", "Kebon Jeruk Raya Barat", ["Jalan Kebon Jeruk Raya"]),
            ("Kebon Jeruk Raya Barat", "Meruya Ilir Timur", ["Jalan Kebon Jeruk Raya", "Jalan Meruya Ilir"]),
            ("Meruya Ilir Timur", "Meruya Ilir", ["Jalan Meruya Ilir"]),
            ("Meruya Ilir", "Meruya Ilir Barat", ["Jalan Meruya Ilir"]),
            ("Meruya Ilir Barat", "Meruya Selatan Utara", ["Jalan Meruya Selatan", "Jalan Meruya Ilir", "Jalan Kembang Kerep"]),
            ("Meruya Selatan Utara", "Puri Kencana", ["Jalan Kembang Kerep", "Jalan Kembang Kencana", "Jalan Puri Kencana"]),
            ("Puri Kencana", "Puri Indah Jalan", ["Jalan Puri Kencana", "Jalan Puri Indah", "Jalan Puri Indah Raya", "Jalan Kembang Kerep"]),
            ("Puri Indah Jalan", "Puri Indah", ["Jalan Puri Indah", "Jalan Puri Indah Raya", "Jalan Puri Lingkar Luar"]),
        ],
        anchors=[
            "Monas",
            "Tanah Abang",
            "Palmerah Utara",
            "Palmerah Barat",
            "Kemanggisan",
            "Kebon Jeruk",
            "Meruya Ilir",
            "Puri Kencana",
            "Puri Indah",
        ],
        keep_detours=True,
        toll=False,
    ),
]


def clip_progress(chain, start, end, max_back_m=45.0):
    if not chain or len(chain) < 2:
        return chain
    vx, vy = end[0] - start[0], end[1] - start[1]
    lat = (start[1] + end[1]) / 2
    kx = 111320 * math.cos(math.radians(lat))
    ky = 110540
    vxm, vym = vx * kx, vy * ky
    vlen = math.hypot(vxm, vym) or 1.0
    out = [list(chain[0])]
    best = -1e9
    for p in chain:
        px, py = (p[0] - start[0]) * kx, (p[1] - start[1]) * ky
        prog = (px * vxm + py * vym) / vlen
        if prog >= best - max_back_m:
            if haversine(out[-1], p) > 4:
                out.append(list(p))
            if prog > best:
                best = prog
    return out if len(out) >= 2 else [list(p) for p in chain]


def merge_collinear(parts, max_gap=220.0):
    runs = stitch([list(map(list, p)) for p in parts if len(p) >= 2], gap=140)
    if len(runs) <= 1:
        return runs
    unused = [list(map(list, r)) for r in runs]
    changed = True
    guard = 0
    while changed and guard < 40 and len(unused) > 1:
        changed = False
        guard += 1
        best = None
        for i, a in enumerate(unused):
            for j, b in enumerate(unused):
                if i == j:
                    continue
                for a_pts, a_flip in ((a, False), (list(reversed(a)), True)):
                    for b_pts, b_flip in ((b, False), (list(reversed(b)), True)):
                        d = haversine(a_pts[-1], b_pts[0])
                        if d > max_gap:
                            continue
                        ax = a_pts[-1][0] - a_pts[max(0, len(a_pts) - 4)][0]
                        ay = a_pts[-1][1] - a_pts[max(0, len(a_pts) - 4)][1]
                        bx = b_pts[0][0] - a_pts[-1][0]
                        by = b_pts[0][1] - a_pts[-1][1]
                        if math.hypot(ax, ay) > 1e-9 and math.hypot(bx, by) > 1e-9:
                            cont = (ax * bx + ay * by) / (math.hypot(ax, ay) * math.hypot(bx, by))
                            if cont < 0.05 and d > 40:
                                continue
                        if best is None or d < best[0]:
                            best = (d, i, j, a_flip, b_flip)
        if best:
            d, i, j, a_flip, b_flip = best
            a = unused[i] if not a_flip else list(reversed(unused[i]))
            b = unused[j] if not b_flip else list(reversed(unused[j]))
            if haversine(a[-1], b[0]) > 8:
                a = a + densify(a[-1], b[0], 30)[1:]
            a = a + b[1:]
            for idx in sorted((i, j), reverse=True):
                unused.pop(idx)
            unused.append(a)
            changed = True
    unused.sort(key=length_m, reverse=True)
    return unused


def force_merge_ew(runs, max_gap=280.0):
    if not runs:
        return []
    oriented = []
    for r in runs:
        r = list(map(list, r))
        if r[0][0] > r[-1][0]:
            r = list(reversed(r))
        oriented.append(r)
    oriented.sort(key=lambda r: (r[0][0] + r[-1][0]) / 2)
    merged = [oriented[0]]
    for r in oriented[1:]:
        last = merged[-1]
        d = haversine(last[-1], r[0])
        dlat = abs(last[-1][1] - r[0][1]) * 111320
        if d <= max_gap and dlat <= 180:
            if d > 8:
                last.extend(densify(last[-1], r[0], 30)[1:])
            last.extend(r[1:])
        else:
            merged.append(r)
    merged.sort(key=length_m, reverse=True)
    return merged


def force_merge_ns(runs, max_gap=220.0):
    """Stitch north-south fragments (south → north). Do not use force_merge_ew on N-S arterials."""
    if not runs:
        return []
    oriented = []
    for r in runs:
        r = list(map(list, r))
        if r[0][1] > r[-1][1]:
            r = list(reversed(r))
        oriented.append(r)
    oriented.sort(key=lambda r: r[0][1])
    merged = [oriented[0]]
    for r in oriented[1:]:
        last = merged[-1]
        d = haversine(last[-1], r[0])
        lat = last[-1][1]
        dlon = abs(last[-1][0] - r[0][0]) * 111320 * math.cos(math.radians(lat))
        if d <= max_gap and dlon <= 240:
            if d > 8:
                last.extend(densify(last[-1], r[0], 30)[1:])
            last.extend(r[1:])
        else:
            merged.append(r)
    merged.sort(key=length_m, reverse=True)
    return merged


def slice_named(road_map, names, a, b, max_off=720):
    straight = haversine(a, b)
    best = None
    for name in names:
        feat = road_map.get(name)
        if not feat:
            continue
        if any(k in name for k in ("Joglo", "Tubun", "Meruya Ilir", "Thamrin", "Kebon Jeruk", "Palmerah", "Abdul Muis", "Fakhrudin", "Fachrudin", "Kemanggisan Utama")):
            runs = force_merge_ew(merge_collinear(flatten(feat["geometry"]), max_gap=420), max_gap=400)
        elif any(k in name for k in ("Kemanggisan Raya", "Rawa Belong", "Budi Raya")):
            runs = force_merge_ns(merge_collinear(flatten(feat["geometry"]), max_gap=240), max_gap=240)
        else:
            runs = merge_collinear(flatten(feat["geometry"]), max_gap=240)
        for run in runs:
            if len(run) < 2:
                continue
            d0, a0, _, tot = nearest_along(a, run)
            d1, a1, _, _ = nearest_along(b, run)
            if d0 > max_off or d1 > max_off:
                continue
            if abs(a1 - a0) < 50:
                continue
            sl = slice_along(run, a0, a1)
            L = length_m(sl)
            if L < 0.45 * straight and L < 250:
                continue
            if straight > 80 and L > 3.8 * straight:
                continue
            score = d0 + d1 + 0.04 * L
            if best is None or score < best[0]:
                best = (score, sl, name, d0, d1, L)
    if not best:
        return None, None, None
    return best[1], best[2], (best[3], best[4], best[5])


def join_slices(chain, sl):
    if not sl:
        return chain, "empty"
    sl = [list(p) for p in sl]
    if not chain:
        return sl, "start"
    d0 = haversine(chain[-1], sl[0])
    d1 = haversine(chain[-1], sl[-1])
    if d1 < d0:
        sl = list(reversed(sl))
        d0 = d1
    if d0 < 55:
        return chain + sl[1:], "join"
    if d0 <= 120:
        return chain + densify(chain[-1], sl[0], 25)[1:] + sl[1:], "junction"
    return None, f"gap:{d0:.0f}"


def load_road_map_clean():
    road_map = tja.load_road_map()
    extra_path = OUT_DIR / "extra_roads.geojson"
    if not extra_path.exists():
        return road_map
    extra = json.loads(extra_path.read_text())
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        src = str(f.get("properties", {}).get("source") or "")
        name = f["properties"].get("name") or "extra"
        if src in SKIP_EXTRA_SRC:
            continue
        if name == "Jalan Raya Pos Pengumben" and src == "osrm_forced_waypoints":
            continue
        buckets.setdefault(name, []).extend(flatten(g))
    for name, parts in buckets.items():
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            parts = old + parts
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name, "highway": "secondary", "source": "extra_clean"},
            "geometry": {"type": "MultiLineString", "coordinates": [list(map(list, x)) for x in parts if len(x) >= 2]},
        }
    return road_map


def inject_cleaned_traces(road_map):
    extra_path = OUT_DIR / "extra_roads.geojson"
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}

    def parts_named(name, src=None):
        out = []
        for f in extra["features"]:
            if (f.get("properties") or {}).get("name") != name:
                continue
            if src and (f.get("properties") or {}).get("source") != src:
                continue
            out.extend(flatten(f["geometry"]))
        return out

    pal_u = parts_named("Jalan Palmerah Utara", "osrm_palmerah")
    pal_b = parts_named("Jalan Palmerah Barat", "osrm_palmerah")
    if pal_u:
        chain = max(pal_u, key=length_m)
        chain = clip_progress(chain, NODES["Tubun Barat"], NODES["Palmerah Barat"])
        chain = rc.remove_loops(chain, rejoin_m=70.0, min_loop=250.0)
        road_map["Jalan Palmerah Utara"] = {
            "type": "Feature",
            "properties": {"name": "Jalan Palmerah Utara"},
            "geometry": {"type": "LineString", "coordinates": chain},
        }
        print("  palmerah utara cleaned", round(length_m(chain) / 1000, 2), "km", len(chain), "vtx")
    if pal_b:
        chain = max(pal_b, key=length_m)
        chain = clip_progress(chain, NODES["Palmerah Barat"], (106.78318, -6.20700))
        chain = rc.remove_loops(chain, rejoin_m=70.0, min_loop=250.0)
        road_map["Jalan Palmerah Barat"] = {
            "type": "Feature",
            "properties": {"name": "Jalan Palmerah Barat"},
            "geometry": {"type": "LineString", "coordinates": chain},
        }
        print("  palmerah barat cleaned", round(length_m(chain) / 1000, 2), "km", len(chain), "vtx")

    # N-S arterials: stitch each name separately. NEVER overwrite Kemanggisan Raya
    # with the Rawa Belong fragment (that drop was why TJ06 skipped Kemanggisan Utama).
    def set_line(name, run, tag):
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "LineString", "coordinates": run},
        }
        print(f"  {tag}", round(length_m(run) / 1000, 2), "km",
              f"{run[0][0]:.5f},{run[0][1]:.5f} → {run[-1][0]:.5f},{run[-1][1]:.5f}")

    feat = road_map.get("Jalan Rawa Belong")
    if feat:
        merged = force_merge_ns(merge_collinear(flatten(feat["geometry"]), max_gap=180), max_gap=180)
        if merged:
            set_line("Jalan Rawa Belong", merged[0], "rawa belong NS")

    feat = road_map.get("Jalan Kemanggisan Raya")
    if feat:
        merged = force_merge_ns(merge_collinear(flatten(feat["geometry"]), max_gap=180), max_gap=180)
        if merged:
            set_line("Jalan Kemanggisan Raya", merged[0], "kemanggisan raya NS")

    feat = road_map.get("Jalan Budi Raya")
    if feat:
        merged = force_merge_ns(merge_collinear(flatten(feat["geometry"]), max_gap=180), max_gap=180)
        if merged:
            set_line("Jalan Budi Raya", merged[0], "budi raya NS")

    feat = road_map.get("Jalan Kemanggisan Utama")
    if feat:
        merged = force_merge_ew(merge_collinear(flatten(feat["geometry"]), max_gap=200), max_gap=220)
        if merged:
            set_line("Jalan Kemanggisan Utama", merged[0], "kemanggisan utama EW")

    # Meruya Ilir: force one E-W arterial
    feat = road_map.get("Jalan Meruya Ilir")
    if feat:
        merged = force_merge_ew(merge_collinear(flatten(feat["geometry"]), max_gap=420), max_gap=500)
        if merged:
            road_map["Jalan Meruya Ilir"] = {
                "type": "Feature",
                "properties": {"name": "Jalan Meruya Ilir"},
                "geometry": {"type": "MultiLineString", "coordinates": merged},
            }
            print("  meruya ilir runs", len(merged), "longest", round(length_m(merged[0]) / 1000, 2), "km")
    return road_map


def xy_of(name):
    return list(NODES[name])


def walk_legs(spec, road_map, graph=None):
    warnings = []
    chain = []
    vertices = []
    vid = 0
    used_road = False
    for i, (a_name, b_name, roads) in enumerate(spec["legs"]):
        a, b = xy_of(a_name), xy_of(b_name)
        sl, rname, meta = slice_named(road_map, roads, a, b)
        method = "ROAD"
        if sl is None and graph is not None:
            gpath, _ = graph.route(a, b, prefer=roads, max_factor=3.0, skip_toll=True)
            if gpath and length_m(gpath) < 4500:
                sl = gpath
                rname = roads[0] if roads else "graph"
                method = "GRAPH"
                meta = (0, 0, length_m(gpath))
                print(f"  GRAPH {a_name}–{b_name} {meta[2]/1000:.2f} km")
        if sl is None:
            d = haversine(a, b)
            if d <= 90:
                sl = densify(a, b, 25)
                rname = roads[0] if roads else "link"
                method = "JUNCTION"
                warnings.append(f"JUNCTION {a_name}–{b_name} {d:.0f}m")
            else:
                warnings.append(f"MISS {a_name}–{b_name} roads={roads}")
                print("  MISS", a_name, b_name, roads)
                continue
        else:
            used_road = True
            d0, d1, L = meta
            if d0 > 80 or d1 > 80:
                warnings.append(f"off {a_name}–{b_name} snap {d0:.0f}/{d1:.0f}m on {rname} L={L:.0f}")
            print(f"  {a_name}–{b_name}: {rname} {L/1000:.2f} km snap {d0:.0f}/{d1:.0f}m")
        vid += 1
        vertices.append(
            {
                "vertex_id": f"{spec['id']}-V{vid:02d}",
                "route_id": spec["id"],
                "vertex_order": vid,
                "vertex_name": a_name,
                "vertex_type": "ENDPOINT" if i == 0 else "ROAD_CHANGE",
                "road_name": rname or "",
                "geometry": a,
                "source": "intent",
                "method": method,
                "confidence": "HIGH" if method == "ROAD" else "MEDIUM",
            }
        )
        joined, how = join_slices(chain, sl)
        if joined is None:
            bridged = False
            if graph is not None and chain:
                for prefer in (roads, None):
                    gpath, _ = graph.route(chain[-1], sl[0], prefer=prefer, max_factor=3.4, skip_toll=True)
                    if gpath and length_m(gpath) < 3500:
                        chain = chain + gpath[1:]
                        chain2, how2 = join_slices(chain, sl)
                        if chain2 is not None:
                            chain = chain2
                            how = "graph-bridge+" + how2
                            bridged = True
                            print(f"    bridged {how} prefer={prefer}")
                            break
                        # graph got us close — attach slice anyway if end of gpath is near sl
                        if haversine(gpath[-1], sl[0]) < 140 or haversine(gpath[-1], sl[-1]) < 140:
                            sl2 = sl if haversine(gpath[-1], sl[0]) <= haversine(gpath[-1], sl[-1]) else list(reversed(sl))
                            chain = chain + sl2[1:]
                            bridged = True
                            print(f"    attached after graph {length_m(gpath):.0f}m")
                            break
            if not bridged:
                warnings.append(f"{how} {a_name}–{b_name}")
                print("  DROP gap", how, a_name, b_name)
                warnings.append(f"UNJOINED {a_name}–{b_name}")
        else:
            chain = joined
            if str(how).startswith("gap"):
                warnings.append(f"{how} {a_name}–{b_name}")
    vid += 1
    vertices.append(
        {
            "vertex_id": f"{spec['id']}-V{vid:02d}",
            "route_id": spec["id"],
            "vertex_order": vid,
            "vertex_name": spec["legs"][-1][1],
            "vertex_type": "ENDPOINT",
            "road_name": spec["legs"][-1][2][0],
            "geometry": xy_of(spec["to_name"]),
            "source": "intent",
            "method": "ROAD" if used_road else "SPINE",
            "confidence": "HIGH",
        }
    )
    chain = clean_chain(chain)
    # keep the Kemanggisan Utama hook (out-and-back on Kemanggisan Raya is intentional backbone)
    chain = rc.remove_loops(chain, rejoin_m=80.0, min_loop=4000.0)
    start, end = xy_of(spec["from_name"]), xy_of(spec["to_name"])
    if chain:
        if haversine(chain[0], start) > 80:
            first_roads = spec["legs"][0][2]
            sl, rname, meta = slice_named(road_map, first_roads, start, chain[0], max_off=900)
            if sl:
                # prepend
                d0 = haversine(sl[-1], chain[0])
                d1 = haversine(sl[0], chain[0])
                if d1 < d0:
                    sl = list(reversed(sl))
                chain = sl[:-1] + chain
                print(f"  start slice {rname} {length_m(sl)/1000:.2f} km")
            elif graph is not None:
                gpath, _ = graph.route(start, chain[0], prefer=first_roads, max_factor=3.0, skip_toll=True)
                if gpath:
                    chain = gpath[:-1] + chain
                    print(f"  start graph {length_m(gpath)/1000:.2f} km")
        if haversine(chain[0], start) <= 250:
            if haversine(chain[0], start) > 12:
                chain = densify(start, chain[0], 20)[:-1] + chain
            chain[0] = list(start)
        if haversine(chain[-1], end) > 80:
            last_roads = spec["legs"][-1][2]
            sl, rname, meta = slice_named(road_map, last_roads, chain[-1], end, max_off=900)
            if sl:
                joined, how = join_slices(chain, sl)
                if joined is not None:
                    chain = joined
                    print(f"  terminus slice {rname} {length_m(sl)/1000:.2f} km how={how}")
        if haversine(chain[-1], end) <= 200:
            if haversine(chain[-1], end) > 12:
                chain = chain + densify(chain[-1], end, 20)[1:]
            chain[-1] = list(end)
    chain = densify_line(clean_chain(chain), 40)
    method = "ROAD_REFERENCE" if used_road else "DOCUMENT_RECONSTRUCTION"
    return chain, vertices, warnings, method


KEEP_STOP = {
    "monas",
    "tanah abang",
    "kebon sirih",
    "petamburan",
    "slipi",
    "kemanggisan",
    "tanjung duren",
    "duri kepa",
    "kedoya",
    "kebon jeruk",
    "meruya ilir",
    "kembangan selatan",
    "puri kencana",
    "puri indah",
    "palmerah utara",
    "palmerah barat",
    "permata hijau",
    "kebayoran lama",
    "pos pengumben",
    "joglo",
    "joglo raya",
    "gang jengkol",
    "puri beta",
    "bundaran hi",
    "abdul muis",
    "fachrudin",
    "rawa belong",
    "kelapa dua",
    "ciledug raya",
    "joglo timur",
    "joglo barat",
}

STOP_RENAME = {
    "medan merdeka selatan": "Monas",
    "medan merdeka barat": "Monas",
    "abdul muis utara": "Abdul Muis",
    "abdul muis selatan": "Abdul Muis",
    "fachrudin utara": "Fachrudin",
    "jatibaru": "Tanah Abang",
    "tubun tengah": "Petamburan",
    "tubun barat": "Slipi",
    "palmerah barat ujung": "Palmerah Barat",
    "rawa belong utara": "Rawa Belong",
    "kemanggisan raya utara": "Kemanggisan",
    "kemanggisan utama barat": "Kemanggisan",
    "budi selatan": "Kemanggisan",
    "kebon jeruk raya timur": "Kebon Jeruk",
    "kebon jeruk raya barat": "Kebon Jeruk",
    "meruya ilir timur": "Meruya Ilir",
    "meruya ilir barat": "Kembangan Selatan",
    "meruya selatan utara": "Kembangan Selatan",
    "puri indah jalan": "Puri Kencana",
    "kembang kerep": "Puri Kencana",
}


def local_name_for(lon, lat, used):
    gazetteer = [
        (106.8227, -6.1764, "Monas"),
        (106.8224, -6.1785, "Medan Merdeka Barat"),
        (106.8218, -6.1802, "Abdul Muis"),
        (106.8172, -6.1812, "Abdul Muis"),
        (106.8145, -6.1865, "Fachrudin"),
        (106.8138, -6.1884, "Tanah Abang"),
        (106.8115, -6.1860, "Tanah Abang"),
        (106.8058, -6.1948, "Petamburan"),
        (106.7998, -6.2006, "Slipi"),
        (106.7968, -6.2040, "Palmerah Utara"),
        (106.7943, -6.2076, "Palmerah Barat"),
        (106.7829, -6.2018, "Rawa Belong"),
        (106.78659, -6.18904, "Kemanggisan"),
        (106.78330, -6.18831, "Kemanggisan"),
        (106.7825, -6.1974, "Rawa Belong"),
        (106.7689, -6.1943, "Kebon Jeruk"),
        (106.7655, -6.1980, "Kebon Jeruk"),
        (106.7644, -6.1977, "Meruya Ilir"),
        (106.7530, -6.1982, "Meruya Ilir"),
        (106.7425, -6.1989, "Kembangan Selatan"),
        (106.7424, -6.1911, "Puri Kencana"),
        (106.7339, -6.1883, "Puri Indah"),
        (106.8228, -6.1828, "Bundaran HI"),
        (106.7900, -6.1885, "Tanjung Duren"),
        (106.7748, -6.1883, "Duri Kepa"),
        (106.7685, -6.1896, "Kedoya"),
    ]
    best = None
    for x, y, name in gazetteer:
        if name.lower() in used:
            continue
        d = haversine((lon, lat), (x, y))
        if best is None or d < best[0]:
            best = (d, name)
    if best:
        return best[1]
    return "Simpang"


def relabel_stops(stops, snaps):
    named = []
    for n, v in snaps.items():
        if not isinstance(n, str) or not n.strip():
            continue
        named.append((n, v[0], v[1], v[2] if len(v) > 2 else "", v[3] if len(v) > 3 else ""))
    used = set()
    out = []
    for s in stops:
        ns = dict(s)
        mapped = STOP_RENAME.get(ns["stop_name"].lower())
        if mapped:
            ns["stop_name"] = mapped
        is_end = ns["placement_reason"] == "TERMINUS"
        if not is_end and ns["stop_name"].lower() not in KEEP_STOP:
            ns["stop_name"] = local_name_for(ns["lon"], ns["lat"], used)
        if ns["placement_reason"] in ("TERMINUS", "ANCHOR"):
            if ns["stop_name"].lower() in used and not is_end:
                ns["stop_name"] = local_name_for(ns["lon"], ns["lat"], used)
            used.add(ns["stop_name"].lower())
            out.append(ns)
            continue
        best = None
        for n, lon, lat, src, mode in named:
            d = haversine((ns["lon"], ns["lat"]), (lon, lat))
            if d > 280:
                continue
            if n.lower() in used:
                continue
            if n.lower() not in KEEP_STOP and n in tja.NODES:
                continue
            if n.lower() in STOP_RENAME:
                continue
            if any(x in n.lower() for x in ("koridor", "tj-k", "cas-")):
                continue
            score = -d + (80 if str(src).startswith("existing_") or mode in ("tj", "krl", "mrt", "lrt") else 0)
            if best is None or score > best[0]:
                best = (score, n, d, src, mode)
        if best:
            ns["stop_name"] = best[1]
            ns["existing"] = "YES" if str(best[3]).startswith("existing_") or best[4] in ("tj", "krl") else ns["existing"]
            ns["name_confidence"] = "HIGH" if best[2] <= 120 else "MEDIUM"
            used.add(best[1].lower())
        else:
            ns["stop_name"] = local_name_for(ns["lon"], ns["lat"], used)
            used.add(ns["stop_name"].lower())
        out.append(ns)
    deduped = []
    for s in out:
        if deduped and s["stop_name"] == deduped[-1]["stop_name"] and s["placement_reason"] != "TERMINUS":
            continue
        if deduped and s["stop_name"] == deduped[-1]["stop_name"] and deduped[-1]["placement_reason"] != "TERMINUS":
            deduped[-1] = s
            continue
        deduped.append(s)
    return deduped


def bbox_of(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def replace_corridor(feats, new_feat, cid):
    out = []
    done = False
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id"))
        rid = str(f["properties"].get("route_id") or "")
        if fid == cid or rid == cid:
            if not done:
                out.append(new_feat)
                done = True
            continue
        out.append(f)
    if not done:
        out.append(new_feat)
    return out


def replace_stops(feats, new_stops, cid):
    kept = [f for f in feats if str(f["properties"].get("route_id") or "") != cid]
    return kept + new_stops


def offroad_stats(coords, road_map):
    segs = []
    for name, feat in road_map.items():
        for part in flatten(feat["geometry"]):
            for i in range(1, len(part)):
                a, b = part[i - 1], part[i]
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if 106.70 <= mx <= 106.83 and -6.24 <= my <= -6.16:
                    segs.append((a, b))

    def dps(p, a, b):
        lat = p[1]
        kx = 111320 * math.cos(math.radians(lat))
        ky = 110540
        px, py = (p[0] - a[0]) * kx, (p[1] - a[1]) * ky
        bx, by = (b[0] - a[0]) * kx, (b[1] - a[1]) * ky
        L2 = bx * bx + by * by
        t = 0 if L2 < 1e-9 else max(0, min(1, (px * bx + py * by) / L2))
        return math.hypot(px - t * bx, py - t * by)

    offs = []
    for p in coords:
        best = 1e9
        for a, b in segs:
            d = dps(p, a, b)
            if d < best:
                best = d
        offs.append(best)
    so = sorted(offs)
    return {
        "max": round(max(offs), 1),
        "p90": round(so[int(len(so) * 0.9)], 1),
        "n80": sum(1 for x in offs if x > 80),
        "n40": sum(1 for x in offs if x > 40),
    }


def main():
    tja.SOURCE = SOURCE
    tja.NODES.update(NODES)
    snaps = tja.load_snaps()
    for n, (lon, lat) in tja.NODES.items():
        snaps.setdefault(n, (lon, lat, "intent", "node"))
    print("loading clean road map...", flush=True)
    road_map = load_road_map_clean()
    road_map = inject_cleaned_traces(road_map)
    print("building road graph...", flush=True)
    graph = tja.RoadGraph(road_map)
    print("graph nodes", len(graph.pts), flush=True)
    pois = tja.poi_index(snaps)

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())

    before = {}
    for f in old_routes["features"]:
        rid = str(f.get("id") or f["properties"].get("route_id"))
        before[rid] = geom_hash(f["geometry"]["coordinates"])
    print("before hashes", before)
    assert before.get("CAS-TJ07") == TJ07_HASH, f"TJ07 hash drifted before rebuild: {before.get('CAS-TJ07')}"

    spec_row = SPECS[0]
    print("walking", spec_row["id"], flush=True)
    geom, vertices, warns, method = walk_legs(spec_row, road_map, graph)
    for w in warns:
        print(" ", w)
    if not geom:
        raise SystemExit("FAIL no geometry")
    stops, tot = tja.place_stops_15(spec_row, geom, snaps, pois, vertices)
    stops = relabel_stops(stops, snaps)
    km = round(tot / 1000, 2)
    print(f"  {km} km  {len(geom)} vtx  {len(stops)} stops  {method}", flush=True)
    conf = spec_row["geometry_confidence"]
    if any(str(w).startswith("MISS") or str(w).startswith("UNJOINED") for w in warns):
        conf = "MEDIUM"
    stats = offroad_stats(geom, road_map)
    print("  offroad", stats)

    all_stops_brief = []
    for f in old_stops["features"]:
        p = f["properties"]
        rid = p.get("route_id")
        if rid == "CAS-TJ06":
            continue
        c = f["geometry"]["coordinates"]
        all_stops_brief.append({"route_id": rid, "stop_name": p.get("stop_name") or p.get("name"), "lon": c[0], "lat": c[1]})
    for s in stops:
        all_stops_brief.append({"route_id": "CAS-TJ06", "stop_name": s["stop_name"], "lon": s["lon"], "lat": s["lat"]})

    rf, sf, gf, vf, ixf, stop_table, km, ix_count = tja.write_route_bundle(
        spec_row, geom, vertices, stops, snaps, all_stops_brief, conf
    )
    rf["properties"]["direction"] = spec_row["direction"]
    rf["properties"]["name"] = spec_row["name"]

    route_feats = replace_corridor(old_routes["features"], rf, "CAS-TJ06")
    stop_feats = replace_stops(old_stops["features"], sf, "CAS-TJ06")
    meta = [m for m in (old_meta.get("corridors") or []) if m.get("id") != "CAS-TJ06"]
    meta.append(
        {
            "id": "CAS-TJ06",
            "name": spec_row["name"],
            "short": spec_row["short"],
            "endpoint": "Monas – Puri Indah",
            "from_name": "Monas",
            "to_name": "Puri Indah",
            "direction": spec_row["direction"],
            "length_km": km,
            "stop_count": len(stops),
            "geometry_confidence": conf,
            "source": SOURCE,
            "status": "PROPOSED",
            "network_type": "BRT_TRUNK",
            "plan_type": "NEW_TRUNK",
            "alignment_type": "MIXED_TRAFFIC",
            "bbox": bbox_of(geom),
        }
    )
    order = [f"CAS-TJ{i:02d}" for i in range(1, 12)]

    def sort_key(f):
        fid = str(f.get("id") or f["properties"].get("route_id") or "")
        return order.index(fid) if fid in order else 99

    route_feats = sorted(route_feats, key=sort_key)
    stop_feats = sorted(stop_feats, key=lambda f: (sort_key(f), f["properties"].get("stop_order") or 0))
    meta = sorted(meta, key=lambda m: order.index(m["id"]) if m.get("id") in order else 99)

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["source"] = SOURCE
    existing["corridors"] = meta
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT_DIR / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
            row["notes"] = (
                "CAS-TJ01..CAS-TJ11. TJ06=Monas–Puri Indah (Medan Merdeka Barat–Abdul Muis–Fachrudin–Palmerah–"
                "Kemanggisan Utama–Kebon Jeruk Raya–Meruya Ilir Raya–Puri Kencana–Puri Indah). "
                "TJ07=Monas–Puri Beta (Tubun–Palmerah–Kebayoran Lama–Joglo–Gang Jengkol) FROZEN. BRT trunk #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    after = {}
    for f in route_feats:
        rid = str(f.get("id") or f["properties"].get("route_id"))
        after[rid] = geom_hash(f["geometry"]["coordinates"])
    frozen = [k for k in after if k != "CAS-TJ06" and after[k] == before.get(k)]
    drifted = [k for k in after if k != "CAS-TJ06" and after[k] != before.get(k)]
    print("\n=== SUMMARY ===")
    print(f"CAS-TJ06   {km} km  stops={len(stops)} vtx={len(geom)}  {method}  {conf}")
    roads_used = []
    for v in vertices:
        n = v.get("road_name") or ""
        if n and n not in roads_used and n not in ("graph", "link", "unresolved"):
            roads_used.append(n)
    print("   roads:", ", ".join(roads_used))
    print("   offroad:", stats)
    print("   stops:", " → ".join(x["name"] for x in stop_table))
    pi = (106.73390, -6.18830)
    pb = (106.72602, -6.23060)
    gj = (106.72996, -6.21897)
    pet = (106.7380, -6.2450)
    print("CAS-TJ06 vs Puri Indah", round(min(haversine(p, pi) for p in geom), 0), "vs Puri Beta", round(min(haversine(p, pb) for p in geom), 0))
    print("  vs Gang Jengkol", round(min(haversine(p, gj) for p in geom), 0), "vs Petukangan", round(min(haversine(p, pet) for p in geom), 0))
    print("  start", [round(geom[0][0], 5), round(geom[0][1], 5)], "end", [round(geom[-1][0], 5), round(geom[-1][1], 5)])
    print("ids", [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats])
    print("TJ07 hash", after.get("CAS-TJ07"), "expected", TJ07_HASH)
    print("frozen ok", frozen)
    if drifted:
        raise SystemExit(f"DRIFT {drifted}")
    assert after.get("CAS-TJ07") == TJ07_HASH
    assert after.get("CAS-TJ01") == before.get("CAS-TJ01")
    assert geom[-1][0] < 106.74 and geom[-1][1] > -6.20
    kem = (106.78659, -6.18904)
    kem_w = (106.78330, -6.18831)
    kj_w = (106.76550, -6.19800)
    mi = (106.75300, -6.19820)
    d_kem = min(haversine(p, kem) for p in geom)
    d_kem_w = min(haversine(p, kem_w) for p in geom)
    d_kj = min(haversine(p, kj_w) for p in geom)
    d_mi = min(haversine(p, mi) for p in geom)
    print(f"  pass Kemanggisan {d_kem:.0f}m  Utama Barat {d_kem_w:.0f}m  Kebon Jeruk {d_kj:.0f}m  Meruya Ilir {d_mi:.0f}m")
    assert d_kem < 80, f"TJ06 missed Kemanggisan Utama ({d_kem:.0f}m)"
    assert d_kem_w < 120, f"TJ06 missed Kemanggisan Utama Barat ({d_kem_w:.0f}m)"
    assert d_kj < 80, f"TJ06 missed Kebon Jeruk Raya ({d_kj:.0f}m)"
    assert d_mi < 80, f"TJ06 missed Meruya Ilir ({d_mi:.0f}m)"
    assert min(haversine(p, pb) for p in geom) > 3000
    assert min(haversine(p, gj) for p in geom) > 1500
    print("TJ06 end is west (Puri Indah side), not Puri Beta")
    print("TJ06 passes Kemanggisan Utama / Kebon Jeruk / Meruya Ilir")


if __name__ == "__main__":
    main()
