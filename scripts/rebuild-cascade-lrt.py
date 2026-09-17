#!/usr/bin/env python3
"""Rebuild ONLY CAS-LRT-C02 and CAS-LRT-C04.

Read-only: masterplan, existing LRT/MRT/KRL/TJ, CAS-TJ01..11.
Harjamukti → Baranangsiang stays MASTERPLAN (LRT_BOGOR). Not CASCADE.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import urllib.request
from copy import deepcopy
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-13"
SOURCE = "CASCADE LRT C02/C04 — usulan analisis, bukan masterplan, bukan LRT Jabodebek existing"
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-lrt)"}

spec = importlib.util.spec_from_file_location("tja", ROOT / "scripts/rebuild-cascade-tj.py")
tja = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tja)

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
point_at = tja.rc.point_at

TJ_HASH = {
    "CAS-TJ01": "68374d307e0f",
    "CAS-TJ02": "627e12003339",
    "CAS-TJ03": "c4de9e575e0e",
    "CAS-TJ04": "e4ddbcd469e9",
    "CAS-TJ05": "8ac52cb52ef2",
    "CAS-TJ06": "e2c8cffa534c",
    "CAS-TJ07": "86db51d43844",
    "CAS-TJ08": "7a9c59880e8c",
    "CAS-TJ09": "482d51c48305",
    "CAS-TJ10": "7aa00eed8a6b",
    "CAS-TJ11": "4a87154787ef",
}
READONLY_FILES = {
    "masterplan.geojson": "fe420c0450d58dba",
    "masterplan_stations.geojson": "b936fca775bc3d2d",
    "masterplan_existing.json": "d0bf7ceb7f98bb28",
    "lrt_routes.geojson": "c8852cc54513d443",
    "lrt_stops.geojson": "e77d05fc567aa98f",
    "mrt_routes.geojson": "366e1977c661fefb",
    "mrt_stops.geojson": "2fc35a61f7d9c113",
    "krl_routes.geojson": "3c5f1d6bbc9f5bac",
    "krl_stops.geojson": "515dc712e432fe2d",
    "transjakarta_routes.geojson": "f6b6e63b75a4180c",
    "transjakarta_stops.geojson": "b91ec3216dc15c5d",
}

HARJAMUKTI = (106.89569, -6.37389)
DUKUH_ATAS_LRT = (106.82554, -6.20480)
KARET_KRL = (106.81600, -6.20086)
TANAH_ABANG_KRL = (106.81079, -6.18653)
GROGOL_KRL = (106.78727, -6.16200)
AIRPORT = (106.65590, -6.12560)


def geom_hash(coords):
    raw = json.dumps(coords, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def osrm_pair(a, b):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}"
        "?overview=full&geometries=geojson"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode())
    g = d["routes"][0]["geometry"]["coordinates"]
    return [list(p) for p in g], d["routes"][0]["distance"]


def merge_named(parts, max_gap=280.0):
    runs = stitch([list(map(list, p)) for p in parts if len(p) >= 2], gap=140)
    if not runs:
        return []
    unused = [list(map(list, r)) for r in runs]
    changed = True
    guard = 0
    while changed and guard < 50 and len(unused) > 1:
        changed = False
        guard += 1
        best = None
        for i, a in enumerate(unused):
            for j, b in enumerate(unused):
                if i == j:
                    continue
                for af, a_flip in ((a, False), (list(reversed(a)), True)):
                    for bf, b_flip in ((b, False), (list(reversed(b)), True)):
                        d = haversine(af[-1], bf[0])
                        if d > max_gap:
                            continue
                        if best is None or d < best[0]:
                            best = (d, i, j, a_flip, b_flip)
        if best:
            d, i, j, a_flip, b_flip = best
            a = unused[i] if not a_flip else list(reversed(unused[i]))
            b = unused[j] if not b_flip else list(reversed(unused[j]))
            if d > 8:
                a = a + densify(a[-1], b[0], 30)[1:]
            a = a + b[1:]
            for idx in sorted((i, j), reverse=True):
                unused.pop(idx)
            unused.append(a)
            changed = True
    unused.sort(key=length_m, reverse=True)
    return unused


def load_lrt_roads():
    road_map = tja.load_road_map()
    extra_path = OUT / "extra_roads_lrt.geojson"
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        name = f["properties"].get("name") or "extra"
        buckets.setdefault(name, []).extend(flatten(g))
    for name, parts in buckets.items():
        merged = merge_named(parts, max_gap=320)
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            merged = merge_named(old + merged, max_gap=320)
        if not merged:
            continue
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "MultiLineString", "coordinates": merged} if len(merged) > 1 else {"type": "LineString", "coordinates": merged[0]},
        }
    return road_map


def slice_named(road_map, names, a, b, max_off=220):
    straight = haversine(a, b)
    best = None
    for name in names:
        feat = road_map.get(name)
        if not feat:
            continue
        runs = merge_named(flatten(feat["geometry"]), max_gap=320)
        for run in runs:
            if len(run) < 2:
                continue
            d0, a0, _, _ = nearest_along(a, run)
            d1, a1, _, _ = nearest_along(b, run)
            if d0 > max_off or d1 > max_off:
                continue
            if abs(a1 - a0) < 40:
                continue
            sl = slice_along(run, a0, a1)
            L = length_m(sl)
            if L < 0.55 * straight and L < 280:
                continue
            if straight > 80 and L > 2.15 * straight:
                continue
            score = d0 + d1 + 0.03 * L
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
    if d0 < 60:
        return chain + sl[1:], "join"
    if d0 <= 140:
        return chain + densify(chain[-1], sl[0], 25)[1:] + sl[1:], "junction"
    return None, f"gap:{d0:.0f}"


def hop(a, b, road_map, names, alignment_notes):
    straight = haversine(a, b)
    force_new = bool(names) and names[0] == "NEW_ROW"
    if not force_new:
        sl, rname, meta = slice_named(road_map, names, a, b)
        if sl:
            end_ok = min(haversine(sl[-1], b), haversine(sl[0], b)) <= 180
            start_ok = min(haversine(sl[0], a), haversine(sl[-1], a)) <= 180
            if end_ok and start_ok:
                alignment_notes.append(f"ROAD {rname} {meta[2]/1000:.2f}km snap {meta[0]:.0f}/{meta[1]:.0f}")
                return sl, "ROAD_MEDIAN", rname
            alignment_notes.append(f"ROAD-MISS-END {rname}")
        if straight <= 90:
            alignment_notes.append(f"JUNCTION {straight:.0f}m")
            return densify(a, b, 25), "ROAD_MEDIAN", names[0] if names else "link"
        try:
            gpath, dist = osrm_pair(a, b)
            if dist <= 2.35 * max(straight, 1) and dist < 4500:
                alignment_notes.append(f"OSRM {dist/1000:.2f}km vs straight {straight/1000:.2f}")
                return gpath, "ROAD_MEDIAN", names[0] if names else "osrm"
            alignment_notes.append(f"OSRM-REJECT ratio {dist/max(straight,1):.2f}")
        except Exception as e:
            alignment_notes.append(f"OSRM-FAIL {e}")
    # NEW_ROW local chord — only after road/OSRM fail, or forced to keep C-shape (Benhil hook).
    tag = "NEW_ROW-forced" if force_new else "NEW_ROW"
    if straight > 2500:
        mids = 3
        pts = [a]
        for i in range(1, mids + 1):
            t = i / (mids + 1)
            pts.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
        pts.append(b)
        chain = []
        for u, v in zip(pts, pts[1:]):
            if not force_new:
                try:
                    gpath, dist = osrm_pair(u, v)
                    if dist <= 2.4 * max(haversine(u, v), 1):
                        chain = chain + gpath[1:] if chain else gpath
                        continue
                except Exception:
                    pass
            d = densify(u, v, 40)
            chain = chain + d[1:] if chain else d
        alignment_notes.append(f"{tag}-split {straight/1000:.2f}km")
        return chain, "NEW_ROW", names[0] if names else "new_row"
    alignment_notes.append(f"{tag} {straight/1000:.2f}km")
    return densify(a, b, 40), "NEW_ROW", names[0] if names else "new_row"


def walk_controls(controls, road_map, min_loop=4000.0):
    chain = []
    notes = []
    types = []
    roads = []
    for i in range(len(controls) - 1):
        a_name, a, names, _st = controls[i]
        b_name, b, _, _ = controls[i + 1]
        sl, atype, rname = hop(a, b, road_map, names, notes)
        print(f"  {a_name} → {b_name}: {atype} {rname} {length_m(sl)/1000:.2f} km")
        types.append(atype)
        if rname and rname not in roads:
            roads.append(rname)
        joined, how = join_slices(chain, sl)
        if joined is None:
            chain = chain + densify(chain[-1], sl[0], 30)[1:] + sl[1:] if chain else sl
            notes.append(f"forced-join {how} {a_name}-{b_name}")
        else:
            chain = joined
    chain = densify_line(clean_chain(chain), 40)
    chain = tja.rc.remove_loops(chain, rejoin_m=80.0, min_loop=min_loop)
    start, end = controls[0][1], controls[-1][1]
    if chain:
        if haversine(chain[0], start) > 12:
            chain = densify(start, chain[0], 20)[:-1] + chain
        chain[0] = list(start)
        if haversine(chain[-1], end) > 12:
            chain = chain + densify(chain[-1], end, 20)[1:]
        chain[-1] = list(end)
    chain = densify_line(clean_chain(chain), 40)
    alignment = "NEW_ROW" if types.count("NEW_ROW") > len(types) / 2 else "ROAD_MEDIAN"
    return chain, notes, roads, alignment


def turn_deg(coords, i):
    if i <= 0 or i >= len(coords) - 1:
        return 0.0
    ax = coords[i][0] - coords[i - 1][0]
    ay = coords[i][1] - coords[i - 1][1]
    bx = coords[i + 1][0] - coords[i][0]
    by = coords[i + 1][1] - coords[i][1]
    la, lb = math.hypot(ax, ay), math.hypot(bx, by)
    if la < 1e-12 or lb < 1e-12:
        return 0.0
    c = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
    return math.degrees(math.acos(c))


def snap_station(geom, pt, min_turn=28.0):
    d, along, ppt, tot = nearest_along(pt, geom)
    # slide off sharp curve
    for delta in (0, 80, -80, 140, -140, 200, -200):
        cand = max(30.0, min(tot - 30.0, along + delta))
        p = point_at(geom, cand)
        # find nearest vertex index
        best_i = min(range(len(geom)), key=lambda i: haversine(geom[i], p))
        if turn_deg(geom, best_i) < min_turn:
            return list(p), cand, d, tot
    return list(ppt), along, d, tot


def build_stops(cid, name, geom, stations, shared):
    out = []
    prev_along = 0.0
    tot = length_m(geom)
    for i, (sname, spt, extra) in enumerate(stations):
        ppt, along, d, _tot = snap_station(geom, spt)
        # keep order
        if out and along < out[-1]["along_m"] + 80:
            along = min(tot - 20, out[-1]["along_m"] + 200)
            ppt = list(point_at(geom, along))
        rec = {
            "stop_name": sname,
            "lon": ppt[0],
            "lat": ppt[1],
            "along_m": along,
            "existing": extra.get("existing", "NO"),
            "interchange": extra.get("interchange", "NO"),
            "interchange_mode": extra.get("interchange_mode", ""),
            "name_confidence": extra.get("name_confidence", "HIGH"),
            "placement_reason": extra.get("placement_reason", "SERVICE_NODE"),
            "station_on_curve": "NO",
        }
        out.append(rec)
        prev_along = along
    # terminus lock
    out[0]["lon"], out[0]["lat"] = geom[0][0], geom[0][1]
    out[0]["along_m"] = 0.0
    out[0]["placement_reason"] = "TERMINUS"
    out[-1]["lon"], out[-1]["lat"] = geom[-1][0], geom[-1][1]
    out[-1]["along_m"] = tot
    out[-1]["placement_reason"] = "TERMINUS"
    return out, tot


def lrt_common(spec, km, n_stops, conf, alignment, roads, note):
    return {
        "id": spec["id"],
        "route_id": spec["id"],
        "corridor_id": spec["id"],
        "corridor_name": spec["name"],
        "name": spec["name"],
        "short": spec["short"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "start_name": spec["from_name"],
        "end_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "lrt",
        "status": "PROPOSED",
        "status_label": "Usulan CASCADE · LRT",
        "cascade_status": "PROPOSED",
        "network_type": "LRT",
        "plan_type": "NEW_TRUNK",
        "existing": "NO",
        "length_km": km,
        "stop_count": n_stops,
        "geometry_confidence": conf,
        "road_alignment_confidence": conf,
        "alignment_confidence": conf,
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "color": COLOR,
        "crs": CRS,
        "source": SOURCE,
        "source_type": "AI_RECONSTRUCTED",
        "geometry_source": "OSM named arterials + Nominatim extras + OSRM road-follow; NEW_ROW only where OSM/OSRM detour",
        "planning_note": note,
        "disclaimer": "Usulan CASCADE. Bukan LRT Jabodebek existing. Bukan masterplan. Bukan DED.",
        "updated_at": RETRIEVED,
        "notes": note,
    }


def make_route_feature(spec, geom, stops, vertices_n, conf, alignment, roads, note, order):
    km = round(length_m(geom) / 1000, 2)
    props = lrt_common(spec, km, len(stops), conf, alignment, roads, note)
    props.update(
        {
            "route_order": order,
            "vertex_count": len(geom),
            "control_vertex_count": vertices_n,
            "interchange_count": sum(1 for s in stops if s["interchange"] == "YES"),
            "digitization_level": "L3",
            "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        }
    )
    return feat_line(spec["id"], geom, props), km


def make_stop_features(spec, geom, stops, conf, alignment, roads, note, common_km):
    feats = []
    tot = length_m(geom)
    for i, s in enumerate(stops):
        order = i + 1
        dist_prev = round((s["along_m"] - stops[i - 1]["along_m"]) / 1000, 2) if i else 0.0
        dist_next = round((stops[i + 1]["along_m"] - s["along_m"]) / 1000, 2) if i < len(stops) - 1 else 0.0
        stop_type = "TERMINUS" if i in (0, len(stops) - 1) else "INTERCHANGE" if s["interchange"] == "YES" else "STATION"
        sid = f"{spec['id']}-S{order:02d}"
        props = lrt_common(spec, common_km, len(stops), conf, alignment, roads, note)
        props.update(
            {
                "stop_id": sid,
                "stop_order": order,
                "stop_name": s["stop_name"],
                "name": s["stop_name"],
                "stop_type": stop_type,
                "existing": s["existing"],
                "interchange": s["interchange"],
                "interchange_mode": s["interchange_mode"],
                "station_on_curve": s["station_on_curve"],
                "placement_reason": s["placement_reason"],
                "name_confidence": s["name_confidence"],
                "distance_from_previous_stop": dist_prev,
                "distance_to_next_stop": dist_next,
                "note": "Stasiun usulan CASCADE LRT. Bukan stasiun resmi. Vertex kontrol ≠ otomatis stasiun.",
            }
        )
        feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
    return feats


def bbox_of(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def replace_lrt(feats, new_feats, prefix="CAS-LRT"):
    kept = []
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id") or "")
        rid = str(f["properties"].get("route_id") or "")
        if fid.startswith(prefix) or rid.startswith(prefix) or "CAS-LRT" in fid:
            continue
        # never keep a CASCADE Harjamukti–Baranangsiang
        name = str(f["properties"].get("name") or "")
        if "baranangsiang" in name.lower() and "harjamukti" in name.lower():
            continue
        kept.append(f)
    return kept + new_feats


def self_intersect(coords):
    # cheap check: duplicate non-adjacent vertices
    seen = {}
    for i, p in enumerate(coords):
        k = (round(p[0], 6), round(p[1], 6))
        if k in seen and i - seen[k] > 3:
            return True
        seen[k] = i
    return False


def build_c02(road_map):
    # Controls: vertex geometry. Stations are a subset.
    # Jatisari = Transyogi / Jatikarya (bukan Desa Jatisari 107.04 di timur Mekarsari).
    # Cibubur Junction ≠ Harjamukti (existing 500 m SW).
    controls = [
        ("Cibubur Junction", (106.89410, -6.36920), ["Jalan Jambore Raya", "Jalan Transyogi"], True),
        ("Transyogi 1", (106.9080, -6.3765), ["Jalan Transyogi", "Jalan Jambore Raya", "Jalan Alternatif Cibubur-Cileungsi"], False),
        ("Jatisari", (106.9280, -6.3845), ["Jalan Transyogi", "Jalan Alternatif Cibubur-Cileungsi"], True),
        ("Transyogi 2", (106.9420, -6.3900), ["Jalan Transyogi"], False),
        ("Limus Nunggal", (106.9528, -6.3942), ["Jalan Transyogi"], True),
        ("Cileungsi Barat", (106.9604, -6.4012), ["Jalan Transyogi", "Jalan Alternatif Cibubur-Cileungsi", "Jalan Raya Cileungsi-Jonggol"], False),
        ("Cileungsi", (106.96912, -6.40750), ["Jalan Raya Cileungsi-Jonggol", "Jalan Transyogi"], True),
        ("Cileungsi Timur", (106.9774, -6.4112), ["Jalan Raya Cileungsi-Jonggol"], True),
        ("Mekarsari", (106.9838, -6.4154), ["Jalan Raya Cileungsi-Jonggol"], True),
    ]
    geom, notes, roads, alignment = walk_controls(controls, road_map, min_loop=1200.0)
    stations = [
        ("Cibubur Junction", controls[0][1], {"interchange": "YES", "interchange_mode": "LRT Jabodebek (Harjamukti nearby)", "existing": "NO", "placement_reason": "TERMINUS"}),
        ("Jatisari", controls[2][1], {"placement_reason": "SERVICE_NODE"}),
        ("Limus Nunggal", controls[4][1], {"placement_reason": "SERVICE_NODE"}),
        ("Cileungsi", controls[6][1], {"placement_reason": "SERVICE_NODE"}),
        ("Cileungsi Timur", controls[7][1], {"placement_reason": "SERVICE_NODE"}),
        ("Mekarsari", controls[8][1], {"placement_reason": "TERMINUS"}),
    ]
    spec = dict(
        id="CAS-LRT-C02",
        name="Cibubur Junction – Mekarsari",
        short="Cibubur Junction – Mekarsari",
        from_name="Cibubur Junction",
        to_name="Mekarsari",
        direction="Cibubur Junction → Mekarsari",
    )
    note = (
        "CAS-LRT-C02 usulan CASCADE: Cibubur Junction–Jatisari–Limus Nunggal–Cileungsi Barat (kontrol)–"
        "Cileungsi–Cileungsi Timur–Mekarsari along Transyogi / Jalan Raya Cileungsi–Jonggol. "
        "Bukan Harjamukti–Baranangsiang (itu masterplan LRT_BOGOR). Bukan LRT 09 Jagakarsa–Cileungsi. "
        "Cileungsi Barat = control vertex, bukan stasiun wajib. Stasiun Cibubur Junction bukan duplikat Harjamukti."
    )
    stops, tot = build_stops(spec["id"], spec["name"], geom, stations, None)
    conf = "MEDIUM"
    new_row_n = sum(1 for n in notes if n.startswith("NEW_ROW"))
    if new_row_n >= 5:
        conf = "REVIEW"
    km = round(tot / 1000, 2)
    straight = haversine(controls[0][1], controls[-1][1]) / 1000
    if km > 2.8 * straight:
        conf = "REVIEW"
        notes.append(f"length {km} vs straight {straight:.1f}")
    rf, km = make_route_feature(spec, geom, stops, len(controls), conf, alignment, roads, note, 12)
    sf = make_stop_features(spec, geom, stops, conf, alignment, roads, note, km)
    d_hjm = min(haversine(p, HARJAMUKTI) for p in geom)
    d_mek = haversine(geom[-1], (106.9840, -6.4160))
    print(f"  C02 {km} km stops={len(stops)} conf={conf} align={alignment} vs Harjamukti min {d_hjm:.0f}m vs Mekarsari end {d_mek:.0f}m")
    return rf, sf, notes, {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": "Cibubur Junction – Mekarsari",
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "lrt",
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": SOURCE,
        "status": "PROPOSED",
        "network_type": "LRT",
        "plan_type": "NEW_TRUNK",
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "notes": note,
        "bbox": bbox_of(geom),
    }


def build_c04(road_map):
    controls = [
        ("Dukuh Atas", DUKUH_ATAS_LRT, ["Jalan Jenderal Sudirman", "Jalan Kyai Haji Mas Mansyur"], True),
        ("Karet", KARET_KRL, ["Jalan Kyai Haji Mas Mansyur", "Jalan Penjernihan 1"], True),
        # L-shape: south on Mas Mansyur (east of rail) then west on Bendungan Hilir.
        # Northbound later uses railway-west NEW_ROW so remove_loops cannot treat the C as retrace.
        ("Karet Selatan", (106.81550, -6.20880), ["Jalan Bendungan Hilir", "Jalan Kyai Haji Mas Mansyur"], False),
        ("Bendungan Hilir", (106.81140, -6.20920), ["NEW_ROW"], False),
        ("Jatibaru tengah", (106.81120, -6.19780), ["NEW_ROW", "Jalan Jatibaru"], False),
        ("Tanah Abang", TANAH_ABANG_KRL, ["Jalan Jatibaru", "Jalan Cideng Barat", "Jalan Cideng Timur"], True),
        ("Petojo", (106.81140, -6.16880), ["Jalan Cideng Barat", "Jalan Cideng Timur"], True),
        ("Cideng Tomang", (106.81080, -6.17750), ["Jalan Tomang Raya"], False),
        ("Tomang", (106.80020, -6.17780), ["Jalan Tomang Raya", "Jalan Letnan Jenderal Siswondo Parman"], True),
        ("S. Parman", (106.79380, -6.17820), ["Jalan Letnan Jenderal Siswondo Parman", "Jalan Tomang Raya"], True),
        ("Central Park", (106.79050, -6.17720), ["Jalan Letnan Jenderal Siswondo Parman"], True),
        ("Tanjung Duren", (106.78820, -6.17640), ["Jalan Letnan Jenderal Siswondo Parman"], True),
        ("Grogol", GROGOL_KRL, ["Jalan Letnan Jenderal Siswondo Parman", "Jalan Daan Mogot", "Jalan Profesor Dokter Latumeten"], True),
        ("Jelambar", (106.77820, -6.16020), ["Jalan Profesor Dokter Latumeten", "Jalan Daan Mogot"], True),
        ("Damai", (106.76820, -6.15540), ["Jalan Daan Mogot"], True),
        ("Pedongkelan", (106.75240, -6.13820), ["Jalan Daan Mogot", "Jalan Kamal Raya"], True),
        ("Kapuk", (106.74520, -6.12680), ["Jalan Kamal Raya", "Jalan Pantai Indah Kapuk"], True),
        ("Kamal", (106.72840, -6.11620), ["Jalan Kamal Raya"], True),
        ("PIK", (106.74080, -6.10880), ["Jalan Pantai Indah Kapuk", "Jalan Kamal Raya"], True),
        ("PIK Avenue", (106.74020, -6.10920), ["Jalan Pantai Indah Kapuk"], True),
        ("PIK 2 Gateway", (106.72480, -6.09880), ["Jalan Pantai Indah Kapuk", "Jalan Tol Profesor Doktor Sedyatmo"], True),
        ("PIK 2 CBD", (106.71020, -6.09180), ["Jalan Pantai Indah Kapuk"], True),
        ("PIK 2 Barat", (106.69200, -6.09480), ["Jalan Tol Profesor Doktor Sedyatmo"], True),
        ("Airport Connector", (106.67200, -6.11800), ["Jalan Tol Profesor Doktor Sedyatmo"], True),
        ("Soekarno-Hatta Airport", AIRPORT, ["Jalan Tol Profesor Doktor Sedyatmo", "Jalan Raya Bandara"], True),
    ]
    geom, notes, roads, alignment = walk_controls(controls, road_map, min_loop=12000.0)
    shared = {
        "Dukuh Atas": {"existing": "YES", "interchange": "YES", "interchange_mode": "LRT Jabodebek / MRT / KRL", "placement_reason": "EXISTING_CONNECTION"},
        "Karet": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "placement_reason": "EXISTING_CONNECTION"},
        "Tanah Abang": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "placement_reason": "EXISTING_CONNECTION"},
        "Grogol": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "placement_reason": "EXISTING_CONNECTION"},
        "Soekarno-Hatta Airport": {"existing": "NO", "interchange": "YES", "interchange_mode": "KA Bandara (nearby)", "placement_reason": "TERMINUS"},
    }
    station_names = [
        "Dukuh Atas",
        "Karet",
        "Tanah Abang",
        "Petojo",
        "Tomang",
        "S. Parman",
        "Central Park",
        "Tanjung Duren",
        "Grogol",
        "Jelambar",
        "Damai",
        "Pedongkelan",
        "Kapuk",
        "Kamal",
        "PIK",
        "PIK Avenue",
        "PIK 2 Gateway",
        "PIK 2 CBD",
        "PIK 2 Barat",
        "Airport Connector",
        "Soekarno-Hatta Airport",
    ]
    by = {c[0]: c[1] for c in controls}
    stations = [(n, by[n], shared.get(n, {"placement_reason": "SERVICE_NODE"})) for n in station_names]
    spec = dict(
        id="CAS-LRT-C04",
        name="Dukuh Atas – Soekarno-Hatta Airport",
        short="Dukuh Atas – Bandara Soekarno-Hatta",
        from_name="Dukuh Atas",
        to_name="Soekarno-Hatta Airport",
        direction="Dukuh Atas → Soekarno-Hatta Airport",
    )
    note = (
        "CAS-LRT-C04 usulan CASCADE: Dukuh Atas–Karet–Bendungan Hilir (kontrol)–Tanah Abang–Petojo–Tomang–"
        "S. Parman–Central Park–Tanjung Duren–Grogol–Jelambar–Damai–Pedongkelan–Kapuk–Kamal–PIK–PIK Avenue–"
        "PIK 2–Airport Connector–Soekarno-Hatta. Bukan masterplan. Bukan existing LRT Jabodebek. "
        "Dukuh Atas menumpang simpul LRT existing (bukan duplikat). Bendungan Hilir = control, bukan stasiun wajib. "
        "PIK 2–Bandara memakai NEW_ROW di lahan reklamasi jika OSM/OSRM memutar."
    )
    stops, tot = build_stops(spec["id"], spec["name"], geom, stations, None)
    conf = "MEDIUM"
    long_new = 0
    for n in notes:
        if not n.startswith("NEW_ROW") or "forced" in n:
            continue
        try:
            km_part = float(n.split("km")[0].split()[-1])
        except (ValueError, IndexError):
            km_part = 0
        if km_part >= 2.8:
            long_new += 1
    if long_new >= 4:
        conf = "REVIEW"
    km = round(tot / 1000, 2)
    straight = haversine(controls[0][1], controls[-1][1]) / 1000
    if km > 3.2 * straight:
        conf = "REVIEW"
    rf, km = make_route_feature(spec, geom, stops, len(controls), conf, alignment, roads, note, 13)
    sf = make_stop_features(spec, geom, stops, conf, alignment, roads, note, km)
    d_air = haversine(geom[-1], AIRPORT)
    d_duk = haversine(geom[0], DUKUH_ATAS_LRT)
    print(f"  C04 {km} km stops={len(stops)} conf={conf} align={alignment} start-Dukuh {d_duk:.0f}m end-Airport {d_air:.0f}m")
    return rf, sf, notes, {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": "Dukuh Atas – Soekarno-Hatta Airport",
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "lrt",
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": SOURCE,
        "status": "PROPOSED",
        "network_type": "LRT",
        "plan_type": "NEW_TRUNK",
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "notes": note,
        "bbox": bbox_of(geom),
    }


def qa(geom, name):
    issues = []
    if len(geom) < 4:
        issues.append("too few vertices")
    if self_intersect(geom):
        issues.append("possible self-intersection / duplicate vertex")
    # gaps
    for a, b in zip(geom, geom[1:]):
        d = haversine(a, b)
        if d > 350:
            issues.append(f"vertex gap {d:.0f}m")
            break
    print(f"  QA {name}: vtx={len(geom)} issues={issues or 'none'}")
    return issues


def main():
    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY DRIFT {fn} {got} != {expect}")
    print("readonly hashes OK")

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())

    before = {}
    for f in old_routes["features"]:
        rid = str(f.get("id") or f["properties"].get("route_id"))
        before[rid] = geom_hash(f["geometry"]["coordinates"])
    for k, h in TJ_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"TJ drifted before LRT rebuild: {k} {before.get(k)} != {h}")
    print("CAS-TJ hashes frozen OK")

    print("loading roads...")
    road_map = load_lrt_roads()

    print("walking CAS-LRT-C02")
    r02, s02, n02, m02 = build_c02(road_map)
    qa02 = qa(r02["geometry"]["coordinates"], "C02")
    print("walking CAS-LRT-C04")
    r04, s04, n04, m04 = build_c04(road_map)
    qa04 = qa(r04["geometry"]["coordinates"], "C04")

    # identity checks
    g02 = r02["geometry"]["coordinates"]
    g04 = r04["geometry"]["coordinates"]
    assert r02["properties"]["status"] == "PROPOSED"
    assert r04["properties"]["status"] == "PROPOSED"
    assert haversine(g02[-1], (106.9840, -6.4160)) < 250, "C02 must end at Mekarsari"
    assert haversine(g04[-1], AIRPORT) < 200, "C04 must end at airport"
    assert min(haversine(p, (106.81140, -6.20920)) for p in g04) < 180, "C04 must pass Bendungan Hilir control"
    assert min(p[1] for p in g04) <= -6.2080, "C04 must reach south of Karet to Bendungan Hilir"
    assert haversine(g02[0], (106.89410, -6.36920)) < 120, "C02 start Cibubur Junction"
    assert min(haversine(p, (106.8160, -6.6010)) for p in g02) > 8000, "C02 must not go to Baranangsiang"
    assert min(p[1] for p in g02) > -6.42, "C02 must stay in Cibubur–Cileungsi band"
    assert max(p[0] for p in g02) < 107.01, "C02 must not use Desa Jatisari east of Mekarsari"
    # C02 should not be a southbound Jagorawi clone
    assert max(p[1] for p in g02) > -6.38  # stays in Cibubur/Cileungsi band, not Sentul

    route_feats = replace_lrt(old_routes["features"], [r02, r04])
    stop_feats = replace_lrt(old_stops["features"], s02 + s04)
    # keep TJ stops
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    assert "CAS-TJ07" in ids and "CAS-LRT-C02" in ids and "CAS-LRT-C04" in ids
    assert not any("baranangsiang" in str(f["properties"].get("name", "")).lower() and str(f["properties"].get("mode")) == "lrt" and str(f["properties"].get("id", "")).startswith("CAS") for f in route_feats)

    meta = [m for m in (old_meta.get("corridors") or []) if not str(m.get("id", "")).startswith("CAS-LRT")]
    meta.extend([m02, m04])

    after = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in TJ_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"TJ DRIFT after LRT write: {k}")

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["source"] = SOURCE
    existing["corridors"] = meta
    existing["lrt_note"] = "CAS-LRT-C02 dan CAS-LRT-C04 saja. Harjamukti–Baranangsiang tetap masterplan."
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
            row["notes"] = (
                "CAS-TJ01..CAS-TJ11 (BRT, frozen this pass) + CAS-LRT-C02 Cibubur Junction–Mekarsari + "
                "CAS-LRT-C04 Dukuh Atas–Soekarno-Hatta. Bukan masterplan. Bukan Harjamukti–Baranangsiang. #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "corridors": [m02, m04],
        "qa": {"C02": qa02, "C04": qa04},
        "notes_c02": n02[-12:],
        "notes_c04": n04[-16:],
        "tj_frozen": TJ_HASH,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "harjamukti_baranangsiang_is_masterplan": True,
        "cas_lrt_ids": ["CAS-LRT-C02", "CAS-LRT-C04"],
    }
    (OUT / "cascade_validation_lrt.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))

    # re-check readonly
    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"CAS-LRT-C02  {m02['length_km']} km  stations={m02['stop_count']}  {m02['geometry_confidence']}  {m02['alignment_type']}")
    print(f"CAS-LRT-C04  {m04['length_km']} km  stations={m04['stop_count']}  {m04['geometry_confidence']}  {m04['alignment_type']}")
    print("TJ frozen", all(after[k] == TJ_HASH[k] for k in TJ_HASH))
    print("masterplan/existing untouched")
    print("ids", [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats])


if __name__ == "__main__":
    main()
