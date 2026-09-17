#!/usr/bin/env python3
"""Register user MRT (4 corridors) + LRT GeoJSON into CASCADE.

Does not redraw KRL / existing MRT-LRT-TJ / masterplan. Light Chaikin only,
clamped to the user path. Stations ~1.5 km with local names + forced hubs.
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
ATT = ROOT / "attachments"
COLOR = "#7C3AED"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-16"
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (mrt-lrt-rebuild)"}
R = 6371000.0

LEBAK_BULUS = (106.7749323, -6.2892957)
DEPOK_BARU = (106.8212108, -6.3920709)
ICE_BSD = (106.63657, -6.30068)
ANCOL = (106.846456, -6.127855)
DUKUH_ATAS = (106.8228278, -6.2008018)
TANAH_ABANG = (106.8107942, -6.186527)
PIK2 = (106.7374, -6.1088)
SOETTA = (106.6554, -6.1256)
CIBUBUR = (106.89578, -6.37452)
CIPUTAT = (106.74675, -6.31797)

MRT_FILE = ATT / "TREK MRT LEBAK BULUS DEPOK BARU, LEBAK BULUS BSD (BELOK DRI CIPUTAT),  DEPOK BARU - ANCOL, DEPOK BARU JONGGOL.geojson"
LRT_FILE = ATT / "LRT DUKUH ATAS BANDARA.geojson"

DISC_MRT = "Usulan CASCADE. Bukan MRT Jakarta existing. Bukan masterplan resmi. Bukan DED."
DISC_LRT = "Usulan CASCADE. Bukan LRT Jabodebek existing. Bukan masterplan. Bukan DED."
SRC_MRT = "CASCADE MRT — trase user GeoJSON, 4 koridor logis, stasiun ~1,5 km"
SRC_LRT = "CASCADE LRT — trase user GeoJSON Dukuh Atas–Bandara, stasiun ~1,5 km"


def hav(a, b):
    to = math.radians
    dlon = to(b[0] - a[0])
    dlat = to(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(to(a[1])) * math.cos(to(b[1])) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def length_m(coords):
    return sum(hav(coords[i - 1], coords[i]) for i in range(1, len(coords)))


def nearest_on(coords, pt):
    best_i, best_d = 0, 1e18
    for i, c in enumerate(coords):
        d = hav(c, pt)
        if d < best_d:
            best_i, best_d = i, d
    return best_i, best_d, coords[best_i]


def densify(coords, step=70.0):
    out = [coords[0]]
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        d = hav(a, b)
        n = max(1, int(d / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def chaikin(coords, rounds=1):
    pts = coords
    for _ in range(rounds):
        nxt = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            nxt.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            nxt.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        nxt.append(pts[-1])
        pts = nxt
    return pts


def project_back(smoothed, original, max_off=70.0):
    out = []
    for p in smoothed:
        _, d, q = nearest_on(original, p)
        out.append(p if d <= max_off else q)
    cleaned = [out[0]]
    for p in out[1:]:
        if hav(cleaned[-1], p) >= 4:
            cleaned.append(p)
    return cleaned


def snap_vertex(coords, pt, which="start"):
    coords = list(coords)
    if which == "start":
        if hav(coords[0], pt) > 8:
            coords = [pt] + coords
        else:
            coords[0] = pt
        while len(coords) > 2 and hav(coords[0], coords[1]) < 8:
            coords.pop(1)
    else:
        if hav(coords[-1], pt) > 8:
            coords = coords + [pt]
        else:
            coords[-1] = pt
        while len(coords) > 2 and hav(coords[-1], coords[-2]) < 8:
            coords.pop(-2)
    return coords


def inject(coords, pt, max_off=3500.0):
    i, d, _ = nearest_on(coords, pt)
    if d > max_off:
        return coords, False
    on = coords[i]
    if i == 0 or i == len(coords) - 1:
        return coords, True
    coords = coords[:i] + [on] + coords[i:]
    return coords, True


def cum(coords):
    d = [0.0]
    for i in range(1, len(coords)):
        d.append(d[-1] + hav(coords[i - 1], coords[i]))
    return d


def point_at(coords, dist, cdist=None):
    cdist = cdist or cum(coords)
    if dist <= 0:
        return coords[0], 0
    if dist >= cdist[-1]:
        return coords[-1], len(coords) - 1
    for i in range(1, len(cdist)):
        if cdist[i] >= dist:
            span = cdist[i] - cdist[i - 1] or 1
            t = (dist - cdist[i - 1]) / span
            a, b = coords[i - 1], coords[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), i
    return coords[-1], len(coords) - 1


def load_mls_parts(path: Path):
    data = json.loads(path.read_text())
    parts = []
    for ft in data["features"]:
        g = ft["geometry"]
        pid = ft.get("properties", {}).get("id")
        rings = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for ring in rings:
            parts.append((pid, [(float(x), float(y)) for x, y in ring]))
    return parts


def join_onto(a, b):
    if hav(a[-1], b[0]) <= hav(a[-1], b[-1]):
        use = list(b)
    else:
        use = list(reversed(b))
    if hav(a[-1], use[0]) < 8:
        return a + use[1:]
    return a + use


def clean(coords):
    out = [coords[0]]
    for p in coords[1:]:
        if hav(out[-1], p) >= 2:
            out.append(p)
    return out


def smooth_user(raw):
    raw = clean(raw)
    d = densify(raw, 90)
    sm = chaikin(d, 1)
    sm = densify(sm, 55)
    return project_back(sm, raw, 70)


LOCAL = [
    ("Lebak Bulus", 106.77493, -6.28930),
    ("Fatmawati", 106.79246, -6.29247),
    ("Ciputat", 106.74720, -6.31250),
    ("Pamulang", 106.73800, -6.34300),
    ("ICE BSD", 106.63657, -6.30068),
    ("Rawa Buntu", 106.67505, -6.31551),
    ("Serpong", 106.6640, -6.3190),
    ("BSD CBD", 106.63657, -6.30068),
    ("Sawangan", 106.76372, -6.40019),
    ("Parung Bingung", 106.74700, -6.40650),
    ("Depok Baru", 106.82121, -6.39207),
    ("Pancoran Mas", 106.8180, -6.3970),
    ("Margonda", 106.83209, -6.36895),
    ("Kelapa Dua Depok", 106.84313, -6.36508),
    ("Cimanggis", 106.8620, -6.3720),
    ("Cibubur", 106.87300, -6.35100),
    ("Cileungsi", 106.9610, -6.4020),
    ("Jonggol", 107.06470, -6.46670),
    ("Cijantung", 106.86191, -6.31215),
    ("Condet", 106.85172, -6.27643),
    ("PGC Cililitan", 106.86570, -6.26190),
    ("Kampung Melayu", 106.86682, -6.22467),
    ("Matraman", 106.86070, -6.21212),
    ("Senen", 106.84410, -6.17276),
    ("Gunung Sahari", 106.83800, -6.15000),
    ("Ancol", 106.84646, -6.12786),
    ("Cinere", 106.78500, -6.33250),
    ("Dukuh Atas", 106.82300, -6.20300),
    ("Tanah Abang", 106.81079, -6.18653),
    ("Palmerah", 106.79400, -6.20700),
    ("PIK 2", 106.73740, -6.10880),
    ("Kosambi", 106.6850, -6.1080),
    ("Bandara Soekarno-Hatta", 106.65540, -6.12560),
    ("Kalideres", 106.70500, -6.15500),
    ("Cawang", 106.86800, -6.24300),
    ("Tanjung Barat", 106.8388, -6.3080),
    ("Lenteng Agung", 106.8330, -6.3330),
    ("Universitas Indonesia", 106.8310, -6.3620),
    ("Beji", 106.8220, -6.3750),
    ("Pondok Cina", 106.8440, -6.3680),
    ("Pasar Rebo", 106.8570, -6.3250),
    ("Kramat Jati", 106.8700, -6.2730),
    ("Cipinang", 106.8820, -6.2100),
    ("Pademangan", 106.8400, -6.1330),
    ("Sunter", 106.8680, -6.1380),
    ("Kelapa Gading", 106.90500, -6.15700),
    ("Ciracas", 106.8760, -6.3290),
    ("Cipayung", 106.9000, -6.3400),
    ("Setu", 106.9300, -6.3550),
    ("Klapanunggal", 107.0100, -6.4300),
    ("Sukamaju", 106.9500, -6.3900),
    ("Karang Tengah", 106.7280, -6.3080),
    ("Pondok Aren", 106.7480, -6.2840),
    ("Bintaro", 106.7480, -6.2720),
    ("Pesanggrahan", 106.7620, -6.2600),
    ("Kebayoran Lama", 106.7780, -6.2440),
    ("Petukangan", 106.7520, -6.2400),
    ("Ciledug", 106.7050, -6.2380),
    ("Sudimara", 106.7130, -6.2360),
    ("Jurangmangu", 106.7230, -6.2980),
    ("Pondok Jagung", 106.6580, -6.3120),
    ("Lengkong Karya", 106.6500, -6.3050),
    ("Jatake", 106.6280, -6.2920),
    ("Grogol", 106.7890, -6.1660),
    ("Jelambar", 106.7860, -6.1665),
    ("Roxy", 106.8010, -6.1680),
    ("Tomang", 106.7970, -6.1780),
    ("Slipi", 106.7970, -6.1900),
    ("Kebon Jeruk", 106.7700, -6.1900),
    ("Kedoya", 106.7620, -6.1780),
    ("Kembangan", 106.7420, -6.1750),
    ("Meruya", 106.7350, -6.2000),
    ("Kamal", 106.7050, -6.1180),
    ("Cengkareng", 106.7280, -6.1390),
    ("Kapuk", 106.7630, -6.1350),
    ("Pantai Indah Kapuk", 106.7440, -6.1080),
    ("Kamal Muara", 106.7280, -6.1090),
    ("Dadap", 106.6950, -6.1220),
    ("Benda", 106.6850, -6.1250),
    ("Jatiasih", 106.9560, -6.3100),
    ("Jati Asih", 106.9560, -6.3100),
    ("Gunung Putri", 106.9230, -6.3720),
    ("Bojong Kulur", 106.9400, -6.3880),
    ("Nagrak", 107.0200, -6.4450),
    ("Sukawangi", 107.0400, -6.4550),
    ("Cibadak", 107.0500, -6.4600),
    ("Tanah Sareal", 106.8030, -6.5620),
    ("Bogor Utara", 106.8080, -6.5570),
    ("Jambu Dua", 106.8080, -6.5570),
    ("Pondok Labu", 106.7700, -6.3080),
    ("Cilandak", 106.8000, -6.2900),
    ("Pondok Cabe", 106.7470, -6.3370),
    ("Jombang", 106.7000, -6.2900),
    ("Sawah Baru", 106.7400, -6.3050),
    ("Sawah Lama", 106.7320, -6.2980),
    ("Bambe", 106.7550, -6.3550),
    ("Pengasinan", 106.7600, -6.3850),
    ("Limo", 106.7750, -6.3550),
    ("Gandul", 106.7880, -6.3450),
    ("Pancoran", 106.8440, -6.2430),
    ("Tebet", 106.8500, -6.2260),
    ("Cikini", 106.8410, -6.1910),
    ("Kwitang", 106.8410, -6.1810),
    ("Kemayoran", 106.8450, -6.1600),
    ("Petojo", 106.8160, -6.1700),
    ("Cideng", 106.8090, -6.1750),
    ("Harmoni", 106.8130, -6.1650),
    ("Tambora", 106.8080, -6.1460),
    ("Angke", 106.7950, -6.1450),
    ("Pluit", 106.7900, -6.1250),
    ("Penjaringan", 106.8050, -6.1350),
    ("Tanjung Priok", 106.8800, -6.1100),
    ("Koja", 106.9000, -6.1210),
    ("Cilincing", 106.9400, -6.1080),
    ("Bambu Apus", 106.9020, -6.3300),
    ("Cipayung Jaya", 106.9050, -6.3550),
    ("Naga Sari", 106.9800, -6.4100),
    ("Cariu", 107.0800, -6.5000),
    ("Sukamakmur", 107.0500, -6.4800),
    ("Tapos", 106.8800, -6.4100),
    ("Cilangkap", 106.9000, -6.3700),
    ("Munjul", 106.9200, -6.3550),
]


def title_id(s):
    s = (s or "").strip()
    if not s:
        return s
    skip = {"dan", "di", "ke", "dari"}
    return " ".join(w if w.lower() in skip else w[:1].upper() + w[1:] for w in s.replace("_", " ").split())


def reverse_name(lon, lat):
    return ""


def local_name(lon, lat, used):
    used_l = {u.lower() for u in used}
    ranked = sorted(((hav((lon, lat), (x, y)), n) for n, x, y in LOCAL), key=lambda t: t[0])
    for d, n in ranked:
        if n.lower() in used_l:
            continue
        if d < 2200:
            return n
    return None


def stations_every(coords, forced_named, start_name, end_name, step=1500.0):
    geom = list(coords)
    for name, xy in forced_named:
        geom, _ = inject(geom, xy, 5000.0)
    cdist = cum(geom)
    total = cdist[-1]
    wanted = [0.0]
    t = step
    while t < total - 700:
        wanted.append(t)
        t += step
    wanted.append(total)
    forced_dist = []
    for name, xy in forced_named:
        i, d, on = nearest_on(geom, xy)
        if d > 5000:
            continue
        forced_dist.append((cdist[min(i, len(cdist) - 1)], name, on if d < 80 else geom[i]))
    for fd, name, on in forced_dist:
        close = min(wanted, key=lambda w: abs(w - fd))
        if abs(close - fd) < 700:
            wanted[wanted.index(close)] = fd
        else:
            wanted.append(fd)
    wanted = sorted(set(round(w, 1) for w in wanted))
    used = []
    stops = []
    for order, dist in enumerate(wanted, start=1):
        xy, _ = point_at(geom, dist, cdist)
        name = None
        for fd, fn, fon in forced_dist:
            if abs(fd - dist) < 90:
                name = fn
                xy = fon
                break
        if order == 1:
            name = start_name
            xy = geom[0]
        if order == len(wanted):
            name = end_name
            xy = geom[-1]
        if not name:
            name = local_name(xy[0], xy[1], used) or f"KM {int(round(dist / 1000))}"
        base = name
        n = 2
        while any(u.lower() == name.lower() for u in used):
            if order in (1, len(wanted)):
                break
            alt = local_name(xy[0] + 0.004 * n, xy[1], used)
            name = alt if alt and alt.lower() not in {x.lower() for x in used} else f"{base} {n}"
            n += 1
            if n > 4:
                break
        used.append(name)
        stops.append({"name": name, "xy": (round(xy[0], 6), round(xy[1], 6)), "order": order, "km": round(dist / 1000, 2)})
    # keep start/end names unique
    if stops:
        start_n, end_n = stops[0]["name"], stops[-1]["name"]
        trimmed = [stops[0]]
        for s in stops[1:-1]:
            if s["name"] in {start_n, end_n}:
                continue
            trimmed.append(s)
        if len(stops) > 1:
            trimmed.append(stops[-1])
        stops = trimmed
    for i, s in enumerate(stops, start=1):
        s["order"] = i
    return geom, stops


def feat_line(gid, coords, props):
    return {
        "type": "Feature",
        "id": gid,
        "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]},
        "properties": props,
    }


def feat_pt(gid, xy, props):
    return {
        "type": "Feature",
        "id": gid,
        "geometry": {"type": "Point", "coordinates": [round(xy[0], 6), round(xy[1], 6)]},
        "properties": props,
    }


def bbox_of(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def common_props(spec, km, n_stops, verts):
    return {
        "id": spec["id"],
        "route_id": spec["id"],
        "corridor_id": spec["id"],
        "corridor_name": spec["short"],
        "name": spec["name"],
        "short": spec["short"],
        "route_name": spec["name"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "start_name": spec["from_name"],
        "end_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": spec["mode"],
        "status": "CASCADE_PROPOSED",
        "status_label": spec["status_label"],
        "network_type": "CASCADE",
        "plan_type": "PROPOSED",
        "existing": "NO",
        "length_km": round(km, 2),
        "stop_count": n_stops,
        "geometry_confidence": "HIGH",
        "alignment_confidence": "HIGH",
        "alignment_type": spec.get("alignment_type", "RAIL_CORRIDOR"),
        "color": COLOR,
        "crs": CRS,
        "source": spec["source"],
        "source_type": "USER_GEOJSON",
        "geometry_source": spec["geometry_source"],
        "disclaimer": spec["disclaimer"],
        "updated_at": RETRIEVED,
        "notes": spec["note"],
        "route_order": spec["route_order"],
        "vertex_count": verts,
        "digitization_level": "L3",
        "endpoint": spec["short"],
        "structure": spec.get("structure", "ELEVATED"),
        "interchange_count": spec.get("interchange_count", 2),
        "operator_type": "CASCADE",
        "bbox": bbox_of(spec["_geom"]) if spec.get("_geom") else None,
    }


def make_stops(spec, stops, km, verts, hubs, existing):
    feats = []
    n = len(stops)
    for s in stops:
        sid = f"{spec['id']}-S{s['order']:02d}"
        is_end = s["order"] in (1, n)
        p = common_props(spec, km, n, verts)
        p.update(
            {
                "id": spec["id"],
                "stop_id": sid,
                "station_id": sid,
                "stop_order": s["order"],
                "stop_name": s["name"],
                "name": s["name"],
                "local_area": s["name"],
                "stop_type": "TERMINUS" if is_end else ("INTERCHANGE" if s["name"] in hubs else "STATION"),
                "existing": "YES" if s["name"] in existing else "NO",
                "interchange": "YES" if s["name"] in hubs else "NO",
                "is_interchange": "YES" if s["name"] in hubs else "NO",
                "km_from_start": s["km"],
                "mode": spec["mode"],
            }
        )
        feats.append(feat_pt(sid, s["xy"], p))
    return feats


def drop_old(feats):
    kept = []
    for f in feats:
        p = f.get("properties") or {}
        rid = str(f.get("id") or p.get("route_id") or p.get("id") or "")
        if rid.startswith("CAS-MRT") or rid.startswith("MRT-CASCADE"):
            continue
        if rid.startswith("CAS-LRT-C04") or rid.startswith("LRT-CASCADE"):
            continue
        kept.append(f)
    return kept


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def build_mrt_geoms():
    parts = load_mls_parts(MRT_FILE)
    feat = [p[1] for p in parts]
    # feat[3] Depok → Lebak Bulus  → reverse = LB → Depok
    lb_depok = list(reversed(feat[3]))
    # C02 Lebak Bulus – Depok Baru
    c02 = smooth_user(lb_depok)
    c02 = snap_vertex(c02, LEBAK_BULUS, "start")
    c02 = snap_vertex(c02, DEPOK_BARU, "end")
    # C01 Lebak Bulus – ICE BSD: along C02 trunk to Ciputat, then feat[6]
    i, d, _ = nearest_on(lb_depok, feat[6][0])
    c01_raw = lb_depok[: i + 1]
    c01_raw = join_onto(c01_raw, feat[6])
    c01 = smooth_user(c01_raw)
    c01 = snap_vertex(c01, LEBAK_BULUS, "start")
    c01 = snap_vertex(c01, ICE_BSD, "end")
    # C04 Depok Baru – Ancol: feat1 + feat2
    c04_raw = join_onto(list(feat[1]), feat[2])
    c04 = smooth_user(c04_raw)
    c04 = snap_vertex(c04, DEPOK_BARU, "start")
    c04 = snap_vertex(c04, ANCOL, "end")
    # C03 Depok Baru – Jonggol: feat1 to branch + feat5 + feat4 + feat0 + feat7
    i, _, _ = nearest_on(feat[1], feat[5][0])
    c03_raw = feat[1][: i + 1]
    c03_raw = join_onto(c03_raw, feat[5])
    c03_raw = join_onto(c03_raw, feat[4])
    c03_raw = join_onto(c03_raw, feat[0])
    c03_raw = join_onto(c03_raw, feat[7])
    c03 = smooth_user(c03_raw)
    c03 = snap_vertex(c03, DEPOK_BARU, "start")
    return {"MRT-CASCADE-01": c01, "MRT-CASCADE-02": c02, "MRT-CASCADE-03": c03, "MRT-CASCADE-04": c04}


def build_lrt_geom():
    parts = [p[1] for p in load_mls_parts(LRT_FILE)]
    raw = parts[0]
    for nxt in parts[1:]:
        raw = join_onto(raw, nxt)
    geom = smooth_user(raw)
    geom = snap_vertex(geom, DUKUH_ATAS, "start")
    geom = snap_vertex(geom, SOETTA, "end")
    return geom


def meta_row(spec, km, n, box):
    return {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": spec["short"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": spec["mode"],
        "length_km": round(km, 2),
        "stop_count": n,
        "geometry_confidence": "HIGH",
        "source": spec["source"],
        "status": "CASCADE_PROPOSED",
        "network_type": "CASCADE",
        "plan_type": "PROPOSED",
        "alignment_type": spec.get("alignment_type", "RAIL_CORRIDOR"),
        "notes": spec["note"],
        "bbox": box,
    }


def add_jambu_dua(routes, stops, meta):
    """Keep C04 geometry; add shared interchange where it meets Bogor KRL."""
    c04 = None
    for f in routes["features"]:
        if str(f.get("id") or f["properties"].get("id")) == "KRL-C04":
            c04 = f
            break
    if not c04:
        return
    bogor = None
    kr = json.loads((PUB / "krl_routes.geojson").read_text())
    for f in kr["features"]:
        if str(f.get("id") or "") == "krl-B":
            bogor = f
            break
    if not bogor:
        return
    c04c = [(float(x), float(y)) for x, y in c04["geometry"]["coordinates"]]
    g = bogor["geometry"]
    bpts = g["coordinates"] if g["type"] == "LineString" else [p for ring in g["coordinates"] for p in ring]
    best = (1e9, None, None)
    step = max(1, len(c04c) // 800)
    for i, p in enumerate(c04c[::step]):
        for q in bpts[:: max(1, len(bpts) // 600)]:
            d = hav(p, q)
            if d < best[0]:
                best = (d, p, (float(q[0]), float(q[1])))
    if best[0] > 250:
        print("Jambu Dua skip, dist", best[0])
        return
    on = best[1]
    nm = "Jambu Dua"
    # insert stop if not already present
    existing_names = {s["properties"].get("name") for s in stops["features"] if s["properties"].get("route_id") == "KRL-C04"}
    if nm in existing_names:
        return
    # place on C04 chainage
    i, _, _ = nearest_on(c04c, on)
    xy = c04c[i]
    km = length_m(c04c[: i + 1]) / 1000
    # shift subsequent stop_order
    c04_stops = [s for s in stops["features"] if s["properties"].get("route_id") == "KRL-C04"]
    c04_stops.sort(key=lambda s: s["properties"].get("stop_order") or 0)
    order = 1
    for s in c04_stops:
        if (s["properties"].get("km_from_start") or 0) < km:
            order = (s["properties"].get("stop_order") or 0) + 1
    for s in c04_stops:
        if (s["properties"].get("stop_order") or 0) >= order:
            s["properties"]["stop_order"] = (s["properties"].get("stop_order") or 0) + 1
    sid = f"KRL-C04-S{order:02d}X"
    template = c04_stops[0]["properties"] if c04_stops else {}
    p = dict(template)
    p.update(
        {
            "id": "KRL-C04",
            "stop_id": sid,
            "station_id": sid,
            "stop_order": order,
            "stop_name": nm,
            "name": nm,
            "local_area": nm,
            "stop_type": "INTERCHANGE",
            "existing": "YES",
            "interchange": "YES",
            "is_interchange": "YES",
            "km_from_start": round(km, 2),
            "connected_corridors": "KRL-C04, krl-B",
            "mode": "krl",
        }
    )
    stops["features"].append(feat_pt(sid, xy, p))
    c04["properties"]["stop_count"] = int(c04["properties"].get("stop_count") or 0) + 1
    c04["properties"]["interchange_count"] = int(c04["properties"].get("interchange_count") or 1) + 1
    for m in meta.get("corridors") or []:
        if m.get("id") == "KRL-C04":
            m["stop_count"] = int(m.get("stop_count") or 0) + 1
    print(f"Jambu Dua @ {xy} {best[0]:.0f}m from Bogor KRL, name={nm}")


def connect_fields(stops):
    from collections import defaultdict

    by_name = defaultdict(set)
    for f in stops["features"]:
        p = f["properties"]
        by_name[p.get("name")].add(p.get("route_id"))
    for f in stops["features"]:
        p = f["properties"]
        conn = sorted(x for x in by_name.get(p.get("name"), []) if x)
        if p.get("existing") == "YES" and p.get("name") in {
            "Lebak Bulus",
            "Depok Baru",
            "Ancol",
            "Dukuh Atas",
            "Tanah Abang",
            "Cibubur",
            "Jambu Dua",
            "Maja",
            "Tangerang",
            "Parung Panjang",
        }:
            conn.append("existing")
        p["connected_corridors"] = ", ".join(dict.fromkeys(conn))
        p["operator_type"] = "CASCADE"


def main():
    geoms = build_mrt_geoms()
    lrt = build_lrt_geom()

    specs = [
        dict(
            id="MRT-CASCADE-01",
            mode="mrt",
            name="LEBAK BULUS – ICE BSD",
            short="Lebak Bulus – ICE BSD",
            from_name="Lebak Bulus",
            to_name="ICE BSD",
            direction="Lebak Bulus → ICE BSD",
            route_order=10,
            source=SRC_MRT,
            geometry_source="User GeoJSON TREK MRT (id=1 trunk + id=3 ICE BSD)",
            disclaimer=DISC_MRT,
            status_label="Usulan CASCADE · MRT",
            note="Koridor CASCADE MRT Lebak Bulus–ICE BSD dari GeoJSON user. Node Lebak Bulus bersama MRT existing dan MRT-CASCADE-02.",
            interchange_count=2,
            _geom=geoms["MRT-CASCADE-01"],
            forced=[("Lebak Bulus", LEBAK_BULUS), ("Ciputat", CIPUTAT), ("ICE BSD", ICE_BSD)],
            hubs={"Lebak Bulus", "Ciputat", "ICE BSD"},
            existing={"Lebak Bulus", "Ciputat"},
        ),
        dict(
            id="MRT-CASCADE-02",
            mode="mrt",
            name="LEBAK BULUS – DEPOK BARU",
            short="Lebak Bulus – Depok Baru",
            from_name="Lebak Bulus",
            to_name="Depok Baru",
            direction="Lebak Bulus → Depok Baru",
            route_order=11,
            source=SRC_MRT,
            geometry_source="User GeoJSON TREK MRT (id=1 Lebak Bulus–Depok Baru)",
            disclaimer=DISC_MRT,
            status_label="Usulan CASCADE · MRT",
            note="Koridor CASCADE MRT Lebak Bulus–Depok Baru. Lebak Bulus = super-node MRT existing. Depok Baru = hub MRT-CASCADE-02/03/04 + KRL existing.",
            interchange_count=2,
            _geom=geoms["MRT-CASCADE-02"],
            forced=[("Lebak Bulus", LEBAK_BULUS), ("Depok Baru", DEPOK_BARU)],
            hubs={"Lebak Bulus", "Depok Baru"},
            existing={"Lebak Bulus", "Depok Baru"},
        ),
        dict(
            id="MRT-CASCADE-03",
            mode="mrt",
            name="DEPOK BARU – JONGGOL",
            short="Depok Baru – Jonggol",
            from_name="Depok Baru",
            to_name="Jonggol",
            direction="Depok Baru → Jonggol",
            route_order=12,
            source=SRC_MRT,
            geometry_source="User GeoJSON TREK MRT (id=1+2+4 Depok Baru–Cibubur–Jonggol)",
            disclaimer=DISC_MRT,
            status_label="Usulan CASCADE · MRT",
            note="Koridor CASCADE MRT Depok Baru–Jonggol. Depok Baru shared dengan MRT-CASCADE-02 dan MRT-CASCADE-04.",
            interchange_count=2,
            _geom=geoms["MRT-CASCADE-03"],
            forced=[("Depok Baru", DEPOK_BARU), ("Cibubur", CIBUBUR)],
            hubs={"Depok Baru", "Cibubur", "Jonggol"},
            existing={"Depok Baru", "Cibubur"},
        ),
        dict(
            id="MRT-CASCADE-04",
            mode="mrt",
            name="DEPOK BARU – ANCOL",
            short="Depok Baru – Ancol",
            from_name="Depok Baru",
            to_name="Ancol",
            direction="Depok Baru → Ancol",
            route_order=13,
            source=SRC_MRT,
            geometry_source="User GeoJSON TREK MRT (id=1 Depok Baru–Ancol)",
            disclaimer=DISC_MRT,
            status_label="Usulan CASCADE · MRT",
            note="Koridor CASCADE MRT Depok Baru–Ancol. Depok Baru shared hub. Ancol menumpang simpul KRL/TJ existing.",
            interchange_count=2,
            _geom=geoms["MRT-CASCADE-04"],
            forced=[("Depok Baru", DEPOK_BARU), ("Ancol", ANCOL)],
            hubs={"Depok Baru", "Ancol"},
            existing={"Depok Baru", "Ancol"},
        ),
        dict(
            id="LRT-CASCADE-NEW-01",
            mode="lrt",
            name="DUKUH ATAS – TANAH ABANG – PIK 2 – BANDARA SOEKARNO-HATTA",
            short="Dukuh Atas – Tanah Abang – PIK 2 – Bandara Soekarno-Hatta",
            from_name="Dukuh Atas",
            to_name="Bandara Soekarno-Hatta",
            direction="Dukuh Atas → Tanah Abang → PIK 2 → Bandara Soekarno-Hatta",
            route_order=21,
            source=SRC_LRT,
            geometry_source="User GeoJSON LRT DUKUH ATAS BANDARA",
            disclaimer=DISC_LRT,
            status_label="Usulan CASCADE · LRT",
            note="LRT CASCADE mengikuti GeoJSON user: Dukuh Atas–Tanah Abang–PIK 2–Bandara Soekarno-Hatta. Bukan LRT Jabodebek existing.",
            interchange_count=3,
            alignment_type="ELEVATED",
            structure="ELEVATED",
            _geom=lrt,
            forced=[
                ("Dukuh Atas", DUKUH_ATAS),
                ("Tanah Abang", TANAH_ABANG),
                ("PIK 2", PIK2),
                ("Bandara Soekarno-Hatta", SOETTA),
            ],
            hubs={"Dukuh Atas", "Tanah Abang", "PIK 2", "Bandara Soekarno-Hatta"},
            existing={"Dukuh Atas", "Tanah Abang"},
        ),
    ]

    new_lines = []
    new_stops = []
    new_meta = []
    for spec in specs:
        print("stations", spec["id"], "...")
        geom, stops = stations_every(spec["_geom"], spec["forced"], spec["from_name"], spec["to_name"], 1500)
        spec["_geom"] = geom
        km = length_m(geom) / 1000
        box = bbox_of(geom)
        p = common_props(spec, km, len(stops), len(geom))
        new_lines.append(feat_line(spec["id"], geom, p))
        new_stops.extend(make_stops(spec, stops, km, len(geom), spec["hubs"], spec["existing"]))
        new_meta.append(meta_row(spec, km, len(stops), box))
        gaps = [stops[i]["km"] - stops[i - 1]["km"] for i in range(1, len(stops))]
        print(
            spec["id"],
            f"{km:.2f}km",
            len(stops),
            "stops",
            "gap",
            f"{min(gaps):.2f}-{max(gaps):.2f}" if gaps else "-",
            [s["name"] for s in stops[:4]],
            "...",
            stops[-1]["name"],
        )

    routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops_fc = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text())
    routes["features"] = drop_old(routes["features"]) + new_lines
    stops_fc["features"] = drop_old(stops_fc["features"]) + new_stops
    meta["corridors"] = [c for c in meta.get("corridors") or [] if not str(c.get("id", "")).startswith("CAS-MRT") and str(c.get("id")) != "CAS-LRT-C04" and not str(c.get("id", "")).startswith("MRT-CASCADE") and not str(c.get("id", "")).startswith("LRT-CASCADE")]
    # keep order: TJ, LRT-C02, new LRT, 4 MRT, KRL
    tj = [c for c in meta["corridors"] if str(c.get("id", "")).startswith("CAS-TJ")]
    lrt_old = [c for c in meta["corridors"] if str(c.get("id", "")).startswith("CAS-LRT")]
    krl = [c for c in meta["corridors"] if str(c.get("id", "")).startswith("KRL-C")]
    other = [c for c in meta["corridors"] if c not in tj + lrt_old + krl]
    meta["corridors"] = tj + lrt_old + new_meta + krl + other

    add_jambu_dua(routes, stops_fc, meta)
    connect_fields(stops_fc)

    write_json(PUB / "cascade_candidates.geojson", routes)
    write_json(PUB / "cascade_stops.geojson", stops_fc)
    write_json(OUT / "cascade_routes.geojson", routes)
    write_json(OUT / "cascade_stops.geojson", stops_fc)
    write_json(PUB / "cascade_existing.json", meta)

    src = json.loads((PUB / "sources.json").read_text())
    for row in src:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(routes["features"])
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stops_fc["features"])
    write_json(PUB / "sources.json", src)
    print("routes", len(routes["features"]), "stops", len(stops_fc["features"]))
    print("ids", [c["id"] for c in meta["corridors"] if c.get("mode") in ("mrt", "lrt", "krl") or str(c["id"]).startswith("KRL")])


if __name__ == "__main__":
    main()
