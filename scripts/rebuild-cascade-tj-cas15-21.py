#!/usr/bin/env python3
"""Add CASTJ15–21 + TJ6/TJ7 extensions from user GeoJSON. Keep other CASCADE modes."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
ATT = ROOT / "attachments"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-16"
R = 6371000.0
DISC = "Usulan CASCADE. Bukan rute resmi TransJakarta. Bukan DED. Estimasi biaya bersifat indikatif."

# anchors
PETOJO = (106.81696, -6.17007)
PULO_GEBANG = (106.95271, -6.21268)
PINANG_RANTI = (106.88628, -6.29112)
LEBAK_BULUS = (106.77493, -6.28930)
PASAR_REBO = (106.86355, -6.30887)
UI = (106.83313, -6.36017)
MARUNDA = (106.96128, -6.09862)
TJ_PRIOK = (106.8808, -6.1085)
KOJA = (106.9038, -6.1085)
JATIWARINGIN = (106.9108, -6.2559)
PASAR_MINGGU = (106.8448, -6.2817)
GALUNGGUNG = (106.82338, -6.20440)
JAGAKARSA = (106.8190, -6.3058)
RAGUNAN = (106.82330, -6.30480)
BLOK_M = (106.8112, -6.2444)
GROGOL = (106.7894, -6.1665)
SENAYAN = (106.7973, -6.2272)
KEMANG = (106.8135, -6.2605)
CIBUBUR = (106.89718, -6.35753)
CIRACAS = (106.8760, -6.3290)
KELAPA_DUA = (106.84313, -6.36508)
TRIKORA = (106.86551, -6.26219)
MOH_KAHFI = (106.80532, -6.33870)
ANDARA = (106.81653, -6.29236)
ASEAN = (106.79920, -6.23996)
KEJAKSAAN = (106.81825, -6.23925)
PETAMBURAN = (106.79723, -6.18510)
TERMINAL_BLOK_M = (106.8110, -6.2435)
MAX_SNAP_M = 80.0


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


def densify(coords, step=80.0):
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


def clean(coords):
    out = [coords[0]]
    for p in coords[1:]:
        if hav(out[-1], p) >= 2:
            out.append(p)
    return out


def smooth_user(raw):
    """Densify along the original GeoJSON. No Chaikin — that was inflating length and drifting off-trase."""
    return densify(clean(raw), 60)


def snap_vertex(coords, pt, which="start"):
    """Only snap if the GeoJSON endpoint is already within 80 m. Never extend the trase."""
    coords = list(coords)
    if which == "start":
        if hav(coords[0], pt) > MAX_SNAP_M:
            return coords
        coords[0] = pt
        while len(coords) > 2 and hav(coords[0], coords[1]) < 8:
            coords.pop(1)
    else:
        if hav(coords[-1], pt) > MAX_SNAP_M:
            return coords
        coords[-1] = pt
        while len(coords) > 2 and hav(coords[-1], coords[-2]) < 8:
            coords.pop(-2)
    return coords


def join_onto(a, b):
    if hav(a[-1], b[0]) <= hav(a[-1], b[-1]):
        use = list(b)
    else:
        use = list(reversed(b))
    if hav(a[-1], use[0]) < 8:
        return a + use[1:]
    return a + use


def load_parts(path: Path):
    data = json.loads(path.read_text())
    parts = []
    for ft in data["features"]:
        g = ft["geometry"]
        rings = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for ring in rings:
            parts.append([(float(x), float(y)) for x, y in ring])
    return parts


def concat_file(path: Path):
    parts = load_parts(path)
    raw = parts[0]
    for nxt in parts[1:]:
        raw = join_onto(raw, nxt)
    return raw


def cut_to(coords, pt):
    i, _, _ = nearest_on(coords, pt)
    return coords[: i + 1]


def inject(coords, pt, max_off=4000.0):
    i, d, _ = nearest_on(coords, pt)
    if d > max_off:
        return coords
    if i in (0, len(coords) - 1):
        return coords
    return coords[:i] + [coords[i]] + coords[i:]


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


LOCAL = [
    ("Petojo", 106.8170, -6.1701), ("Cideng", 106.8090, -6.1750), ("Harmoni", 106.8130, -6.1650),
    ("Gambir", 106.8300, -6.1760), ("Senen", 106.8441, -6.1728), ("Kwitang", 106.8410, -6.1810),
    ("Galur", 106.8550, -6.1750), ("Cempaka Putih", 106.8680, -6.1700), ("Kayu Manis", 106.8600, -6.1850),
    ("Matraman", 106.8607, -6.2121), ("Jatinegara", 106.8680, -6.2200), ("Kampung Melayu", 106.8668, -6.2247),
    ("Otista", 106.8680, -6.2280), ("Bidara Cina", 106.8720, -6.2300), ("Cipinang", 106.8820, -6.2100),
    ("Pulo Gadung", 106.9080, -6.1830), ("Cakung", 106.9480, -6.1750), ("Pulo Gebang", 106.9527, -6.2127),
    ("Pinang Ranti", 106.8863, -6.2911), ("Makasar", 106.8900, -6.2850), ("Halim", 106.8900, -6.2660),
    ("Pasar Rebo", 106.8636, -6.3089), ("Kalisari", 106.8550, -6.3200), ("Cijantung", 106.8619, -6.3122),
    ("Pekayon", 106.8500, -6.3000), ("Condet", 106.8517, -6.2764), ("Tanjung Barat", 106.8388, -6.3080),
    ("Lenteng Agung", 106.8330, -6.3330), ("Jagakarsa", 106.8190, -6.3058), ("Ciganjur", 106.8050, -6.3300),
    ("Lebak Bulus", 106.7749, -6.2893), ("Pondok Labu", 106.7700, -6.3080), ("Fatmawati", 106.7925, -6.2925),
    ("Cipete", 106.8050, -6.2700), ("Blok M", 106.8112, -6.2444), ("Kebayoran Baru", 106.8020, -6.2430),
    ("Kemang", 106.8135, -6.2605), ("Bangka", 106.8080, -6.2550), ("Mampang", 106.8250, -6.2450),
    ("Pancoran", 106.8440, -6.2430), ("Tebet", 106.8500, -6.2260), ("Kuningan", 106.8300, -6.2290),
    ("Senayan", 106.7973, -6.2272), ("Gelora", 106.8030, -6.2180), ("Slipi", 106.7970, -6.1900),
    ("Palmerah", 106.7940, -6.2070), ("Tomang", 106.7970, -6.1780), ("Grogol", 106.7894, -6.1665),
    ("Jelambar", 106.7860, -6.1665), ("UI", 106.8331, -6.3602), ("Pondok Cina", 106.8440, -6.3680),
    ("Margonda", 106.8321, -6.3689), ("Beji", 106.8220, -6.3750), ("Kelapa Dua Depok", 106.8431, -6.3651),
    ("Cimanggis", 106.8620, -6.3720), ("Cibubur", 106.8972, -6.3575), ("Ciracas", 106.8760, -6.3290),
    ("Cipayung", 106.9000, -6.3400), ("Munjul", 106.9200, -6.3550), ("Jatiwaringin", 106.9108, -6.2559),
    ("Pondok Gede", 106.9260, -6.2750), ("Jatibening", 106.9240, -6.2580), ("Kayu Putih", 106.8880, -6.1850),
    ("Rawamangun", 106.8880, -6.1950), ("Kelapa Gading", 106.9050, -6.1570), ("Koja", 106.9038, -6.1085),
    ("Tanjung Priok", 106.8808, -6.1085), ("Cilincing", 106.9400, -6.1080), ("Marunda", 106.9613, -6.0986),
    ("Cakung Timur", 106.9600, -6.1750), ("Ujung Menteng", 106.9550, -6.1900), ("Penggilingan", 106.9400, -6.1950),
    ("Galunggung", 106.8234, -6.2044), ("Dukuh Atas", 106.8230, -6.2030), ("Pasar Minggu", 106.8448, -6.2817),
    ("Ragunan", 106.8230, -6.3050), ("Pejaten", 106.8380, -6.2770), ("Kalibata", 106.8450, -6.2570),
    ("Duren Tiga", 106.8350, -6.2550), ("PGC Cililitan", 106.8657, -6.2619), ("Cawang", 106.8680, -6.2430),
    ("Bumi Perkemahan Cibubur", 106.8972, -6.3575), ("Senayan City", 106.7973, -6.2272),
    ("Grogol Reformasi", 106.7894, -6.1665), ("Marunda Center", 106.9613, -6.0986),
    ("Kampung Rambutan", 106.8820, -6.3080), ("Cilandak", 106.7970, -6.2920),
    ("Ampera", 106.8150, -6.2930), ("TB Simatupang", 106.8300, -6.2970),
    ("Moh Kahfi", 106.8053, -6.3387), ("Andara", 106.8165, -6.2924),
    ("Petamburan", 106.7972, -6.1851), ("Kejaksaan Agung", 106.8183, -6.2393),
    ("ASEAN", 106.7992, -6.2400), ("Cinere", 106.7880, -6.3400), ("Limo", 106.8000, -6.3500),
    ("Harjamukti", 106.9000, -6.3480), ("Cimanggis", 106.8620, -6.3720),
    ("Ragunan", 106.8233, -6.3048), ("Kukusan", 106.8380, -6.3550), ("Gedong", 106.8620, -6.3000),
]


def local_name(lon, lat, used):
    used_l = {u.lower() for u in used}
    ranked = sorted(((hav((lon, lat), (x, y)), n) for n, x, y in LOCAL), key=lambda t: t[0])
    for d, n in ranked:
        if n.lower() in used_l:
            continue
        if d < 1100:
            return n
    return None


def load_existing_stops():
    pts = []
    for name, mode in [
        ("transjakarta_stops.geojson", "transjakarta"),
        ("mrt_stops.geojson", "mrt"),
        ("lrt_stops.geojson", "lrt"),
        ("krl_stops.geojson", "krl"),
        ("cascade_stops.geojson", "cascade"),
    ]:
        try:
            fc = json.loads((PUB / name).read_text())
        except Exception:
            continue
        for f in fc["features"]:
            if f["geometry"]["type"] != "Point":
                continue
            p = f["properties"]
            xy = tuple(f["geometry"]["coordinates"][:2])
            nm = p.get("name") or p.get("stop_name") or ""
            pts.append((nm, xy, mode, p.get("route_id") or p.get("corridor_id") or ""))
    return pts


EXISTING = []


def match_existing(xy):
    best = None
    bd = 1e18
    for nm, p, mode, rid in EXISTING:
        d = hav(xy, p)
        if d < bd:
            bd, best = d, (nm, p, mode, rid)
    if best and bd <= 160:
        return best + (bd,)
    return None


def stations_every(coords, forced, start_name, end_name, step=1500.0):
    geom = list(coords)
    for _, xy in forced:
        geom = inject(geom, xy, 5000.0)
    cdist = cum(geom)
    total = cdist[-1]
    wanted = [0.0]
    t = step
    while t < total - 700:
        wanted.append(t)
        t += step
    wanted.append(total)
    forced_dist = []
    for name, xy in forced:
        i, d, on = nearest_on(geom, xy)
        if d > 5000:
            continue
        forced_dist.append((cdist[min(i, len(cdist) - 1)], name, geom[i] if d >= 80 else on))
    for fd, name, on in forced_dist:
        close = min(wanted, key=lambda w: abs(w - fd))
        if abs(close - fd) < 700:
            wanted[wanted.index(close)] = fd
        else:
            wanted.append(fd)
    wanted = sorted(set(round(w, 1) for w in wanted))
    used, stops = [], []
    for order, dist in enumerate(wanted, start=1):
        xy, _ = point_at(geom, dist, cdist)
        name = None
        hit = match_existing(xy)
        for fd, fn, fon in forced_dist:
            if abs(fd - dist) < 90:
                name, xy = fn, fon
                break
        if order == 1:
            name, xy = start_name, geom[0]
        if order == len(wanted):
            name, xy = end_name, geom[-1]
        shared = False
        if hit and hit[4] <= 160 and order not in (1, len(wanted)):
            name = hit[0] or name
            xy = hit[1]
            shared = True
        if not name:
            name = local_name(xy[0], xy[1], used) or f"KM {int(round(dist / 1000))}"
        n = 2
        base = name
        while any(u.lower() == name.lower() for u in used):
            if order in (1, len(wanted)):
                break
            alt = local_name(xy[0] + 0.004 * n, xy[1], used)
            name = alt if alt and alt.lower() not in {x.lower() for x in used} else f"{base} {n}"
            n += 1
            if n > 4:
                break
        used.append(name)
        stops.append({"name": name, "xy": (round(xy[0], 6), round(xy[1], 6)), "order": order, "km": round(dist / 1000, 2), "shared": shared})
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
    return {"type": "Feature", "id": gid, "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]}, "properties": props}


def feat_pt(gid, xy, props):
    return {"type": "Feature", "id": gid, "geometry": {"type": "Point", "coordinates": [round(xy[0], 6), round(xy[1], 6)]}, "properties": props}


def bbox_of(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def split_last():
    """Map the 3 GeoJSON parts exactly. No invented alignment."""
    parts = load_parts(ATT / "KORIDOR 20 BLOK M PERKEMAHAN CIBUBUR & KORIDOR 21 JAGAKARSA GROGOL VIA SENAYAN CITY.geojson")
    feat0, feat1, feat2 = parts[0], parts[1], parts[2]
    # CASTJ06-EXT = feat0 full: Ragunan → Moh Kahfi → Jagakarsa (selatan, sampai endpoint GeoJSON)
    ext6 = list(feat0)
    if hav(ext6[0], RAGUNAN) > hav(ext6[-1], RAGUNAN):
        ext6 = list(reversed(ext6))
    ext6 = smooth_user(ext6)
    print("CASTJ06-EXT feat0 km", round(length_m(ext6) / 1000, 2), "start", ext6[0], "end", ext6[-1])
    # CASTJ21: Cibubur → Ciracas → Kemang → Kejaksaan Agung → ASEAN (subset feat1, jangan potong di Blok M pertama)
    i_asean, d_asean, _ = nearest_on(feat1, ASEAN)
    c21 = smooth_user(feat1[: i_asean + 1])
    print("CASTJ21 through ASEAN idx", i_asean, "d", int(d_asean), "km", round(length_m(c21) / 1000, 2), "end", c21[-1])
    # CASTJ20: feat0 reversed (Moh Kahfi, shared with CASTJ06) + feat2 + feat1 to Grogol
    moh = list(reversed(feat0))
    gjn = list(feat2)
    if hav(gjn[0], JAGAKARSA) > hav(gjn[-1], JAGAKARSA):
        gjn = list(reversed(gjn))
    i_join, _, _ = nearest_on(feat1, gjn[-1])
    i_gro, _, _ = nearest_on(feat1, GROGOL)
    c20 = smooth_user(moh + gjn[1:] + feat1[i_join + 1 : i_gro + 1])
    print("CASTJ20 idx join", i_join, "→", i_gro, "km", round(length_m(c20) / 1000, 2), "start", c20[0], "end", c20[-1])
    return ext6, c20, c21


def props_of(spec, km, n, verts, geom):
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
        "mode": "transjakarta",
        "status": "CASCADE_PROPOSED",
        "status_label": spec.get("status_label", "Usulan CASCADE · TransJakarta"),
        "network_type": "CASCADE",
        "plan_type": spec.get("plan_type", "PROPOSED"),
        "parent_corridor": spec.get("parent_corridor", ""),
        "parent_route": spec.get("parent_corridor", ""),
        "existing": "NO",
        "length_km": round(km, 2),
        "stop_count": n,
        "interchange_count": spec.get("interchange_count", 2),
        "geometry_confidence": "HIGH",
        "alignment_confidence": "HIGH",
        "alignment_type": "ROAD_CORRIDOR",
        "color": COLOR,
        "crs": CRS,
        "source": "CASCADE TJ — trase user GeoJSON, halte ±1,5 km",
        "source_type": "USER_GEOJSON",
        "geometry_source": spec["geometry_source"],
        "original_length_km": spec.get("original_length_km", round(km, 2)),
        "geometry_role": "display_from_geojson",
        "disclaimer": DISC,
        "updated_at": RETRIEVED,
        "notes": spec["note"],
        "planning_note": spec["note"],
        "insight": spec["insight"],
        "route_order": spec["route_order"],
        "vertex_count": verts,
        "endpoint": spec["short"],
        "structure": spec.get("structure", "AT_GRADE"),
        "elevated_km": spec.get("elevated_km", 0),
        "elevated_note": spec.get("elevated_note", ""),
        "widening_level": spec["widening_level"],
        "widening_reason": spec["widening_reason"],
        "widening_km": spec.get("widening_km", 0),
        "widening_cost_label": spec["widening_cost_label"],
        "cost_label": spec["cost_label"],
        "cost_confidence": spec.get("cost_confidence", "medium"),
        "cost_basis": "Indicative planning estimate. Bukan RAB/DED.",
        "cost_source": spec.get("cost_source", "Benchmark BRT/pelebaran jalan urban Indonesia 2024–2026"),
        "bbox": bbox_of(geom),
        "operator_type": "CASCADE",
    }


def make_stops(spec, stops, km, verts, hubs, existing_names, geom):
    feats = []
    n = len(stops)
    p0 = props_of(spec, km, n, verts, geom)
    for s in stops:
        sid = f"{spec['id']}-S{s['order']:02d}"
        is_end = s["order"] in (1, n)
        p = dict(p0)
        p.update({
            "id": spec["id"],
            "stop_id": sid,
            "station_id": sid,
            "stop_order": s["order"],
            "stop_name": s["name"],
            "name": s["name"],
            "local_area": s["name"],
            "kelurahan": s["name"],
            "name_source": "existing_stop" if s.get("shared") else "local_area",
            "distance_from_previous": s["km"],
            "corridor_code": spec["id"],
            "stop_type": "TERMINUS" if is_end else ("INTERCHANGE" if s["name"] in hubs or s.get("shared") else "STOP"),
            "existing": "YES" if s["name"] in existing_names or s.get("shared") else "NO",
            "interchange": "YES" if s["name"] in hubs or s.get("shared") else "NO",
            "is_interchange": "YES" if s["name"] in hubs or s.get("shared") else "NO",
            "shared_stop": "YES" if s.get("shared") else "NO",
            "km_from_start": s["km"],
            "mode": "transjakarta",
        })
        feats.append(feat_pt(sid, s["xy"], p))
    return feats


def drop_cascade_tj(feats):
    out = []
    for f in feats:
        p = f.get("properties") or {}
        rid = str(f.get("id") or p.get("route_id") or p.get("id") or "")
        mode = str(p.get("mode") or "").lower()
        if rid.startswith("CASTJ") or rid.startswith("CAS-TJ"):
            continue
        if mode == "transjakarta" and str(p.get("network_type") or "").upper().startswith("CASCADE"):
            continue
        out.append(f)
    return out


def main():
    global EXISTING
    EXISTING = load_existing_stops()
    ext6, c20, c21 = split_last()
    raw07 = concat_file(next(ATT.glob("CASTJ07*.geojson")))
    geoms = {
        "CASTJ15": smooth_user(concat_file(ATT / "CASTJ15_Petojo-Pulogebang Via BKT.geojson")),
        "CASTJ16": smooth_user(concat_file(ATT / "CASTJ16_Pinang Ranti -Lebak Bulus via Pasar Rebo.geojson")),
        "CASTJ07-EXT": smooth_user(raw07),
        "CASTJ17": smooth_user(concat_file(ATT / "CASTJ17_Pinang Ranti - Marunda Center (Via Pulo Gebang).geojson")),
        "CASTJ18": smooth_user(concat_file(ATT / "CASTJ18_Pinang Ranti - Tanjung Priok Via Jatiwaringin & Koja.geojson")),
        "CASTJ19": smooth_user(concat_file(ATT / "CASTJ19_UI-Galunggung Via Pasar Minggu.geojson")),
        "CASTJ06-EXT": ext6,
        "CASTJ20": c20,
        "CASTJ21": c21,
    }
    specs = [
        dict(id="CASTJ15", name="Petojo – Pulo Gebang", short="Petojo – Pulo Gebang", from_name="Petojo", to_name="Pulo Gebang",
             route_order=40, geometry_source="CASTJ15_Petojo-Pulogebang Via BKT.geojson",
             forced=[("Petojo", PETOJO), ("Pulo Gebang", PULO_GEBANG)],
             hubs={"Petojo", "Pulo Gebang", "Jatinegara", "Kampung Melayu"}, existing={"Petojo", "Pulo Gebang"},
             widening_level="MODERATE", widening_km=6, widening_reason="Ruas padat Otista–Cakung, penyesuaian lajur BRT terbatas.",
             widening_cost_label="Rp 0,18–0,45 T", cost_label="Rp 0,9–1,8 T", cost_confidence="medium",
             note="Koridor timur–barat Petojo–Pulo Gebang mengikuti GeoJSON user via BKT.",
             insight="Menghubungkan pusat kota ke Pulo Gebang sebagai simpul timur. Bottleneck di Jatinegara/Otista. Pelebaran sedang, bukan koridor elevated."),
        dict(id="CASTJ16", name="Pinang Ranti – Lebak Bulus via Pasar Rebo", short="Pinang Ranti – Lebak Bulus via Pasar Rebo",
             from_name="Pinang Ranti", to_name="Lebak Bulus", route_order=41,
             geometry_source="CASTJ16_Pinang Ranti -Lebak Bulus via Pasar Rebo.geojson",
             forced=[("Pinang Ranti", PINANG_RANTI), ("Pasar Rebo", PASAR_REBO), ("Lebak Bulus", LEBAK_BULUS)],
             hubs={"Pinang Ranti", "Pasar Rebo", "Lebak Bulus", "Fatmawati"}, existing={"Pinang Ranti", "Lebak Bulus", "Pasar Rebo"},
             widening_level="MODERATE", widening_km=5, widening_reason="Pasar Rebo–Cijantung padat, lajur bus perlu pengamanan.",
             widening_cost_label="Rp 0,12–0,32 T", cost_label="Rp 0,7–1,5 T",
             note="TJ CASCADE Pinang Ranti–Lebak Bulus via Pasar Rebo. Bukan trase MRT.",
             insight="Menyambungkan Pinang Ranti ke Lebak Bulus (MRT) lewat Pasar Rebo. Celah transit selatan-timur. Interchange MRT di Lebak Bulus."),
        dict(id="CASTJ07-EXT", name="Perpanjangan Koridor 7: Trikora – UI via Kelapa Dua Depok",
             short="Perpanjangan Koridor 7: Trikora – UI via Kelapa Dua Depok",
             from_name="Trikora", to_name="UI", route_order=42, plan_type="EXTENSION", parent_corridor="TJ-07",
             status_label="Usulan CASCADE · perpanjangan Koridor 7",
             geometry_source="CASTJ07_PERPANJANGAN KORIDOR 7 HALTE TRIKORA - UI VIA KELAPA DUA DEPOK,.geojson",
             forced=[("Trikora", TRIKORA), ("Kelapa Dua Depok", KELAPA_DUA), ("UI", UI)],
             hubs={"Trikora", "UI", "Kelapa Dua Depok", "Cililitan"}, existing={"UI", "Cililitan"},
             widening_level="HIGH", widening_km=5, widening_reason="Cililitan–Condet–Kelapa Dua mixed traffic, ROW terbatas di ruas kampung.",
             widening_cost_label="Rp 0,18–0,48 T", cost_label="Rp 0,6–1,3 T",
             note="Ekstensi Koridor 7 Trikora–UI via Kelapa Dua Depok. Geometry 100% dari GeoJSON user.",
             insight="Perpanjangan Koridor 7 dari Trikora/PGC ke UI lewat Kelapa Dua. Interchange KRL di UI. Pelebaran tinggi di ruas Condet–Cimanggis."),
        dict(id="CASTJ17", name="Pinang Ranti – Marunda Center via Pulo Gebang", short="Pinang Ranti – Marunda Center via Pulo Gebang",
             from_name="Pinang Ranti", to_name="Marunda Center", route_order=43,
             geometry_source="CASTJ17_Pinang Ranti - Marunda Center (Via Pulo Gebang).geojson",
             forced=[("Pinang Ranti", PINANG_RANTI), ("Pulo Gebang", PULO_GEBANG), ("Marunda Center", MARUNDA)],
             hubs={"Pinang Ranti", "Pulo Gebang", "Marunda Center"}, existing={"Pinang Ranti", "Pulo Gebang"},
             widening_level="HIGH", widening_km=10, widening_reason="Koridor panjang timur-utara, ruas Cakung–Marunda perlu kapasitas BRT.",
             widening_cost_label="Rp 0,35–0,80 T", cost_label="Rp 1,4–2,8 T",
             note="Pinang Ranti–Marunda via Pulo Gebang mengikuti GeoJSON.",
             insight="Mengikat Pinang Ranti ke Marunda/Pulo Gebang. Akses kawasan kerja timur-utara lemah. Pelebaran tinggi di Cakung–Cilincing."),
        dict(id="CASTJ18", name="Pinang Ranti – Tanjung Priok via Jatiwaringin & Koja", short="Pinang Ranti – Tanjung Priok via Jatiwaringin & Koja",
             from_name="Pinang Ranti", to_name="Tanjung Priok", route_order=44,
             geometry_source="CASTJ18_Pinang Ranti - Tanjung Priok Via Jatiwaringin & Koja.geojson",
             forced=[("Pinang Ranti", PINANG_RANTI), ("Jatiwaringin", JATIWARINGIN), ("Koja", KOJA), ("Tanjung Priok", TJ_PRIOK)],
             hubs={"Pinang Ranti", "Jatiwaringin", "Koja", "Tanjung Priok"}, existing={"Pinang Ranti", "Tanjung Priok"},
             widening_level="MODERATE", widening_km=7, widening_reason="Jatiwaringin–Kelapa Gading campuran arterial, Koja padat.",
             widening_cost_label="Rp 0,20–0,50 T", cost_label="Rp 1,1–2,2 T",
             note="Pinang Ranti–Tanjung Priok via Jatiwaringin dan Koja.",
             insight="Mengisi celah timur–utara lewat Jatiwaringin dan Koja ke Tanjung Priok. Interchange KRL/TJ di Priok. Bottleneck Kelapa Gading–Koja."),
        dict(id="CASTJ19", name="UI – Galunggung via Pasar Minggu", short="UI – Galunggung via Pasar Minggu",
             from_name="UI", to_name="Galunggung", route_order=45,
             geometry_source="CASTJ19_UI-Galunggung Via Pasar Minggu.geojson",
             forced=[("UI", UI), ("Pasar Minggu", PASAR_MINGGU), ("Galunggung", GALUNGGUNG)],
             hubs={"UI", "Pasar Minggu", "Galunggung", "Dukuh Atas"}, existing={"UI", "Pasar Minggu", "Galunggung"},
             widening_level="MODERATE", widening_km=4, widening_reason="Pasar Minggu–Pejaten arterial sudah lebar sebagian, perlu lajur khusus.",
             widening_cost_label="Rp 0,10–0,28 T", cost_label="Rp 0,8–1,6 T",
             note="UI–Galunggung via Pasar Minggu dari GeoJSON user.",
             insight="Menyambungkan UI ke Galunggung/Dukuh Atas lewat Pasar Minggu. Tumpang tindih KRL Bogor di UI. Properti Margonda–Pasar Minggu aktif."),
        dict(id="CASTJ06-EXT", name="Perpanjangan Koridor 6: Ragunan – Jagakarsa",
             short="Perpanjangan Koridor 6: Ragunan – Jagakarsa",
             from_name="Ragunan", to_name="Cinere", route_order=46, plan_type="EXTENSION", parent_corridor="TJ-06",
             status_label="Usulan CASCADE · perpanjangan Koridor 6",
             geometry_source="KORIDOR 20/21 GeoJSON feat0 (Ragunan–Moh Kahfi–Jagakarsa, penuh sampai endpoint)",
             forced=[("Ragunan", RAGUNAN), ("Moh Kahfi", MOH_KAHFI)],
             hubs={"Ragunan", "Jagakarsa", "Moh Kahfi"}, existing={"Ragunan"},
             widening_level="HIGH", widening_km=5, widening_reason="Jl. Moh Kahfi sempit, mixed traffic tinggi sampai pangkalan selatan.",
             widening_cost_label="Rp 0,12–0,32 T", cost_label="Rp 0,35–0,80 T",
             note="Ekstensi Koridor 6 Ragunan → Moh Kahfi → Jagakarsa. Geometry feat0 utuh, tidak dipotong.",
             insight="Mengikuti Jl. Moh Kahfi sesuai GeoJSON sampai endpoint selatan. Bukan Jagakarsa–Galunggung dan bukan shortcut Ragunan–Jagakarsa."),
        dict(id="CASTJ20", name="Jagakarsa – Grogol Reformasi via Kemang & Senayan City", short="Jagakarsa – Grogol Reformasi via Kemang & Senayan City",
             from_name="Jagakarsa", to_name="Grogol Reformasi", route_order=47,
             geometry_source="KORIDOR 20/21 GeoJSON feat1 subset Jagakarsa–Andara–Kemang–Senayan–Petamburan–Grogol",
             forced=[("Jagakarsa", JAGAKARSA), ("Andara", ANDARA), ("Kemang", KEMANG), ("Senayan City", SENAYAN), ("Petamburan", PETAMBURAN), ("Grogol Reformasi", GROGOL)],
             hubs={"Jagakarsa", "Kemang", "Senayan City", "Petamburan", "Grogol Reformasi"}, existing={"Grogol Reformasi"},
             widening_level="VERY HIGH", widening_km=8, widening_reason="Jagakarsa–Kemang ROW sempit, kepadatan bangunan tinggi, bottleneck persimpangan rapat.",
             widening_cost_label="Rp 0,45–1,10 T", cost_label="Rp 1,6–3,2 T",
             note="CAS20 GeoJSON: Jagakarsa–Andara–Kemang–Senayan City–Petamburan–Grogol. Bukan Blok M. Terpisah dari CASTJ21.",
             insight="Tidak berhenti di Senayan/Blok M. Terpisah dari CASTJ21 meski sama-sama lewat Kemang. Pelebaran VERY HIGH di Jagakarsa–Kemang."),
        dict(id="CASTJ21", name="Bumi Perkemahan Cibubur – Blok M via Ciracas & Kemang", short="Bumi Perkemahan Cibubur – Blok M via Ciracas & Kemang",
             from_name="Bumi Perkemahan Cibubur", to_name="ASEAN", route_order=48, structure="MIXED",
             geometry_source="KORIDOR 20/21 GeoJSON feat1 Cibubur–Ciracas–Kemang–Kejaksaan Agung–ASEAN",
             forced=[("Bumi Perkemahan Cibubur", CIBUBUR), ("Ciracas", CIRACAS), ("Kemang", KEMANG), ("Kejaksaan Agung", KEJAKSAAN), ("ASEAN", ASEAN)],
             hubs={"Bumi Perkemahan Cibubur", "Ciracas", "Kemang", "Kejaksaan Agung", "ASEAN", "Blok M"}, existing={"ASEAN", "Kejaksaan Agung", "Blok M", "Cibubur"},
             widening_level="HIGH", widening_km=6, widening_reason="Ciracas–Kemang padat; Cibubur lebih sesuai skenario elevated konseptual.",
             widening_cost_label="Rp 0,25–0,65 T", cost_label="Rp 4,5–9,5 T",
             elevated_km=9.0, elevated_note="Skenario elevated konseptual ±9 km Cibubur–Ciracas. Bukan proyek resmi. Acuan pendekatan Koridor 13, bukan klaim DED.",
             cost_source="Benchmark elevated BRT/struktur layang urban ID 2024–2026 ±Rp 0,4–0,8 T/km; halte+pendukung terpisah.",
             cost_confidence="low",
             note="CAS21 sampai ASEAN/Kejaksaan Agung sesuai GeoJSON. Shared stop Koridor 1, geometry tidak disalin dari TJ existing.",
             insight="Approach Blok M mengikuti Kejaksaan Agung/ASEAN. Simpul Koridor 1 dipakai bersama, linestring CASTJ21 tetap terpisah."),
    ]

    new_lines, new_stops, new_meta = [], [], []
    for spec in specs:
        print("stations", spec["id"])
        reserved = {s["from_name"] for s in specs if s["id"] != spec["id"]} | {s["to_name"] for s in specs if s["id"] != spec["id"]}
        geom, stops = stations_every(geoms[spec["id"]], spec["forced"], spec["from_name"], spec["to_name"], 1500)
        for s in stops[1:-1]:
            if s["name"] in reserved or str(s["name"]).startswith("KM "):
                used = [x["name"] for x in stops] + list(reserved)
                alt = local_name(s["xy"][0], s["xy"][1], used)
                if not alt:
                    ranked = sorted(((hav(s["xy"], (x, y)), n) for n, x, y in LOCAL), key=lambda t: t[0])
                    for d, n in ranked:
                        if n.lower() in {u.lower() for u in used}:
                            continue
                        if d < 2500:
                            alt = n
                            break
                if alt:
                    s["name"] = alt
        km = length_m(geom) / 1000
        p = props_of(spec, km, len(stops), len(geom), geom)
        new_lines.append(feat_line(spec["id"], geom, p))
        new_stops.extend(make_stops(spec, stops, km, len(geom), spec["hubs"], spec["existing"], geom))
        new_meta.append({
            "id": spec["id"], "name": spec["name"], "short": spec["short"], "endpoint": spec["short"],
            "from_name": spec["from_name"], "to_name": spec["to_name"], "mode": "transjakarta",
            "length_km": round(km, 2), "stop_count": len(stops), "geometry_confidence": "HIGH",
            "source": p["source"], "status": "CASCADE_PROPOSED", "network_type": "CASCADE",
            "plan_type": spec.get("plan_type", "PROPOSED"), "bbox": bbox_of(geom),
            "widening_level": spec["widening_level"], "widening_cost_label": spec["widening_cost_label"],
            "elevated_km": spec.get("elevated_km", 0), "cost_label": spec["cost_label"],
            "insight": spec["insight"], "parent_corridor": spec.get("parent_corridor", ""),
        })
        gaps = [stops[i]["km"] - stops[i - 1]["km"] for i in range(1, len(stops))]
        print(spec["id"], f"{km:.2f}km", len(stops), "gap", f"{min(gaps):.2f}-{max(gaps):.2f}" if gaps else "-", [s["name"] for s in stops[:3]], "→", stops[-1]["name"])

    routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops_fc = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text())
    routes["features"] = drop_cascade_tj(routes["features"]) + new_lines
    stops_fc["features"] = drop_cascade_tj(stops_fc["features"]) + new_stops
    meta["corridors"] = [c for c in meta.get("corridors") or [] if "TJ" not in str(c.get("id"))]
    meta["corridors"] = meta["corridors"] + new_meta

    write_json(PUB / "cascade_candidates.geojson", routes)
    write_json(PUB / "cascade_stops.geojson", stops_fc)
    write_json(OUT / "cascade_routes.geojson", routes)
    write_json(OUT / "cascade_stops.geojson", stops_fc)
    write_json(PUB / "cascade_existing.json", meta)
    print("routes", len(routes["features"]), "stops", len(stops_fc["features"]))
    tj_ids = [c["id"] for c in meta["corridors"] if "TJ" in str(c["id"])]
    print("TJ ids", tj_ids)
    print("CASCADE TJ DATA RESET: OK")
    print("OLD CASCADE TJ: REMOVED")
    for spec in specs:
        g = geoms[spec["id"]]
        print(f"{spec['id']}: GEOJSON GEOMETRY km={length_m(g)/1000:.2f} {spec['from_name']} → {spec['to_name']}")


if __name__ == "__main__":
    main()
    subprocess.check_call(["python3", str(ROOT / "scripts/rename-cascade-tj-stops.py")])
