#!/usr/bin/env python3
"""Rebuild CASCADE MRT geometry from the user TREKMRT.geojson.

id=1  → CAS-MRT-C01   Lebak Bulus – Ancol (3 QGIS parts joined)
id=2  → CAS-MRT-C01-E Kelapa Dua – Cibubur (cabang timur)
id=3  → CAS-MRT-C01-BR02 Ciputat – ICE BSD

Stations every 2 km, named from local kelurahan / known interchange.
Does NOT follow OSM roads — the QGIS digitised line is the trase.
Does NOT touch: masterplan, existing, CAS-TJ, CAS-LRT, CAS-MRT-C01-A, KRL-C03.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
TREK = ROOT / "attachments" / "TREKMRT.geojson"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-13"
SOURCE = "TREKMRT.geojson digitasi pengguna — usulan CASCADE, bukan masterplan, bukan MRT existing"
GAP_M = 2000.0

spec_m = importlib.util.spec_from_file_location("mrtb", ROOT / "scripts/rebuild-cascade-mrt.py")
mrtb = importlib.util.module_from_spec(spec_m)
spec_m.loader.exec_module(mrtb)

haversine = mrtb.haversine
length_m = mrtb.length_m
feat_line = mrtb.feat_line
feat_pt = mrtb.feat_pt
fc = mrtb.fc
densify_line = mrtb.densify_line
clean_chain = mrtb.clean_chain
bbox_of = mrtb.bbox_of
make_route_feature = mrtb.make_route_feature
make_stop_features = mrtb.make_stop_features
TJ_HASH = dict(mrtb.TJ_HASH)
LRT_HASH = dict(mrtb.LRT_HASH)
READONLY_FILES = dict(mrtb.READONLY_FILES)

FROZEN = {
    "CAS-MRT-C01-A": "ae3767b7fef3",
    "KRL-C03-N": "711afcad81d6",
    "KRL-C03-S": "c6ce84ce0d82",
}

NOTE_C01 = (
    "CAS-MRT-C01 mainline usulan CASCADE dari trase TREKMRT (digitasi pengguna). "
    "Lebak Bulus–Ciputat–Pamulang/Bojongsari–Sawangan–Depok Baru–Margonda–Kelapa Dua–Cijantung–Condet–PGC–"
    "Kampung Melayu–Matraman–Senen–Gunung Sahari–Ancol. "
    "Stasiun dipasang interval 2 km; nama = wilayah setempat terdekat. "
    "Bukan MRT existing. Bukan masterplan. Bukan DED."
)
NOTE_E = (
    "CAS-MRT-C01-E cabang timur usulan CASCADE dari trase TREKMRT: Kelapa Dua – Cimanggis – Cibubur. "
    "Bukan mainline Lebak Bulus–Ancol. Stasiun interval 2 km, nama wilayah setempat. Bukan masterplan."
)
NOTE_BR = (
    "CAS-MRT-C01-BR02 cabang Ciputat–Pamulang–Serpong–ICE BSD dari trase TREKMRT. "
    "Ciputat = node cabang mainline. Stasiun interval 2 km. Bukan masterplan. Bukan MRT existing."
)

KNOWN = [
    ("Lebak Bulus", 106.77493, -6.28930, "YES", "MRT", "TERMINUS"),
    ("Ciputat", 106.74720, -6.31250, "NO", "", "MAJOR_DESTINATION"),
    ("Pondok Cabe", 106.74700, -6.35400, "NO", "", "URBAN_NODE"),
    ("Parung Bingung", 106.74700, -6.40650, "NO", "", "URBAN_NODE"),
    ("Sawangan", 106.76372, -6.40019, "NO", "", "URBAN_NODE"),
    ("Depok Baru", 106.82169, -6.39113, "YES", "KRL", "MAJOR_TRANSIT"),
    ("Margonda", 106.83209, -6.36895, "NO", "", "COMMERCIAL"),
    ("Kelapa Dua", 106.84313, -6.36508, "NO", "", "URBAN_NODE"),
    ("Cijantung", 106.86191, -6.31215, "NO", "", "COMMERCIAL"),
    ("Condet", 106.85172, -6.27643, "NO", "", "URBAN_NODE"),
    ("PGC", 106.86570, -6.26190, "YES", "TransJakarta", "MAJOR_TRANSIT"),
    ("Kampung Melayu", 106.86682, -6.22467, "YES", "TransJakarta", "MAJOR_TRANSIT"),
    ("Matraman", 106.86070, -6.21212, "NO", "", "URBAN_NODE"),
    ("Senen", 106.84410, -6.17276, "YES", "KRL", "INTERCHANGE"),
    ("Gunung Sahari", 106.83800, -6.15000, "NO", "", "URBAN_NODE"),
    ("Ancol", 106.84646, -6.12786, "YES", "KRL", "TERMINUS"),
    ("Cibubur", 106.89500, -6.37000, "NO", "", "MAJOR_DESTINATION"),
    ("Harjamukti", 106.89000, -6.36500, "NO", "", "URBAN_NODE"),
    ("ICE BSD", 106.64100, -6.30100, "NO", "", "TERMINUS"),
    ("Rawa Buntu", 106.67505, -6.31551, "YES", "KRL", "INTERCHANGE"),
    ("Pamulang", 106.73800, -6.34300, "NO", "", "URBAN_NODE"),
    ("BSD CBD", 106.63657, -6.30068, "NO", "", "COMMERCIAL"),
    ("Jasin", 106.84400, -6.35500, "NO", "", "URBAN_NODE"),
    ("Jatijajar", 106.85500, -6.35500, "NO", "", "URBAN_NODE"),
    ("Cimanggis", 106.86800, -6.37200, "NO", "", "URBAN_NODE"),
    ("Tugu Cimanggis", 106.87000, -6.36500, "NO", "", "URBAN_NODE"),
]

GENERIC = {
    "Baru", "Depok", "Jakarta", "Tangerang", "Bogor", "Miami", "Indonesia",
    "Malaka Village", "Paradesa Cibubur", "Paradise Serpong City",
}


def geom_hash(coords):
    return hashlib.sha256(json.dumps(coords, separators=(",", ":")).encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def line_of(feat):
    g = feat["geometry"]
    if g["type"] == "LineString":
        return [list(p) for p in g["coordinates"]]
    return [list(p) for p in g["coordinates"][0]]


def join_c01(parts):
    """Reverse west trunk (Fatmawati/Lebak Bulus ← Depok) + Depok→Kelapa Dua + Kelapa Dua→Ancol."""
    west, east_short, east_long = parts
    chain = list(reversed(west))
    for nxt in (east_short, east_long):
        if haversine(chain[-1], nxt[0]) < 120:
            chain.extend(nxt[1:])
        else:
            chain.extend(nxt)
    return chain


def densify(coords, step=40.0):
    return densify_line(clean_chain(coords), step)


def cum_dist(coords):
    s = [0.0]
    for i in range(1, len(coords)):
        s.append(s[-1] + haversine(coords[i - 1], coords[i]))
    return s


def point_at(coords, s, dist):
    if dist <= 0:
        return list(coords[0])
    if dist >= s[-1]:
        return list(coords[-1])
    for i in range(1, len(s)):
        if s[i] >= dist:
            t = (dist - s[i - 1]) / (s[i] - s[i - 1] or 1)
            a, b = coords[i - 1], coords[i]
            return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    return list(coords[-1])


def load_wilayah():
    path = OUT / "wilayah_places.json"
    if path.exists():
        return json.loads(path.read_text())
    raw = Path("/tmp/osm_wilayah.json")
    if raw.exists():
        data = json.loads(raw.read_text())
        path.write_text(json.dumps(data, ensure_ascii=False))
        return data
    return []


def score_place(p, d):
    w = 0
    if p.get("p") == "suburb":
        w = 4
    elif p.get("p") == "quarter":
        w = 3.5
    elif p.get("p") == "village":
        w = 3
    elif p.get("p") == "neighbourhood":
        w = 1.5
    elif str(p.get("a")) == "8":
        w = 3.5
    elif str(p.get("a")) == "7":
        w = 2
    return w - d / 450.0


def nearest_wilayah(pt, wilayah, used, maxd=950.0):
    ranked = []
    for p in wilayah:
        name = p.get("n") or ""
        if not name or name in GENERIC or name in used:
            continue
        if any(k in name for k in ("RW ", "RT ", "Kantor", "Pos ", "Perumahan")):
            continue
        d = haversine(pt, (p["lon"], p["lat"]))
        if d > maxd:
            continue
        ranked.append((score_place(p, d), -d, name, d))
    ranked.sort(reverse=True)
    return ranked


def nearest_known(pt, used, maxd=520.0):
    best = None
    for rec in KNOWN:
        name = rec[0]
        if name in used:
            continue
        d = haversine(pt, (rec[1], rec[2]))
        if d <= maxd and (best is None or d < best[-1]):
            best = rec + (d,)
    return best


def name_station(pt, used, wilayah, termini_force=None):
    if termini_force:
        return {
            "stop_name": termini_force[0],
            "area_name": termini_force[0],
            "existing": termini_force[3],
            "interchange": "YES" if termini_force[3] == "YES" else "NO",
            "interchange_mode": termini_force[4],
            "node_type": termini_force[5],
            "name_confidence": "HIGH",
            "placement_reason": "TERMINUS",
        }
    known = nearest_known(pt, used, 720)
    if known:
        name, _x, _y, existing, mode, ntype, d = known
        return {
            "stop_name": name,
            "area_name": name,
            "existing": existing,
            "interchange": "YES" if existing == "YES" else "NO",
            "interchange_mode": mode,
            "node_type": ntype,
            "name_confidence": "HIGH" if d < 300 else "MEDIUM",
            "placement_reason": "INTERVAL_2KM",
            "snap_m": round(d, 1),
        }
    cand = nearest_wilayah(pt, wilayah, used, 900)
    if not cand:
        cand = nearest_wilayah(pt, wilayah, used, 1600)
    if cand:
        name, d = cand[0][2], cand[0][3]
        return {
            "stop_name": name,
            "area_name": name,
            "existing": "NO",
            "interchange": "NO",
            "interchange_mode": "",
            "node_type": "STATION",
            "name_confidence": "MEDIUM" if d < 700 else "LOW",
            "placement_reason": "INTERVAL_2KM",
            "snap_m": round(d, 1),
        }
    km = f"Km {len(used)}"
    return {
        "stop_name": km,
        "area_name": km,
        "existing": "NO",
        "interchange": "NO",
        "interchange_mode": "",
        "node_type": "STATION",
        "name_confidence": "LOW",
        "placement_reason": "INTERVAL_2KM",
    }


def place_every_2km(geom, wilayah, start_force=None, end_force=None):
    geom = densify(geom, 40)
    s = cum_dist(geom)
    total = s[-1]
    n = max(1, int(round(total / GAP_M)))
    used = set()
    stops = []
    for i in range(n + 1):
        dist = total if i == n else i * (total / n)
        pt = point_at(geom, s, dist)
        force = start_force if i == 0 else end_force if i == n else None
        rec = name_station(pt, used, wilayah, force)
        used.add(rec["stop_name"])
        rec.update(
            {
                "lon": pt[0],
                "lat": pt[1],
                "along_m": dist,
                "station_on_curve": "NO",
            }
        )
        stops.append(rec)
    stops[0]["lon"], stops[0]["lat"] = geom[0][0], geom[0][1]
    stops[0]["along_m"] = 0.0
    stops[0]["placement_reason"] = "TERMINUS"
    stops[-1]["lon"], stops[-1]["lat"] = geom[-1][0], geom[-1][1]
    stops[-1]["along_m"] = total
    stops[-1]["placement_reason"] = "TERMINUS"
    return geom, stops, total


def known_by_name(name):
    for rec in KNOWN:
        if rec[0] == name:
            return rec
    return None


def patch_stop_areas(feats, stops):
    by_id = {}
    for i, s in enumerate(stops):
        by_id[i] = s
    for i, f in enumerate(feats):
        s = stops[i]
        f["properties"]["area_name"] = s.get("area_name") or s["stop_name"]
        f["properties"]["placement_reason"] = s.get("placement_reason", "INTERVAL_2KM")
        f["properties"]["note"] = (
            "Stasiun usulan CASCADE MRT, interval 2 km pada trase TREKMRT. "
            "Nama = wilayah setempat terdekat. Bukan stasiun resmi."
        )
    return feats


def replace_mrt_keep_a(feats, new_feats):
    kept = []
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or "")
        rid = str(f["properties"].get("route_id") or "")
        if fid.startswith("CAS-MRT-C01-A") or rid.startswith("CAS-MRT-C01-A"):
            kept.append(f)
            continue
        if fid.startswith("CAS-MRT") or rid.startswith("CAS-MRT"):
            continue
        kept.append(f)
    return kept + new_feats


def main():
    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY DRIFT {fn} {got} != {expect}")
    print("readonly hashes OK")

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())
    before = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in old_routes["features"]}
    for k, h in TJ_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"TJ drifted: {k} {before.get(k)}")
    for k, h in LRT_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"LRT drifted: {k} {before.get(k)}")
    for k, h in FROZEN.items():
        if before.get(k) != h:
            raise SystemExit(f"FROZEN drifted: {k} {before.get(k)}")
    print("TJ+LRT+C01-A+KRL frozen OK")

    trek = json.loads(TREK.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TREK, OUT / "trek_mrt_user.geojson")
    wilayah = load_wilayah()
    print(f"wilayah gazetteer {len(wilayah)}")

    by_id = {}
    for f in trek["features"]:
        by_id.setdefault(int(f["properties"]["id"]), []).append(line_of(f))
    # id 1 has 3 parts in file order: east-short, east-long, west
    p1 = by_id[1]
    assert len(p1) == 3, len(p1)
    west, east_short, east_long = p1[2], p1[0], p1[1]
    c01_raw = join_c01([west, east_short, east_long])
    e_raw = by_id[2][0]
    br_raw = by_id[3][0]

    lb = known_by_name("Lebak Bulus")
    ancol = known_by_name("Ancol")
    kelapa = known_by_name("Kelapa Dua")
    cib = known_by_name("Cibubur")
    cip = known_by_name("Ciputat")
    ice = known_by_name("ICE BSD")

    geom_c01, st_c01, tot_c01 = place_every_2km(c01_raw, wilayah, start_force=lb, end_force=ancol)
    geom_e, st_e, tot_e = place_every_2km(e_raw, wilayah, start_force=kelapa, end_force=cib)
    geom_br, st_br, tot_br = place_every_2km(br_raw, wilayah, start_force=cip, end_force=ice)

    print(f"C01 {tot_c01/1000:.2f} km  {len(st_c01)} st  {' → '.join(s['stop_name'] for s in st_c01)}")
    print(f"E   {tot_e/1000:.2f} km  {len(st_e)} st  {' → '.join(s['stop_name'] for s in st_e)}")
    print(f"BR  {tot_br/1000:.2f} km  {len(st_br)} st  {' → '.join(s['stop_name'] for s in st_br)}")

    spec_c01 = dict(
        id="CAS-MRT-C01",
        name="Lebak Bulus – Ancol",
        short="Lebak Bulus – Ancol",
        from_name="Lebak Bulus",
        to_name="Ancol",
        direction="Lebak Bulus → Ancol",
        branch_id="MAIN",
        branch_name="Mainline Lebak Bulus – Ancol",
        parent_route="",
    )
    spec_e = dict(
        id="CAS-MRT-C01-E",
        name="Kelapa Dua – Cibubur",
        short="Kelapa Dua – Cibubur",
        from_name="Kelapa Dua",
        to_name="Cibubur",
        direction="Kelapa Dua → Cibubur",
        branch_id="E",
        branch_name="Cabang timur Kelapa Dua – Cibubur",
        parent_route="CAS-MRT-C01",
    )
    spec_br = dict(
        id="CAS-MRT-C01-BR02",
        name="Ciputat – Pamulang – BSD – ICE",
        short="Ciputat – ICE BSD",
        from_name="Ciputat",
        to_name="ICE BSD",
        direction="Ciputat → ICE BSD",
        branch_id="BR02",
        branch_name="Cabang Ciputat – ICE BSD",
        parent_route="CAS-MRT-C01",
    )

    rf1, km1 = make_route_feature(spec_c01, geom_c01, st_c01, len(c01_raw), "MEDIUM", "VIADUCT", ["TREKMRT id=1"], NOTE_C01, 20)
    rfE, kmE = make_route_feature(spec_e, geom_e, st_e, len(e_raw), "MEDIUM", "VIADUCT", ["TREKMRT id=2"], NOTE_E, 21)
    rfB, kmB = make_route_feature(spec_br, geom_br, st_br, len(br_raw), "MEDIUM", "VIADUCT", ["TREKMRT id=3"], NOTE_BR, 22)
    for rf, note in ((rf1, NOTE_C01), (rfE, NOTE_E), (rfB, NOTE_BR)):
        rf["properties"]["planning_note"] = note
        rf["properties"]["notes"] = note
        rf["properties"]["geometry_source"] = "TREKMRT.geojson digitasi pengguna (QGIS CRS84)"
        rf["properties"]["source"] = SOURCE

    sf1 = patch_stop_areas(make_stop_features(spec_c01, geom_c01, st_c01, "MEDIUM", "VIADUCT", ["TREKMRT id=1"], NOTE_C01, km1), st_c01)
    sfE = patch_stop_areas(make_stop_features(spec_e, geom_e, st_e, "MEDIUM", "VIADUCT", ["TREKMRT id=2"], NOTE_E, kmE), st_e)
    sfB = patch_stop_areas(make_stop_features(spec_br, geom_br, st_br, "MEDIUM", "VIADUCT", ["TREKMRT id=3"], NOTE_BR, kmB), st_br)
    for f in sf1 + sfE + sfB:
        f["properties"]["geometry_source"] = "TREKMRT.geojson + interval 2 km"
        f["properties"]["source"] = SOURCE

    route_feats = replace_mrt_keep_a(old_routes["features"], [rf1, rfE, rfB])
    stop_feats = replace_mrt_keep_a(old_stops["features"], sf1 + sfE + sfB)
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    for need in ("CAS-TJ07", "CAS-LRT-C02", "CAS-MRT-C01", "CAS-MRT-C01-A", "CAS-MRT-C01-BR02", "CAS-MRT-C01-E", "KRL-C03-N"):
        assert need in ids, f"missing {need}"

    after = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in TJ_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"TJ DRIFT {k}")
    for k, h in LRT_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"LRT DRIFT {k}")
    for k, h in FROZEN.items():
        if after.get(k) != h:
            raise SystemExit(f"FROZEN DRIFT {k}")
    assert after["CAS-MRT-C01-A"] == FROZEN["CAS-MRT-C01-A"]

    def meta_row(spec, km, n, geom, note):
        return {
            "id": spec["id"],
            "name": spec["name"],
            "short": spec["short"],
            "endpoint": f"{spec['from_name']} – {spec['to_name']}",
            "from_name": spec["from_name"],
            "to_name": spec["to_name"],
            "direction": spec["direction"],
            "mode": "mrt",
            "branch_id": spec["branch_id"],
            "length_km": km,
            "stop_count": n,
            "geometry_confidence": "MEDIUM",
            "source": SOURCE,
            "status": "PROPOSED",
            "network_type": "MRT" if spec["branch_id"] == "MAIN" else "BRANCH",
            "plan_type": "NEW_TRUNK",
            "alignment_type": "VIADUCT",
            "road_backbone": "Digitasi TREKMRT",
            "notes": note,
            "bbox": bbox_of(geom),
        }

    metas = [
        meta_row(spec_c01, km1, len(st_c01), geom_c01, NOTE_C01),
        meta_row(spec_e, kmE, len(st_e), geom_e, NOTE_E),
        meta_row(spec_br, kmB, len(st_br), geom_br, NOTE_BR),
    ]
    new_meta = []
    inserted = False
    for m in old_meta.get("corridors") or []:
        mid = str(m.get("id") or "")
        if mid.startswith("CAS-MRT") and mid != "CAS-MRT-C01-A":
            if not inserted:
                new_meta.extend(metas)
                inserted = True
            continue
        if mid == "CAS-MRT-C01-A":
            if not inserted:
                new_meta.extend(metas)
                inserted = True
            new_meta.append(m)
            continue
        new_meta.append(m)
    if not inserted:
        new_meta.extend(metas)

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["corridors"] = new_meta
    existing["mrt_note"] = (
        "CAS-MRT-C01 mainline Lebak Bulus–Ancol dari trase TREKMRT + cabang C01-E Kelapa Dua–Cibubur "
        "+ C01-A Sawangan–Fatmawati (tetap) + BR02 Ciputat–ICE BSD. Stasiun interval 2 km, nama wilayah setempat. "
        "Bukan MRT existing. Bukan masterplan."
    )
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
        if row.get("dataset") == "cascade_candidates":
            row["notes"] = (
                "CAS-TJ01..11 + CAS-LRT-C02/C04 + CAS-MRT-C01/A/E/BR02 + KRL-C03-N/S. "
                "MRT trase = TREKMRT.geojson; stasiun interval 2 km."
            )
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "source": "TREKMRT.geojson",
        "gap_m": GAP_M,
        "corridors": metas,
        "stops": {
            "CAS-MRT-C01": [s["stop_name"] for s in st_c01],
            "CAS-MRT-C01-E": [s["stop_name"] for s in st_e],
            "CAS-MRT-C01-BR02": [s["stop_name"] for s in st_br],
        },
        "km": {"CAS-MRT-C01": km1, "CAS-MRT-C01-E": kmE, "CAS-MRT-C01-BR02": kmB},
        "tj_frozen": TJ_HASH,
        "lrt_frozen": LRT_HASH,
        "frozen_other": FROZEN,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "hashes": {k: after[k] for k in ("CAS-MRT-C01", "CAS-MRT-C01-E", "CAS-MRT-C01-BR02", "CAS-MRT-C01-A")},
    }
    (OUT / "cascade_validation_mrt_trek.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))

    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"CAS-MRT-C01    {km1} km  {len(st_c01)} stasiun")
    print("  ", " → ".join(s["stop_name"] for s in st_c01))
    print(f"CAS-MRT-C01-E  {kmE} km  {len(st_e)} stasiun")
    print("  ", " → ".join(s["stop_name"] for s in st_e))
    print(f"CAS-MRT-C01-BR02 {kmB} km  {len(st_br)} stasiun")
    print("  ", " → ".join(s["stop_name"] for s in st_br))
    print("C01-A frozen  TJ/LRT/KRL/masterplan/existing untouched")


if __name__ == "__main__":
    main()
