#!/usr/bin/env python3
"""Rename CASTJ halte: no KM / Stop / Station / Name 2. Geometry untouched."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

PUB = Path("/workspace/public/data")
R = 6371000.0
BAD = re.compile(
    r"(^KM\b|\bKM\b|Stop\s*\d|Station\s*\d|Halte\s*\d|CASCADE\s*TJ|\d+\s*\+\s*\d+|\s+\d+$)",
    re.I,
)

KELURAHAN = [
    # Jakpus
    ("Petojo", 106.8170, -6.1701), ("Cideng", 106.8090, -6.1750), ("Kebon Kacang", 106.8115, -6.1870),
    ("Kebon Melati", 106.8140, -6.1920), ("Gondangdia", 106.8320, -6.1860), ("Menteng", 106.8310, -6.1960),
    ("Pegangsaan", 106.8430, -6.1980), ("Cikini", 106.8400, -6.1910), ("Kwitang", 106.8410, -6.1810),
    ("Senen", 106.8441, -6.1728), ("Kenari", 106.8500, -6.1930), ("Paseban", 106.8520, -6.1980),
    ("Karet Tengsin", 106.8150, -6.2050), ("Karet Kuningan", 106.8280, -6.2210), ("Kuningan Timur", 106.8310, -6.2300),
    ("Setiabudi", 106.8230, -6.2150), ("Guntur", 106.8380, -6.2080), ("Pasar Manggis", 106.8470, -6.2090),
    ("Menteng Dalam", 106.8450, -6.2180), ("Bukit Duri", 106.8580, -6.2200),
    # Jaksel
    ("Tebet Barat", 106.8500, -6.2260), ("Tebet Timur", 106.8580, -6.2260), ("Kebon Baru", 106.8600, -6.2350),
    ("Manggarai Selatan", 106.8520, -6.2150), ("Pancoran", 106.8440, -6.2430), ("Kalibata", 106.8450, -6.2570),
    ("Rawajati", 106.8550, -6.2550), ("Duren Tiga", 106.8350, -6.2550), ("Mampang Prapatan", 106.8250, -6.2450),
    ("Bangka", 106.8080, -6.2550), ("Pela Mampang", 106.8180, -6.2480), ("Tegal Parang", 106.8300, -6.2480),
    ("Kemang", 106.8135, -6.2605), ("Bangka", 106.8080, -6.2550), ("Cipete Utara", 106.8050, -6.2650),
    ("Cipete Selatan", 106.8050, -6.2750), ("Gandaria Utara", 106.7920, -6.2500), ("Kebayoran Baru", 106.8020, -6.2430),
    ("Melawai", 106.8050, -6.2430), ("Gunung", 106.8000, -6.2480), ("Rawa Barat", 106.7980, -6.2380),
    ("Senayan", 106.7973, -6.2272), ("Gelora", 106.8030, -6.2180), ("Grogol Utara", 106.7900, -6.2100),
    ("Grogol Selatan", 106.7850, -6.2250), ("Petogogan", 106.7980, -6.2450), ("Pulo", 106.7980, -6.2550),
    ("Cilandak Barat", 106.7900, -6.2900), ("Cilandak Timur", 106.8050, -6.2880), ("Pondok Labu", 106.7700, -6.3080),
    ("Lebak Bulus", 106.7749, -6.2893), ("Fatmawati", 106.7925, -6.2925), ("Ampera", 106.8150, -6.2930),
    ("TB Simatupang", 106.8300, -6.2970), ("Tanjung Barat", 106.8388, -6.3080), ("Jagakarsa", 106.8190, -6.3058),
    ("Ragunan", 106.8233, -6.3048), ("Lenteng Agung", 106.8330, -6.3330), ("Srengseng Sawah", 106.8300, -6.3400),
    ("Ciganjur", 106.8050, -6.3300), ("Cipedak", 106.8000, -6.3400), ("Pejaten Barat", 106.8380, -6.2770),
    ("Pejaten Timur", 106.8480, -6.2770), ("Pasar Minggu", 106.8448, -6.2817), ("Jati Padang", 106.8500, -6.2850),
    ("Kebagusan", 106.8380, -6.3000), ("Condet", 106.8517, -6.2764), ("Balekambang", 106.8580, -6.2830),
    ("Batu Ampar", 106.8620, -6.2780), ("Kampung Tengah", 106.8600, -6.2680),
    # Jaktim
    ("Pinang Ranti", 106.8863, -6.2911), ("Makasar", 106.8900, -6.2850), ("Halim", 106.8900, -6.2660),
    ("Kebon Pala", 106.8800, -6.2700), ("Cipinang Melayu", 106.9000, -6.2500), ("Halim Perdanakusuma", 106.8950, -6.2660),
    ("Kampung Rambutan", 106.8820, -6.3080), ("Dukuh", 106.9000, -6.3150), ("Kalisari", 106.8550, -6.3200),
    ("Cijantung", 106.8619, -6.3122), ("Pekayon", 106.8500, -6.3000), ("Pasar Rebo", 106.8636, -6.3089),
    ("Gedong", 106.8620, -6.3000), ("Baru", 106.8700, -6.2950), ("Cipayung", 106.9000, -6.3400),
    ("Munjul", 106.9200, -6.3550), ("Cilangkap", 106.9100, -6.3480), ("Setu", 106.9250, -6.3480),
    ("Bambu Apus", 106.9050, -6.3300), ("Lubang Buaya", 106.8950, -6.2950), ("Ceger", 106.9000, -6.3100),
    ("Ciracas", 106.8760, -6.3290), ("Cibubur", 106.8972, -6.3575), ("Harjamukti", 106.9000, -6.3480),
    ("Susukan", 106.8700, -6.3200), ("Kelapa Dua Wetan", 106.8800, -6.3400),
    ("Jatiwaringin", 106.9108, -6.2559), ("Pondok Gede", 106.9260, -6.2750), ("Jatibening", 106.9240, -6.2580),
    ("Jaticempaka", 106.9350, -6.2600), ("Jatimakmur", 106.9350, -6.2750), ("Jatiasih", 106.9430, -6.2850),
    ("Pondok Kopi", 106.9420, -6.2200), ("Duren Sawit", 106.9180, -6.2340), ("Pondok Bambu", 106.9100, -6.2400),
    ("Klender", 106.9100, -6.2150), ("Malaka Jaya", 106.9280, -6.2200), ("Malaka Sari", 106.9250, -6.2280),
    ("Pondok Kelapa", 106.9330, -6.2400), ("Pulo Gebang", 106.9527, -6.2127), ("Penggilingan", 106.9400, -6.1950),
    ("Cakung Barat", 106.9350, -6.1800), ("Cakung Timur", 106.9600, -6.1750), ("Ujung Menteng", 106.9550, -6.1900),
    ("Pulo Gadung", 106.9080, -6.1830), ("Kayu Putih", 106.8880, -6.1850), ("Rawamangun", 106.8880, -6.1950),
    ("Pisangan Timur", 106.8800, -6.2000), ("Cipinang", 106.8820, -6.2100), ("Jatinegara", 106.8680, -6.2200),
    ("Kampung Melayu", 106.8668, -6.2247), ("Bidara Cina", 106.8720, -6.2300), ("Cipinang Muara", 106.8900, -6.2250),
    ("Cipinang Cempedak", 106.8750, -6.2250), ("Otista", 106.8680, -6.2280), ("Bali Mester", 106.8620, -6.2200),
    ("Rawa Bunga", 106.8700, -6.2150), ("Cipinang Besar Selatan", 106.8850, -6.2200),
    ("Cipinang Besar Utara", 106.8850, -6.2080), ("Jati", 106.9000, -6.2050),
    ("Kayu Manis", 106.8600, -6.1850), ("Matraman", 106.8607, -6.2121), ("Pal Meriam", 106.8550, -6.2000),
    ("Utan Kayu Selatan", 106.8650, -6.2000), ("Utan Kayu Utara", 106.8680, -6.1950),
    ("Flyover Pondok Kopi", 106.9420, -6.2250), ("Buaran", 106.9280, -6.2150),
    ("Cawang", 106.8680, -6.2430), ("Cililitan", 106.8663, -6.2624), ("Kramat Jati", 106.8700, -6.2730),
    ("Batu Ampar Makasar", 106.8800, -6.2800), ("Trikora", 106.8655, -6.2622), ("PGC Cililitan", 106.8657, -6.2619),
    # Jakut
    ("Kelapa Gading Barat", 106.9000, -6.1600), ("Kelapa Gading Timur", 106.9150, -6.1570),
    ("Pegangsaan Dua", 106.9150, -6.1650), ("Sunter Jaya", 106.8700, -6.1470), ("Sunter Agung", 106.8600, -6.1400),
    ("Tanjung Priok", 106.8808, -6.1085), ("Kebon Bawang", 106.8900, -6.1150), ("Sungai Bambu", 106.8850, -6.1250),
    ("Papanggo", 106.8950, -6.1200), ("Warakas", 106.8900, -6.1300), ("Koja", 106.9038, -6.1085),
    ("Lagoa", 106.9100, -6.1080), ("Tugu Utara", 106.9200, -6.1150), ("Tugu Selatan", 106.9180, -6.1250),
    ("Rawa Badak Utara", 106.9050, -6.1200), ("Rawa Badak Selatan", 106.9000, -6.1280),
    ("Cilincing", 106.9400, -6.1080), ("Semper Barat", 106.9250, -6.1250), ("Semper Timur", 106.9350, -6.1250),
    ("Sukapura", 106.9250, -6.1350), ("Rorotan", 106.9400, -6.1400), ("Marunda", 106.9613, -6.0986),
    ("Marunda Center", 106.9613, -6.0986), ("Kalibaru", 106.9500, -6.1080),
    ("Ancol", 106.8300, -6.1270), ("Pademangan Barat", 106.8400, -6.1350), ("Pademangan Timur", 106.8500, -6.1330),
    # Jakbar
    ("Palmerah", 106.7940, -6.2070), ("Slipi", 106.7970, -6.1900), ("Kota Bambu Utara", 106.7880, -6.1880),
    ("Kota Bambu Selatan", 106.7900, -6.1950), ("Kemanggisan", 106.7850, -6.2000), ("Pal Merah", 106.7950, -6.2000),
    ("Jatipulo", 106.8000, -6.1780), ("Tomang", 106.7970, -6.1780), ("Grogol", 106.7894, -6.1665),
    ("Jelambar", 106.7860, -6.1665), ("Jelambar Baru", 106.7800, -6.1600), ("Wijaya Kusuma", 106.7750, -6.1550),
    ("Tanjung Duren Selatan", 106.7850, -6.1780), ("Tanjung Duren Utara", 106.7850, -6.1700),
    ("Duri Kepa", 106.7800, -6.1850), ("Kedoya Selatan", 106.7620, -6.1800),
    # Depok
    ("Beji", 106.8220, -6.3750), ("Kukusan", 106.8380, -6.3550), ("Tanah Baru", 106.8250, -6.3600),
    ("Kemiri Muka", 106.8300, -6.3700), ("Pondok Cina", 106.8440, -6.3680), ("Margonda", 106.8321, -6.3689),
    ("UI", 106.8331, -6.3602), ("Kelapa Dua Depok", 106.8431, -6.3651), ("Tugu Cimanggis", 106.8620, -6.3720),
    ("Cisalak", 106.8700, -6.3650), ("Mekarsari", 106.8680, -6.3500), ("Tapos", 106.8800, -6.3800),
    ("Cimanggis", 106.8620, -6.3720), ("Pasir Gunung Selatan", 106.8550, -6.3550),
    ("Tirtajaya", 106.8600, -6.3450), ("Cisalak Pasar", 106.8720, -6.3550),
    # Bekasi fringe
    ("Jatiwaringin Bekasi", 106.9180, -6.2580), ("Pondok Gede Timur", 106.9350, -6.2700),
    ("Jatibening Baru", 106.9280, -6.2500),
]


def hav(a, b):
    to = math.radians
    dlon = to(b[0] - a[0])
    dlat = to(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(to(a[1])) * math.cos(to(b[1])) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def load_transit_poi():
    pts = []
    for fname in ["transjakarta_stops.geojson", "mrt_stops.geojson", "lrt_stops.geojson", "krl_stops.geojson"]:
        try:
            fc = json.loads((PUB / fname).read_text())
        except Exception:
            continue
        for f in fc["features"]:
            if f["geometry"]["type"] != "Point":
                continue
            nm = f["properties"].get("name") or f["properties"].get("stop_name")
            if not nm:
                continue
            if re.search(r"\bKM\b|\s+\d+$", str(nm), re.I):
                continue
            xy = f["geometry"]["coordinates"][:2]
            pts.append((str(nm), float(xy[0]), float(xy[1])))
    return pts


def pick_name(xy, used, pool, max_m=3500):
    used_l = {u.lower() for u in used}
    ranked = sorted(((hav(xy, (x, y)), n) for n, x, y in pool), key=lambda t: t[0])
    for d, n in ranked:
        if n.lower() in used_l:
            continue
        if d <= max_m:
            return n, d
    # last resort: nearest unused even if farther, plus arah
    for d, n in ranked:
        if n.lower() not in used_l:
            suffix = "Timur" if xy[0] >= 106.9 else "Barat" if xy[0] < 106.8 else "Utara" if xy[1] > -6.2 else "Selatan"
            cand = f"{n} {suffix}"
            if cand.lower() not in used_l:
                return cand, d
            return n, d
    return None, None


def is_bad(name: str) -> bool:
    if not name:
        return True
    if BAD.search(name):
        return True
    if re.fullmatch(r"KM\s*\d+(\s+\d+)?", name, re.I):
        return True
    return False


def main():
    stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    poi = load_transit_poi()
    pool = KELURAHAN + poi
    used_global = []
    by_route = {}
    for f in stops["features"]:
        p = f["properties"]
        rid = str(p.get("route_id") or p.get("id") or "")
        if not rid.startswith("CASTJ"):
            continue
        by_route.setdefault(rid, []).append(f)

    changed = 0
    leftover = []
    for rid, feats in by_route.items():
        feats.sort(key=lambda f: f["properties"].get("stop_order") or 0)
        used = []
        for f in feats:
            p = f["properties"]
            name = str(p.get("name") or "")
            xy = tuple(f["geometry"]["coordinates"][:2])
            termini = {str(p.get("from_name") or ""), str(p.get("to_name") or "")}
            order = p.get("stop_order")
            is_end = order in (1, feats[-1]["properties"].get("stop_order"))
            if is_end and name and not is_bad(name):
                used.append(name)
                continue
            if not is_bad(name) and name not in used:
                used.append(name)
                continue
            new, dist = pick_name(xy, used + [n for n in termini if n != name], pool)
            if not new:
                leftover.append((rid, name, xy))
                continue
            print(f"  {rid:12} {name:18} → {new:22} ({int(dist)} m)")
            p["name"] = new
            p["stop_name"] = new
            p["local_area"] = new
            p["kelurahan"] = new
            p["name_source"] = "kelurahan_or_transit"
            used.append(new)
            changed += 1

    # second pass: any remaining KM
    for f in stops["features"]:
        p = f["properties"]
        rid = str(p.get("route_id") or "")
        if not rid.startswith("CASTJ"):
            continue
        if is_bad(str(p.get("name") or "")):
            xy = tuple(f["geometry"]["coordinates"][:2])
            used = [x["properties"]["name"] for x in by_route[rid]]
            new, dist = pick_name(xy, used, pool, 8000)
            if new:
                print(f"  PASS2 {rid:12} {p.get('name'):18} → {new}")
                p["name"] = p["stop_name"] = p["local_area"] = new
                p["kelurahan"] = new
                changed += 1
            else:
                leftover.append((rid, p.get("name"), xy))

    # write
    text = json.dumps(stops, ensure_ascii=False, separators=(",", ":"))
    (PUB / "cascade_stops.geojson").write_text(text)
    (PUB / "cascade" / "cascade_stops.geojson").write_text(text)

    print("\nCHANGED", changed)
    print("LEFTOVER", leftover)
    print("\nAUDIT")
    still = []
    for f in stops["features"]:
        p = f["properties"]
        rid = str(p.get("route_id") or "")
        if not rid.startswith("CASTJ"):
            continue
        n = str(p.get("name") or "")
        if is_bad(n):
            still.append((rid, n))
    if still:
        print("STILL BAD", still)
        raise SystemExit(1)
    for rid in sorted(by_route):
        names = [f["properties"]["name"] for f in sorted(by_route[rid], key=lambda x: x["properties"].get("stop_order") or 0)]
        print(rid, "→", ", ".join(names))


if __name__ == "__main__":
    main()
