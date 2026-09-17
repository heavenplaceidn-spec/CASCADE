#!/usr/bin/env python3
"""Additive CASTJ22–26 from user GeoJSON. Do not mutate CASTJ06–21."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
ATT = ROOT / "attachments"
R = 6371000.0
COLOR = "#D62F7F"
CRS = "EPSG:4326"
DISC = "Usulan CASCADE. Bukan rute resmi TransJakarta. Bukan DED. Estimasi biaya bersifat indikatif."
RETRIEVED = "2026-09-17"
OLD_IDS = {
    "CASTJ06-EXT", "CASTJ07-EXT", "CASTJ15", "CASTJ16", "CASTJ17",
    "CASTJ18", "CASTJ19", "CASTJ20", "CASTJ21",
}

SPECS = [
    dict(
        id="CASTJ22",
        file="CASTJ22_SAWANGAN-BLOK M VIA UPN VETERAN.geojson",
        name="Sawangan – Blok M via UPN Veteran",
        from_name="Sawangan", to_name="Blok M", route_order=49,
        forced=[("Sawangan", (106.77266, -6.39456)), ("UPN Veteran", (106.7705, -6.3110)), ("Blok M", (106.8112, -6.2444))],
        widening_level="HIGH", widening_km=6, widening_reason="Sawangan–Fatmawati mixed traffic, ROW terbatas di ruas Depok–UPN.",
        widening_cost_label="Rp 0,22–0,55 T", cost_label="Rp 0,9–1,9 T",
        note="CASTJ22 mengikuti GeoJSON Sawangan–UPN Veteran–Blok M. Endpoint tidak digeser ke Terminal Blok M.",
        insight="Sawangan–Blok M via UPN Veteran mengisi celah selatan-barat. Interchange di Blok M/ASEAN hanya jika spasial bertemu.",
    ),
    dict(
        id="CASTJ23",
        file="CASTJ23_PONDOK LABU - KALIDERES (VIA PURI INDAH).geojson",
        name="Pondok Labu – Kalideres via Puri Indah",
        from_name="Pondok Labu", to_name="Kalideres", route_order=50,
        forced=[("Pondok Labu", (106.79387, -6.30920)), ("Puri Indah", (106.7360, -6.1867)), ("Kalideres", (106.70585, -6.15440))],
        widening_level="HIGH", widening_km=8, widening_reason="Pesanggrahan–Joglo–Puri Indah padat, Kalideres arterial.",
        widening_cost_label="Rp 0,28–0,70 T", cost_label="Rp 1,2–2,4 T",
        note="CASTJ23 GeoJSON Pondok Labu–Puri Indah–Kalideres. Tidak memakai trek CASTJ24/25.",
        insight="Mengikat Pondok Labu ke Kalideres lewat Puri Indah. Shared node hanya jika bertemu TJ existing.",
    ),
    dict(
        id="CASTJ24",
        file="CASTJ24_CBD CILEDUG - MONAS (VIA JOGLO).geojson",
        name="CBD Ciledug – Monas via Joglo",
        from_name="CBD Ciledug", to_name="Monas", route_order=51,
        forced=[("CBD Ciledug", (106.70906, -6.22367)), ("Joglo", (106.7484, -6.2175)), ("Monas", (106.82288, -6.17623))],
        widening_level="MODERATE", widening_km=5, widening_reason="Joglo–Kembangan mixed arterial, pusat kota lebih siap BRT.",
        widening_cost_label="Rp 0,15–0,40 T", cost_label="Rp 1,0–2,0 T",
        note="CASTJ24 GeoJSON via Joglo. Terpisah dari CASTJ25 via Meruya meski Ciledug/Monas berdekatan.",
        insight="Ciledug–Monas via Joglo. Boleh berbagi halte Ciledug/Monas dengan CASTJ25, trek tetap berbeda.",
    ),
    dict(
        id="CASTJ25",
        file="CASTJ25_PURI BETA - MONAS (VIA MERUYA).geojson",
        name="Ciledug – Monas via Meruya",
        from_name="Ciledug", to_name="Monas", route_order=52,
        forced=[("Ciledug", (106.70907, -6.22354)), ("Meruya", (106.7463, -6.1975)), ("Monas", (106.82293, -6.17635))],
        widening_level="MODERATE", widening_km=5, widening_reason="Meruya–Kebon Jeruk padat, overlap visual dengan CASTJ24 bukan alasan merge.",
        widening_cost_label="Rp 0,15–0,40 T", cost_label="Rp 1,0–2,0 T",
        note="CASTJ25 GeoJSON via Meruya. Entity terpisah dari CASTJ24. Overlap ≠ merge.",
        insight="Ciledug–Monas via Meruya. Shared Ciledug/Monas boleh, geometry tetap dari GeoJSON CASTJ25.",
    ),
    dict(
        id="CASTJ26",
        file="CASTJ26_KOJA - CENGKARENG BUSINESS CITY (VIA PLUMPANG, KAPUK).geojson",
        name="Koja – Cengkareng Business City via Plumpang, Kapuk",
        from_name="Koja", to_name="Cengkareng Business City", route_order=53,
        forced=[("Koja", (106.91706, -6.12185)), ("Plumpang", (106.8922, -6.1379)), ("Kapuk", (106.7560, -6.1370)), ("Cengkareng Business City", (106.69470, -6.11003))],
        widening_level="HIGH", widening_km=10, widening_reason="Pantai utara Kapuk–Plumpang, akses CBC masih lemah.",
        widening_cost_label="Rp 0,35–0,85 T", cost_label="Rp 1,5–3,0 T",
        note="CASTJ26 GeoJSON Koja–Plumpang–Kapuk–CBC. Tidak diluruskan antar endpoint.",
        insight="Koja ke CBC via Plumpang dan Kapuk. Interchange hanya jika spasial bertemu TJ existing.",
    ),
]

LOCAL = [
    ("Sawangan", 106.7727, -6.3946), ("Pengasinan", 106.7700, -6.3940), ("Cinangka", 106.7680, -6.3870),
    ("Bojongsari", 106.7705, -6.3767), ("Curug", 106.7748, -6.3678), ("Rangkapan Jaya", 106.7761, -6.3617),
    ("Pancoran Mas", 106.7750, -6.3546), ("Depok", 106.7764, -6.3520), ("Mampang Depok", 106.7774, -6.3462),
    ("UPN Veteran", 106.7705, -6.3110), ("Pondok Labu", 106.7939, -6.3092), ("Fatmawati", 106.7925, -6.2925),
    ("Cilandak", 106.7970, -6.2920), ("Lebak Bulus", 106.7749, -6.2893), ("Pondok Pinang", 106.7823, -6.2913),
    ("Kebayoran Lama", 106.7820, -6.2440), ("Cipete", 106.8050, -6.2700), ("Kemang", 106.8135, -6.2605),
    ("Blok M", 106.8112, -6.2444), ("ASEAN", 106.7992, -6.23996), ("Melawai", 106.8050, -6.2430),
    ("Masjid Agung", 106.7984, -6.2365), ("Puri Indah", 106.7360, -6.1867), ("Kembangan Selatan", 106.7387, -6.1867),
    ("Joglo", 106.7484, -6.2175), ("Meruya", 106.7463, -6.1975), ("Meruya Utara", 106.7463, -6.1868),
    ("Meruya Selatan", 106.7420, -6.1909), ("Kalideres", 106.7059, -6.1544), ("Tegal Alur", 106.7120, -6.1557),
    ("Kamal", 106.7204, -6.1528), ("Cengkareng Timur", 106.7272, -6.1561), ("Cengkareng Barat", 106.7270, -6.1652),
    ("Kapuk", 106.7560, -6.1370), ("Kapuk Muara", 106.7542, -6.1357), ("Pluit", 106.7940, -6.1429),
    ("Pejagalan", 106.8016, -6.1419), ("Penjaringan", 106.8059, -6.1419), ("Waduk Pluit", 106.7895, -6.1434),
    ("Ancol", 106.8304, -6.1276), ("Pademangan", 106.8407, -6.1472), ("Tanjung Priok", 106.8808, -6.1085),
    ("Plumpang", 106.8922, -6.1379), ("Koja", 106.9171, -6.1218), ("Lagoa", 106.9100, -6.1080),
    ("Rawa Badak", 106.9050, -6.1200), ("Sungai Bambu", 106.8850, -6.1250), ("Papanggo", 106.8950, -6.1200),
    ("Cengkareng Business City", 106.6947, -6.1100), ("Pantai Indah Kapuk", 106.7443, -6.1297),
    ("Kamal Muara", 106.7195, -6.1075), ("Tegal Alur Utara", 106.7031, -6.1061),
    ("CBD Ciledug", 106.7091, -6.2237), ("Ciledug", 106.7091, -6.2235), ("Puri Beta", 106.7091, -6.2235),
    ("Petukangan Utara", 106.7479, -6.2365), ("Ulujami", 106.7639, -6.2382), ("Pesanggrahan", 106.7605, -6.2556),
    ("Bintaro", 106.7644, -6.2722), ("Pondok Jaya", 106.7718, -6.2834), ("Cipulir", 106.7779, -6.2890),
    ("Kebayoran Lama Utara", 106.7823, -6.2440), ("Palmerah", 106.7961, -6.2076), ("Slipi", 106.7970, -6.1900),
    ("Tanah Abang", 106.8100, -6.1858), ("Kebon Kacang", 106.8115, -6.1870), ("Gambir", 106.8227, -6.1762),
    ("Monas", 106.8229, -6.1763), ("Harmoni", 106.8200, -6.1650), ("Kebon Jeruk", 106.7690, -6.1910),
    ("Kedoya", 106.7620, -6.1800), ("Duri Kepa", 106.7800, -6.1850), ("Tomang", 106.7970, -6.1780),
    ("Grogol", 106.7894, -6.1665), ("Tanjung Duren", 106.7896, -6.1760), ("Kota Bambu", 106.7880, -6.1880),
    ("Kemanggisan", 106.7850, -6.2000), ("Pal Merah", 106.7950, -6.2000), ("Gelora", 106.8030, -6.2180),
    ("Senayan", 106.7973, -6.2272), ("Kembangan", 106.7384, -6.1867), ("Srengseng", 106.7540, -6.2004),
    ("Sukabumi Utara", 106.7837, -6.2067), ("Petamburan", 106.7972, -6.1851), ("Cikini", 106.8400, -6.1910),
    ("Senen", 106.8441, -6.1728), ("Kwitang", 106.8410, -6.1810), ("Gondangdia", 106.8320, -6.1860),
    ("Menteng", 106.8310, -6.1960), ("Cempaka Putih", 106.8680, -6.1700),
]


def hav(a, b):
    to = math.radians
    dlon = to(b[0] - a[0])
    dlat = to(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(to(a[1])) * math.cos(to(b[1])) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def length_m(c):
    return sum(hav(c[i - 1], c[i]) for i in range(1, len(c)))


def nearest_on(coords, pt):
    bi, bd = 0, 1e18
    for i, c in enumerate(coords):
        d = hav(c, pt)
        if d < bd:
            bi, bd = i, d
    return bi, bd, coords[bi]


def clean(coords):
    out = [coords[0]]
    for c in coords[1:]:
        if hav(out[-1], c) >= 2:
            out.append(c)
    return out


def densify(coords, step=55.0):
    out = [coords[0]]
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        d = hav(a, b)
        n = max(1, int(d / step))
        for k in range(1, n):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        out.append(b)
    return out


def chaikin_sharp(coords, min_turn_deg=55.0):
    """Light smooth only at sharp digitization kinks. Endpoints unchanged."""
    if len(coords) < 3:
        return coords
    out = [coords[0]]
    for i in range(1, len(coords) - 1):
        a, b, c = coords[i - 1], coords[i], coords[i + 1]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1 = math.hypot(*v1) or 1e-12
        n2 = math.hypot(*v2) or 1e-12
        dot = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        ang = math.degrees(math.acos(dot))
        if ang >= min_turn_deg:
            out.append((0.75 * b[0] + 0.25 * a[0], 0.75 * b[1] + 0.25 * a[1]))
            out.append((0.75 * b[0] + 0.25 * c[0], 0.75 * b[1] + 0.25 * c[1]))
        else:
            out.append(b)
    out.append(coords[-1])
    return out


def inject(coords, pt, max_off=5000.0):
    i, d, _ = nearest_on(coords, pt)
    if d > max_off:
        return coords
    out = list(coords)
    if hav(out[i], pt) > 8:
        out.insert(i, out[i])
    return out


def cum(coords):
    d = [0.0]
    for i in range(1, len(coords)):
        d.append(d[-1] + hav(coords[i - 1], coords[i]))
    return d


def point_at(coords, dist, cdist):
    if dist <= 0:
        return coords[0]
    if dist >= cdist[-1]:
        return coords[-1]
    for i in range(1, len(cdist)):
        if cdist[i] >= dist:
            t = (dist - cdist[i - 1]) / max(1e-9, cdist[i] - cdist[i - 1])
            a, b = coords[i - 1], coords[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return coords[-1]


def load_line(path: Path):
    raw = json.loads(path.read_text())
    coords = []
    for ft in raw["features"]:
        g = ft["geometry"]
        if g["type"] == "LineString":
            coords.extend((float(x), float(y)) for x, y in g["coordinates"])
        elif g["type"] == "MultiLineString":
            for part in g["coordinates"]:
                coords.extend((float(x), float(y)) for x, y in part)
    return clean(coords)


def local_name(xy, used):
    used_l = {u.lower() for u in used}
    ranked = sorted(((hav(xy, (x, y)), n) for n, x, y in LOCAL), key=lambda t: t[0])
    for d, n in ranked:
        if n.lower() in used_l:
            continue
        if d <= 2200:
            return n
    for d, n in ranked:
        if n.lower() not in used_l:
            return n
    return None


def load_existing():
    pts = []
    for fname in ["transjakarta_stops.geojson", "mrt_stops.geojson", "lrt_stops.geojson", "krl_stops.geojson", "cascade_stops.geojson"]:
        p = PUB / fname
        if not p.exists():
            continue
        fc = json.loads(p.read_text())
        for f in fc["features"]:
            if f["geometry"]["type"] != "Point":
                continue
            pr = f["properties"]
            nm = pr.get("name") or pr.get("stop_name")
            if not nm:
                continue
            xy = tuple(f["geometry"]["coordinates"][:2])
            pts.append((str(nm), float(xy[0]), float(xy[1]), str(pr.get("mode") or fname.split("_")[0])))
    return pts


EXISTING = []


def match_name(xy):
    best, bd = None, 1e18
    for nm, x, y, mode in EXISTING:
        d = hav(xy, (x, y))
        if d < bd:
            bd, best = d, (nm, d, mode)
    if best and best[1] <= 160:
        return best
    return None


def stations(geom, forced, start_name, end_name, step=1500.0, reserved=None):
    reserved = {n.lower() for n in (reserved or set()) if n.lower() not in {start_name.lower(), end_name.lower()}}
    reserved |= {end_name.lower()}
    g = list(geom)
    for _, xy in forced:
        g = inject(g, xy, 5000.0)
    cdist = cum(g)
    total = cdist[-1]
    wanted = [0.0]
    t = step
    while t < total - 700:
        wanted.append(t)
        t += step
    wanted.append(total)
    forced_d = []
    for name, xy in forced:
        i, d, on = nearest_on(g, xy)
        if d > 5000:
            continue
        forced_d.append((cdist[min(i, len(cdist) - 1)], name, g[i]))
    for fd, name, on in forced_d:
        close = min(wanted, key=lambda w: abs(w - fd))
        if abs(close - fd) < 700:
            wanted[wanted.index(close)] = fd
        else:
            wanted.append(fd)
    wanted = sorted(set(round(w, 1) for w in wanted))
    used, stops = [], []
    for order, dist in enumerate(wanted, start=1):
        xy = point_at(g, dist, cdist)
        name = None
        shared = "NO"
        for fd, fn, fon in forced_d:
            if abs(fd - dist) < 90:
                name = fn
                break
        if order == 1:
            name, xy = start_name, g[0]
        if order == len(wanted):
            name, xy = end_name, g[-1]
        hit = match_name(xy)
        if hit and order not in (1, len(wanted)):
            # reuse NAME only; keep coordinate on the CASTJ line
            if not name:
                name = hit[0]
            shared = "YES"
        if not name:
            name = local_name(xy, used) or start_name
        if name.lower() in reserved and name.lower() not in {start_name.lower(), end_name.lower()} and order not in (1, len(wanted)):
            alt = local_name((xy[0] + 0.004, xy[1]), used + list(reserved))
            if alt:
                name = alt
        if name.lower() == end_name.lower() and order not in (1, len(wanted)):
            alt = local_name((xy[0] + 0.005, xy[1] - 0.004), used + [end_name])
            if alt and alt.lower() != end_name.lower():
                name = alt
        if name.lower().startswith("km"):
            name = local_name(xy, used) or start_name
        base = name
        n = 2
        while any(u.lower() == name.lower() for u in used):
            if order in (1, len(wanted)):
                break
            alt = local_name((xy[0] + 0.003 * n, xy[1]), used)
            name = alt if alt and alt.lower() not in {x.lower() for x in used} else f"{base}"
            n += 1
            if n > 5:
                break
        used.append(name)
        if stops and hav(stops[-1]["xy"], xy) < 650 and order not in (1, len(wanted)):
            forced_hit = any(abs(fd - dist) < 90 for fd, fn, fon in forced_d)
            if not forced_hit:
                used.pop()
                continue
        stops.append({
            "name": name,
            "xy": (round(xy[0], 6), round(xy[1], 6)),
            "order": order,
            "km": round(dist / 1000, 2),
            "shared": shared,
        })
    for i, s in enumerate(stops, start=1):
        s["order"] = i
    return g, stops


def bbox_of(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def props_of(spec, km, n, verts, geom):
    return {
        "id": spec["id"],
        "route_id": spec["id"],
        "corridor_id": spec["id"],
        "corridor_name": spec["name"],
        "name": spec["name"],
        "short": spec["name"],
        "route_name": spec["name"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "start_name": spec["from_name"],
        "end_name": spec["to_name"],
        "mode": "transjakarta",
        "status": "CASCADE_PROPOSED",
        "status_label": "Usulan CASCADE · TransJakarta",
        "network_type": "CASCADE",
        "plan_type": "PROPOSED",
        "parent_corridor": "",
        "parent_route": "",
        "existing": "NO",
        "length_km": round(km, 2),
        "stop_count": n,
        "interchange_count": 2,
        "geometry_confidence": "HIGH",
        "alignment_confidence": "HIGH",
        "alignment_type": "ROAD_CORRIDOR",
        "color": COLOR,
        "crs": CRS,
        "source": "CASCADE TJ — trase user GeoJSON, halte ±1,5 km",
        "source_type": "USER_GEOJSON",
        "geometry_source": spec["file"],
        "original_length_km": round(km, 2),
        "geometry_role": "display_from_geojson",
        "disclaimer": DISC,
        "updated_at": RETRIEVED,
        "notes": spec["note"],
        "planning_note": spec["note"],
        "insight": spec["insight"],
        "route_order": spec["route_order"],
        "vertex_count": verts,
        "endpoint": spec["name"],
        "structure": "AT_GRADE",
        "elevated_km": 0,
        "elevated_note": "",
        "widening_level": spec["widening_level"],
        "widening_reason": spec["widening_reason"],
        "widening_km": spec["widening_km"],
        "widening_cost_label": spec["widening_cost_label"],
        "cost_label": spec["cost_label"],
        "cost_confidence": "medium",
        "cost_basis": "Indicative planning estimate. Bukan RAB/DED.",
        "cost_source": "Benchmark BRT/pelebaran jalan urban Indonesia 2024–2026",
        "bbox": bbox_of(geom),
        "operator_type": "CASCADE",
        "corridor_type": "CASCADE",
        "source_geojson": spec["file"],
    }


def write_both(name, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    (PUB / name).write_text(text)
    cas = PUB / "cascade" / name
    if cas.parent.exists():
        cas.write_text(text)


def main():
    global EXISTING
    EXISTING = load_existing()
    cand = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops_fc = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text())
    freeze = {str(f.get("id")): json.dumps(f["geometry"]) for f in cand["features"] if str(f.get("id")) in OLD_IDS}
    freeze_stops = sum(1 for f in stops_fc["features"] if str(f["properties"].get("route_id")) in OLD_IDS)

    # drop previous CASTJ22-26 if rerun
    new_ids = {s["id"] for s in SPECS}
    cand["features"] = [f for f in cand["features"] if str(f.get("id")) not in new_ids]
    stops_fc["features"] = [f for f in stops_fc["features"] if str(f["properties"].get("route_id")) not in new_ids]
    meta["corridors"] = [c for c in meta.get("corridors", []) if str(c.get("id")) not in new_ids]

    for spec in SPECS:
        raw = load_line(ATT / spec["file"])
        raw_km = length_m(raw) / 1000
        geom = densify(chaikin_sharp(raw), 55)
        assert abs(geom[0][0] - raw[0][0]) < 1e-8 and abs(geom[-1][0] - raw[-1][0]) < 1e-8
        geom, stps = stations(
            geom, spec["forced"], spec["from_name"], spec["to_name"],
            reserved={s["from_name"] for s in SPECS} | {s["to_name"] for s in SPECS} | {"Harmoni", "Senen", "Cengkareng Business City", "Monas", "Blok M", "Grogol", "Grogol Reformasi"},
        )
        used_n = [s["name"] for s in stps]
        for s in stps[1:-1]:
            if s["name"] in {spec["to_name"], spec["from_name"], "Cengkareng Business City"}:
                alt = local_name((s["xy"][0] + 0.006, s["xy"][1]), used_n)
                if alt and alt not in used_n:
                    used_n[used_n.index(s["name"])] = alt
                    s["name"] = alt
        km = length_m(geom) / 1000
        print(spec["id"], f"raw {raw_km:.2f}km display {km:.2f}km", "n", len(stps), "→", [s["name"] for s in stps[:4]], "...", stps[-1]["name"])
        assert not any(s["name"].upper().startswith("KM") for s in stps), spec["id"]
        props = props_of(spec, km, len(stps), len(geom), geom)
        cand["features"].append({
            "type": "Feature",
            "id": spec["id"],
            "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in geom]},
            "properties": props,
        })
        p0 = props
        n = len(stps)
        for s in stps:
            p = dict(p0)
            p.update({
                "id": spec["id"],
                "stop_id": f"{spec['id']}-S{s['order']:02d}",
                "station_id": f"{spec['id']}-S{s['order']:02d}",
                "stop_order": s["order"],
                "name": s["name"],
                "stop_name": s["name"],
                "local_area": s["name"],
                "kelurahan": s["name"],
                "name_source": "local_area",
                "stop_type": "TERMINUS" if s["order"] in (1, n) else "STOP",
                "interchange": "YES" if s["shared"] == "YES" or s["order"] in (1, n) else "NO",
                "is_interchange": "YES" if s["shared"] == "YES" or s["order"] in (1, n) else "NO",
                "shared_stop": s["shared"],
                "km_from_start": s["km"],
                "corridor_code": spec["id"],
            })
            stops_fc["features"].append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["xy"][0], s["xy"][1]]},
                "properties": p,
            })
        meta["corridors"].append({
            "id": spec["id"],
            "name": spec["name"],
            "short": spec["name"],
            "endpoint": spec["name"],
            "from_name": spec["from_name"],
            "to_name": spec["to_name"],
            "mode": "transjakarta",
            "length_km": round(km, 2),
            "stop_count": n,
            "geometry_confidence": "HIGH",
            "source": "CASCADE TJ — trase user GeoJSON, halte ±1,5 km",
            "status": "CASCADE_PROPOSED",
            "network_type": "CASCADE",
            "plan_type": "PROPOSED",
            "bbox": bbox_of(geom),
            "widening_level": spec["widening_level"],
            "widening_cost_label": spec["widening_cost_label"],
            "elevated_km": 0,
            "cost_label": spec["cost_label"],
            "insight": spec["insight"],
            "parent_corridor": "",
        })

    after = {str(f.get("id")): json.dumps(f["geometry"]) for f in cand["features"] if str(f.get("id")) in OLD_IDS}
    assert after == freeze, "old CASTJ geometry mutated"
    after_stops = sum(1 for f in stops_fc["features"] if str(f["properties"].get("route_id")) in OLD_IDS)
    assert after_stops == freeze_stops, "old CASTJ stops mutated"

    write_both("cascade_candidates.geojson", cand)
    write_both("cascade_stops.geojson", stops_fc)
    write_both("cascade_existing.json", meta)
    print("OLD CASTJ frozen", sorted(OLD_IDS))
    print("NEW", [s["id"] for s in SPECS])
    print("routes", len(cand["features"]), "stops", len(stops_fc["features"]), "meta", len(meta["corridors"]))


if __name__ == "__main__":
    main()
