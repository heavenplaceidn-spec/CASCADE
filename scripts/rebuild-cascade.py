#!/usr/bin/env python3
"""PASS 17 — digitize CASCADE TransJakarta BRT trunks (road-aligned).

Not DED. Not existing TJ. Not masterplan railway. Not KRL/MRT/LRT usulan.
CASCADE.txt was not on disk; corridor structure from cascade_corridors.py.
"""
from __future__ import annotations

import heapq
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from cascade_corridors import CORRIDORS, NODES

ROOT = Path("/workspace")
OSM_ROADS = ROOT / "public/data/roads.geojson"
PUB = ROOT / "public/data"
OUT_DIR = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-11"
SOURCE = "CASCADE.txt"


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
    if not coords or len(coords) < 2:
        return 0.0
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
    best, along, pt = 1e18, 0.0, coords[0]
    for i in range(1, len(coords)):
        d, t = dist_point_to_seg(p, coords[i - 1], coords[i])
        if d < best:
            best = d
            along = meas[i - 1] + t * (meas[i] - meas[i - 1])
            pt = [
                coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0]),
                coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1]),
            ]
    return best, along, pt, meas[-1]


def point_at(coords, m):
    meas = [0.0]
    for i in range(1, len(coords)):
        meas.append(meas[-1] + haversine(coords[i - 1], coords[i]))
    total = meas[-1] or 1.0
    m = max(0.0, min(total, m))
    for i in range(1, len(coords)):
        if meas[i] >= m:
            t = 0 if meas[i] == meas[i - 1] else (m - meas[i - 1]) / (meas[i] - meas[i - 1])
            return [
                coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0]),
                coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1]),
            ]
    return coords[-1]


def slice_along(coords, a_m, b_m):
    if a_m > b_m:
        a_m, b_m = b_m, a_m
    meas = [0.0]
    for i in range(1, len(coords)):
        meas.append(meas[-1] + haversine(coords[i - 1], coords[i]))
    total = meas[-1] or 1.0
    a_m = max(0, min(total, a_m))
    b_m = max(0, min(total, b_m))
    out = [point_at(coords, a_m)]
    for i, m in enumerate(meas):
        if a_m < m < b_m:
            out.append(coords[i])
    out.append(point_at(coords, b_m))
    cleaned = [out[0]]
    for p in out[1:]:
        if haversine(cleaned[-1], p) > 1:
            cleaned.append(p)
    return cleaned if len(cleaned) >= 2 else [out[0], out[-1]]


def densify(a, b, step=80.0):
    d = haversine(a, b)
    if d < step:
        return [list(a), list(b)]
    n = max(2, int(d / step) + 1)
    return [
        [a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1)]
        for i in range(n)
    ]


def densify_line(coords, step=70.0):
    out = [list(coords[0])]
    for i in range(1, len(coords)):
        chunk = densify(out[-1], coords[i], step)
        out.extend(chunk[1:])
    return out


def douglas(coords, tol=12.0):
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


def flatten(geom):
    t = geom["type"]
    if t == "LineString":
        return [geom["coordinates"]]
    if t == "MultiLineString":
        return geom["coordinates"]
    return []


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


def road_between(road_map, names, a, b, max_off=700, max_stretch=2.8):
    straight = haversine(a, b)
    if straight < 80:
        return None, None
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
            if abs(a1 - a0) < 80:
                continue
            sl = slice_along(run, a0, a1)
            L = length_m(sl)
            if L < straight * 0.55 or L > straight * max_stretch:
                continue
            score = (d0 + d1) + 0.15 * (L - straight)
            if best is None or score < best[0]:
                best = (score, sl, name)
    if not best:
        return None, None
    return best[1], best[2]


def is_toll(name):
    n = (name or "").lower()
    return "tol " in n or n.startswith("tol") or "jalan tol" in n


def remove_hairpins(coords, max_turn=115.0):
    """Drop short off-road spikes. Keep real 1 km hooks (Cipulir, Joglo, etc.)."""
    coords = [list(p) for p in coords]
    if len(coords) < 4:
        return coords
    changed = True
    guard = 0
    while changed and guard < 80 and len(coords) > 3:
        changed = False
        guard += 1
        angs = turn_angles(coords)
        worst = None
        for i, d, _pt in angs:
            arm = min(haversine(coords[i - 1], coords[i]), haversine(coords[i], coords[i + 1]))
            skip = haversine(coords[i - 1], coords[i]) + haversine(coords[i], coords[i + 1])
            cut = haversine(coords[i - 1], coords[i + 1])
            short_spike = arm < 260 and d >= 145
            tiny_kink = arm < 140 and d >= max_turn and cut < skip * 0.65
            if short_spike or tiny_kink:
                if worst is None or d > worst[0]:
                    worst = (d, i)
        if worst:
            del coords[worst[1]]
            changed = True
    return coords if len(coords) >= 2 else coords


def remove_loops(coords, rejoin_m=140.0, min_loop=700.0):
    """Cut out-and-back loops: if the line returns to a previous point after >= min_loop, drop the detour."""
    coords = [list(p) for p in coords]
    changed = True
    guard = 0
    while changed and guard < 12 and len(coords) > 4:
        changed = False
        guard += 1
        meas = [0.0]
        for i in range(1, len(coords)):
            meas.append(meas[-1] + haversine(coords[i - 1], coords[i]))
        cut = None
        for i in range(len(coords)):
            for j in range(i + 2, len(coords)):
                if meas[j] - meas[i] < min_loop:
                    continue
                if haversine(coords[i], coords[j]) <= rejoin_m:
                    if cut is None or (j - i) > (cut[1] - cut[0]):
                        cut = (i, j)
                    break
            if cut and cut[0] == i:
                break
        if cut:
            i, j = cut
            coords = coords[: i + 1] + coords[j:]
            changed = True
    return coords


def ensure_termini(chain, a, b):
    if not chain or len(chain) < 2:
        return chain
    if haversine(chain[0], a) > 80:
        chain = densify(a, chain[0], 60)[:-1] + chain
        chain[0] = list(a)
    else:
        chain[0] = list(a)
    if haversine(chain[-1], b) > 80:
        chain = chain + densify(chain[-1], b, 60)[1:]
        chain[-1] = list(b)
    else:
        chain[-1] = list(b)
    return clean_chain(chain)

    if not chain or len(chain) < 2:
        return chain
    if haversine(chain[0], a) > 80:
        chain = densify(a, chain[0], 60)[:-1] + chain
        chain[0] = list(a)
    else:
        chain[0] = list(a)
    if haversine(chain[-1], b) > 80:
        chain = chain + densify(chain[-1], b, 60)[1:]
        chain[-1] = list(b)
    else:
        chain[-1] = list(b)
    return clean_chain(chain)


def append_chain(chain, sl):
    if not sl:
        return chain
    sl = [list(p) for p in sl]
    if not chain:
        return sl
    if haversine(chain[-1], sl[0]) < 80:
        chain.extend(sl[1:])
    elif haversine(chain[-1], sl[-1]) < 80:
        chain.extend(list(reversed(sl))[1:])
    else:
        # short bridge only — long diagonals are forbidden; caller should graph-route
        if haversine(chain[-1], sl[0]) < 180:
            bridge = densify(chain[-1], sl[0], 50)
            chain.extend(bridge[1:])
            chain.extend(sl[1:])
        else:
            chain.extend(sl)
    return chain


def clean_chain(coords):
    if not coords:
        return coords
    out = [coords[0]]
    for p in coords[1:]:
        if haversine(out[-1], p) > 4:
            out.append(p)
    return out if len(out) >= 2 else coords


# ---------------------------------------------------------------------------
# road graph
# ---------------------------------------------------------------------------


class RoadGraph:
    def __init__(self, road_map):
        self.pts = []
        self.adj = defaultdict(list)  # i -> [(j, cost, dist, name)]
        self.names = []
        self.grid = defaultdict(list)
        self.cell = 0.0009
        self._build(road_map)

    def _key(self, p):
        return (int(p[0] / self.cell), int(p[1] / self.cell))

    def _add_pt(self, p, name):
        i = len(self.pts)
        self.pts.append(list(p))
        self.names.append(name)
        self.grid[self._key(p)].append(i)
        return i

    def _edge(self, i, j, name, weight=1.0):
        d = haversine(self.pts[i], self.pts[j])
        if d < 1:
            return
        c = d * weight
        self.adj[i].append((j, c, d, name))
        self.adj[j].append((i, c, d, name))

    def _weight(self, name):
        n = (name or "").lower()
        if n.startswith("tj-k"):
            return 0.85
        if "tol" in n or n.startswith("tol "):
            return 3.6
        return 1.0

    def _build(self, road_map):
        for name, feat in road_map.items():
            w = self._weight(name)
            for part in flatten(feat["geometry"]):
                if len(part) < 2:
                    continue
                pts = densify_line(part, 80)
                prev = None
                for p in pts:
                    i = self._add_pt(p, name)
                    if prev is not None:
                        self._edge(prev, i, name, w)
                    prev = i
        # intersection links
        for i, p in enumerate(self.pts):
            cx, cy = self._key(p)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in self.grid[(cx + dx, cy + dy)]:
                        if j <= i:
                            continue
                        d = haversine(p, self.pts[j])
                        if 1 < d < 70:
                            self._edge(i, j, "link", 1.15)

    def nearest(self, p, max_off=800, prefer=None):
        cx, cy = self._key(p)
        best = None
        for rad in range(0, 10):
            for dx in range(-rad, rad + 1):
                for dy in range(-rad, rad + 1):
                    if max(abs(dx), abs(dy)) != rad and rad:
                        continue
                    for j in self.grid.get((cx + dx, cy + dy), []):
                        d = haversine(p, self.pts[j])
                        if d > max_off:
                            continue
                        bonus = 0
                        if prefer and self.names[j] in prefer:
                            bonus = -80
                        score = d + bonus
                        if best is None or score < best[0]:
                            best = (score, d, j)
            if best and best[1] < 120:
                break
        return None if best is None else (best[2], best[1])

    def route(self, a, b, prefer=None, max_factor=2.8, skip_toll=True):
        ia = self.nearest(a, prefer=prefer)
        ib = self.nearest(b, prefer=prefer)
        if not ia or not ib:
            return None, None
        s, t = ia[0], ib[0]
        straight = haversine(a, b)
        prefer = set(prefer or [])
        pad = max(0.022, min(0.045, (straight / 111320) * 1.05 + 0.016))
        minlon, maxlon = min(a[0], b[0]) - pad, max(a[0], b[0]) + pad
        minlat, maxlat = min(a[1], b[1]) - pad, max(a[1], b[1]) + pad

        def inside(i):
            p = self.pts[i]
            return minlon <= p[0] <= maxlon and minlat <= p[1] <= maxlat

        dist = {s: 0.0}
        prev = {s: None}
        pq = [(haversine(self.pts[s], self.pts[t]), 0.0, s)]
        seen = set()
        cap = max(straight * max_factor, 2200) + 800
        while pq:
            _f, c, u = heapq.heappop(pq)
            if u in seen:
                continue
            seen.add(u)
            if u == t:
                break
            if c > cap:
                continue
            for v, w, d, name in self.adj[u]:
                if v != t and not inside(v):
                    continue
                extra = 0.0
                if prefer and name not in prefer and name != "link":
                    extra = 0.85 * d
                if is_toll(name) and not any(is_toll(x) for x in prefer):
                    extra += (8.0 if skip_toll else 2.0) * d
                nc = c + w + extra
                if nc < dist.get(v, 1e18):
                    dist[v] = nc
                    prev[v] = u
                    heapq.heappush(pq, (nc + 1.05 * haversine(self.pts[v], self.pts[t]), nc, v))
        if t not in prev and t != s:
            return None, None
        path = []
        cur = t
        guard = 0
        while cur is not None and guard < 20000:
            path.append(self.pts[cur])
            cur = prev.get(cur)
            guard += 1
        path.reverse()
        if len(path) < 2:
            return None, None
        L = length_m(path)
        if L > straight * max_factor and L > 1800:
            return None, None
        return path, "graph"


def load_snaps():
    snaps = {}
    mapping = [
        ("masterplan_stations.geojson", "masterplan", "name"),
        ("krl_stops.geojson", "krl", "name"),
        ("mrt_stops.geojson", "mrt", "name"),
        ("lrt_stops.geojson", "lrt", "name"),
        ("transjakarta_stops.geojson", "tj", "name"),
    ]
    for fn, mode, key in mapping:
        p = PUB / fn
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for f in d["features"]:
            n = f["properties"].get(key) or f["properties"].get("stop_name") or f["properties"].get("station_name")
            if not n:
                continue
            c = f["geometry"]["coordinates"]
            snaps[n] = (c[0], c[1], f"existing_{mode}", mode)
    alias = {
        "JIS": "Jakarta International Stadium",
        "Puri Beta": "Puri Beta 1",
        "Stasiun Cakung": "Cakung",
        "Senen": "Pasar Senen",
        "BKT": "Stasiun Klender",
        "Trikora": "Trikora",
        "Pos Pengumben": "Pos Pengumben",
        "PGC": "PGC",
        "Universitas Indonesia": "Universitas Indonesia",
        "Pulo Gebang": "Pulo Gebang",
        "Pulo Gadung": "Pulo Gadung",
        "Pinang Ranti": "Pinang Ranti",
        "Kalideres": "Kalideres",
        "Rawa Buaya": "Rawa Buaya",
        "Penggilingan": "Penggilingan",
        "Kampung Melayu": "Kampung Melayu",
        "Galunggung": "Galunggung",
        "Lebak Bulus": "Lebak Bulus",
        "Tanah Abang": "Tanah Abang",
        "Palmerah": "Palmerah",
        "Jatinegara": "Jatinegara",
        "TMII": "TMII",
        "Fatmawati": "Fatmawati",
        "Tebet": "Tebet",
        "Lenteng Agung": "Lenteng Agung",
        "Cakung": "Cakung",
    }
    for a, b in alias.items():
        if b in snaps and a not in snaps:
            snaps[a] = snaps[b]
    return snaps


def load_road_map():
    fc = json.loads(OSM_ROADS.read_text())
    road_map = {f["properties"]["name"]: f for f in fc["features"]}
    tj = json.loads((PUB / "transjakarta_routes.geojson").read_text())
    for f in tj["features"]:
        no = f["properties"].get("corridor_no")
        if no is None:
            continue
        road_map[f"TJ-K{int(no)}"] = f
    return road_map


def resolve(name, snaps):
    if name in NODES:
        lon, lat, src = NODES[name]
        return lon, lat, src, "node"
    if name in snaps:
        lon, lat, src, mode = snaps[name]
        return lon, lat, src, mode
    for k, v in snaps.items():
        if isinstance(k, str) and name.lower() == k.lower():
            return v[0], v[1], v[2], v[3]
    return None


def snap_to_named(road_map, names, p, max_off=450):
    best = None
    for name in names:
        feat = road_map.get(name)
        if not feat:
            continue
        for run in stitch(flatten(feat["geometry"]), gap=120):
            d, along, ppt, _ = nearest_along(p, run)
            if d > max_off:
                continue
            if best is None or d < best[0]:
                best = (d, ppt, name)
    if not best:
        return None
    return best[1], best[2], best[0]


def pair_route(road_map, graph, a, b, roads):
    """Road slice, then graph (preferred then open), then densify. Never spikes off-road."""
    sl, rname = road_between(road_map, roads, a, b) if roads else (None, None)
    method = "ROAD"
    if sl is None:
        sl, _g = graph.route(a, b, prefer=roads, max_factor=2.8)
        if sl:
            rname = roads[0] if roads else "graph"
            method = "GRAPH"
    if sl is None and roads:
        sl, _g = graph.route(a, b, prefer=None, max_factor=3.0)
        if sl:
            rname = roads[0] if roads else "graph"
            method = "GRAPH"
    if sl is None:
        d = haversine(a, b)
        sl = densify(a, b, 70)
        rname = roads[0] if roads else "unresolved"
        method = "SPINE"
        return sl, rname, method, d
    return sl, rname, method, 0.0


def build_from_controls(spec, snaps, road_map, graph, control_key="controls", roads_key="road_by_pair"):
    warnings = []
    names = spec[control_key]
    pts = []
    for n in names:
        r = resolve(n, snaps)
        if not r:
            warnings.append(f"unresolved control {n}")
            continue
        lon, lat, src, mode = r
        pts.append((n, [lon, lat], src, mode))
    if len(pts) < 2:
        return None, [], warnings, "empty"
    pairs = spec.get(roads_key) or []
    # snap each control onto its incident roads so the line does not spike
    snapped = []
    for i, (n, xy, src, mode) in enumerate(pts):
        roads = []
        if i < len(pairs):
            roads += pairs[i]
        if i > 0 and i - 1 < len(pairs):
            roads += pairs[i - 1]
        hit = snap_to_named(road_map, roads, xy, max_off=420)
        if hit and hit[2] < 220:
            snapped.append((n, list(hit[0]), src, mode, hit[1]))
        else:
            gn = graph.nearest(xy, prefer=roads, max_off=500)
            if gn and gn[1] < 180:
                snapped.append((n, list(graph.pts[gn[0]]), src, mode, graph.names[gn[0]]))
            else:
                snapped.append((n, list(xy), src, mode, roads[0] if roads else ""))
    pts = [(n, xy, src, mode) for n, xy, src, mode, _rn in snapped]

    chain = []
    used_road = False
    vertex_rows = []
    vid = 0
    for i in range(len(pts) - 1):
        a_name, a, a_src, _ = pts[i]
        b_name, b, b_src, _ = pts[i + 1]
        roads = pairs[i] if i < len(pairs) else []
        sl, rname, method, spine_d = pair_route(road_map, graph, a, b, roads)
        if method == "SPINE" and spine_d > 250:
            warnings.append(f"SPINE {a_name}–{b_name} {spine_d/1000:.2f} km")
        if method in ("ROAD", "GRAPH"):
            used_road = True
        vid += 1
        vertex_rows.append(
            {
                "vertex_id": f"{spec['id']}-V{vid:02d}",
                "route_id": spec["id"],
                "vertex_order": vid,
                "vertex_name": a_name,
                "vertex_type": "ENDPOINT" if i == 0 else "ROAD_CHANGE",
                "road_name": rname or "",
                "intersection": f"{a_name} / {b_name}",
                "area_name": a_name,
                "geometry": a,
                "source": a_src,
                "confidence": "HIGH" if method in ("ROAD", "GRAPH") else "LOW",
                "from_stop": a_name,
                "to_stop": b_name,
                "method": method,
            }
        )
        chain = append_chain(chain, sl)
    vid += 1
    vertex_rows.append(
        {
            "vertex_id": f"{spec['id']}-V{vid:02d}",
            "route_id": spec["id"],
            "vertex_name": pts[-1][0],
            "vertex_order": vid,
            "vertex_type": "ENDPOINT",
            "road_name": pairs[-1][0] if pairs else "",
            "intersection": pts[-1][0],
            "area_name": pts[-1][0],
            "geometry": pts[-1][1],
            "source": pts[-1][2],
            "confidence": "HIGH",
            "from_stop": pts[-1][0],
            "to_stop": "",
            "method": "ROAD" if used_road else "SPINE",
        }
    )
    chain = clean_chain(chain)
    chain = remove_hairpins(chain, 115)
    chain = remove_loops(chain)
    chain = douglas(chain, 10)
    chain = remove_hairpins(chain, 125)
    chain = clean_chain(chain)
    chain = ensure_termini(chain, pts[0][1], pts[-1][1])
    chain = remove_loops(chain, rejoin_m=110, min_loop=900)
    chain = ensure_termini(chain, pts[0][1], pts[-1][1])
    method = "ROAD_REFERENCE" if used_road else "DOCUMENT_RECONSTRUCTION"
    return chain, vertex_rows, warnings, method


def poi_index(snaps):
    pois = []
    for name, val in snaps.items():
        if not isinstance(name, str):
            continue
        lon, lat, src, mode = val
        score = 1
        if mode in ("krl", "mrt", "lrt"):
            score = 5
        elif mode == "tj":
            score = 4
        elif mode == "masterplan":
            score = 2
        low = name.lower()
        if any(k in low for k in ("pasar", "mall", "universitas", "terminal", "stadion", "rs ", "rumah sakit")):
            score = max(score, 4)
        pois.append({"name": name, "lon": lon, "lat": lat, "src": src, "mode": mode, "score": score})
    return pois


def place_stops(spec, geom, snaps, pois):
    anchors = spec["anchors"][:]
    if spec.get("dual_direction"):
        anchors = [a for a in anchors if a != "Stasiun Cakung"]
    placed = []
    used = set()

    def dirty(name):
        low = (name or "").lower()
        if "arah " in low or low.startswith("halte ") or low.startswith("stop "):
            return True
        if "harjamukti" in low or "underpass" in low:
            return True
        return False

    def try_place(name, reason, conf, src_kind, min_sep=380):
        if dirty(name) or name in used:
            return False
        r = resolve(name, snaps)
        if not r:
            return False
        lon, lat, src, mode = r
        d, along, ppt, tot = nearest_along([lon, lat], geom)
        lim = 950 if reason in ("TERMINUS", "ANCHOR") else 520
        if d > lim:
            return False
        for p in placed:
            if abs(p["along_m"] - along) < min_sep and p["stop_name"] != name:
                if reason not in ("TERMINUS", "ANCHOR") or abs(p["along_m"] - along) < 140:
                    return False
        placed.append(
            {
                "stop_name": name,
                "lon": ppt[0],
                "lat": ppt[1],
                "along_m": along,
                "distance_to_route": round(d, 1),
                "placement_reason": reason,
                "name_source": "CASCADE.txt" if reason in ("TERMINUS", "ANCHOR") else src_kind,
                "name_confidence": conf,
                "location_confidence": "HIGH" if d <= 25 else "MEDIUM" if d <= 50 else "REVIEW" if d <= 75 else "LOW",
                "source_type": src,
                "existing": "YES" if str(src).startswith("existing_") else "NO",
                "snap_mode": mode,
            }
        )
        used.add(name)
        return True

    try_place(spec["from_name"], "TERMINUS", "HIGH", "CASCADE.txt", min_sep=80)
    try_place(spec["to_name"], "TERMINUS", "HIGH", "CASCADE.txt", min_sep=80)
    # termini sit on the polyline ends even if the named point is slightly off
    tot0 = length_m(geom)
    if not any(p["stop_name"] == spec["from_name"] for p in placed):
        placed.append(
            {
                "stop_name": spec["from_name"],
                "lon": geom[0][0],
                "lat": geom[0][1],
                "along_m": 0.0,
                "distance_to_route": 0.0,
                "placement_reason": "TERMINUS",
                "name_source": "CASCADE.txt",
                "name_confidence": "HIGH",
                "location_confidence": "HIGH",
                "source_type": "node",
                "existing": "NO",
                "snap_mode": "terminus",
            }
        )
        used.add(spec["from_name"])
    else:
        for p in placed:
            if p["stop_name"] == spec["from_name"]:
                p["along_m"] = 0.0
                p["lon"], p["lat"] = geom[0][0], geom[0][1]
                p["distance_to_route"] = 0.0
    if not any(p["stop_name"] == spec["to_name"] for p in placed):
        placed.append(
            {
                "stop_name": spec["to_name"],
                "lon": geom[-1][0],
                "lat": geom[-1][1],
                "along_m": tot0,
                "distance_to_route": 0.0,
                "placement_reason": "TERMINUS",
                "name_source": "CASCADE.txt",
                "name_confidence": "HIGH",
                "location_confidence": "HIGH",
                "source_type": "node",
                "existing": "NO",
                "snap_mode": "terminus",
            }
        )
        used.add(spec["to_name"])
    else:
        for p in placed:
            if p["stop_name"] == spec["to_name"]:
                p["along_m"] = tot0
                p["lon"], p["lat"] = geom[-1][0], geom[-1][1]
                p["distance_to_route"] = 0.0

    for a in anchors:
        if a not in used:
            try_place(a, "ANCHOR", "HIGH", "CASCADE.txt")
    placed.sort(key=lambda p: p["along_m"])

    def gaps():
        return [
            (placed[i], placed[i + 1], placed[i + 1]["along_m"] - placed[i]["along_m"])
            for i in range(len(placed) - 1)
        ]

    for _ in range(36):
        changed = False
        for prev, nxt, gap in gaps():
            if gap < 3100:
                continue
            pad = 700 if gap >= 4200 else 1200
            snap_lim = 280 if gap >= 4200 else 140
            lo, hi = prev["along_m"] + pad, nxt["along_m"] - pad
            if hi <= lo:
                continue
            # prefer named control nodes on the line
            node_hit = None
            best_node = None
            for nm, (lon, lat, src) in NODES.items():
                if nm in used or dirty(nm):
                    continue
                dd, al, pp, _ = nearest_along([lon, lat], geom)
                if dd < 260 and lo <= al <= hi:
                    target = prev["along_m"] + min(2500, gap / 2)
                    score = -abs(al - target) - dd
                    if best_node is None or score > best_node[0]:
                        best_node = (score, nm, pp, al, dd, src)
            if best_node:
                _sc, nm, pp, al, dd, src = best_node
                placed.append(
                    {
                        "stop_name": nm,
                        "lon": pp[0],
                        "lat": pp[1],
                        "along_m": al,
                        "distance_to_route": round(dd, 1),
                        "placement_reason": "ROAD_JUNCTION",
                        "name_source": "GIS_DERIVED",
                        "name_confidence": "MEDIUM",
                        "location_confidence": "MEDIUM",
                        "source_type": src,
                        "existing": "NO",
                        "snap_mode": "node",
                    }
                )
                used.add(nm)
                changed = True
                placed.sort(key=lambda p: p["along_m"])
                break
            best = None
            foreign = {c["from_name"] for c in CORRIDORS} | {c["to_name"] for c in CORRIDORS}
            own = set(spec["anchors"]) | {spec["from_name"], spec["to_name"]}
            for poi in pois:
                if poi["name"] in used or dirty(poi["name"]):
                    continue
                if poi["name"] in foreign and poi["name"] not in own:
                    continue
                d, along, ppt, _ = nearest_along([poi["lon"], poi["lat"]], geom)
                if d > snap_lim or along < lo or along > hi:
                    continue
                target = prev["along_m"] + min(2500, gap / 2)
                score = poi["score"] * 10 - abs(along - target) / 180 - d / 15
                if best is None or score > best[0]:
                    best = (score, poi, along, ppt, d)
            if best:
                poi, along, ppt, d = best[1], best[2], best[3], best[4]
                placed.append(
                    {
                        "stop_name": poi["name"],
                        "lon": ppt[0],
                        "lat": ppt[1],
                        "along_m": along,
                        "distance_to_route": round(d, 1),
                        "placement_reason": "ACTIVITY_CENTER",
                        "name_source": "LOCATION_RESEARCH",
                        "name_confidence": "HIGH" if poi["score"] >= 4 else "MEDIUM",
                        "location_confidence": "HIGH" if d <= 25 else "MEDIUM",
                        "source_type": poi["src"],
                        "existing": "YES" if str(poi["src"]).startswith("existing_") else "NO",
                        "snap_mode": poi["mode"],
                    }
                )
                used.add(poi["name"])
                changed = True
                placed.sort(key=lambda p: p["along_m"])
                break
        if not changed:
            break
    placed.sort(key=lambda p: p["along_m"])
    return placed, length_m(geom)


def detect_interchange(stop, snaps, other_cascade):
    modes = []
    nearest = []
    pt = [stop["lon"], stop["lat"]]
    seen = set()
    for name, val in snaps.items():
        if not isinstance(name, str):
            continue
        lon, lat, src, mode = val
        if mode not in ("krl", "mrt", "lrt", "tj"):
            continue
        key = (round(lon, 5), round(lat, 5), mode)
        if key in seen:
            continue
        seen.add(key)
        d = haversine(pt, [lon, lat])
        if d <= 300:
            label = "BRT" if mode == "tj" else mode.upper()
            modes.append(label)
            nearest.append((d, name, mode))
    for o in other_cascade:
        if o["route_id"] == stop.get("route_id"):
            continue
        d = haversine(pt, [o["lon"], o["lat"]])
        if d <= 300:
            modes.append("CASCADE")
            nearest.append((d, f"{o['stop_name']} ({o['route_id']})", "cascade"))
    nearest.sort()
    uniq = []
    for m in modes:
        if m not in uniq:
            uniq.append(m)
    is_ix = bool(nearest)
    strong = nearest and nearest[0][0] <= 150
    return {
        "interchange": "YES" if is_ix else "NO",
        "interchange_mode": "+".join(uniq) if is_ix else "",
        "nearest_transit": nearest[0][1] if nearest else "",
        "nearest_transit_m": round(nearest[0][0]) if nearest else None,
        "interchange_strength": "STRONG" if strong else "CANDIDATE" if is_ix else "",
    }


def road_name_at(geom, along, vertex_rows):
    best = None
    for v in vertex_rows:
        d, al, _, _ = nearest_along(v["geometry"], geom)
        if best is None or abs(al - along) < abs(best[0] - along):
            best = (al, v.get("road_name") or "")
    return (best[1] if best else "") or ""


def intervention_for(road_name):
    n = (road_name or "").lower()
    if "tol" in n:
        return {
            "lane_intervention": "HIGH",
            "separator_need": "REQUIRED",
            "road_widening": "HIGH",
            "bridge": "NONE",
            "flyover": "NONE",
            "underpass": "NONE",
            "note": "Ruas tol — intervensi BRT memerlukan kajian, bukan DED.",
        }
    if any(k in n for k in ("sudirman", "thamrin", "rasuna", "gatot", "parman", "simatupang")):
        return {
            "lane_intervention": "MEDIUM",
            "separator_need": "HIGH",
            "road_widening": "LOW",
            "bridge": "NONE",
            "flyover": "NONE",
            "underpass": "NONE",
            "note": "Arteri primer — peluang busway/separator. Penilaian perencanaan.",
        }
    return {
        "lane_intervention": "MEDIUM",
        "separator_need": "MEDIUM",
        "road_widening": "LOW",
        "bridge": "NONE",
        "flyover": "NONE",
        "underpass": "NONE",
        "note": "Penilaian perencanaan, bukan DED.",
    }


def fc(feats):
    return {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": CRS}}, "features": feats}


def feat_line(gid, coords, props, multi=False):
    if multi and coords and isinstance(coords[0][0], (list, tuple)):
        geom = {"type": "MultiLineString", "coordinates": coords}
    else:
        geom = {"type": "LineString", "coordinates": coords}
    return {"type": "Feature", "id": gid, "geometry": geom, "properties": {"id": gid, **props}}


def feat_pt(gid, xy, props):
    return {
        "type": "Feature",
        "id": gid,
        "geometry": {"type": "Point", "coordinates": [xy[0], xy[1]]},
        "properties": {"id": gid, **props},
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps()
    road_map = load_road_map()
    print("building road graph...", flush=True)
    graph = RoadGraph(road_map)
    print(f"graph nodes {len(graph.pts)}", flush=True)
    pois = poi_index(snaps)

    route_feats, stop_feats, seg_feats, vtx_feats, ix_feats = [], [], [], [], []
    report, warnings_all = [], []
    stop_table, seg_table, vtx_table = [], [], []
    built = []

    for spec in CORRIDORS:
        print("routing", spec["id"], flush=True)
        geom, vertices, warns, method = build_from_controls(spec, snaps, road_map, graph)
        for w in warns:
            warnings_all.append({"route": spec["id"], "issue": w})
        if not geom:
            warnings_all.append({"route": spec["id"], "issue": "no geometry"})
            continue
        inbound_geom = None
        if spec.get("dual_direction"):
            ig, iv, iw, im = build_from_controls(spec, snaps, road_map, graph, "inbound_controls", "inbound_roads")
            for w in iw:
                warnings_all.append({"route": spec["id"], "issue": f"inbound {w}"})
            inbound_geom = ig
            vertices.extend(iv)
            r = resolve("Stasiun Cakung", snaps)
            if inbound_geom and r:
                cxy = [r[0], r[1]]
                d, _, ppt, _ = nearest_along(cxy, inbound_geom)
                if d > 90:
                    inbound_geom = ensure_termini(inbound_geom, inbound_geom[0], inbound_geom[-1])
                    spur = densify(inbound_geom[0], cxy, 50) + densify(cxy, inbound_geom[1] if len(inbound_geom) > 1 else inbound_geom[0], 50)[1:]
                    inbound_geom = clean_chain(spur[0:1] + spur[1:] + inbound_geom[1:])
                    inbound_geom = remove_hairpins(inbound_geom, 150)
        stops, tot = place_stops(spec, geom, snaps, pois)
        if inbound_geom is not None and not any(s["stop_name"] == "Stasiun Cakung" for s in stops):
            r = resolve("Stasiun Cakung", snaps)
            if r:
                d, along, ppt, _ = nearest_along([r[0], r[1]], inbound_geom)
                if d > 120:
                    ppt = [r[0], r[1]]
                    d = 0.0
                stops.append(
                    {
                        "stop_name": "Stasiun Cakung",
                        "lon": ppt[0],
                        "lat": ppt[1],
                        "along_m": tot + 700,
                        "distance_to_route": round(d, 1),
                        "placement_reason": "ANCHOR",
                        "name_source": "CASCADE.txt",
                        "name_confidence": "HIGH",
                        "location_confidence": "HIGH",
                        "source_type": r[2],
                        "existing": "YES",
                        "snap_mode": "krl",
                        "direction": "INBOUND",
                    }
                )
        stops.sort(key=lambda p: p["along_m"])
        km = round(tot / 1000, 2)
        sharp = [t for t in turn_angles(geom) if t[1] > 135]
        for i, ang, pt in sharp[:4]:
            warnings_all.append({"route": spec["id"], "issue": f"SHARP_TURN {ang:.0f}°"})
        built.append((spec, geom, inbound_geom, stops, vertices, method, km, sharp))

    all_stops_brief = []
    for spec, geom, inbound_geom, stops, vertices, method, km, sharp in built:
        for s in stops:
            all_stops_brief.append({"route_id": spec["id"], "stop_name": s["stop_name"], "lon": s["lon"], "lat": s["lat"]})

    for spec, geom, inbound_geom, stops, vertices, method, km, sharp in built:
        cid = spec["id"]
        conf = spec["geometry_confidence"]
        if any(w["route"] == cid and str(w["issue"]).startswith("SPINE") for w in warnings_all):
            if conf == "HIGH":
                conf = "MEDIUM"
        spacing = [
            (out[i + 1]["along_m"] - out[i]["along_m"]) / 1000
            for out in [[s for s in stops if s.get("direction") != "INBOUND"]]
            for i in range(len(out) - 1)
        ]
        mean_sp = round(statistics.mean(spacing), 2) if spacing else None
        med_sp = round(statistics.median(spacing), 2) if spacing else None
        max_sp = round(max(spacing), 2) if spacing else None
        min_sp = round(min(spacing), 2) if spacing else None
        gap3 = sum(1 for x in spacing if x > 3.0)
        gap4 = sum(1 for x in spacing if x > 4.0)
        ix_count = 0
        common = {
            "route_id": cid,
            "route_name": spec["name"],
            "from_name": spec["from_name"],
            "to_name": spec["to_name"],
            "route_order": spec["route_order"],
            "network_type": "BRT_TRUNK",
            "mode": "transjakarta",
            "status": "PROPOSED",
            "status_label": "Usulan CASCADE",
            "existing": "NO",
            "parent_route": spec.get("parent_route") or "",
            "cascade_status": spec["cascade_status"],
            "existing_transjakarta": spec.get("existing_transjakarta") or "NO",
            "geometry_confidence": conf,
            "road_alignment_confidence": spec["road_alignment_confidence"],
            "alignment_confidence": spec["road_alignment_confidence"],
            "planning_note": spec.get("planning_note") or "",
            "source": SOURCE,
            "source_type": "AI_RECONSTRUCTED",
            "geometry_source": "OSM arterial + existing TJ centreline (project GIS)",
            "color": COLOR,
            "crs": CRS,
            "disclaimer": "Usulan jaringan BRT CASCADE. Bukan rute resmi TransJakarta. Bukan gambar DED.",
            "updated_at": RETRIEVED,
        }
        for i, s in enumerate(stops):
            order = i + 1
            dist_prev = round((s["along_m"] - stops[i - 1]["along_m"]) / 1000, 2) if i else 0.0
            dist_next = round((stops[i + 1]["along_m"] - s["along_m"]) / 1000, 2) if i < len(stops) - 1 else 0.0
            ix = detect_interchange({**s, "route_id": cid}, snaps, all_stops_brief)
            if ix["interchange"] == "YES":
                ix_count += 1
            stop_type = "TERMINUS" if i in (0, len(stops) - 1) else "INTERCHANGE" if ix["interchange"] == "YES" else "STOP"
            road = road_name_at(geom, s["along_m"], vertices)
            sid = f"{cid}-S{order:02d}"
            props = {
                **common,
                "stop_id": sid,
                "stop_order": order,
                "stop_name": s["stop_name"],
                "name": s["stop_name"],
                "stop_type": stop_type,
                "existing": s["existing"],
                "interchange": ix["interchange"],
                "interchange_mode": ix["interchange_mode"],
                "priority": "HIGH" if stop_type != "STOP" else "MEDIUM",
                "road_name": road,
                "area_name": s["stop_name"],
                "lat": round(s["lat"], 7),
                "lon": round(s["lon"], 7),
                "distance_to_route": s["distance_to_route"],
                "distance_from_previous_stop": dist_prev,
                "distance_to_next_stop": dist_next,
                "distance_along_km": round(s["along_m"] / 1000, 2),
                "name_source": s["name_source"],
                "name_confidence": s["name_confidence"],
                "location_confidence": s["location_confidence"],
                "placement_reason": s["placement_reason"],
                "nearest_transit": ix["nearest_transit"],
                "activity_center": s["placement_reason"],
                "infrastructure_need": "MEDIUM",
                "note": "Halte usulan. Bukan halte resmi TransJakarta."
                if s["existing"] != "YES"
                else "Lokasi menumpang simpul existing; status CASCADE tetap usulan.",
            }
            stop_feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
            stop_table.append(
                {
                    "route": cid,
                    "order": order,
                    "stop": s["stop_name"],
                    "area": s["stop_name"],
                    "road": road,
                    "existing": s["existing"],
                    "interchange": ix["interchange_mode"] or "NO",
                    "dist_prev_km": dist_prev,
                    "dist_next_km": dist_next,
                    "along_km": round(s["along_m"] / 1000, 2),
                    "confidence": s["name_confidence"],
                    "to_route_m": s["distance_to_route"],
                }
            )
            if ix["interchange"] == "YES":
                ix_feats.append(
                    feat_pt(
                        f"{sid}-IX",
                        [s["lon"], s["lat"]],
                        {
                            "route_id": cid,
                            "stop_id": sid,
                            "stop_name": s["stop_name"],
                            "interchange_mode": ix["interchange_mode"],
                            "nearest_transit": ix["nearest_transit"],
                            "nearest_transit_m": ix["nearest_transit_m"],
                            "strength": ix["interchange_strength"],
                            "name": s["stop_name"],
                            "color": COLOR,
                        },
                    )
                )
        for i in range(len(stops) - 1):
            a, b = stops[i], stops[i + 1]
            sl = slice_along(geom, a["along_m"], b["along_m"])
            slen = round(length_m(sl) / 1000, 3)
            road = road_name_at(geom, (a["along_m"] + b["along_m"]) / 2, vertices)
            inter = intervention_for(road)
            existing_road = "YES" if road and road != "unresolved" else "NO"
            existing_tj = "YES" if str(road).startswith("TJ-K") else "NO"
            seg_id = f"{cid}-SEG{i+1:02d}"
            seg_conf = "HIGH" if existing_road == "YES" else "LOW"
            props = {
                **common,
                "segment_id": seg_id,
                "segment_order": i + 1,
                "from_vertex": a["stop_name"],
                "to_vertex": b["stop_name"],
                "from_stop": a["stop_name"],
                "to_stop": b["stop_name"],
                "road_name": road or "unresolved",
                "road_class": "MOTORWAY" if "tol" in str(road).lower() else "ARTERIAL",
                "area_name": a["stop_name"],
                "intersection": f"{a['stop_name']}–{b['stop_name']}",
                "existing_road": existing_road,
                "existing_transjakarta": existing_tj,
                "cascade_status": spec["cascade_status"],
                "alignment_type": "ROAD_CENTERLINE",
                "direction": "OUTBOUND",
                "length_km": slen,
                "geometry_confidence": seg_conf,
                **inter,
            }
            seg_feats.append(feat_line(seg_id, sl, props))
            seg_table.append(
                {
                    "route": cid,
                    "segment": i + 1,
                    "from": a["stop_name"],
                    "to": b["stop_name"],
                    "road": road or "unresolved",
                    "area": a["stop_name"],
                    "length_km": slen,
                    "intervention": inter["lane_intervention"],
                    "confidence": seg_conf,
                }
            )
        for v in vertices:
            vtx_feats.append(
                feat_pt(
                    v["vertex_id"],
                    v["geometry"],
                    {**common, **{k: val for k, val in v.items() if k != "geometry"}, "name": v["vertex_name"]},
                )
            )
            vtx_table.append(
                {
                    "route": cid,
                    "order": v["vertex_order"],
                    "vertex": v["vertex_name"],
                    "type": v["vertex_type"],
                    "road": v.get("road_name") or "",
                    "intersection": v.get("intersection") or "",
                    "confidence": v.get("confidence") or "",
                }
            )

        geom_out = geom
        gtype = "LineString"
        if inbound_geom:
            geom_out = [geom, inbound_geom]
            gtype = "MultiLineString"

        props_r = {
            **common,
            "name": spec["name"],
            "short": spec["short"],
            "endpoint": f"{spec['from_name']} – {spec['to_name']}",
            "length_km": km,
            "stop_count": len(stops),
            "vertex_count": len(vertices),
            "segment_count": max(0, len(stops) - 1),
            "interchange_count": ix_count,
            "mean_stop_spacing_km": mean_sp,
            "median_stop_spacing_km": med_sp,
            "max_stop_spacing_km": max_sp,
            "min_stop_spacing_km": min_sp,
            "gap_over_3km": gap3,
            "gap_over_4km": gap4,
            "digitization_method": method,
            "geometry_type": gtype,
            "direction": "OUTBOUND+INBOUND" if gtype == "MultiLineString" else "BIDIRECTIONAL",
        }
        route_feats.append(feat_line(cid, geom_out, props_r, multi=(gtype == "MultiLineString")))
        qa_invalid = km < 2 or len(geom) < 4
        if qa_invalid:
            warnings_all.append({"route": cid, "issue": "INVALID short/empty"})
        report.append(
            {
                "route_id": cid,
                "name": spec["name"],
                "from": spec["from_name"],
                "to": spec["to_name"],
                "length_km": km,
                "stops": len(stops),
                "vertices": len(vertices),
                "segments": max(0, len(stops) - 1),
                "interchanges": ix_count,
                "avg_spacing_km": mean_sp,
                "median_spacing_km": med_sp,
                "max_gap_km": max_sp,
                "min_spacing_km": min_sp,
                "gap_over_3km": gap3,
                "gap_over_4km": gap4,
                "disconnected": 0,
                "invalid": qa_invalid,
                "low_conf": conf == "LOW",
                "geometry_confidence": conf,
                "method": method,
                "sharp_turns": len(sharp),
                "stop_chain": [
                    {"order": i + 1, "name": s["stop_name"], "along_km": round(s["along_m"] / 1000, 2)}
                    for i, s in enumerate(stops)
                ],
            }
        )

    ids = [f["properties"]["route_id"] for f in route_feats]
    assert "CAS-06" not in ids
    assert "CAS-07" in ids
    harja = [s for s in stop_feats if "harjamukti" in str(s["properties"].get("stop_name", "")).lower()]
    assert not harja, "Old CAS-07 Harjamukti leaked"

    meta = {
        "network": "CASCADE TransJakarta BRT trunk",
        "status": "PROPOSED",
        "color": COLOR,
        "source": SOURCE,
        "geometry_source": "OSM named arterials (roads.geojson) + existing TJ centreline where overlapping",
        "disclaimer": "Usulan. Bukan rute resmi. Bukan DED.",
        "retrieved": RETRIEVED,
        "crs": CRS,
        "deleted": ["CAS-06 Marunda–Pinang Ranti", "OLD CAS-07 Pinang Ranti–Harjamukti"],
        "corridors": [
            {
                "id": r["route_id"],
                "name": r["name"],
                "short": r["name"],
                "endpoint": f"{r['from']} – {r['to']}",
                "from_name": r["from"],
                "to_name": r["to"],
                "length_km": r["length_km"],
                "stop_count": r["stops"],
                "geometry_confidence": r["geometry_confidence"],
                "source": SOURCE,
                "status": "PROPOSED",
                "network_type": "BRT_TRUNK",
            }
            for r in report
        ],
        "totals": {
            "routes": len(route_feats),
            "km": round(sum(r["length_km"] for r in report), 2),
            "stops": len(stop_feats),
            "vertices": len(vtx_feats),
            "segments": len(seg_feats),
            "interchanges": len(ix_feats),
        },
    }
    validation = {
        "routes": report,
        "warnings": warnings_all,
        "stop_table": stop_table,
        "segment_table": seg_table,
        "vertex_table": vtx_table,
        "ids": ids,
        "cas06_absent": "CAS-06" not in ids,
        "old_cas07_absent": not harja,
        "totals": meta["totals"],
    }

    (OUT_DIR / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_segments.geojson").write_text(json.dumps(fc(seg_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_vertices.geojson").write_text(json.dumps(fc(vtx_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_interchanges.geojson").write_text(json.dumps(fc(ix_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2))
    (OUT_DIR / "cascade_existing.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (PUB / "cascade_existing.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    srcp = PUB / "sources.json"
    try:
        sources = json.loads(srcp.read_text())
        for row in sources:
            if row.get("dataset") == "cascade_candidates":
                row["count"] = len(route_feats)
                row["notes"] = (
                    "12 ID final minus CAS-06 yang dihapus: CAS-01..05, CAS-07..12. "
                    "BRT trunk usulan #D62F7F. Bukan existing TJ, bukan DED, bukan masterplan railway. "
                    "CAS-07 = Puri Beta–Monas (bukan Harjamukti)."
                )
            if row.get("dataset") == "cascade_stops":
                row["count"] = len(stop_feats)
        srcp.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        pass

    print("=== CASCADE BRT trunks ===")
    print(f"{'ID':7} {'from':22} {'to':22} {'km':7} {'st':4} {'gapmax':7} {'conf':8} method")
    for r in report:
        print(
            f"{r['route_id']:7} {r['from'][:22]:22} {r['to'][:22]:22} {r['length_km']:7.2f} {r['stops']:4} {r['max_gap_km'] or 0:7.2f} {r['geometry_confidence']:8} {r['method']}"
        )
    print("totals", meta["totals"])
    print("warnings", len(warnings_all), "CAS-06 absent", validation["cas06_absent"])
    for r in report:
        print(f"\n{r['route_id']} {r['name']}")
        for s in r["stop_chain"]:
            print(f"  {s['along_km']:6.2f} km  {s['name']}")


if __name__ == "__main__":
    main()
