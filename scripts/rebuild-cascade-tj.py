#!/usr/bin/env python3
"""PASS revisi geometri CAS-TJ01..CAS-TJ06.

CAS-TJ06 = rename CAS-07 (Puri Beta–Monas), geometry tidak diubah.
CAS-08..CAS-12 tidak dikerjakan pada pass ini.
"""
from __future__ import annotations

import importlib.util
import json
import math
import statistics
from copy import deepcopy
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT_DIR = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-11"
SOURCE = "CASCADE.txt + user road-intent 2026-09-11"

spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts/rebuild-cascade.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

haversine = rc.haversine
length_m = rc.length_m
nearest_along = rc.nearest_along
point_at = rc.point_at
slice_along = rc.slice_along
densify = rc.densify
densify_line = rc.densify_line
clean_chain = rc.clean_chain
append_chain = rc.append_chain
ensure_termini = rc.ensure_termini
remove_hairpins = rc.remove_hairpins
flatten = rc.flatten
stitch = rc.stitch
road_between = rc.road_between
snap_to_named = rc.snap_to_named
load_snaps = rc.load_snaps
load_road_map = rc.load_road_map
RoadGraph = rc.RoadGraph
poi_index = rc.poi_index
detect_interchange = rc.detect_interchange
road_name_at = rc.road_name_at
intervention_for = rc.intervention_for
feat_line = rc.feat_line
feat_pt = rc.feat_pt
fc = rc.fc
turn_angles = rc.turn_angles
is_toll = rc.is_toll


def N(*a):
    return list(a)


# Control points on the intended spine (not kecamatan centroids).
# OSM aliases documented in planning_note / osm_alias.
NODES = {
    "Petojo": (106.81698, -6.16998),
    "Cideng Timur": (106.8124, -6.1748),
    "Underpass Tanah Abang": (106.8115, -6.1845),  # OSM: Jalan Jatibaru
    "Tanah Abang": (106.8140, -6.1885),
    "KH Mas Mansyur": (106.8162, -6.1972),
    "Karet Tengsin": (106.81600, -6.20086),
    "Sudirman Karet": (106.8194, -6.2088),
    "Satrio Barat": (106.8184, -6.2255),
    "Karet Kuningan": (106.8275, -6.2215),
    "Casablanca": (106.8415, -6.2244),
    "Kampung Melayu": (106.86682, -6.22467),
    "KH Abdullah Syafei": (106.8600, -6.2248),
    "Bassura": (106.8800, -6.2260),
    "BKT Cipinang": (106.8900, -6.2265),
    "Kolonel Sugiono": (106.9100, -6.2285),
    "Duren Sawit": (106.9180, -6.2280),
    "Jend RS Soekanto": (106.9300, -6.2265),
    "Pondok Kopi Raya": (106.9415, -6.2220),
    "Klender Baru": (106.94018, -6.21766),
    "Penggilingan": (106.9396, -6.2141),
    "Pulo Gebang": (106.95265, -6.21270),
    "Pulo Gadung": (106.90885, -6.18333),
    "Rawa Terate": (106.9220, -6.1835),
    "Cakung": (106.9380, -6.1830),
    "Pasar Cakung": (106.9500, -6.1850),
    "Ujung Menteng": (106.9650, -6.1825),
    "Bundaran Harapan Indah": (106.97730, -6.18363),
    "Harapan Indah": (106.97461, -6.18431),
    "Pasar Modern HI": (106.97421, -6.16876),
    "Transera": (106.97554, -6.15326),
    "Senen": (106.84251, -6.17821),
    "Kemayoran": (106.85151, -6.15889),
    "JIS": (106.85587, -6.12669),
    "Ancol Timur": (106.8578, -6.1240),  # sisi timur JIS / Ketel, BUKAN Ancol park barat
    "Jl Ketel": (106.8613, -6.1214),
    "RE Martadinata": (106.8680, -6.1105),
    "Taman Stasiun Priok": (106.8735, -6.1110),
    "Tanjung Priok": (106.8815, -6.1100),
    "Enggano": (106.8880, -6.1097),
    "Raya Sulawesi": (106.8932, -6.1088),
    "Raya Pelabuhan": (106.8950, -6.1076),
    "Jampea": (106.9020, -6.1082),
    "Raya Cilincing": (106.9160, -6.1120),
    "Akses Marunda": (106.9320, -6.1120),
    "Marunda Bidara": (106.9500, -6.1085),
    "Marunda Makmur": (106.9602, -6.1077),
    "Rusunawa Marunda": (106.96128, -6.09863),
    "Lebak Bulus": (106.77493, -6.28930),
    "Pondok Pinang": (106.77204, -6.28217),
    "Pondok Indah": (106.7805, -6.2680),
    "Kebayoran": (106.7830, -6.2450),
    "Simprug": (106.78647, -6.23394),
    "Jl Panjang": (106.7780, -6.2195),
    "Kelapa Dua": (106.7694, -6.2105),
    "Pos Pengumben": (106.77226, -6.21294),
    "Joglo Timur": (106.7603, -6.21742),
    "Joglo Raya": (106.7388, -6.2178),
    "Gerbang Tol Joglo": (106.74426, -6.21894),
    "Gerbang Tol Ciledug": (106.7350, -6.2370),
    "Exit Rawa Buaya": (106.72712, -6.16340),
    "Kalideres": (106.70550, -6.15441),
    "TB Simatupang": (106.7953, -6.2940),
    "Cilandak": (106.8100, -6.2930),
    "Simpang Ragunan": (106.8235, -6.2945),
    "Pasar Rebo": (106.8624, -6.3082),
    "Pasar Rebo Putar Balik": (106.8620, -6.3150),
    "Mabes Hankam": (106.8845, -6.3058),
    "Taman Mini": (106.8820, -6.2935),
    "Pinang Ranti": (106.88634, -6.29108),
}

SPECS = [
    dict(
        id="CAS-TJ01",
        route_order=1,
        name="Petojo – Pulo Gebang",
        short="Petojo – Pulo Gebang",
        from_name="Petojo",
        to_name="Pulo Gebang",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Koridor baru. Spine Jalur Petojo–Duren Sawit: Cideng Timur–Jatibaru (underpass Tanah Abang)–Mas Mansyur–Sudirman Karet (konektor OSM 1,5 km)–Satrio–Casablanca–Abdul Syafi'ie–Bassura–Soegiono–Soekanto–Pondok Kopi–Klender Baru–Ngurah Rai/Penggilingan–Pulo Gebang. Bukan Suryopranoto/Hasyim/Balikpapan.",
        osm_alias={
            "Underpass Tanah Abang": "Jalan Jatibaru",
            "KH Abdullah Syafei": "Jalan K. Haji Abdul Syafi'ie",
            "Kolonel Sugiono": "Jalan Kolonel Soegiono",
            "Jend RS Soekarno": "Jalan Jenderal Polisi RS. Soekanto",
            "Raya Penggilingan (timur Klender Baru)": "Jalan I Gusti Ngurah Rai",
        },
        controls=N(
            "Petojo",
            "Cideng Timur",
            "Underpass Tanah Abang",
            "Tanah Abang",
            "KH Mas Mansyur",
            "Karet Tengsin",
            "Sudirman Karet",
            "Satrio Barat",
            "Karet Kuningan",
            "Casablanca",
            "KH Abdullah Syafei",
            "Kampung Melayu",
            "Bassura",
            "BKT Cipinang",
            "Kolonel Sugiono",
            "Duren Sawit",
            "Jend RS Soekanto",
            "Pondok Kopi Raya",
            "Klender Baru",
            "Penggilingan",
            "Pulo Gebang",
        ),
        road_by_pair=[
            ["Jalan Cideng Timur"],
            ["Jalan Cideng Timur", "Jalan Jatibaru", "Jalan Jatibaru Raya"],
            ["Jalan Jatibaru", "Jalan Jatibaru Raya", "Jalan Haji Fachrudin"],
            ["Jalan Haji Fachrudin", "Jalan Kyai Haji Mas Mansyur"],
            ["Jalan Kyai Haji Mas Mansyur"],
            ["Jalan Kyai Haji Mas Mansyur", "Jalan Jenderal Sudirman"],
            ["Jalan Jenderal Sudirman", "Jalan Profesor Doktor Satrio"],
            ["Jalan Profesor Doktor Satrio"],
            ["Jalan Profesor Doktor Satrio", "Jalan Raya Casablanca"],
            ["Jalan Raya Casablanca", "Jalan K. Haji Abdul Syafi'ie"],
            ["Jalan K. Haji Abdul Syafi'ie"],
            ["Jalan K. Haji Abdul Syafi'ie", "Jalan Jenderal Basuki Rahmat"],
            ["Jalan Jenderal Basuki Rahmat"],
            ["Jalan Jenderal Basuki Rahmat", "Jalan Kolonel Soegiono"],
            ["Jalan Kolonel Soegiono"],
            ["Jalan Kolonel Soegiono", "Jalan Jenderal Polisi RS. Soekanto"],
            ["Jalan Jenderal Polisi RS. Soekanto", "Jalan Raya Pondok Kopi"],
            ["Jalan Raya Pondok Kopi", "Pondok Kopi Flyover", "Penggilingan Raya", "Jalan I Gusti Ngurah Rai"],
            ["Penggilingan Raya", "Pondok Kopi Flyover", "Jalan I Gusti Ngurah Rai", "Jalan Raya Penggilingan"],
            ["Jalan I Gusti Ngurah Rai", "Jalan Pulo Gebang", "TJ-K11"],
        ],
        anchors=N(
            "Petojo",
            "Cideng Timur",
            "Tanah Abang",
            "KH Mas Mansyur",
            "Satrio Barat",
            "Karet Kuningan",
            "Casablanca",
            "Kampung Melayu",
            "Bassura",
            "Kolonel Sugiono",
            "Duren Sawit",
            "Pondok Kopi Raya",
            "Klender Baru",
            "Penggilingan",
            "Pulo Gebang",
        ),
        keep_detours=False,
        toll=False,
    ),
    dict(
        id="CAS-TJ02",
        route_order=2,
        name="Pulo Gadung – Harapan Indah – Transera",
        short="Pulo Gadung – Transera",
        from_name="Pulo Gadung",
        to_name="Transera",
        parent_route="2",
        plan_type="CASCADE_EXTENSION",
        cascade_status="EXTENSION",
        existing_transjakarta="YES",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Perpanjangan Koridor 2. Backbone Jalan Bekasi Raya (OSM name; di Bekasi dikenal sebagai Sri Sultan Hamengkubuwono IX / Pantura) lalu Jalan Harapan Indah Bulevar ke Bundaran–Living Plaza–Pasar Modern–Transera Waterpark. Bukan feeder.",
        osm_alias={
            "Jalan Raya Bekasi / Pantura / Hamengkubuwono IX": "Jalan Bekasi Raya + Jalan Harapan Indah Raya / Bulevar",
        },
        controls=N(
            "Pulo Gadung",
            "Rawa Terate",
            "Cakung",
            "Pasar Cakung",
            "Ujung Menteng",
            "Bundaran Harapan Indah",
            "Harapan Indah",
            "Pasar Modern HI",
            "Transera",
        ),
        road_by_pair=[
            ["Jalan Bekasi Raya"],
            ["Jalan Bekasi Raya"],
            ["Jalan Bekasi Raya"],
            ["Jalan Bekasi Raya"],
            ["Jalan Bekasi Raya", "Jalan Harapan Indah Raya", "Jalan Harapan Indah Bulevar"],
            ["Jalan Harapan Indah Raya", "Jalan Harapan Indah Bulevar", "Jalan Tanafit"],
            ["Jalan Harapan Indah Bulevar", "Jalan Tanafit"],
            ["Jalan Harapan Indah Bulevar", "Jalan Pusaka Rakyat"],
        ],
        anchors=N(
            "Pulo Gadung",
            "Rawa Terate",
            "Cakung",
            "Ujung Menteng",
            "Bundaran Harapan Indah",
            "Harapan Indah",
            "Pasar Modern HI",
            "Transera",
        ),
        keep_detours=False,
        toll=False,
    ),
    dict(
        id="CAS-TJ03",
        route_order=3,
        name="Senen – JIS – Marunda",
        short="Senen – Marunda",
        from_name="Senen",
        to_name="Rusunawa Marunda",
        parent_route="14",
        plan_type="CASCADE_EXTENSION",
        cascade_status="EXTENSION",
        existing_transjakarta="YES",
        geometry_confidence="MEDIUM",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="Perpanjangan Koridor 14. Senen–JIS (existing TJ-K14) lalu Ketel–Martadinata–Tanjung Priok–Enggano–Pelabuhan–Jampea–Cilincing–Akses Marunda–Marunda Bidara–Makmur–Akses Rusun–Rusunawa. Ancol Timur OSM di taman Ancol (barat JIS) TIDAK dipakai sebagai backbone; vertex Ancol Timur = sisi timur JIS/Ketel. Sheikh Nawawi OSM ada di selatan Rorotan (bukan pesisir) — tidak ditarik sebagai detour 4 km.",
        osm_alias={
            "Jl Ancol Timur (maksud user setelah JIS)": "Jalan Ketel + Jalan R. E. Martadinata (bukan way Ancol park 106.847)",
            "Sheikh Nawawi Al Bantani": "Jalan Syech Nawawi Al Bantani (inland, tidak di-trace)",
            "Cilincing Landak": "Jalan Sungai Landak / Jalan Marunda Bidara",
        },
        controls=N(
            "Senen",
            "Kemayoran",
            "JIS",
            "Ancol Timur",
            "Jl Ketel",
            "RE Martadinata",
            "Taman Stasiun Priok",
            "Tanjung Priok",
            "Enggano",
            "Raya Sulawesi",
            "Raya Pelabuhan",
            "Jampea",
            "Raya Cilincing",
            "Akses Marunda",
            "Marunda Bidara",
            "Marunda Makmur",
            "Rusunawa Marunda",
        ),
        road_by_pair=[
            ["TJ-K14"],
            ["TJ-K14"],
            ["TJ-K14", "Jalan Ketel", "Jalan Ketel Ancol", "Jalan R. E. Martadinata"],
            ["Jalan Ketel", "Jalan Ketel Ancol", "Jalan R. E. Martadinata"],
            ["Jalan R. E. Martadinata"],
            ["Jalan R. E. Martadinata", "Jalan Enggano"],
            ["Jalan R. E. Martadinata", "Jalan Enggano"],
            ["Jalan Enggano"],
            ["Jalan Enggano", "Jalan Sulawesi"],
            ["Jalan Sulawesi", "Jalan Raya Pelabuhan"],
            ["Jalan Raya Pelabuhan", "Jalan Jampea"],
            ["Jalan Jampea", "Jalan Raya Cilincing Koja"],
            ["Jalan Raya Cilincing Koja", "Jalan Akses Marunda"],
            ["Jalan Akses Marunda", "Jalan Marunda Bidara"],
            ["Jalan Marunda Bidara", "Jalan Marunda Makmur"],
            ["Jalan Marunda Makmur", "Jalan Akses Rusun Marunda", "Jalan Sungai Landak"],
        ],
        anchors=N(
            "Senen",
            "Kemayoran",
            "JIS",
            "Tanjung Priok",
            "Enggano",
            "Raya Cilincing",
            "Akses Marunda",
            "Marunda Makmur",
            "Rusunawa Marunda",
        ),
        keep_detours=False,
        toll=False,
    ),
    dict(
        id="CAS-TJ04",
        route_order=4,
        name="Lebak Bulus – Kalideres",
        short="Lebak Bulus – Kalideres",
        from_name="Lebak Bulus",
        to_name="Kalideres",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="MEDIUM",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TOLL",
        planning_note="Lebak Bulus–Pondok Indah–Kebayoran–Simprug–Kelapa Dua–Pengumben–Joglo Raya–Gerbang Tol Ciledug–JORR W2–Exit Rawa Buaya–Daan Mogot–Kalideres. Tidak ada halte di dalam W2. bus_lane=NOT_ASSUMED. Jalan Panjang Raya OSM memanjang ke utara Tanjung Duren — tidak dipakai sebagai backbone utara.",
        osm_alias={
            "Arteri Kelapa Dua Raya": "Jalan Kelapa Dua Raya",
            "Jl Pantura setelah exit": "Jalan Daan Mogot",
            "Tol Lingkar Luar Jakarta W2": "JORR W2 Ciledug–Rawa Buaya (OSRM; extract JORR di roads.geojson terpotong selatan Joglo)",
        },
        controls=N(
            "Lebak Bulus",
            "Pondok Pinang",
            "Pondok Indah",
            "Kebayoran",
            "Simprug",
            "Jl Panjang",
            "Kelapa Dua",
            "Pos Pengumben",
            "Joglo Timur",
            "Joglo Raya",
            "Gerbang Tol Joglo",
            "Gerbang Tol Ciledug",
            "Exit Rawa Buaya",
            "Kalideres",
        ),
        road_by_pair=[
            ["TJ-K8"],
            ["TJ-K8"],
            ["TJ-K8"],
            ["TJ-K8"],
            ["TJ-K8", "Jalan Arteri Pos Pengumben", "Jalan Kelapa Dua Raya"],
            ["Jalan Kelapa Dua Raya", "Jalan Arteri Pos Pengumben"],
            ["Jalan Kelapa Dua Raya", "Jalan Arteri Pos Pengumben"],
            ["Jalan Joglo Raya", "Jalan Kelapa Dua Raya"],
            ["Jalan Joglo Raya"],
            ["Jalan Joglo Raya"],
            ["Jalan Ciledug Raya", "JORR W2 Ciledug–Rawa Buaya"],
            ["JORR W2 Ciledug–Rawa Buaya", "Jalan Tol Lingkar Luar Jakarta"],
            ["Jalan Daan Mogot", "TJ-K3"],
        ],
        anchors=N(
            "Lebak Bulus",
            "Pondok Pinang",
            "Pondok Indah",
            "Kebayoran",
            "Simprug",
            "Kelapa Dua",
            "Pos Pengumben",
            "Joglo Raya",
            "Gerbang Tol Joglo",
            "Gerbang Tol Ciledug",
            "Exit Rawa Buaya",
            "Kalideres",
        ),
        keep_detours=True,
        toll=True,
        toll_from="Gerbang Tol Ciledug",
        toll_to="Exit Rawa Buaya",
    ),
    dict(
        id="CAS-TJ05",
        route_order=5,
        name="Lebak Bulus – Pinang Ranti",
        short="Lebak Bulus – Pinang Ranti",
        from_name="Lebak Bulus",
        to_name="Pinang Ranti",
        parent_route="",
        plan_type="NEW_TRUNK",
        cascade_status="NEW_TRUNK",
        existing_transjakarta="PARTIAL",
        geometry_confidence="HIGH",
        road_alignment_confidence="HIGH",
        alignment_type="MIXED_TRAFFIC",
        planning_note="TB Simatupang sepanjang koridor hingga Pasar Rebo, putar balik di Jalan Raya Bogor, lalu Mabes Hankam–Taman Mini I–Pinang Ranti. Bukan shortcut lokal.",
        osm_alias={
            "TB Simatupang": "Jalan Tahi Bonar Simatupang",
        },
        controls=N(
            "Lebak Bulus",
            "TB Simatupang",
            "Cilandak",
            "Simpang Ragunan",
            "Pasar Rebo",
            "Pasar Rebo Putar Balik",
            "Mabes Hankam",
            "Taman Mini",
            "Pinang Ranti",
        ),
        road_by_pair=[
            ["Jalan Tahi Bonar Simatupang", "TJ-K8"],
            ["Jalan Tahi Bonar Simatupang"],
            ["Jalan Tahi Bonar Simatupang"],
            ["Jalan Tahi Bonar Simatupang", "Jalan Raya Bogor"],
            ["Jalan Raya Bogor", "Jalan Tahi Bonar Simatupang"],
            ["Jalan Raya Bogor", "Jalan Mabes Hankam", "Jalan Hankam"],
            ["Jalan Mabes Hankam", "Jalan Taman Mini I", "Jalan Hankam"],
            ["Jalan Taman Mini I", "TJ-K9", "Simpang Susun Taman Mini"],
        ],
        anchors=N("Lebak Bulus", "Cilandak", "Simpang Ragunan", "Pasar Rebo", "Mabes Hankam", "Taman Mini", "Pinang Ranti"),
        keep_detours=True,
        toll=False,
    ),
]


def ingest_extra(road_map):
    p = OUT_DIR / "extra_roads.geojson"
    if not p.exists():
        return
    extra = json.loads(p.read_text())
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        name = f["properties"].get("name") or "extra"
        buckets.setdefault(name, []).extend(flatten(g))
    for name, parts in buckets.items():
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            parts = old + parts
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name, "highway": "secondary", "source": "nominatim"},
            "geometry": {"type": "MultiLineString", "coordinates": [list(map(list, x)) for x in parts if len(x) >= 2]},
        }
    # aliases that must NOT merge into the truncated full-ring JORR
    if "JORR W2 Ciledug–Rawa Buaya" in road_map:
        road_map.setdefault(
            "Jalan Tol Lingkar Luar Jakarta W2",
            road_map["JORR W2 Ciledug–Rawa Buaya"],
        )


def pair_route_tj(road_map, graph, a, b, roads, keep_detours=False, allow_toll=False):
    """Named-road slice, then graph with a looser cap, then densify. Never invent a short-cut as the primary."""
    sl, rname = road_between(road_map, roads, a, b, max_off=850, max_stretch=2.2) if roads else (None, None)
    method = "ROAD"
    if sl is None and roads and haversine(a, b) > 180:
        sl, _g = graph.route(a, b, prefer=roads, max_factor=2.8, skip_toll=not allow_toll)
        if sl:
            rname = roads[0] if roads else "graph"
            method = "GRAPH"
    if sl is None:
        d = haversine(a, b)
        sl = densify(a, b, 60)
        rname = roads[0] if roads else "unresolved"
        method = "SPINE"
        return densify_line(sl, 70), rname, method, d
    return densify_line(sl, 70), rname, method, 0.0


def resolve_xy(name, snaps):
    if name in NODES:
        lon, lat = NODES[name]
        return lon, lat, "intent", "node"
    if name in snaps:
        lon, lat, src, mode = snaps[name]
        return lon, lat, src, mode
    return None


def build_spine(spec, snaps, road_map, graph):
    warnings = []
    names = spec["controls"]
    pts = []
    for n in names:
        r = resolve_xy(n, snaps)
        if not r:
            warnings.append(f"unresolved {n}")
            continue
        lon, lat, src, mode = r
        pts.append((n, [lon, lat], src, mode))
    if len(pts) < 2:
        return None, [], warnings, "empty"
    pairs = spec.get("road_by_pair") or []
    snapped = []
    for i, (n, xy, src, mode) in enumerate(pts):
        roads = []
        if i < len(pairs):
            roads += pairs[i]
        if i > 0 and i - 1 < len(pairs):
            roads += pairs[i - 1]
        hit = snap_to_named(road_map, roads, xy, max_off=900)
        terminus = i == 0 or i == len(pts) - 1
        if terminus:
            # keep declared start/end; do not slide Monas onto a truncated Thamrin, etc.
            snapped.append((n, list(xy), src, mode))
        elif hit and hit[2] < 520:
            snapped.append((n, list(hit[0]), src, mode))
        else:
            gn = graph.nearest(xy, prefer=roads, max_off=900)
            if gn and gn[1] < 420:
                snapped.append((n, list(graph.pts[gn[0]]), src, mode))
            else:
                snapped.append((n, list(xy), src, mode))
    pts = snapped
    chain = []
    used_road = False
    vertices = []
    vid = 0
    allow_toll = bool(spec.get("toll"))
    for i in range(len(pts) - 1):
        a_name, a, a_src, _ = pts[i]
        b_name, b, b_src, _ = pts[i + 1]
        roads = pairs[i] if i < len(pairs) else []
        sl, rname, method, spine_d = pair_route_tj(
            road_map, graph, a, b, roads, keep_detours=spec.get("keep_detours"), allow_toll=allow_toll
        )
        if method == "SPINE" and spine_d > 250:
            warnings.append(f"SPINE {a_name}–{b_name} {spine_d/1000:.2f} km")
        if method in ("ROAD", "GRAPH"):
            used_road = True
        vid += 1
        vertices.append(
            {
                "vertex_id": f"{spec['id']}-V{vid:02d}",
                "route_id": spec["id"],
                "vertex_order": vid,
                "vertex_name": a_name,
                "vertex_type": "ENDPOINT" if i == 0 else "ROAD_CHANGE",
                "road_name": rname or "",
                "geometry": a,
                "source": a_src,
                "method": method,
                "confidence": "HIGH" if method in ("ROAD", "GRAPH") else "LOW",
            }
        )
        chain = append_chain(chain, sl)
    vid += 1
    vertices.append(
        {
            "vertex_id": f"{spec['id']}-V{vid:02d}",
            "route_id": spec["id"],
            "vertex_order": vid,
            "vertex_name": pts[-1][0],
            "vertex_type": "ENDPOINT",
            "road_name": pairs[-1][0] if pairs else "",
            "geometry": pts[-1][1],
            "source": pts[-1][2],
            "method": "ROAD" if used_road else "SPINE",
            "confidence": "HIGH",
        }
    )
    chain = clean_chain(chain)
    if not spec.get("keep_detours"):
        chain = remove_hairpins(chain, 125)
        chain = rc.remove_loops(chain)
    else:
        # still cut true out-and-backs (≥1.5 km return) but keep road wiggles
        chain = rc.remove_loops(chain, rejoin_m=90.0, min_loop=1500.0)
    chain = ensure_termini(chain, pts[0][1], pts[-1][1])
    chain = densify_line(clean_chain(chain), 80)
    method = "ROAD_REFERENCE" if used_road else "DOCUMENT_RECONSTRUCTION"
    return chain, vertices, warnings, method


def along_is_toll(geom, vertices, along):
    name = road_name_at(geom, along, vertices) or ""
    n = name.lower()
    return is_toll(name) or "lingkar luar jakarta" in n or "jorr w2" in n


def _norm_stop(name):
    n = (name or "").lower()
    n = n.replace("soegiono", "sugiono")
    n = n.replace("syafi'ie", "syafei").replace("syafiie", "syafei")
    for tok in ("jalan ", "jl ", "kyai haji ", "k. haji ", "kh ", "jenderal ", "profesor doktor "):
        n = n.replace(tok, "")
    n = " ".join(n.split())
    if n.endswith(" tengah"):
        n = n[: -len(" tengah")]
    return n.strip()


def place_stops_15(spec, geom, snaps, pois, vertices):
    """Target ±1.5 km. No stops on toll interior. Prefer named activity nodes."""
    tot = length_m(geom)
    placed = []
    used = set()
    used_norm = set()

    def add(name, along, lon, lat, reason, conf, src="intent", existing="NO", d=0.0):
        nn = _norm_stop(name)
        if name in used or (nn and nn in used_norm and reason != "TERMINUS"):
            return False
        min_sep = 80 if reason == "TERMINUS" else 650 if reason == "SPACING" else 900
        for p in placed:
            if abs(p["along_m"] - along) < min_sep:
                if reason != "TERMINUS":
                    return False
        placed.append(
            {
                "stop_name": name,
                "lon": lon,
                "lat": lat,
                "along_m": along,
                "distance_to_route": d,
                "placement_reason": reason,
                "name_source": "USER_INTENT" if reason in ("TERMINUS", "ANCHOR") else "LOCATION_RESEARCH",
                "name_confidence": conf,
                "location_confidence": "HIGH" if d <= 40 else "MEDIUM",
                "source_type": src,
                "existing": existing,
            }
        )
        used.add(name)
        if nn:
            used_norm.add(nn)
        return True

    a = geom[0]
    b = geom[-1]
    add(spec["from_name"], 0.0, a[0], a[1], "TERMINUS", "HIGH")
    add(spec["to_name"], tot, b[0], b[1], "TERMINUS", "HIGH")
    toll_ends = {spec.get("toll_from"), spec.get("toll_to")}
    toll_lo = toll_hi = None
    if spec.get("toll") and spec.get("toll_from") and spec.get("toll_to"):
        fa = resolve_xy(spec["toll_from"], snaps)
        tb = resolve_xy(spec["toll_to"], snaps)
        if fa and tb:
            _, a_al, _, _ = nearest_along([fa[0], fa[1]], geom)
            _, b_al, _, _ = nearest_along([tb[0], tb[1]], geom)
            toll_lo, toll_hi = min(a_al, b_al), max(a_al, b_al)

    def on_toll_interior(along):
        if toll_lo is None:
            return False
        return toll_lo + 80 < along < toll_hi - 80

    nearby = []
    for poi in pois:
        d, along, ppt, _ = nearest_along([poi["lon"], poi["lat"]], geom)
        if d <= 180 and not on_toll_interior(along):
            nearby.append((poi, along, ppt, d))
    for nm in spec.get("anchors") or []:
        if nm in used:
            continue
        r = resolve_xy(nm, snaps)
        if not r:
            continue
        lon, lat, src, mode = r
        d, along, ppt, _ = nearest_along([lon, lat], geom)
        if d > 1100:
            continue
        if on_toll_interior(along) and nm not in toll_ends:
            continue
        exist = "YES" if str(src).startswith("existing_") or mode in ("tj", "krl", "mrt", "lrt") else "NO"
        add(nm, along, ppt[0], ppt[1], "ANCHOR", "HIGH", src, exist, d)
    placed.sort(key=lambda p: p["along_m"])

    for _ in range(50):
        placed.sort(key=lambda p: p["along_m"])
        changed = False
        for i in range(len(placed) - 1):
            gap = placed[i + 1]["along_m"] - placed[i]["along_m"]
            if gap < 1850:
                continue
            target = placed[i]["along_m"] + min(1500, gap * 0.5)
            if on_toll_interior(target):
                slid = None
                for step in range(int(gap / 200)):
                    cand = placed[i]["along_m"] + 400 + step * 200
                    if cand >= placed[i + 1]["along_m"] - 400:
                        break
                    if not on_toll_interior(cand):
                        slid = cand
                        break
                if slid is None:
                    continue
                target = slid
            lo, hi = placed[i]["along_m"] + 700, placed[i + 1]["along_m"] - 700
            if hi <= lo:
                continue
            best = None
            for poi, along, ppt, d in nearby:
                if poi["name"] in used or _norm_stop(poi["name"]) in used_norm:
                    continue
                if along < lo or along > hi:
                    continue
                score = poi["score"] * 12 - abs(along - target) / 120 - d / 12
                if best is None or score > best[0]:
                    best = (score, poi, along, ppt, d)
            if best:
                poi, along, ppt, d = best[1], best[2], best[3], best[4]
                exist = "YES" if str(poi["src"]).startswith("existing_") or poi["mode"] in ("tj", "krl", "mrt", "lrt") else "NO"
                if add(poi["name"], along, ppt[0], ppt[1], "ACTIVITY_CENTER", "HIGH" if poi["score"] >= 4 else "MEDIUM", poi["src"], exist, d):
                    changed = True
                    break
            ppt = point_at(geom, target)
            road = road_name_at(geom, target, vertices) or "jalan"
            label = (
                road.replace("Jalan ", "")
                .replace("Jalan", "")
                .replace("JORR W2 Ciledug–Rawa Buaya", "Gerbang Tol")
                .strip()
                or f"Ruas {i+1}"
            )
            if label.lower().startswith("tj-k") or label == spec.get("short") or " – " in label:
                label = (road_name_at(geom, target, vertices) or f"Ruas {i+1}").replace("Jalan ", "").strip() or f"Ruas {i+1}"
            base = label
            n = 1
            while label in used or _norm_stop(label) in used_norm:
                n += 1
                label = f"{base} {n}"
            ok = add(label, target, ppt[0], ppt[1], "SPACING", "MEDIUM", "along_line", "NO", 0.0)
            if not ok:
                mid = (placed[i]["along_m"] + placed[i + 1]["along_m"]) / 2
                if on_toll_interior(mid):
                    continue
                ppt = point_at(geom, mid)
                label = f"{base} tengah"
                n = 1
                while label in used or _norm_stop(label) in used_norm:
                    n += 1
                    label = f"{base} {n}"
                ok = add(label, mid, ppt[0], ppt[1], "SPACING", "MEDIUM", "along_line", "NO", 0.0)
            if ok:
                changed = True
            break
        if not changed:
            break
    placed.sort(key=lambda p: p["along_m"])
    return placed, tot


def bbox_of(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def remap_id(obj, old, new):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str):
                v = v.replace(old, new)
            else:
                v = remap_id(v, old, new)
            out[k.replace(old, new) if isinstance(k, str) else k] = v
        if "id" in out and isinstance(out["id"], str):
            out["id"] = out["id"].replace(old, new)
        return out
    if isinstance(obj, list):
        return [remap_id(x, old, new) for x in obj]
    return obj


def write_route_bundle(spec, geom, vertices, stops, snaps, all_stops_brief, conf):
    cid = spec["id"]
    tot = length_m(geom)
    km = round(tot / 1000, 2)
    common = {
        "route_id": cid,
        "route_name": spec["name"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "route_order": spec["route_order"],
        "network_type": "BRT_TRUNK",
        "plan_type": spec.get("plan_type") or "NEW_TRUNK",
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
        "alignment_type": spec.get("alignment_type") or "MIXED_TRAFFIC",
        "bus_lane": "NOT_ASSUMED",
        "planning_note": spec.get("planning_note") or "",
        "osm_alias": spec.get("osm_alias") or {},
        "source": SOURCE,
        "source_type": "ROAD_TRACE",
        "geometry_source": "OSM named arterials (roads.geojson + nominatim extras) + existing TJ centreline where overlapping",
        "color": COLOR,
        "crs": CRS,
        "disclaimer": "Usulan jaringan BRT CASCADE. Bukan rute resmi TransJakarta. Bukan gambar DED.",
        "updated_at": RETRIEVED,
    }
    stop_feats, seg_feats, vtx_feats, ix_feats = [], [], [], []
    stop_table, seg_table = [], []
    ix_count = 0
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
            "road_name": road,
            "area_name": s["stop_name"],
            "distance_from_previous_stop": dist_prev,
            "distance_to_next_stop": dist_next,
            "name_confidence": s["name_confidence"],
            "placement_reason": s["placement_reason"],
            "nearest_transit": ix["nearest_transit"],
            "note": "Halte usulan CASCADE. Bukan halte resmi.",
        }
        stop_feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
        stop_table.append(
            {
                "sequence": order,
                "name": s["stop_name"],
                "road": road,
                "distance_from_previous_km": dist_prev,
            }
        )
        if ix["interchange"] == "YES":
            ix_feats.append(
                feat_pt(
                    f"{sid}-IX",
                    [s["lon"], s["lat"]],
                    {"route_id": cid, "stop_id": sid, "stop_name": s["stop_name"], "interchange_mode": ix["interchange_mode"], "name": s["stop_name"], "color": COLOR},
                )
            )
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        sl = slice_along(geom, a["along_m"], b["along_m"])
        road = road_name_at(geom, (a["along_m"] + b["along_m"]) / 2, vertices)
        align = "MIXED_TOLL" if is_toll(road) or "lingkar luar" in str(road).lower() or "jorr w2" in str(road).lower() else spec.get("alignment_type") or "MIXED_TRAFFIC"
        seg_id = f"{cid}-SEG{i+1:02d}"
        seg_feats.append(
            feat_line(
                seg_id,
                sl,
                {
                    **common,
                    "segment_id": seg_id,
                    "from_vertex": a["stop_name"],
                    "to_vertex": b["stop_name"],
                    "road_name": road or "",
                    "alignment_type": align,
                    "geometry_confidence": "HIGH" if road and road not in ("unresolved", "graph", "link") else "MEDIUM",
                    "length_km": round(length_m(sl) / 1000, 3),
                    "bus_lane": "NOT_ASSUMED",
                },
            )
        )
        seg_table.append({"from": a["stop_name"], "to": b["stop_name"], "road": road, "align": align})
    for v in vertices:
        vtx_feats.append(
            feat_pt(
                v["vertex_id"],
                v["geometry"],
                {
                    **common,
                    "vertex_id": v["vertex_id"],
                    "vertex_order": v["vertex_order"],
                    "name": v["vertex_name"],
                    "vertex_type": v["vertex_type"],
                    "road_name": v["road_name"],
                    "geometry_confidence": v.get("confidence") or "MEDIUM",
                },
            )
        )
    route_props = {
        **common,
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        "length_km": km,
        "stop_count": len(stops),
        "interchange_count": ix_count,
        "vertex_count": len(vertices),
        "digitization_level": "ROAD_TRACE",
    }
    route_feat = feat_line(cid, geom, route_props)
    return route_feat, stop_feats, seg_feats, vtx_feats, ix_feats, stop_table, km, ix_count


def load_frozen_tj06():
    p = OUT_DIR / "cas_tj06_frozen.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def keep_leftovers(route_feats, stop_feats, meta, reports):
    """Keep CAS-08..12 untouched. CAS-TJ06 from frozen CAS-07 geometry (idempotent)."""
    frozen = load_frozen_tj06()
    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())
    keep_ids = {"CAS-08", "CAS-09", "CAS-10", "CAS-11", "CAS-12"}

    def is_tj06(fid):
        s = str(fid or "")
        return s == "CAS-07" or s == "CAS-TJ06" or s.startswith("CAS-07") or s.startswith("CAS-TJ06")

    got_tj06 = False
    if frozen and frozen.get("routes"):
        for f in frozen["routes"]:
            nf = remap_id(deepcopy(f), "CAS-07", "CAS-TJ06")
            nf["properties"]["route_id"] = "CAS-TJ06"
            nf["properties"]["id"] = "CAS-TJ06"
            nf["properties"]["short"] = "Puri Beta – Monas"
            nf["id"] = "CAS-TJ06"
            route_feats.append(nf)
            got_tj06 = True
        for f in frozen.get("stops") or []:
            stop_feats.append(remap_id(deepcopy(f), "CAS-07", "CAS-TJ06"))
        c = frozen.get("meta") or {}
        c = remap_id(deepcopy(c), "CAS-07", "CAS-TJ06")
        c["id"] = "CAS-TJ06"
        meta.append(c)
        reports.append(
            {
                "id": "CAS-TJ06",
                "name": c.get("name") or "Puri Beta – Monas",
                "km": c.get("length_km"),
                "stops": c.get("stop_count"),
                "vertices": "kept",
                "segments": "kept",
                "conf": c.get("geometry_confidence") or "MEDIUM",
                "method": "RENAME_ONLY",
                "roads": ["(CAS-07 geometry preserved)"],
                "stop_table": [],
                "spacing_pass": True,
                "warnings": [],
            }
        )
    if not got_tj06:
        for f in old_routes["features"]:
            fid = str(f.get("id") or f["properties"].get("id") or f["properties"].get("route_id"))
            if is_tj06(fid):
                nf = remap_id(deepcopy(f), "CAS-07", "CAS-TJ06")
                nf["properties"]["route_id"] = "CAS-TJ06"
                nf["id"] = "CAS-TJ06"
                route_feats.append(nf)
        for f in old_stops["features"]:
            rid = str(f["properties"].get("route_id") or f.get("id") or "")
            if is_tj06(rid):
                stop_feats.append(remap_id(deepcopy(f), "CAS-07", "CAS-TJ06"))

    present = {str(f.get("id") or f["properties"].get("route_id")) for f in route_feats}
    for f in old_routes["features"]:
        fid = str(f.get("id") or f["properties"].get("id") or f["properties"].get("route_id"))
        if fid in keep_ids and fid not in present:
            route_feats.append(f)
    present_stops = {str(f["properties"].get("route_id")) for f in stop_feats}
    for f in old_stops["features"]:
        rid = str(f["properties"].get("route_id") or "")
        if rid in keep_ids:
            stop_feats.append(f)
    have_meta = {c["id"] for c in meta}
    for c in old_meta.get("corridors") or []:
        if c["id"] in keep_ids and c["id"] not in have_meta:
            meta.append(c)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snaps = load_snaps()
    for n, (lon, lat) in NODES.items():
        snaps.setdefault(n, (lon, lat, "intent", "node"))
    road_map = load_road_map()
    ingest_extra(road_map)
    print("building road graph...", flush=True)
    graph = RoadGraph(road_map)
    print("graph nodes", len(graph.pts), flush=True)
    pois = poi_index(snaps)

    built = []
    warnings_all = []
    for spec in SPECS:
        print("routing", spec["id"], flush=True)
        geom, vertices, warns, method = build_spine(spec, snaps, road_map, graph)
        for w in warns:
            warnings_all.append({"route": spec["id"], "issue": w})
            print(" ", w)
        if not geom:
            print("  FAIL no geometry")
            continue
        stops, tot = place_stops_15(spec, geom, snaps, pois, vertices)
        km = round(tot / 1000, 2)
        print(f"  {km} km  {len(geom)} vtx  {len(stops)} stops  {method}")
        conf = spec["geometry_confidence"]
        if any(str(w).startswith("SPINE") and float(str(w).split()[-2]) >= 0.4 for w in warns):
            if conf == "HIGH":
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
        rf, sf, gf, vf, ixf, stop_table, km, ix_count = write_route_bundle(spec, geom, vertices, stops, snaps, all_stops_brief, conf)
        route_feats.append(rf)
        stop_feats.extend(sf)
        seg_feats.extend(gf)
        vtx_feats.extend(vf)
        ix_feats.extend(ixf)
        gaps = [stop_table[i]["distance_from_previous_km"] for i in range(1, len(stop_table))]
        max_gap = max(gaps) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        mean_gap = round(statistics.mean(gaps), 2) if gaps else None
        # MIXED_TOLL: ignore the W2 interior gap for spacing_pass
        toll = spec.get("alignment_type") == "MIXED_TOLL"
        if toll:
            non_toll = []
            for i in range(1, len(stop_table)):
                road = str(stop_table[i].get("road") or "")
                if is_toll(road) or "lingkar luar" in road.lower() or "jorr" in road.lower():
                    continue
                # gap that lands on the exit after a toll segment is the toll span
                prev_road = str(stop_table[i - 1].get("road") or "")
                if is_toll(prev_road) or "lingkar luar" in prev_road.lower() or "jorr" in prev_road.lower():
                    continue
                if stop_table[i]["name"] in (spec.get("toll_to"),) or stop_table[i - 1]["name"] in (spec.get("toll_from"),):
                    continue
                non_toll.append(stop_table[i]["distance_from_previous_km"])
            spacing_pass = (not non_toll) or (max(non_toll) <= 2.4 and min(non_toll) >= 0.7)
        else:
            spacing_pass = max_gap <= 2.4 and min_gap >= 0.7 if gaps else False
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
                "segments": len(gf),
                "conf": conf,
                "method": method,
                "roads": roads,
                "stop_table": stop_table,
                "max_gap": max_gap,
                "min_gap": min_gap,
                "mean_gap": mean_gap,
                "spacing_pass": spacing_pass,
                "warnings": [w["issue"] for w in warnings_all if w["route"] == spec["id"]],
                "osm_alias": spec.get("osm_alias") or {},
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
                "parent_route": spec.get("parent_route") or "",
                "alignment_type": spec.get("alignment_type"),
                "bus_lane": "NOT_ASSUMED",
                "bbox": bbox_of(geom),
            }
        )

    keep_leftovers(route_feats, stop_feats, meta, reports)

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
        "deleted": ["CAS-06 Marunda–Pinang Ranti", "CAS-07 id retired → CAS-TJ06", "OLD CAS-07 Pinang Ranti–Harjamukti"],
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
                "CAS-TJ01..CAS-TJ06 (revisi road-trace) plus CAS-08..CAS-12 (Output 17, tidak diubah pada pass ini). "
                "CAS-TJ06 = rename CAS-07 Puri Beta–Monas. Tidak ada CAS-06. BRT trunk usulan #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    print("\n=== SUMMARY ===")
    for r in reports:
        print(f"{r['id']:10} {r['km']} km  stops={r['stops']} vtx={r['vertices']}  {r['method']}  {r['conf']}")
        if r.get("warnings"):
            for w in r["warnings"]:
                print("   ", w)
    print("routes", len(route_feats), "stops", len(stop_feats))
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    assert "CAS-TJ06" in ids
    assert "CAS-TJ07" not in ids
    assert "CAS-07" not in ids
    assert "CAS-06" not in ids


if __name__ == "__main__":
    main()
