#!/usr/bin/env python3
"""Rebuild ONLY CAS-MRT-C01 (mainline Lebak Bulus–Ancol + branch Sawangan–Fatmawati).

Road-backbone. Not masterplan. Not existing MRT NS. Frozen: CAS-TJ01..11, CAS-LRT-C02/C04.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-13"
SOURCE = "CASCADE MRT C01 — usulan analisis, bukan masterplan, bukan MRT Jakarta existing"
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (cas-mrt)"}

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
LRT_HASH = {"CAS-LRT-C02": "df511bac7ab9", "CAS-LRT-C04": "e09a32724f56"}
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

PARUNG = (106.73320, -6.42100)
SAWANGAN = (106.76372, -6.40019)
LEBAK_BULUS = (106.77493, -6.28930)
FATMAWATI = (106.79246, -6.29247)
ANCOL = (106.84646, -6.12786)
PGC = (106.86570, -6.26190)
CONDET = (106.85172, -6.27643)
KAMPUNG_MELAYU = (106.86682, -6.22467)
MANGGARAI = (106.85025, -6.21110)

KEEP_EXTRA = (
    "ciputat", "parung", "sawangan", "cinere", "limo", "andara", "krukut",
    "margonda", "tole", "condet", "tanah merdeka", "palakali", "lebak bulus",
    "arif rahman", "dewi sartika", "proklamasi", "pegangsaan", "minangkabau",
    "sultan agung", "angkasa", "ancol", "gunung sahari", "lodan", "benyamin",
    "fatmawati", "kartini", "simatupang", "batu ampar", "nusantara",
    "kayu manis", "raya bogor", "martadinata", "saharjo", "salemba",
    "kramat raya", "suprapto", "otista", "otto iskandar", "juanda",
)
SKIP_EXTRA = (
    "pondok pinang", "cemara", "mars raya", "haji kodja", "pesanggrahan",
    "sdn 01", "jati raya", "elang", "bawang putih", "cendrawasih",
    "pondok hijau", "ratu bidadari", "pandan wangi", "gang salihun",
)
OSRM_CACHE = {}


def geom_hash(coords):
    raw = json.dumps(coords, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def osrm_pair(a, b):
    key = (round(a[0], 5), round(a[1], 5), round(b[0], 5), round(b[1], 5))
    if key in OSRM_CACHE:
        return OSRM_CACHE[key]
    url = (
        f"http://router.project-osrm.org/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}"
        "?overview=full&geometries=geojson"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode())
    g = [list(p) for p in d["routes"][0]["geometry"]["coordinates"]]
    dist = d["routes"][0]["distance"]
    OSRM_CACHE[key] = (g, dist)
    return g, dist


def clip_progress(chain, start, end, max_back_m=55.0):
    """Drop OSRM/named out-and-backs that reverse along the hop vector."""
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


def load_mrt_roads():
    road_map = tja.load_road_map()
    extra_path = OUT / "extra_roads_mrt.geojson"
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        name = (f.get("properties") or {}).get("name") or "extra"
        low = name.lower()
        if any(s in low for s in SKIP_EXTRA):
            continue
        if not any(k in low for k in KEEP_EXTRA):
            continue
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


def slice_named(road_map, names, a, b, max_off=280):
    straight = haversine(a, b)
    best = None
    for name in names:
        feat = road_map.get(name)
        if not feat:
            continue
        runs = merge_named(flatten(feat["geometry"]), max_gap=360)
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
            if straight > 80 and L > 2.4 * straight:
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
    if d0 <= 160:
        return chain + densify(chain[-1], sl[0], 25)[1:] + sl[1:], "junction"
    return None, f"gap:{d0:.0f}"


def hop(a, b, road_map, names, alignment_notes):
    straight = haversine(a, b)
    force_new = bool(names) and names[0] == "NEW_ROW"
    force_osrm = bool(names) and names[0] == "FORCE_OSRM"
    road_names = [n for n in names if n not in ("NEW_ROW", "FORCE_OSRM")]

    def finish(sl, atype, rname):
        sl = clip_progress(sl, a, b)
        if not sl or len(sl) < 2:
            sl = densify(a, b, 40)
            atype = "NEW_ROW"
        if haversine(sl[0], a) > 25:
            sl = densify(a, sl[0], 25)[:-1] + sl
            sl[0] = list(a)
        else:
            sl[0] = list(a)
        if haversine(sl[-1], b) > 25:
            sl = sl + densify(sl[-1], b, 25)[1:]
            sl[-1] = list(b)
        else:
            sl[-1] = list(b)
        return sl, atype, rname

    if not force_new and not force_osrm:
        sl, rname, meta = slice_named(road_map, road_names, a, b)
        if sl:
            end_ok = min(haversine(sl[-1], b), haversine(sl[0], b)) <= 220
            start_ok = min(haversine(sl[0], a), haversine(sl[-1], a)) <= 220
            if end_ok and start_ok:
                alignment_notes.append(f"ROAD {rname} {meta[2]/1000:.2f}km snap {meta[0]:.0f}/{meta[1]:.0f}")
                return finish(sl, "ROAD_MEDIAN", rname)
            alignment_notes.append(f"ROAD-MISS-END {rname}")
        if straight <= 90:
            alignment_notes.append(f"JUNCTION {straight:.0f}m")
            return finish(densify(a, b, 25), "ROAD_MEDIAN", road_names[0] if road_names else "link")
    if not force_new:
        try:
            gpath, dist = osrm_pair(a, b)
            if dist <= 2.20 * max(straight, 1) and dist < 14000:
                alignment_notes.append(f"OSRM {dist/1000:.2f}km vs straight {straight/1000:.2f}")
                return finish(gpath, "ROAD_MEDIAN", road_names[0] if road_names else "osrm")
            alignment_notes.append(f"OSRM-REJECT ratio {dist/max(straight,1):.2f} dist {dist:.0f}")
        except Exception as e:
            alignment_notes.append(f"OSRM-FAIL {e}")
        if straight > 2800:
            mid = [a[0] + (b[0] - a[0]) * 0.5, a[1] + (b[1] - a[1]) * 0.5]
            chain = []
            ok = True
            for u, v in ((a, mid), (mid, b)):
                try:
                    gpath, dist = osrm_pair(u, v)
                    if dist <= 2.25 * max(haversine(u, v), 1):
                        chain = chain + gpath[1:] if chain else gpath
                        continue
                except Exception:
                    pass
                ok = False
                break
            if ok and chain:
                alignment_notes.append(f"OSRM-split {straight/1000:.2f}km")
                return finish(chain, "ROAD_MEDIAN", road_names[0] if road_names else "osrm")
    tag = "NEW_ROW-forced" if force_new else "NEW_ROW"
    alignment_notes.append(f"{tag} {straight/1000:.2f}km")
    return finish(densify(a, b, 40), "NEW_ROW", road_names[0] if road_names else "new_row")


def walk_controls(controls, road_map, min_loop=8000.0):
    chain = []
    notes = []
    types = []
    roads = []
    segments = []
    for i in range(len(controls) - 1):
        a_name, a, names, _st = controls[i]
        b_name, b, _, _ = controls[i + 1]
        sl, atype, rname = hop(a, b, road_map, names, notes)
        print(f"  {a_name} → {b_name}: {atype} {rname} {length_m(sl)/1000:.2f} km")
        types.append(atype)
        if rname and rname not in roads and rname not in ("FORCE_OSRM", "NEW_ROW"):
            roads.append(rname)
        joined, how = join_slices(chain, sl)
        if joined is None:
            chain = chain + densify(chain[-1], sl[0], 30)[1:] + sl[1:] if chain else sl
            notes.append(f"forced-join {how} {a_name}-{b_name}")
        else:
            chain = joined
        segments.append(
            {
                "segment_id": f"{i+1:02d}",
                "from_node": a_name,
                "to_node": b_name,
                "road_name": rname,
                "alignment_type": atype,
                "length_km": round(length_m(sl) / 1000, 2),
            }
        )
    chain = densify_line(clean_chain(chain), 45)
    if chain:
        d_saw = min(haversine(p, SAWANGAN) for p in chain)
        print(f"  pre-loop Sawangan {d_saw:.0f}m  Condet {min(haversine(p, CONDET) for p in chain):.0f}m")
    chain = tja.rc.remove_loops(chain, rejoin_m=80.0, min_loop=min_loop)
    if chain:
        print(f"  post-loop Sawangan {min(haversine(p, SAWANGAN) for p in chain):.0f}m  Condet {min(haversine(p, CONDET) for p in chain):.0f}m")
    start, end = controls[0][1], controls[-1][1]
    if chain:
        if haversine(chain[0], start) > 12:
            chain = densify(start, chain[0], 20)[:-1] + chain
        chain[0] = list(start)
        if haversine(chain[-1], end) > 12:
            chain = chain + densify(chain[-1], end, 20)[1:]
        chain[-1] = list(end)
    chain = densify_line(clean_chain(chain), 45)
    alignment = "NEW_ROW" if types.count("NEW_ROW") > len(types) / 2 else "ROAD_MEDIAN"
    return chain, notes, roads, alignment, segments


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
    chosen = list(ppt)
    chosen_along = along
    on_curve = True
    for delta in (0, 80, -80, 140, -140, 200, -200, 280, -280):
        cand = max(30.0, min(tot - 30.0, along + delta))
        p = point_at(geom, cand)
        best_i = min(range(len(geom)), key=lambda i: haversine(geom[i], p))
        if turn_deg(geom, best_i) < min_turn:
            chosen, chosen_along = list(p), cand
            on_curve = False
            break
    return chosen, chosen_along, d, tot, on_curve


def build_stops(geom, stations):
    out = []
    tot = length_m(geom)
    for i, (sname, spt, extra) in enumerate(stations):
        ppt, along, d, _tot, on_curve = snap_station(geom, spt)
        if out and along < out[-1]["along_m"] + 80:
            along = min(tot - 20, out[-1]["along_m"] + 250)
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
            "station_on_curve": "YES" if on_curve else "NO",
            "node_type": extra.get("node_type", "STATION"),
        }
        out.append(rec)
    out[0]["lon"], out[0]["lat"] = geom[0][0], geom[0][1]
    out[0]["along_m"] = 0.0
    out[0]["placement_reason"] = "TERMINUS"
    out[-1]["lon"], out[-1]["lat"] = geom[-1][0], geom[-1][1]
    out[-1]["along_m"] = tot
    out[-1]["placement_reason"] = "TERMINUS"
    return out, tot


def mrt_common(spec, km, n_stops, conf, alignment, roads, note):
    return {
        "id": spec["id"],
        "route_id": spec["id"],
        "corridor_id": "CAS-MRT-C01",
        "corridor_name": "CASCADE MRT Lebak Bulus – Ancol",
        "branch_id": spec.get("branch_id", "MAIN"),
        "branch_name": spec.get("branch_name", "Mainline Lebak Bulus – Ancol"),
        "name": spec["name"],
        "short": spec["short"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "start_name": spec["from_name"],
        "end_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "mrt",
        "status": "PROPOSED",
        "status_label": "Usulan CASCADE · MRT",
        "cascade_status": "PROPOSED",
        "network_type": "MRT",
        "plan_type": "NEW_TRUNK",
        "existing": "NO",
        "parent_route": spec.get("parent_route", ""),
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
        "geometry_source": "OSM named arterials + Nominatim extras + OSRM road-follow; NEW_ROW only if road network fails",
        "planning_note": note,
        "disclaimer": "Usulan CASCADE. Bukan MRT Jakarta existing (Lebak Bulus–Bundaran HI). Bukan masterplan resmi. Bukan DED.",
        "updated_at": RETRIEVED,
        "notes": note,
    }


def make_route_feature(spec, geom, stops, vertices_n, conf, alignment, roads, note, order):
    km = round(length_m(geom) / 1000, 2)
    props = mrt_common(spec, km, len(stops), conf, alignment, roads, note)
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
    for i, s in enumerate(stops):
        order = i + 1
        dist_prev = round((s["along_m"] - stops[i - 1]["along_m"]) / 1000, 2) if i else 0.0
        dist_next = round((stops[i + 1]["along_m"] - s["along_m"]) / 1000, 2) if i < len(stops) - 1 else 0.0
        stop_type = "TERMINUS" if i in (0, len(stops) - 1) else "INTERCHANGE" if s["interchange"] == "YES" else "STATION"
        sid = f"{spec['id']}-S{order:02d}"
        props = mrt_common(spec, common_km, len(stops), conf, alignment, roads, note)
        props.update(
            {
                "stop_id": sid,
                "stop_order": order,
                "stop_name": s["stop_name"],
                "name": s["stop_name"],
                "stop_type": stop_type,
                "node_type": s.get("node_type") or stop_type,
                "existing": s["existing"],
                "interchange": s["interchange"],
                "interchange_mode": s["interchange_mode"],
                "station_on_curve": s["station_on_curve"],
                "placement_reason": s["placement_reason"],
                "name_confidence": s["name_confidence"],
                "distance_from_previous_stop": dist_prev,
                "distance_to_next_stop": dist_next,
                "note": "Stasiun usulan CASCADE MRT. Bukan stasiun resmi. Vertex kontrol ≠ otomatis stasiun.",
            }
        )
        feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
    return feats


def inject_node(geom, pt, max_off=2500.0):
    if not geom:
        return geom
    d, along, ppt, tot = nearest_along(pt, geom)
    if d < 70:
        return geom
    if d > max_off:
        return geom
    i = min(range(len(geom)), key=lambda k: haversine(geom[k], ppt))
    j = min(i + 1, len(geom) - 1)
    left = densify(geom[i], pt, 30)
    right = densify(pt, geom[j], 30)
    return geom[: i + 1] + left[1:] + right[1:] + geom[j + 1 :]


def bbox_of(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def replace_mrt(feats, new_feats):
    kept = []
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id") or "")
        rid = str(f["properties"].get("route_id") or "")
        if fid.startswith("CAS-MRT") or rid.startswith("CAS-MRT"):
            continue
        kept.append(f)
    return kept + new_feats


def self_intersect(coords):
    seen = {}
    for i, p in enumerate(coords):
        k = (round(p[0], 6), round(p[1], 6))
        if k in seen and i - seen[k] > 3:
            return True
        seen[k] = i
    return False


def qa(geom, name):
    issues = []
    if len(geom) < 8:
        issues.append("too few vertices")
    if self_intersect(geom):
        issues.append("possible self-intersection")
    dups = 0
    seen = {}
    for i, p in enumerate(geom):
        k = (round(p[0], 5), round(p[1], 5))
        if k in seen and i - seen[k] > 8:
            dups += 1
        seen[k] = i
    if dups:
        issues.append(f"retrace-dup {dups}")
    for a, b in zip(geom, geom[1:]):
        d = haversine(a, b)
        if d > 450:
            issues.append(f"vertex gap {d:.0f}m")
            break
    print(f"  QA {name}: vtx={len(geom)} issues={issues or 'none'}")
    return issues


def confidence(notes, km, straight_km):
    conf = "HIGH"
    new_n = sum(1 for n in notes if n.startswith("NEW_ROW"))
    if new_n >= 3:
        conf = "MEDIUM"
    if new_n >= 6:
        conf = "REVIEW"
    if straight_km > 0 and km > 2.6 * straight_km:
        conf = "MEDIUM"
        notes.append(f"length {km} vs straight {straight_km:.1f}")
    return conf


def mainline_controls():
    return [
        ("Lebak Bulus", LEBAK_BULUS, ["Jalan Lebak Bulus Raya", "Jalan Ciputat Raya", "Jalan Laksamana RE Martadinata"], True),
        ("Lebak Bulus Selatan", (106.77250, -6.29820), ["Jalan Lebak Bulus Raya", "Jalan Ciputat Raya", "Jalan Laksamana RE Martadinata"], False),
        ("Ciputat Timur", (106.75800, -6.30480), ["FORCE_OSRM", "Jalan Ciputat Raya", "Jalan Laksamana RE Martadinata"], False),
        ("Ciputat", (106.74720, -6.31250), ["Jalan Laksamana RE Martadinata", "Jalan Raya Parung—Ciputat", "Jalan Ciputat Raya"], True),
        ("Gaplek Pamulang", (106.74900, -6.34500), ["Jalan Laksamana RE Martadinata", "Jalan Raya Parung—Ciputat"], False),
        ("Parung Utara", (106.74500, -6.38000), ["Jalan Raya Parung—Ciputat", "Jalan Raya Parung"], False),
        ("Parung", (106.73320, -6.42100), ["FORCE_OSRM"], True),
        ("Parung Bingung", (106.74700, -6.40650), ["FORCE_OSRM", "Jalan Raya Parung", "Jalan Raya Sawangan"], True),
        ("Sawangan", SAWANGAN, ["FORCE_OSRM", "Jalan Raya Sawangan"], True),
        ("Sawangan Timur", (106.79450, -6.39480), ["Jalan Raya Sawangan", "Jalan Arif Rahman Hakim", "FORCE_OSRM"], False),
        ("Depok Baru", (106.82169, -6.39113), ["FORCE_OSRM", "Jalan Arif Rahman Hakim", "Jalan Margonda Raya", "Jalan Raya Margonda"], True),
        ("Margonda Selatan", (106.82850, -6.38000), ["FORCE_OSRM", "Jalan Margonda Raya", "Jalan Raya Margonda"], False),
        ("Margonda", (106.83209, -6.36895), ["Jalan Raya Margonda", "Jalan Margonda Raya"], True),
        ("Universitas Indonesia", (106.83178, -6.36053), ["FORCE_OSRM", "Jalan Tole Iskandar"], False),
        ("Tole Iskandar Timur", (106.84800, -6.37000), ["FORCE_OSRM", "Jalan Tole Iskandar", "Jalan Raya Bogor"], False),
        ("Cimanggis", (106.86050, -6.37100), ["Jalan Raya Bogor"], True),
        ("Cibubur", (106.86800, -6.34800), ["Jalan Raya Bogor"], True),
        ("Ciracas", (106.87050, -6.32900), ["Jalan Raya Bogor"], True),
        ("Pasar Rebo", (106.86820, -6.32350), ["Jalan Raya Bogor", "Jalan Tanah Merdeka"], True),
        ("Tanah Merdeka", (106.87500, -6.31200), ["Jalan Tanah Merdeka", "Jalan Raya Bogor"], True),
        ("Kampung Rambutan", (106.88215, -6.30988), ["Jalan Tanah Merdeka", "Jalan Raya Bogor"], True),
        ("Raya Bogor Utara", (106.86800, -6.30000), ["Jalan Raya Bogor"], False),
        ("Kramat Jati vertex", (106.86700, -6.27800), ["Jalan Raya Bogor"], False),
        ("PGC", PGC, ["Jalan Condet Raya", "Jalan Batu Ampar III", "Jalan Dewi Sartika"], True),
        ("Batu Ampar", (106.86000, -6.27200), ["Jalan Condet Raya", "Jalan Batu Ampar III"], False),
        ("Condet", CONDET, ["NEW_ROW"], True),
        ("Condet Utara", (106.85400, -6.25800), ["FORCE_OSRM", "Jalan Dewi Sartika", "Jalan Otto Iskandar Dinata"], False),
        ("Otista", (106.86750, -6.23800), ["FORCE_OSRM", "Jalan Dewi Sartika", "Jalan Otto Iskandar Dinata"], False),
        ("Kampung Melayu", KAMPUNG_MELAYU, ["Jalan Otto Iskandar Dinata", "Jalan Jatinegara Barat Raya", "Jalan Dewi Sartika"], True),
        ("Tebet", (106.85842, -6.22640), ["FORCE_OSRM", "Jalan Jatinegara Barat Raya", "Jalan Dokter Saharjo"], True),
        ("Manggarai", MANGGARAI, ["FORCE_OSRM", "Jalan Salemba Raya", "Jalan Sultan Agung"], True),
        ("Salemba", (106.85080, -6.19550), ["FORCE_OSRM", "Jalan Salemba Raya", "Jalan Proklamasi", "Jalan Kramat Raya"], True),
        ("Senen", (106.84410, -6.17276), ["FORCE_OSRM", "Jalan Gunung Sahari Raya", "Jalan Letnan Jenderal Suprapto"], True),
        ("Kemayoran", (106.84174, -6.16255), ["Jalan Gunung Sahari Raya", "Jalan Benyamin Sueb"], True),
        ("Kemayoran Utara", (106.84600, -6.14500), ["FORCE_OSRM", "Jalan Benyamin Sueb", "Jalan Lodan Raya"], False),
        ("Ancol", ANCOL, ["Jalan Benyamin Sueb", "Jalan Lodan Raya"], True),
    ]


def branch_controls():
    return [
        ("Sawangan", SAWANGAN, ["FORCE_OSRM", "Jalan Raya Limo", "Jalan Cinere Raya"], True),
        ("Limo", (106.77620, -6.35100), ["Jalan Raya Limo", "Jalan Cinere Raya"], False),
        ("Cinere", (106.78500, -6.33250), ["Jalan Cinere Raya", "Jalan Raya Cinere"], True),
        ("Krukut", (106.79600, -6.32200), ["Jalan Cinere Raya", "Jalan Andara"], True),
        ("Andara", (106.80362, -6.31392), ["Jalan Andara", "Jalan Tahi Bonar Simatupang", "Jalan TB Simatupang"], True),
        ("Cilandak", (106.79995, -6.29147), ["FORCE_OSRM", "Jalan Tahi Bonar Simatupang", "Jalan TB Simatupang"], True),
        ("Fatmawati", FATMAWATI, ["Jalan RS Fatmawati", "Jalan Raden Ajeng Kartini"], True),
    ]


NOTE_MAIN = (
    "CAS-MRT-C01 mainline usulan CASCADE: Lebak Bulus–Ciputat–Parung–Parung Bingung–Sawangan "
    "(node percabangan)–Depok Baru–Margonda–Jalan Raya Bogor–Cimanggis–Cibubur–Ciracas–Pasar Rebo–"
    "Tanah Merdeka–Kampung Rambutan–PGC–Condet–Kampung Melayu–Tebet–Manggarai–Salemba–Senen–"
    "Kemayoran–Ancol. Bukan MRT existing Lebak Bulus–Bundaran HI. Bukan masterplan resmi. "
    "PGC→Condet→Kampung Melayu (bukan Kramat Jati sebagai jalur utama setelah PGC). "
    "Kramat Jati hanya vertex di Raya Bogor Kampung Rambutan–PGC, bukan stasiun. "
    "Manggarai interchange, bukan terminus. Fatmawati adalah ujung BRANCH, bukan mainline."
)
NOTE_BRANCH = (
    "CAS-MRT-C01-A branch usulan CASCADE: Sawangan (node yang sama dengan mainline)–Cinere–Krukut–"
    "Andara–Cilandak–Fatmawati (menumpang stasiun MRT existing). Bukan bagian mainline setelah Sawangan. "
    "Bukan perpanjangan MRT NS existing. Bukan masterplan."
)


def pack(spec, geom, controls, stations, notes, roads, alignment, order):
    stops, tot = build_stops(geom, stations)
    km = round(tot / 1000, 2)
    straight = haversine(controls[0][1], controls[-1][1]) / 1000
    conf = confidence(notes, km, straight)
    rf, km = make_route_feature(spec, geom, stops, len(controls), conf, alignment, roads, spec["note"], order)
    sf = make_stop_features(spec, geom, stops, conf, alignment, roads, spec["note"], km)
    meta = {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "mrt",
        "branch_id": spec.get("branch_id", "MAIN"),
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": SOURCE,
        "status": "PROPOSED",
        "network_type": "MRT",
        "plan_type": "NEW_TRUNK",
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "notes": spec["note"],
        "bbox": bbox_of(geom),
    }
    return rf, sf, stops, km, conf, meta


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
            raise SystemExit(f"TJ drifted: {k} {before.get(k)}")
    for k, h in LRT_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"LRT drifted: {k} {before.get(k)}")
    print("CAS-TJ + CAS-LRT hashes frozen OK")

    print("loading roads...")
    road_map = load_mrt_roads()

    print("walking CAS-MRT-C01 mainline")
    main_c = mainline_controls()
    geom_m, notes_m, roads_m, align_m, segs_m = walk_controls(main_c, road_map, min_loop=3800.0)
    for pin in (SAWANGAN, CONDET, PGC, MANGGARAI, ANCOL, LEBAK_BULUS, PARUNG, KAMPUNG_MELAYU):
        geom_m = inject_node(geom_m, pin, max_off=2500.0)
    geom_m = densify_line(clean_chain(geom_m), 45)
    qa_m = qa(geom_m, "MAIN")
    by = {c[0]: c[1] for c in main_c}
    station_names_m = [
        "Lebak Bulus", "Ciputat", "Parung", "Parung Bingung", "Sawangan",
        "Depok Baru", "Margonda", "Cimanggis", "Cibubur", "Ciracas", "Pasar Rebo",
        "Tanah Merdeka", "Kampung Rambutan", "PGC", "Condet", "Kampung Melayu",
        "Tebet", "Manggarai", "Salemba", "Senen", "Kemayoran", "Ancol",
    ]
    shared_m = {
        "Lebak Bulus": {"existing": "YES", "interchange": "YES", "interchange_mode": "MRT existing NS", "placement_reason": "EXISTING_CONNECTION", "node_type": "TERMINUS"},
        "Sawangan": {"interchange": "YES", "interchange_mode": "BRANCH", "node_type": "BRANCH"},
        "Depok Baru": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "MAJOR_TRANSIT"},
        "Kampung Rambutan": {"existing": "YES", "interchange": "YES", "interchange_mode": "LRT Jabodebek / TJ", "node_type": "MAJOR_TRANSIT"},
        "PGC": {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT"},
        "Condet": {"node_type": "CONTROL"},
        "Kampung Melayu": {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT"},
        "Tebet": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL"},
        "Manggarai": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "INTERCHANGE"},
        "Senen": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL"},
        "Kemayoran": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL"},
        "Ancol": {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "TERMINUS"},
    }
    stations_m = [(n, by[n], shared_m.get(n, {"placement_reason": "SERVICE_NODE"})) for n in station_names_m]
    spec_m = dict(
        id="CAS-MRT-C01",
        name="Lebak Bulus – Ancol",
        short="Lebak Bulus – Ancol",
        from_name="Lebak Bulus",
        to_name="Ancol",
        direction="Lebak Bulus → Ancol",
        branch_id="MAIN",
        branch_name="Mainline Lebak Bulus – Ancol",
        parent_route="",
        note=NOTE_MAIN,
    )
    rf_m, sf_m, stops_m, km_m, conf_m, meta_m = pack(spec_m, geom_m, main_c, stations_m, notes_m, roads_m, align_m, 20)

    print("walking CAS-MRT-C01-A Fatmawati branch")
    br_c = branch_controls()
    geom_b, notes_b, roads_b, align_b, segs_b = walk_controls(br_c, road_map, min_loop=1800.0)
    qa_b = qa(geom_b, "BRANCH")
    byb = {c[0]: c[1] for c in br_c}
    station_names_b = ["Sawangan", "Cinere", "Krukut", "Andara", "Cilandak", "Fatmawati"]
    shared_b = {
        "Sawangan": {"interchange": "YES", "interchange_mode": "BRANCH", "node_type": "BRANCH"},
        "Fatmawati": {"existing": "YES", "interchange": "YES", "interchange_mode": "MRT existing NS", "node_type": "TERMINUS"},
    }
    stations_b = [(n, byb[n], shared_b.get(n, {"placement_reason": "SERVICE_NODE"})) for n in station_names_b]
    spec_b = dict(
        id="CAS-MRT-C01-A",
        name="Sawangan – Fatmawati",
        short="Sawangan – Fatmawati",
        from_name="Sawangan",
        to_name="Fatmawati",
        direction="Sawangan → Fatmawati",
        branch_id="A",
        branch_name="Branch Sawangan – Cinere – Fatmawati",
        parent_route="CAS-MRT-C01",
        note=NOTE_BRANCH,
    )
    rf_b, sf_b, stops_b, km_b, conf_b, meta_b = pack(spec_b, geom_b, br_c, stations_b, notes_b, roads_b, align_b, 21)

    assert haversine(geom_m[0], LEBAK_BULUS) < 40, "start not Lebak Bulus"
    assert haversine(geom_m[-1], ANCOL) < 80, "end not Ancol"
    assert haversine(geom_b[0], SAWANGAN) < 40, "branch start not Sawangan"
    assert haversine(geom_b[-1], FATMAWATI) < 80, "branch end not Fatmawati"
    assert min(haversine(p, SAWANGAN) for p in geom_m) < 80, "mainline missed Sawangan"
    assert min(haversine(p, CONDET) for p in geom_m) < 250, "mainline missed Condet"
    assert min(haversine(p, PGC) for p in geom_m) < 150, "mainline missed PGC"
    assert min(haversine(p, MANGGARAI) for p in geom_m) < 150, "mainline missed Manggarai"
    assert min(p[1] for p in geom_m) < -6.410, "mainline must reach Parung south"
    assert max(p[1] for p in geom_m) > -6.135, "mainline must reach Ancol north"
    d_fat_main = min(haversine(p, FATMAWATI) for p in geom_m)
    assert d_fat_main > 1500, f"mainline must not go to Fatmawati ({d_fat_main:.0f}m)"
    assert min(haversine(p, ANCOL) for p in geom_b) > 8000
    assert min(haversine(p, PGC) for p in geom_b) > 5000
    assert all(s["stop_name"] != "Kramat Jati" for s in stops_m)
    d_saw = haversine(geom_b[0], min(geom_m, key=lambda p: haversine(p, SAWANGAN)))
    print(f"  Sawangan shared node {d_saw:.0f}m  Fatmawati vs main {d_fat_main:.0f}m")

    route_feats = replace_mrt(old_routes["features"], [rf_m, rf_b])
    stop_feats = replace_mrt(old_stops["features"], sf_m + sf_b)
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    assert "CAS-TJ07" in ids and "CAS-LRT-C02" in ids and "CAS-MRT-C01" in ids and "CAS-MRT-C01-A" in ids

    meta = [m for m in (old_meta.get("corridors") or []) if not str(m.get("id", "")).startswith("CAS-MRT")]
    meta.extend([meta_m, meta_b])

    after = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in TJ_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"TJ DRIFT after MRT write: {k}")
    for k, h in LRT_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"LRT DRIFT after MRT write: {k}")

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["source"] = SOURCE
    existing["corridors"] = meta
    existing["mrt_note"] = "CAS-MRT-C01 mainline Lebak Bulus–Ancol + branch Sawangan–Fatmawati. Bukan MRT existing. Bukan masterplan."
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_mrt_segments.json").write_text(json.dumps({"main": segs_m, "branch": segs_b}, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
            row["notes"] = (
                "CAS-TJ01..11 BRT frozen + CAS-LRT-C02/C04 + CAS-MRT-C01 Lebak Bulus–Ancol "
                "(branch Sawangan–Fatmawati). Usulan CASCADE. Bukan masterplan. #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "corridors": [meta_m, meta_b],
        "qa": {"MAIN": qa_m, "BRANCH": qa_b},
        "notes_main": notes_m[-20:],
        "notes_branch": notes_b[-12:],
        "tj_frozen": TJ_HASH,
        "lrt_frozen": LRT_HASH,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "cas_mrt_ids": ["CAS-MRT-C01", "CAS-MRT-C01-A"],
        "sawangan_shared_m": round(d_saw, 1),
        "fatmawati_vs_main_m": round(d_fat_main, 1),
        "hashes": {"CAS-MRT-C01": after["CAS-MRT-C01"], "CAS-MRT-C01-A": after["CAS-MRT-C01-A"]},
    }
    (OUT / "cascade_validation_mrt.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))

    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"CAS-MRT-C01    {km_m} km  stations={len(stops_m)}  {conf_m}  {align_m}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops_m))
    print(f"CAS-MRT-C01-A  {km_b} km  stations={len(stops_b)}  {conf_b}  {align_b}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops_b))
    print("TJ+LRT frozen OK  masterplan/existing untouched")
    print("ids", ids)


if __name__ == "__main__":
    main()
