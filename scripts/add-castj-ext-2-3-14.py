#!/usr/bin/env python3
"""Additive TJ extensions 2/3/14 from user GeoJSON. Do not mutate CASTJ06–26."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
ATT = ROOT / "attachments"

spec = importlib.util.spec_from_file_location("add22", ROOT / "scripts/add-castj22-26.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

OLD_IDS = {
    "CASTJ06-EXT", "CASTJ07-EXT", "CASTJ15", "CASTJ16", "CASTJ17", "CASTJ18",
    "CASTJ19", "CASTJ20", "CASTJ21", "CASTJ22", "CASTJ23", "CASTJ24", "CASTJ25", "CASTJ26",
}

SPECS = [
    dict(
        id="CASTJ03-EXT",
        file="PERPANJANGAN KORIDOR 3 ARAH BANDARA 3B.geojson",
        name="Perpanjangan Koridor 3 – Arah Bandara",
        from_name="Kalideres", to_name="Bandara Soekarno-Hatta", route_order=54,
        parent_corridor="TJ-03",
        parent_label="Koridor 3",
        status_label="Usulan CASCADE · perpanjangan Koridor 3",
        plan_type="EXTENSION",
        forced=[
            ("Kalideres", (106.70587, -6.15464)),
            ("Kamal", (106.67586, -6.16395)),
            ("Bandara Soekarno-Hatta", (106.66506, -6.12046)),
        ],
        widening_level="HIGH", widening_km=5,
        widening_reason="Kalideres–Kamal–akses bandara mixed traffic, ROW terbatas di ruas pergudangan.",
        widening_cost_label="Rp 0,18–0,48 T", cost_label="Rp 0,6–1,4 T",
        note="Ekstensi Koridor 3 dari Kalideres ke arah Bandara. Geometry 100% GeoJSON user. Bukan pengganti Koridor 3 existing.",
        insight="Perpanjangan Koridor 3 Kalideres–Bandara. Shared node di Kalideres jika berimpit dengan TJ 3. Geometry tidak digeser.",
    ),
    dict(
        id="CASTJ02-EXT",
        file="PERPANJANGAN KORIDOR 2 ARAH HARAPAN INDAH.geojson",
        name="Perpanjangan Koridor 2 – Arah Harapan Indah",
        from_name="Pulo Gadung", to_name="Harapan Indah", route_order=55,
        parent_corridor="TJ-02",
        parent_label="Koridor 2",
        status_label="Usulan CASCADE · perpanjangan Koridor 2",
        plan_type="EXTENSION",
        forced=[
            ("Pulo Gadung", (106.90885, -6.18327)),
            ("Cakung", (106.94732, -6.18514)),
            ("Harapan Indah", (106.97578, -6.15228)),
        ],
        widening_level="MODERATE", widening_km=4,
        widening_reason="Cakung–Ujung Menteng–Harapan Indah arterial Bekasi, lajur BRT perlu pengamanan.",
        widening_cost_label="Rp 0,12–0,32 T", cost_label="Rp 0,5–1,1 T",
        note="Ekstensi Koridor 2 Pulo Gadung–Harapan Indah. Bukan pengganti 2B existing. Geometry dari GeoJSON.",
        insight="Perpanjangan Koridor 2 ke Harapan Indah. Shared Pulo Gadung jika spasial bertemu. Tidak menimpa rute 2B.",
    ),
    dict(
        id="CASTJ14-EXT",
        file="PERPANJANGAN KORIDOR 14 JIS-MARUNDA (VIA CILINCING).geojson",
        name="Perpanjangan Koridor 14 – JIS–Marunda via Cilincing",
        from_name="JIS", to_name="Marunda", route_order=56,
        parent_corridor="TJ-14",
        parent_label="Koridor 14",
        status_label="Usulan CASCADE · perpanjangan Koridor 14",
        plan_type="EXTENSION",
        forced=[
            ("JIS", (106.85714, -6.12648)),
            ("Cilincing", (106.92707, -6.10693)),
            ("Marunda", (106.96129, -6.09613)),
        ],
        widening_level="HIGH", widening_km=6,
        widening_reason="Cilincing–Marunda pesisir utara, mixed truck/BRT, ROW sempit di ruas industri.",
        widening_cost_label="Rp 0,20–0,50 T", cost_label="Rp 0,7–1,5 T",
        note="Ekstensi Koridor 14 JIS–Marunda via Cilincing. Geometry 100% GeoJSON. Parent JIS–Senen tidak diubah.",
        insight="Perpanjangan Koridor 14 dari JIS ke Marunda lewat Cilincing. Shared JIS jika berimpit. Endpoint GeoJSON tidak dipanjangkan.",
    ),
]

EXTRA_LOCAL = [
    ("Kalideres", 106.70587, -6.15464), ("Kamal", 106.67586, -6.16395),
    ("Tegal Alur", 106.69431, -6.15957), ("Cengkareng Barat", 106.68886, -6.15979),
    ("Rawa Bokor", 106.68214, -6.16143), ("Benda", 106.66601, -6.16340),
    ("Jatake", 106.65847, -6.16366), ("Neglasari", 106.65356, -6.17141),
    ("Selapajang", 106.65307, -6.18241), ("Kedaung Wetan", 106.66103, -6.15753),
    ("Benda Baru", 106.66424, -6.14192), ("Pajang", 106.67536, -6.13797),
    ("Bandara Soekarno-Hatta", 106.66506, -6.12046), ("Soetta", 106.66506, -6.12046),
    ("P3", 106.68191, -6.11547), ("Cargo Bandara", 106.67825, -6.11699),
    ("Pulo Gadung", 106.90885, -6.18327), ("Kayu Putih", 106.91220, -6.18281),
    ("Jatinegara Kaum", 106.91717, -6.18277), ("Pulo Gebang", 106.93264, -6.18295),
    ("Cakung", 106.94732, -6.18514), ("Ujung Menteng", 106.96218, -6.18825),
    ("Medan Satria", 106.96968, -6.19126), ("Pejuang", 106.97277, -6.19398),
    ("Harapan Jaya", 106.97515, -6.19253), ("Harapan Mulya", 106.97510, -6.18617),
    ("Harapan Indah", 106.97578, -6.15228), ("Kaliabang", 106.97467, -6.16478),
    ("JIS", 106.85714, -6.12648), ("Tanjung Priok", 106.88045, -6.10975),
    ("Koja", 106.88744, -6.10995), ("Lagoa", 106.90023, -6.10800),
    ("Cilincing", 106.92707, -6.10693), ("Marunda", 106.96129, -6.09613),
    ("Rorotan", 106.94125, -6.10605), ("Semper", 106.92156, -6.10818),
    ("Kalibaru", 106.91000, -6.10880), ("Sungai Bambu", 106.87510, -6.11264),
    ("Papanggo", 106.87326, -6.11423), ("Warakas", 106.86124, -6.12146),
    ("Marunda Center", 106.95615, -6.10927), ("Marunda Baru", 106.9600, -6.1040),
    ("Pintu Selatan Bandara", 106.67890, -6.11672),
]


def main():
    m.LOCAL.extend(EXTRA_LOCAL)
    m.EXISTING = m.load_existing()
    cand = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops_fc = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text())
    freeze = {str(f.get("id")): json.dumps(f["geometry"]) for f in cand["features"] if str(f.get("id")) in OLD_IDS}
    freeze_stops = sum(1 for f in stops_fc["features"] if str(f["properties"].get("route_id")) in OLD_IDS)

    new_ids = {s["id"] for s in SPECS}
    cand["features"] = [f for f in cand["features"] if str(f.get("id")) not in new_ids]
    stops_fc["features"] = [f for f in stops_fc["features"] if str(f["properties"].get("route_id")) not in new_ids]
    meta["corridors"] = [c for c in meta.get("corridors", []) if str(c.get("id")) not in new_ids]

    reserved = (
        {s["from_name"] for s in SPECS} | {s["to_name"] for s in SPECS}
        | {"Harmoni", "Senen", "Monas", "Blok M", "Grogol", "Cengkareng Business City", "Harapan Indah"}
    )

    for spec in SPECS:
        raw = m.load_line(ATT / spec["file"])
        raw_km = m.length_m(raw) / 1000
        geom = m.densify(m.chaikin_sharp(raw), 55)
        assert abs(geom[0][0] - raw[0][0]) < 1e-8
        assert abs(geom[-1][0] - raw[-1][0]) < 1e-8
        geom, stps = m.stations(
            geom, spec["forced"], spec["from_name"], spec["to_name"], reserved=reserved,
        )
        used_n = [s["name"] for s in stps]
        for s in stps[1:-1]:
            if s["name"] in {spec["to_name"], spec["from_name"]}:
                alt = m.local_name((s["xy"][0] + 0.006, s["xy"][1]), used_n)
                if alt and alt not in used_n:
                    used_n[used_n.index(s["name"])] = alt
                    s["name"] = alt
        km = m.length_m(geom) / 1000
        print(spec["id"], f"raw {raw_km:.2f} display {km:.2f}", [s["name"] for s in stps])
        assert not any(x["name"].upper().startswith("KM") for x in stps)
        props = m.props_of(spec, km, len(stps), len(geom), geom)
        props["parent_corridor"] = spec["parent_corridor"]
        props["parent_route"] = spec.get("parent_label") or spec["parent_corridor"]
        props["plan_type"] = "EXTENSION"
        props["status_label"] = spec["status_label"]
        props["corridor_type"] = "TJ_EXTENSION"
        cand["features"].append({
            "type": "Feature",
            "id": spec["id"],
            "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in geom]},
            "properties": props,
        })
        n = len(stps)
        for s in stps:
            p = dict(props)
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
            "plan_type": "EXTENSION",
            "bbox": m.bbox_of(geom),
            "widening_level": spec["widening_level"],
            "widening_cost_label": spec["widening_cost_label"],
            "elevated_km": 0,
            "cost_label": spec["cost_label"],
            "insight": spec["insight"],
            "parent_corridor": spec["parent_corridor"],
        })

    after = {str(f.get("id")): json.dumps(f["geometry"]) for f in cand["features"] if str(f.get("id")) in OLD_IDS}
    assert after == freeze, "old CASTJ geometry mutated"
    after_stops = sum(1 for f in stops_fc["features"] if str(f["properties"].get("route_id")) in OLD_IDS)
    assert after_stops == freeze_stops, "old CASTJ stops mutated"

    m.write_both("cascade_candidates.geojson", cand)
    m.write_both("cascade_stops.geojson", stops_fc)
    m.write_both("cascade_existing.json", meta)
    print("FROZEN", len(OLD_IDS), "NEW", [s["id"] for s in SPECS])
    print("routes", len(cand["features"]), "stops", len(stops_fc["features"]))


if __name__ == "__main__":
    main()
