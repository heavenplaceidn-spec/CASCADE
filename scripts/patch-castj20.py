#!/usr/bin/env python3
"""Surgical CASTJ20 patch. Do not touch CASTJ06-EXT / CASTJ21 / other corridors."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
ATT = ROOT / "attachments"
R = 6371000.0
JAGAKARSA = (106.8190, -6.3058)
MOH_KAHFI = (106.80532, -6.33870)
ANDARA = (106.81653, -6.29236)
KEMANG = (106.8135, -6.2605)
ASEAN = (106.79920, -6.23996)
SENAYAN = (106.7973, -6.2272)
PALMERAH_LINE = (106.79608, -6.20762)  # on GeoJSON, NOT KRL Palmerah
TANJUNG_DUREN = (106.7896, -6.1760)
GROGOL = (106.7894, -6.1665)


def hav(a, b):
    to = math.radians
    dlon = to(b[0] - a[0])
    dlat = to(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(to(a[1])) * math.cos(to(b[1])) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def length_m(c):
    return sum(hav(c[i - 1], c[i]) for i in range(1, len(c)))


def nearest_on(coords, pt):
    bi, bd, bp = 0, 1e18, coords[0]
    for i, c in enumerate(coords):
        d = hav(c, pt)
        if d < bd:
            bi, bd, bp = i, d, c
    return bi, bd, bp


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


def inject(coords, pt, max_off=5000.0):
    i, d, _ = nearest_on(coords, pt)
    if d > max_off:
        return coords
    out = list(coords)
    if hav(out[i], pt) > 1:
        out.insert(i, pt)
    return out


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
            t = (dist - cdist[i - 1]) / max(1e-9, cdist[i] - cdist[i - 1])
            a, b = coords[i - 1], coords[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), i
    return coords[-1], len(coords) - 1


LOCAL = [
    ("Jagakarsa", 106.8190, -6.3058), ("Moh Kahfi", 106.8053, -6.3387), ("Cinere", 106.7940, -6.3480),
    ("Limo", 106.8000, -6.3550), ("Ciganjur", 106.8050, -6.3300), ("Andara", 106.8165, -6.2924),
    ("Ampera", 106.8150, -6.2930), ("Kemang", 106.8135, -6.2605), ("Bangka", 106.8080, -6.2550),
    ("ASEAN", 106.7992, -6.2400), ("Senayan City", 106.7973, -6.2272), ("Gelora", 106.8030, -6.2180),
    ("Palmerah", 106.7961, -6.2076), ("Slipi", 106.7970, -6.1900), ("Tanjung Duren", 106.7896, -6.1760),
    ("Tomang", 106.7970, -6.1780), ("Grogol Reformasi", 106.7894, -6.1665), ("Jelambar", 106.7860, -6.1665),
    ("Petamburan", 106.7972, -6.1851), ("Kebayoran Baru", 106.8020, -6.2430),
    ("Cipedak", 106.8000, -6.3400), ("Srengseng Sawah", 106.8300, -6.3400), ("Lenteng Agung", 106.8330, -6.3330),
    ("Fatmawati", 106.7925, -6.2925), ("Cipete", 106.8050, -6.2700), ("Pela Mampang", 106.8180, -6.2480),
    ("Kebayoran Lama", 106.7820, -6.2440), ("Melawai", 106.8050, -6.2430), ("Senayan", 106.7973, -6.2272),
    ("Gelora Bung Karno", 106.8070, -6.2180), ("Kota Bambu", 106.7880, -6.1880), ("Kemanggisan", 106.7850, -6.2000),
    ("Tanjung Duren Selatan", 106.7850, -6.1780), ("Grogol", 106.7894, -6.1665),
    ("Gandul", 106.7950, -6.3550), ("Pangkalan Jati", 106.8100, -6.3500), ("Pondok Cabe", 106.7750, -6.3300),
    ("Kedaung", 106.7900, -6.3580), ("Ragunan", 106.8230, -6.3050),
]


def local_name(x, y, used):
    used_l = {u.lower() for u in used}
    ranked = sorted(((hav((x, y), (a, b)), n) for n, a, b in LOCAL), key=lambda t: t[0])
    for d, n in ranked:
        if n.lower() in used_l:
            continue
        if d < 2800:
            return n
    return ranked[0][1] if ranked else None


def load_parts():
    raw = json.loads((ATT / "KORIDOR 20 BLOK M PERKEMAHAN CIBUBUR & KORIDOR 21 JAGAKARSA GROGOL VIA SENAYAN CITY.geojson").read_text())
    return [[(float(x), float(y)) for x, y in ft["geometry"]["coordinates"][0]] for ft in raw["features"]]


def build_castj20():
    feat0, feat1, feat2 = load_parts()
    moh = list(reversed(feat0))  # Cinere/Moh Kahfi → Jagakarsa (same vertices as CASTJ06-EXT)
    gj = list(feat2)
    if hav(gj[0], JAGAKARSA) > hav(gj[-1], JAGAKARSA):
        gj = list(reversed(gj))
    i_join, d_join, _ = nearest_on(feat1, gj[-1])
    i_gro, _, _ = nearest_on(feat1, GROGOL)
    north = feat1[i_join : i_gro + 1]
    geom = moh + gj[1:] + north[1:]
    print("CASTJ20 parts km moh", round(length_m(moh) / 1000, 2), "gj", round(length_m(gj) / 1000, 2), "north", round(length_m(north) / 1000, 2), "join_gap", int(d_join))
    return densify(geom, 55)


def stations(geom):
    forced = [
        ("Jagakarsa", JAGAKARSA),
        ("Moh Kahfi", MOH_KAHFI),
        ("Andara", ANDARA),
        ("Kemang", KEMANG),
        ("ASEAN", ASEAN),
        ("Senayan City", SENAYAN),
        ("Palmerah", PALMERAH_LINE),
        ("Tanjung Duren", TANJUNG_DUREN),
        ("Grogol Reformasi", GROGOL),
    ]
    for _, xy in forced:
        geom = inject(geom, xy, 5000)
    cdist = cum(geom)
    total = cdist[-1]
    wanted = [0.0]
    t = 1500.0
    while t < total - 700:
        wanted.append(t)
        t += 1500
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
        for fd, fn, fon in forced_dist:
            if abs(fd - dist) < 90:
                name, xy = fn, fon
                break
        if order == 1:
            name = local_name(geom[0][0], geom[0][1], used) or "Cinere"
            xy = geom[0]
        if not name:
            name = local_name(xy[0], xy[1], used) or "Cinere"
        if name.lower().startswith("jagakarsa") and order not in (1, len(wanted)):
            alt = local_name(xy[0] + 0.003, xy[1] - 0.003, used)
            if alt and alt.lower() != "jagakarsa":
                name = alt
        if name.lower() == "blok m":
            name = local_name(xy[0] + 0.002, xy[1], used) or "Kebayoran Baru"
        # never snap Palmerah off the line
        if name == "Palmerah":
            xy = PALMERAH_LINE
            i, d, on = nearest_on(geom, PALMERAH_LINE)
            xy = geom[i] if d >= 80 else on
        base = name
        n = 2
        while any(u.lower() == name.lower() for u in used):
            alt = local_name(xy[0] + 0.004 * n, xy[1], used)
            name = alt if alt and alt.lower() not in {x.lower() for x in used} else f"{base} {n}"
            n += 1
            if n > 4:
                break
        used.append(name)
        stops.append({"name": name, "xy": (round(xy[0], 6), round(xy[1], 6)), "order": order, "km": round(dist / 1000, 2)})
    if stops:
        end_n = stops[-1]["name"]
        keep = []
        for s in stops:
            if keep and s["name"] == end_n and s is not stops[-1]:
                continue
            keep.append(s)
        stops = keep
        if stops[-1]["name"] != "Grogol Reformasi":
            stops[-1]["name"] = "Grogol Reformasi"
            stops[-1]["xy"] = (round(geom[-1][0], 6), round(geom[-1][1], 6))
    for i, s in enumerate(stops, start=1):
        s["order"] = i
    return geom, stops


def bbox(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def main():
    # freeze other corridor ids
    cand = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops_fc = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text()) if (PUB / "cascade_existing.json").exists() else {}
    before = {str(f.get("id")): f["geometry"]["coordinates"][0] for f in cand["features"] if str(f.get("id")) in {"CASTJ06-EXT", "CASTJ21"}}

    geom, stps = stations(build_castj20())
    km = length_m(geom) / 1000
    print("CASTJ20 km", round(km, 2), "stops", [s["name"] for s in stps], "start", geom[0], "end", geom[-1])
    assert any(abs(p[1] + 6.33) < 0.05 or p[1] < -6.33 for p in geom), "Moh Kahfi south missing"
    assert geom[-1][1] > -6.18, "must end Grogol"

    old = next(f for f in cand["features"] if str(f.get("id")) == "CASTJ20")
    props = dict(old["properties"])
    props.update({
        "length_km": round(km, 2),
        "stop_count": len(stps),
        "vertex_count": len(geom),
        "from_name": "Jagakarsa",
        "to_name": "Grogol Reformasi",
        "start_name": "Jagakarsa",
        "end_name": "Grogol Reformasi",
        "geometry_source": "user GeoJSON feat0 (Moh Kahfi, shared with CASTJ06-EXT) + feat2 + feat1 to Grogol",
        "original_length_km": round(km, 2),
        "overlap_corridor": "CASTJ06-EXT",
        "overlap_note": "Segmen Jagakarsa–Moh Kahfi beririsan dengan Perpanjangan Koridor 6. Feature terpisah.",
        "note": "CASTJ20: Jagakarsa → Moh Kahfi → Andara → Kemang → ASEAN → Senayan City → Palmerah → Grogol. Palmerah tidak di-snap ke KRL.",
        "insight": "Koridor panjang Jagakarsa–Grogol. Segmen Moh Kahfi berbagi geometry dengan CASTJ06-EXT tanpa di-merge. Palmerah tetap di garis GeoJSON, bukan stasiun KRL.",
        "bbox": bbox(geom),
    })
    old["geometry"] = {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in geom]}
    old["properties"] = props

    # replace CASTJ20 stops only
    kept = [f for f in stops_fc["features"] if f["properties"].get("route_id") != "CASTJ20"]
    for s in stps:
        kept.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["xy"][0], s["xy"][1]]},
            "properties": {
                "id": f"CASTJ20-{s['order']:02d}",
                "route_id": "CASTJ20",
                "corridor_id": "CASTJ20",
                "name": s["name"],
                "stop_name": s["name"],
                "stop_order": s["order"],
                "mode": "transjakarta",
                "status": "CASCADE_PROPOSED",
                "network_type": "CASCADE",
                "km": s["km"],
                "from_name": "Jagakarsa",
                "to_name": "Grogol Reformasi",
                "no_krl_snap": s["name"] == "Palmerah",
                "is_interchange": s["name"] in {"Jagakarsa", "ASEAN", "Grogol Reformasi", "Kemang", "Senayan City"},
            },
        })
    stops_fc["features"] = kept

    text_c = json.dumps(cand, ensure_ascii=False, separators=(",", ":"))
    text_s = json.dumps(stops_fc, ensure_ascii=False, separators=(",", ":"))
    (PUB / "cascade_candidates.geojson").write_text(text_c)
    (PUB / "cascade" / "cascade_candidates.geojson").write_text(text_c)
    (PUB / "cascade_stops.geojson").write_text(text_s)
    (PUB / "cascade" / "cascade_stops.geojson").write_text(text_s)

    after = {str(f.get("id")): f["geometry"]["coordinates"][0] for f in json.loads((PUB / "cascade_candidates.geojson").read_text())["features"] if str(f.get("id")) in {"CASTJ06-EXT", "CASTJ21"}}
    assert after["CASTJ06-EXT"] == before["CASTJ06-EXT"], "CASTJ06 mutated"
    assert after["CASTJ21"] == before["CASTJ21"], "CASTJ21 mutated"
    print("CASTJ06-EXT / CASTJ21 unchanged")
    print("OK CASTJ20", round(km, 2), "km", len(stps), "stops")


if __name__ == "__main__":
    main()
