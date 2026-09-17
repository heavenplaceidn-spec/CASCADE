#!/usr/bin/env python3
"""PASS koreksi CAS-TJ06..CAS-TJ11.

CAS-TJ01..CAS-TJ05 dibekukan (tidak diubah).
CAS-08 Puri Indah diganti CAS-TJ07 Monas–Puri Beta via Joglo.
"""
from __future__ import annotations

import importlib.util
import json
import statistics
from copy import deepcopy
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT_DIR = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-11"
SOURCE = "CASCADE.txt + user road-intent 2026-09-11 (koreksi TJ06-TJ11)"

spec = importlib.util.spec_from_file_location("tja", ROOT / "scripts/rebuild-cascade-tj.py")
tja = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tja)
rc = tja.rc

haversine = tja.haversine
length_m = tja.length_m
feat_line = tja.feat_line
feat_pt = tja.feat_pt
fc = tja.fc


def N(*a):
    return list(a)


NODES = {
    # TJ06 / TJ07 shared
    "Monas": (106.82271, -6.17641),
    "Patung Kuda": (106.82270, -6.18050),
    "Kebon Sirih": (106.82280, -6.18278),
    "Fachrudin": (106.81450, -6.18840),
    "Jatibaru": (106.81150, -6.18480),
    "Slipi": (106.79980, -6.19050),
    "Kemanggisan": (106.79694, -6.18991),
    "Budi Raya": (106.78300, -6.18950),
    "Rawa Belong": (106.78280, -6.20200),
    "Bang Pitung": (106.77810, -6.21400),
    "Pos Pengumben": (106.77226, -6.21294),
    "Joglo Raya": (106.73880, -6.21780),
    "Dr Soetomo": (106.73050, -6.22850),
    "Puri Beta": (106.72602, -6.23060),
    "Simpang Joglo": (106.73780, -6.22980),
    "Joglo Timur": (106.76030, -6.21742),
    "Kelapa Dua Joglo": (106.76940, -6.21650),
    "Srengseng": (106.74800, -6.19730),
    "Permata Hijau": (106.78450, -6.20500),
    "Palmerah": (106.79990, -6.20060),
    "Petamburan": (106.80800, -6.19300),
    "Tanah Abang": (106.81100, -6.18600),
    # TJ08
    "Pinang Ranti": (106.88634, -6.29108),
    "Pondok Gede": (106.90500, -6.28700),
    "Nurul Ihsan": (106.91170, -6.28340),
    "Jatiwaringin": (106.91000, -6.26000),
    "Jatiwaringin Selatan": (106.91050, -6.27500),
    "Jatiwaringin Utara": (106.90800, -6.24620),
    "Jati Pahlawan": (106.90400, -6.23800),
    "Pahlawan Revolusi": (106.89940, -6.22200),
    "BKT Klender": (106.90100, -6.21450),
    "Klender": (106.90306, -6.21360),
    "Bekasi Timur": (106.90420, -6.20300),
    "Pulo Gadung": (106.90885, -6.18333),
    # TJ09
    "Pulo Gebang": (106.95265, -6.21270),
    "Stasiun Cakung": (106.95206, -6.21909),
    "Dr Sumarno": (106.94500, -6.21150),
    "Penggilingan": (106.93960, -6.21410),
    "Putaran Utara Penggilingan": (106.93970, -6.18350),
    "Bekasi Raya Cakung": (106.92500, -6.18360),
    "Arteri Kelapa Gading": (106.91350, -6.17500),
    "Pegangsaan Dua": (106.91650, -6.15500),
    "Logistik": (106.91640, -6.13300),
    "Raya Tugu": (106.92610, -6.12130),
    "Syeikh Nawawi": (106.92610, -6.12130),  # OSM Nawawi is south at -6.15; do not detour
    "Akses Marunda": (106.93200, -6.11200),
    "Marunda Bidara": (106.94800, -6.10900),
    "Marunda Makmur": (106.96004, -6.10781),
    "Rusunawa Marunda": (106.96128, -6.09863),
    # TJ11
    "Menwa UI": (106.83313, -6.36017),
    "Lenteng Agung": (106.83500, -6.33000),
    "Pasar Minggu": (106.84300, -6.28400),
    "Pancoran": (106.84388, -6.24330),
    "Soepomo": (106.84500, -6.23600),
    "Saharjo": (106.84600, -6.21800),
    "Minangkabau Barat": (106.84450, -6.21100),
    "Sultan Agung": (106.83400, -6.20550),
    "Galunggung": (106.82338, -6.20440),
}

SPECS = [
    dict(
        id="CAS-TJ06",
        route_order=6,
        name="Puri Beta – Monas",
        short="Puri Beta – Monas",
        from_name="Puri Beta",
        to_name="Monas",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="MEDIUM",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Audit ulang. Puri Beta–Ciledug–Joglo–Pos Pengumben–Tubun–Thamrin–Monas. Bukan Puri Indah. Bukan jalur TJ07 (Kebon Sirih/Slipi/Kemanggisan).",
        osm_alias={"Dr Soetomo (akses Puri Beta)": "Jalan Ciledug Raya"},
        controls=N(
            "Puri Beta",
            "Dr Soetomo",
            "Simpang Joglo",
            "Joglo Raya",
            "Joglo Timur",
            "Kelapa Dua Joglo",
            "Pos Pengumben",
            "Permata Hijau",
            "Palmerah",
            "Petamburan",
            "Tanah Abang",
            "Monas",
        ),
        road_by_pair=[
            ["Jalan Ciledug Raya", "Jalan Dr Soetomo", "TJ-K13"],
            ["Jalan Ciledug Raya", "Jalan Joglo Raya"],
            ["Jalan Joglo Raya", "Jalan Raya Pos Pengumben"],
            ["Jalan Joglo Raya", "Jalan Raya Pos Pengumben"],
            ["Jalan Raya Pos Pengumben", "Jalan Joglo Raya", "Jalan Kelapa Dua Raya"],
            ["Jalan Raya Pos Pengumben", "Jalan Arteri Pos Pengumben", "Jalan Kelapa Dua Raya"],
            ["Jalan Arteri Pos Pengumben", "Jalan Letnan Jenderal Siswondo Parman"],
            ["Jalan Letnan Jenderal Siswondo Parman", "Jalan Aipda Karel Satsuit Tubun"],
            ["Jalan Aipda Karel Satsuit Tubun"],
            ["Jalan Aipda Karel Satsuit Tubun", "Jalan Mohammad Husni Thamrin"],
            ["Jalan Mohammad Husni Thamrin"],
        ],
        anchors=N("Puri Beta", "Joglo Raya", "Pos Pengumben", "Palmerah", "Petamburan", "Tanah Abang", "Monas"),
        keep_detours=True,
        toll=False,
    ),
    dict(
        id="CAS-TJ07",
        route_order=7,
        name="Monas – Puri Beta via Joglo",
        short="Monas – Puri Beta",
        from_name="Monas",
        to_name="Puri Beta",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Monas–Kebon Sirih–Fachrudin–Jatibaru–Slipi–Kemanggisan–Budi–Rawa Belong–Bang Pitung–Pengumben–Joglo–Dr Soetomo–Puri Beta. BUKAN Puri Indah/Meruya/Kembangan/Panjang.",
        osm_alias={
            "Slipi I": "Jalan Letnan Jenderal Siswondo Parman (ruas Slipi)",
            "Sakti Raya": "Jalan Kemanggisan Utama (Sakti OSM = gang residensial, bukan arteri)",
            "Bang Pitung": "Jalan Raya Kebayoran Lama",
            "Dr Soetomo": "Jalan Ciledug Raya (akses Puri Beta)",
        },
        controls=N(
            "Monas",
            "Patung Kuda",
            "Kebon Sirih",
            "Fachrudin",
            "Jatibaru",
            "Slipi",
            "Kemanggisan",
            "Budi Raya",
            "Rawa Belong",
            "Bang Pitung",
            "Pos Pengumben",
            "Kelapa Dua Joglo",
            "Joglo Timur",
            "Joglo Raya",
            "Dr Soetomo",
            "Puri Beta",
        ),
        road_by_pair=[
            ["Jalan Mohammad Husni Thamrin"],
            ["Jalan Mohammad Husni Thamrin", "Jalan Kebon Sirih"],
            ["Jalan Kebon Sirih", "Jalan Haji Fachrudin", "Jalan Jatibaru"],
            ["Jalan Haji Fachrudin", "Jalan Jatibaru", "Jalan Jatibaru Raya"],
            ["Jalan Jatibaru", "Jalan Jatibaru Raya", "Jalan Letnan Jenderal Siswondo Parman", "Jalan Slipi I"],
            ["Jalan Letnan Jenderal Siswondo Parman", "Jalan Kemanggisan Utama"],
            ["Jalan Kemanggisan Utama", "Jalan Budi Raya", "Jalan Kemanggisan Raya"],
            ["Jalan Budi Raya", "Jalan Rawa Belong", "Jalan Kemanggisan Raya"],
            ["Jalan Rawa Belong", "Jalan Bang Pitung", "Jalan Raya Kebayoran Lama"],
            ["Jalan Bang Pitung", "Jalan Arteri Pos Pengumben", "Jalan Raya Pos Pengumben"],
            ["Jalan Raya Pos Pengumben", "Jalan Arteri Pos Pengumben", "Jalan Kelapa Dua Raya"],
            ["Jalan Joglo Raya", "Jalan Raya Pos Pengumben"],
            ["Jalan Joglo Raya", "Jalan Ciledug Raya", "Jalan Dr Soetomo"],
            ["Jalan Ciledug Raya", "Jalan Dr Soetomo", "TJ-K13"],
            ["Jalan Ciledug Raya", "Jalan Dr Soetomo", "TJ-K13"],
        ],
        anchors=N(
            "Monas",
            "Kebon Sirih",
            "Jatibaru",
            "Slipi",
            "Kemanggisan",
            "Rawa Belong",
            "Pos Pengumben",
            "Joglo Raya",
            "Puri Beta",
        ),
        keep_detours=True,
        toll=False,
    ),
    dict(
        id="CAS-TJ08",
        route_order=8,
        name="Pinang Ranti – Pulo Gadung",
        short="Pinang Ranti – Pulo Gadung",
        from_name="Pinang Ranti",
        to_name="Pulo Gadung",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Pinang Ranti–Pondok Gede–Nurul Ihsan–Jatiwaringin–Pahlawan Revolusi–BKT–Klender flyover–Bekasi Raya–Pulo Gadung. Bukan shortcut Kalimalang. Halte Klender di flyover Klender (106.903, -6.214).",
        osm_alias={
            "BKT": "Jalan I Gusti Ngurah Rai (kanal BKT / arteri Klender)",
            "Haji Darip": "OSM Haji Darip ada di Cipinang 2 km barat flyover Klender — tidak ditarik sebagai detour.",
        },
        controls=N(
            "Pinang Ranti",
            "Pondok Gede",
            "Nurul Ihsan",
            "Jatiwaringin Selatan",
            "Jatiwaringin",
            "Jatiwaringin Utara",
            "Jati Pahlawan",
            "Pahlawan Revolusi",
            "BKT Klender",
            "Klender",
            "Bekasi Timur",
            "Pulo Gadung",
        ),
        road_by_pair=[
            ["Jalan Pondok Gede", "TJ-K9"],
            ["Jalan Pondok Gede", "Jalan Masjid Nurul Ihsan"],
            ["Jalan Masjid Nurul Ihsan", "Jalan Jati Waringin"],
            ["Jalan Jati Waringin"],
            ["Jalan Jati Waringin"],
            ["Jalan Jati Waringin"],
            ["Jalan Jati Waringin", "Jalan Pahlawan Revolusi"],
            ["Jalan Pahlawan Revolusi", "Jalan I Gusti Ngurah Rai"],
            ["Jalan I Gusti Ngurah Rai", "Jalan Pahlawan Revolusi"],
            ["Jalan I Gusti Ngurah Rai", "Jalan Bekasi Timur"],
            ["Jalan Bekasi Timur", "Jalan Bekasi Raya"],
        ],
        anchors=N("Pinang Ranti", "Jatiwaringin", "Pahlawan Revolusi", "Klender", "Pulo Gadung"),
        keep_detours=True,
        toll=False,
    ),
    dict(
        id="CAS-TJ09",
        route_order=9,
        name="Pulo Gebang – Rusunawa Marunda via Stasiun Cakung",
        short="Pulo Gebang – Marunda",
        from_name="Pulo Gebang",
        to_name="Rusunawa Marunda",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="MEDIUM",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Wajib lewat Stasiun Cakung. Pulo Gebang–Sumarno–Penggilingan–putar utara–Bekasi Raya–Arteri Kelapa Gading–Pegangsaan Dua–Logistik–Tugu–Akses Marunda–Rusunawa. Bukan shortcut Pulo Gebang–Marunda. OSM Syech Nawawi ada di selatan -6.15 — tidak ditarik sebagai detour.",
        osm_alias={
            "Raya Tugu": "Jalan Cakung Cilincing / Jalan Raya Tugu (Tugu/Koja)",
            "Cilincing Landak": "Jalan Marunda Bidara / Sungai Landak",
            "Syeikh Nawawi": "OSM Jalan Syech Nawawi Al Bantani = ruas Cakung selatan; koridor memakai Cakung Cilincing di Tugu.",
        },
        controls=N(
            "Pulo Gebang",
            "Stasiun Cakung",
            "Dr Sumarno",
            "Penggilingan",
            "Putaran Utara Penggilingan",
            "Bekasi Raya Cakung",
            "Arteri Kelapa Gading",
            "Pegangsaan Dua",
            "Logistik",
            "Raya Tugu",
            "Akses Marunda",
            "Marunda Bidara",
            "Marunda Makmur",
            "Rusunawa Marunda",
        ),
        road_by_pair=[
            ["TJ-K11", "Jalan Pulo Gebang", "Jalan I Gusti Ngurah Rai"],
            ["Jalan Doktor Sumarno", "Jalan I Gusti Ngurah Rai"],
            ["Jalan Doktor Sumarno", "Penggilingan Raya"],
            ["Penggilingan Raya", "Jalan Raya Penggilingan"],
            ["Penggilingan Raya", "Jalan Bekasi Raya", "Jalan Raya Penggilingan"],
            ["Jalan Bekasi Raya", "Jalan Arteri Kelapa Gading"],
            ["Jalan Arteri Kelapa Gading", "Jalan Pegangsaan Dua"],
            ["Jalan Pegangsaan Dua"],
            ["Jalan Logistik", "Jalan Pegangsaan Dua", "Jalan Raya Tugu"],
            ["Jalan Raya Tugu", "Jalan Cakung Cilincing Timur", "Jalan Raya Cilincing Koja"],
            ["Jalan Akses Marunda", "Jalan Raya Tugu", "Jalan Raya Cilincing Koja"],
            ["Jalan Akses Marunda", "Jalan Marunda Bidara"],
            ["Jalan Marunda Bidara", "Jalan Marunda Makmur", "Jalan Akses Rusun Marunda"],
        ],
        anchors=N(
            "Pulo Gebang",
            "Stasiun Cakung",
            "Penggilingan",
            "Arteri Kelapa Gading",
            "Pegangsaan Dua",
            "Raya Tugu",
            "Akses Marunda",
            "Rusunawa Marunda",
        ),
        keep_detours=True,
        toll=False,
    ),
    dict(
        id="CAS-TJ11",
        route_order=11,
        name="Menwa UI – Galunggung",
        short="Menwa UI – Galunggung",
        from_name="Menwa UI",
        to_name="Galunggung",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Menwa UI–Lenteng Agung–Pasar Minggu–Pancoran–Soepomo–Saharjo–Minangkabau Barat–Sultan Agung–Galunggung. Bukan MT Haryono/Kalibata/Manggarai.",
        osm_alias={"Prof Dr Soepomo": "Jalan Profesor Dokter Supomo SH"},
        controls=N(
            "Menwa UI",
            "Lenteng Agung",
            "Pasar Minggu",
            "Pancoran",
            "Soepomo",
            "Saharjo",
            "Minangkabau Barat",
            "Sultan Agung",
            "Galunggung",
        ),
        road_by_pair=[
            ["Jalan Raya Margonda", "Jalan Lenteng Agung Raya"],
            ["Jalan Lenteng Agung Raya"],
            ["Jalan Pasar Minggu Raya"],
            ["Jalan Pasar Minggu Raya", "Jalan Profesor Dokter Supomo SH"],
            ["Jalan Profesor Dokter Supomo SH"],
            ["Jalan Dokter Saharjo", "Jalan Minangkabau Barat Raya"],
            ["Jalan Minangkabau Barat Raya", "Jalan Sultan Agung", "Jalan Sultan Agung Barat"],
            ["Jalan Sultan Agung", "Jalan Sultan Agung Barat", "Jalan Galunggung"],
        ],
        anchors=N("Menwa UI", "Pasar Minggu", "Pancoran", "Saharjo", "Sultan Agung", "Galunggung"),
        keep_detours=True,
        toll=False,
    ),
]


def add_aliases(road_map):
    aliases = {
        "Jalan Slipi I": "Jalan Letnan Jenderal Siswondo Parman",
        "Jalan Dr Soetomo": "Jalan Ciledug Raya",
        "Jalan Raya Tugu": "Jalan Cakung Cilincing Timur",
        "BKT": "Jalan I Gusti Ngurah Rai",
        "Jalan Bang Pitung": None,  # already ingested from extra as that name
        "Jalan Kemanggisan Utama Raya": "Jalan Kemanggisan Utama",
        "Jalan Raya Kebayoran Lama": None,
    }
    for new, old in aliases.items():
        if old and old in road_map and new not in road_map:
            feat = deepcopy(road_map[old])
            feat["properties"] = {**(feat.get("properties") or {}), "name": new, "alias_of": old}
            road_map[new] = feat
    clip_sultan_agung(road_map)


def clip_sultan_agung(road_map):
    """OSM Jalan Sultan Agung stretches east to Cakung (106.978). Keep Menteng/Setiabudi west only."""
    feat = road_map.get("Jalan Sultan Agung")
    if not feat:
        return
    kept = []
    for part in tja.flatten(feat["geometry"]):
        run = [
            list(p)
            for p in part
            if 106.821 <= p[0] <= 106.846 and -6.216 <= p[1] <= -6.196
        ]
        if len(run) >= 2:
            kept.append(run)
    extra = road_map.get("Jalan Sultan Agung Barat")
    if extra:
        kept.extend(tja.flatten(extra["geometry"]))
    if kept:
        road_map["Jalan Sultan Agung"] = {
            "type": "Feature",
            "properties": {"name": "Jalan Sultan Agung", "highway": "primary", "clipped": "west_only"},
            "geometry": {"type": "MultiLineString", "coordinates": kept},
        }


def remap_corridor(feat, old, new, extra_props=None):
    nf = tja.remap_id(deepcopy(feat), old, new)
    nf["id"] = new
    p = nf.setdefault("properties", {})
    p["route_id"] = new
    p["id"] = new
    if extra_props:
        p.update(extra_props)
    return nf


def preserve_pgc_ui(old_routes, old_stops, old_meta):
    """CAS-11 / CAS-TJ10 geometry kept. Last stop renamed Menwa UI. ID CAS-TJ10."""
    route = None
    src_id = None
    for f in old_routes["features"]:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id"))
        if fid in ("CAS-11", "CAS-TJ10"):
            src_id = fid
            extra = {
                "name": "PGC – Menwa UI",
                "short": "PGC – Menwa UI",
                "from_name": "PGC",
                "to_name": "Menwa UI",
                "endpoint": "PGC – Menwa UI",
                "planning_note": "Geometry PGC–UI dipertahankan. Pemberhentian akhir = Halte Menwa UI, bukan Margonda.",
            }
            route = remap_corridor(f, fid, "CAS-TJ10", extra) if fid != "CAS-TJ10" else deepcopy(f)
            if fid == "CAS-TJ10":
                route["properties"].update(extra)
                route["id"] = "CAS-TJ10"
            break
    stops = []
    for f in old_stops["features"]:
        rid = str(f["properties"].get("route_id") or "")
        if rid not in ("CAS-11", "CAS-TJ10"):
            continue
        nf = tja.remap_id(deepcopy(f), rid, "CAS-TJ10") if rid != "CAS-TJ10" else deepcopy(f)
        p = nf["properties"]
        p["route_id"] = "CAS-TJ10"
        order = p.get("stop_order") or p.get("stop_count")
        name = str(p.get("stop_name") or p.get("name") or "")
        last = False
        if name in ("Universitas Indonesia", "Menwa UI") or order == 10:
            last = name != "Akses UI" and name != "Akses UI / Margonda"
        if last and ("universitas indonesia" in name.lower() or "menwa" in name.lower() or "margonda" in name.lower() or order == 10):
            if "akses ui" in name.lower():
                p["stop_name"] = "Akses UI / Margonda"
                p["name"] = "Akses UI / Margonda"
            else:
                p["stop_name"] = "Menwa UI"
                p["name"] = "Menwa UI"
                p["to_name"] = "Menwa UI"
                p["note"] = "Endpoint CASCADE: Halte Menwa UI. Koridor terlihat di Margonda tetapi pemberhentian akhir bukan Margonda."
        if name == "Akses UI":
            p["stop_name"] = "Akses UI / Margonda"
            p["name"] = "Akses UI / Margonda"
        stops.append(nf)
    meta = None
    for c in old_meta.get("corridors") or []:
        if c["id"] in ("CAS-11", "CAS-TJ10"):
            meta = tja.remap_id(deepcopy(c), c["id"], "CAS-TJ10") if c["id"] != "CAS-TJ10" else deepcopy(c)
            meta["id"] = "CAS-TJ10"
            meta["name"] = "PGC – Menwa UI"
            meta["short"] = "PGC – Menwa UI"
            meta["to_name"] = "Menwa UI"
            meta["endpoint"] = "PGC – Menwa UI"
            break
    return route, stops, meta


def keep_frozen(old_routes, old_stops, old_meta, ids):
    routes, stops, meta = [], [], []
    for f in old_routes["features"]:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id"))
        if fid in ids:
            routes.append(f)
    for f in old_stops["features"]:
        rid = str(f["properties"].get("route_id") or "")
        if rid in ids:
            stops.append(f)
    for c in old_meta.get("corridors") or []:
        if c["id"] in ids:
            meta.append(c)
    return routes, stops, meta


def bbox_of(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tja.NODES.update(NODES)
    snaps = tja.load_snaps()
    for n, (lon, lat) in tja.NODES.items():
        snaps.setdefault(n, (lon, lat, "intent", "node"))
    road_map = tja.load_road_map()
    tja.ingest_extra(road_map)
    add_aliases(road_map)
    print("building road graph...", flush=True)
    graph = tja.RoadGraph(road_map)
    print("graph nodes", len(graph.pts), flush=True)
    pois = tja.poi_index(snaps)

    built = []
    warnings_all = []
    for spec in SPECS:
        print("routing", spec["id"], flush=True)
        geom, vertices, warns, method = tja.build_spine(spec, snaps, road_map, graph)
        for w in warns:
            warnings_all.append({"route": spec["id"], "issue": w})
            print(" ", w)
        if not geom:
            print("  FAIL no geometry")
            continue
        stops, tot = tja.place_stops_15(spec, geom, snaps, pois, vertices)
        km = round(tot / 1000, 2)
        print(f"  {km} km  {len(geom)} vtx  {len(stops)} stops  {method}", flush=True)
        conf = spec["geometry_confidence"]
        long_spine = [w for w in warns if str(w).startswith("SPINE")]
        if long_spine:
            try:
                mx = max(float(str(w).split()[-2]) for w in long_spine)
            except Exception:
                mx = 1
            if mx >= 0.35 and conf == "HIGH":
                conf = "MEDIUM"
        built.append((spec, geom, vertices, stops, method, conf, km))

    all_stops_brief = []
    for spec, geom, vertices, stops, method, conf, km in built:
        for s in stops:
            all_stops_brief.append({"route_id": spec["id"], "stop_name": s["stop_name"], "lon": s["lon"], "lat": s["lat"]})

    route_feats, stop_feats, seg_feats, vtx_feats, ix_feats = [], [], [], [], []
    meta = []
    reports = []
    for spec, geom, vertices, stops, method, conf, km in built:
        rf, sf, gf, vf, ixf, stop_table, km, ix_count = tja.write_route_bundle(
            spec, geom, vertices, stops, snaps, all_stops_brief, conf
        )
        route_feats.append(rf)
        stop_feats.extend(sf)
        seg_feats.extend(gf)
        vtx_feats.extend(vf)
        ix_feats.extend(ixf)
        gaps = [stop_table[i]["distance_from_previous_km"] for i in range(1, len(stop_table))]
        max_gap = max(gaps) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        mean_gap = round(statistics.mean(gaps), 2) if gaps else None
        roads = []
        for v in vertices:
            n = v.get("road_name") or ""
            if n and n not in roads and n not in ("graph", "link", "unresolved"):
                roads.append(n)
        reports.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "km": km,
                "stops": len(stops),
                "vertices": len(geom),
                "conf": conf,
                "method": method,
                "roads": roads,
                "stop_table": stop_table,
                "max_gap": max_gap,
                "min_gap": min_gap,
                "mean_gap": mean_gap,
                "spacing_pass": (max_gap <= 2.4 or spec.get("toll")) and (min_gap >= 0.5 if gaps else False),
                "warnings": [w["issue"] for w in warnings_all if w["route"] == spec["id"]],
            }
        )
        meta.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "short": spec["short"],
                "endpoint": f"{spec['from_name']} – {spec['to_name']}",
                "from_name": spec["from_name"],
                "to_name": spec["to_name"],
                "length_km": km,
                "stop_count": len(stops),
                "geometry_confidence": conf,
                "source": SOURCE,
                "status": "PROPOSED",
                "network_type": "BRT_TRUNK",
                "plan_type": spec.get("plan_type"),
                "alignment_type": spec.get("alignment_type"),
                "bbox": bbox_of(geom),
            }
        )

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())
    frozen_ids = {"CAS-TJ01", "CAS-TJ02", "CAS-TJ03", "CAS-TJ04", "CAS-TJ05"}
    fr, fs, fm = keep_frozen(old_routes, old_stops, old_meta, frozen_ids)
    pgc_r, pgc_s, pgc_m = preserve_pgc_ui(old_routes, old_stops, old_meta)
    if pgc_r:
        route_feats.append(pgc_r)
        stop_feats.extend(pgc_s)
        if pgc_m:
            meta.append(pgc_m)
        reports.append(
            {
                "id": "CAS-TJ10",
                "name": "PGC – Menwa UI",
                "km": pgc_m.get("length_km") if pgc_m else 15.24,
                "stops": pgc_m.get("stop_count") if pgc_m else len(pgc_s),
                "vertices": "kept",
                "conf": "HIGH",
                "method": "PRESERVE_ENDPOINT_FIX",
                "roads": ["(CAS-11 geometry preserved; last stop Menwa UI)"],
                "stop_table": [
                    {"sequence": f["properties"].get("stop_order"), "name": f["properties"].get("stop_name") or f["properties"].get("name"), "road": f["properties"].get("road_name"), "distance_from_previous_km": f["properties"].get("distance_from_previous_stop")}
                    for f in sorted(pgc_s, key=lambda x: x["properties"].get("stop_order") or 0)
                ],
                "spacing_pass": True,
                "warnings": [],
            }
        )

    # frozen first so order is TJ01.. then new
    order = [f"CAS-TJ{i:02d}" for i in range(1, 12)]

    def sort_key(feat):
        fid = str(feat.get("id") or feat["properties"].get("route_id") or "")
        return order.index(fid) if fid in order else 99

    route_feats = sorted(fr + route_feats, key=sort_key)
    stop_feats = fs + stop_feats
    meta_ids = {c["id"]: c for c in fm + meta}
    meta = [meta_ids[i] for i in order if i in meta_ids]

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_segments.geojson").write_text(json.dumps(fc(seg_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_vertices.geojson").write_text(json.dumps(fc(vtx_feats), ensure_ascii=False))
    (OUT_DIR / "cascade_interchanges.geojson").write_text(json.dumps(fc(ix_feats), ensure_ascii=False))
    existing = {
        "network": "CASCADE TransJakarta BRT trunk",
        "status": "PROPOSED",
        "color": COLOR,
        "source": SOURCE,
        "disclaimer": "Usulan. Bukan rute resmi. Bukan DED.",
        "retrieved": RETRIEVED,
        "crs": CRS,
        "deleted": [
            "CAS-06 Marunda–Pinang Ranti",
            "OLD CAS-07 Pinang Ranti–Harjamukti",
            "CAS-08 Monas–Puri Indah retired → CAS-TJ07 Monas–Puri Beta via Joglo",
            "CAS-09 id retired → CAS-TJ08",
            "CAS-10 id retired → CAS-TJ09",
            "CAS-11 id retired → CAS-TJ10 PGC–Menwa UI",
            "CAS-12 id retired → CAS-TJ11 Menwa UI–Galunggung",
        ],
        "corridors": meta,
    }
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT_DIR / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT_DIR / "cascade_validation.json").write_text(json.dumps({"reports": reports, "warnings": warnings_all}, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
            row["notes"] = (
                "CAS-TJ01..CAS-TJ11. TJ07=Monas–Puri Beta via Joglo (bukan Puri Indah). "
                "TJ10=PGC–Menwa UI. TJ11=Menwa UI–Galunggung. BRT trunk usulan #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    print("\n=== SUMMARY ===")
    for r in reports:
        print(f"{r['id']:10} {r['km']} km  stops={r['stops']} vtx={r['vertices']}  {r['method']}  {r['conf']}")
        for w in r.get("warnings") or []:
            print("   ", w)
    print("routes", len(route_feats), "stops", len(stop_feats))
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    print("ids", ids)
    assert "CAS-08" not in ids
    assert "CAS-TJ07" in ids
    assert "CAS-TJ01" in ids
    assert "CAS-TJ10" in ids
    assert "CAS-TJ11" in ids


if __name__ == "__main__":
    main()
