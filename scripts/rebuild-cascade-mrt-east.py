#!/usr/bin/env python3
"""Rebuild CAS-MRT-C01 eastern geometry only: Depok Baru → Ancol via
Kelapa Dua → RA Fadillah → Kesehatan → TB Simatupang → Condet → PGC →
Dewi Sartika → Otista → Jatinegara Barat → Matraman → Pramuka → Kramat Raya →
Senen → Gunung Sahari → Ancol.

Does NOT go via Cibubur / Ciracas / Pasar Rebo / Kampung Rambutan.
Does NOT touch: masterplan, existing, CAS-TJ, CAS-LRT, CAS-MRT-C01-A, CAS-MRT-C01-BR02, KRL-C03.
South of Depok Baru (Lebak Bulus–Ciputat–Parung–Sawangan–Depok) is spliced from current C01.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-13"
SOURCE = "CASCADE MRT C01 — usulan analisis, bukan masterplan, bukan MRT Jakarta existing"

spec_m = importlib.util.spec_from_file_location("mrtb", ROOT / "scripts/rebuild-cascade-mrt.py")
mrtb = importlib.util.module_from_spec(spec_m)
spec_m.loader.exec_module(mrtb)

haversine = mrtb.haversine
length_m = mrtb.length_m
feat_line = mrtb.feat_line
feat_pt = mrtb.feat_pt
fc = mrtb.fc
densify = mrtb.densify
densify_line = mrtb.densify_line
clean_chain = mrtb.clean_chain
flatten = mrtb.flatten
hop = mrtb.hop
join_slices = mrtb.join_slices
snap_station = mrtb.snap_station
point_at = mrtb.point_at
nearest_along = mrtb.nearest_along
qa = mrtb.qa
bbox_of = mrtb.bbox_of
inject_node = mrtb.inject_node
merge_named = mrtb.merge_named
tja = mrtb.tja

TJ_HASH = dict(mrtb.TJ_HASH)
LRT_HASH = dict(mrtb.LRT_HASH)
READONLY_FILES = dict(mrtb.READONLY_FILES)
FROZEN_OTHER = {
    "CAS-MRT-C01-A": "ae3767b7fef3",
    "CAS-MRT-C01-BR02": "31ebf64e5ec5",
    "KRL-C03-N": "711afcad81d6",
    "KRL-C03-S": "c6ce84ce0d82",
}

DEPOK = (106.82169, -6.39113)
MARGONDA = (106.83209, -6.36895)
KELAPA_DUA = (106.84313, -6.36508)
KELAPA_DUA_UTARA = (106.84286, -6.35486)
RA_FADILLAH_SELATAN = (106.84387, -6.33703)
RA_FADILLAH_MID = (106.84573, -6.33381)
CIJANTUNG = (106.86063, -6.31313)
KESEHATAN = (106.85916, -6.30534)
KESEHATAN_UTARA = (106.85897, -6.30231)
CONDET_SELATAN = (106.85635, -6.30248)
CONDET = (106.85504, -6.27757)
PGC = (106.86570, -6.26190)
OTISTA = (106.86882, -6.24382)
KAMPUNG_MELAYU = (106.86682, -6.22467)
MATRAMAN = (106.86070, -6.21212)
PRAMUKA = (106.86620, -6.19241)
KRAMAT_RAYA = (106.84450, -6.18200)
SENEN = (106.84410, -6.17276)
GUNUNG_SAHARI = (106.83800, -6.15000)
ANCOL = (106.84646, -6.12786)

KR_FORBIDDEN = (106.88215, -6.30988)
CIRACAS_FORBIDDEN = (106.87050, -6.32900)
PASAR_REBO_FORBIDDEN = (106.86820, -6.32350)

KEEP_EAST = (
    "kelapa", "jasin", "fadil", "kesehatan", "condet", "dewi sartika",
    "otto", "jatinegara", "matraman", "pramuka", "kramat", "senen",
    "gunung sahari", "simatupang", "margonda", "benyamin", "lodan",
    "suprapto", "pasar senen",
)
SKIP_EAST = ("raya bogor", "tanah merdeka", "akses marunda", "pondok pinang")

NOTE = (
    "CAS-MRT-C01 mainline usulan CASCADE: Lebak Bulus–Ciputat (BRANCH)–Parung–Sawangan (BRANCH)–"
    "Depok Baru–Margonda–Kelapa Dua–Jalan RA Fadillah–Jalan Kesehatan–TB Simatupang–"
    "Jalan Raya Condet–PGC–Dewi Sartika–Otista–Jatinegara Barat–Matraman Raya–Pramuka–"
    "Kramat Raya–Senen–Pasar Senen–Gunung Sahari–Ancol. "
    "Bukan lewat Cibubur, Ciracas, Pasar Rebo, atau Kampung Rambutan. "
    "Bukan MRT existing. Bukan masterplan. Vertex kontrol ≠ otomatis stasiun."
)


def geom_hash(coords):
    return hashlib.sha256(json.dumps(coords, separators=(",", ":")).encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def load_east_roads():
    road_map = mrtb.load_mrt_roads()
    extra_path = OUT / "extra_roads_mrt_east.geojson"
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        name = (f.get("properties") or {}).get("name") or "extra"
        low = name.lower()
        if any(s in low for s in SKIP_EAST):
            continue
        if not any(k in low for k in KEEP_EAST):
            continue
        buckets.setdefault(name, []).extend(flatten(g))
    east_clip = ("dewi sartika", "otista raya", "lodan")
    bbox = (106.830, -6.380, 106.878, -6.118)

    def clip_runs(runs):
        minx, miny, maxx, maxy = bbox
        out = []
        for r in runs:
            pr = [p for p in r if minx <= p[0] <= maxx and miny <= p[1] <= maxy]
            if len(pr) >= 2:
                out.append(pr)
        return out or runs

    for name, parts in buckets.items():
        if any(k in name.lower() for k in east_clip):
            parts = clip_runs(parts)
        merged = merge_named(parts, max_gap=360)
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            if any(k in name.lower() for k in east_clip):
                old = clip_runs(old)
            merged = merge_named(old + merged, max_gap=360)
        if not merged:
            continue
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "MultiLineString", "coordinates": merged} if len(merged) > 1 else {"type": "LineString", "coordinates": merged[0]},
        }
    if "Jalan Dewi Sartika" in road_map:
        runs = clip_runs(flatten(road_map["Jalan Dewi Sartika"]["geometry"]))
        if runs:
            road_map["Jalan Dewi Sartika"]["geometry"] = (
                {"type": "MultiLineString", "coordinates": runs} if len(runs) > 1 else {"type": "LineString", "coordinates": runs[0]}
            )
    return road_map


def walk_east(controls, road_map, min_loop=2200.0):
    chain = []
    notes = []
    types = []
    roads = []
    segments = []
    for i in range(len(controls) - 1):
        a_name, a, names, _st = controls[i]
        b_name, b, _, _ = controls[i + 1]
        sl, atype, rname = hop(a, b, road_map, names, notes)
        print(f"  {a_name} → {b_name}: {atype} {rname} {length_m(sl)/1000:.2f} km")
        types.append(atype)
        if atype != "NEW_ROW" and rname and rname not in roads and rname not in ("FORCE_OSRM", "NEW_ROW", "osrm", "new_row", "link"):
            roads.append(rname)
        joined, how = join_slices(chain, sl)
        if joined is None:
            chain = chain + densify(chain[-1], sl[0], 30)[1:] + sl[1:] if chain else sl
            notes.append(f"forced-join {how} {a_name}-{b_name}")
        else:
            chain = joined
        segments.append(
            {
                "segment_id": f"{i+1:02d}",
                "from_node": a_name,
                "to_node": b_name,
                "road_name": rname,
                "alignment_type": atype,
                "length_km": round(length_m(sl) / 1000, 2),
            }
        )
    chain = densify_line(clean_chain(chain), 45)
    chain = tja.rc.remove_loops(chain, rejoin_m=80.0, min_loop=min_loop)
    start, end = controls[0][1], controls[-1][1]
    if chain:
        if haversine(chain[0], start) > 12:
            chain = densify(start, chain[0], 20)[:-1] + chain
        chain[0] = list(start)
        if haversine(chain[-1], end) > 12:
            chain = chain + densify(chain[-1], end, 20)[1:]
        chain[-1] = list(end)
    chain = densify_line(clean_chain(chain), 45)
    alignment = "VIADUCT"
    return chain, notes, roads, alignment, segments


def east_controls():
    return [
        ("Depok Baru", DEPOK, ["Jalan Raya Margonda", "Jalan Margonda Raya", "FORCE_OSRM"], True),
        ("Margonda Selatan", (106.82850, -6.38000), ["Jalan Raya Margonda", "Jalan Margonda Raya", "FORCE_OSRM"], False),
        ("Margonda", MARGONDA, ["Jalan Raya Margonda", "Jalan Kelapa Dua Raya", "FORCE_OSRM"], False),
        ("Kelapa Dua", KELAPA_DUA, ["Jalan Kelapa Dua Raya", "Jalan Komjen Pol. M. Jasin"], False),
        ("Kelapa Dua Utara", KELAPA_DUA_UTARA, ["NEW_ROW", "Jalan Kelapa Dua Raya", "Jalan RA. Fadillah"], False),
        ("RA Fadillah Selatan", RA_FADILLAH_SELATAN, ["Jalan RA. Fadillah"], False),
        ("RA Fadillah", RA_FADILLAH_MID, ["Jalan RA. Fadillah"], False),
        ("Cijantung", CIJANTUNG, ["Jalan RA. Fadillah", "Jalan Kesehatan", "FORCE_OSRM"], False),
        ("Kesehatan", KESEHATAN, ["Jalan Kesehatan", "Jalan Tahi Bonar Simatupang", "Jalan Condet Raya"], False),
        ("TB Simatupang", KESEHATAN_UTARA, ["Jalan Tahi Bonar Simatupang", "Jalan Condet Raya", "Jalan Kesehatan"], False),
        ("Condet Selatan", CONDET_SELATAN, ["Jalan Condet Raya"], False),
        ("Condet", CONDET, ["Jalan Condet Raya"], False),
        ("Condet Utara", (106.86001, -6.26754), ["Jalan Condet Raya", "Jalan Dewi Sartika"], False),
        ("PGC", PGC, ["NEW_ROW", "Jalan Dewi Sartika", "Jalan Otto Iskandar Dinata"], False),
        ("Cililitan", (106.86650, -6.25200), ["NEW_ROW", "Jalan Dewi Sartika", "Jalan Otto Iskandar Dinata"], False),
        ("Otista", OTISTA, ["NEW_ROW", "Jalan Otto Iskandar Dinata"], False),
        ("Otista Utara", (106.86850, -6.23200), ["NEW_ROW", "Jalan Otto Iskandar Dinata", "Jalan Jatinegara Barat Raya"], False),
        ("Jatinegara Barat", KAMPUNG_MELAYU, ["Jalan Jatinegara Barat Raya", "Jalan Matraman"], False),
        ("Matraman", MATRAMAN, ["Jalan Matraman", "Jalan Pramuka", "FORCE_OSRM"], False),
        ("Pramuka", PRAMUKA, ["Jalan Pramuka"], False),
        ("Pramuka Barat", (106.85000, -6.19120), ["Jalan Pramuka", "Jalan Kramat Raya", "FORCE_OSRM"], False),
        ("Kramat Raya", KRAMAT_RAYA, ["Jalan Kramat Raya", "FORCE_OSRM"], False),
        ("Senen", SENEN, ["NEW_ROW", "Jalan Pasar Senen", "Jalan Gunung Sahari Raya"], False),
        ("Gunung Sahari", GUNUNG_SAHARI, ["FORCE_OSRM", "Jalan Gunung Sahari Raya", "Jalan Benyamin Sueb"], False),
        ("Kemayoran Utara", (106.84600, -6.14500), ["FORCE_OSRM", "Jalan Benyamin Sueb", "Jalan Lodan Raya"], False),
        ("Ancol", ANCOL, ["Jalan Benyamin Sueb", "Jalan Lodan Raya"], False),
    ]


EAST_SEEDS = [
    ("Margonda", MARGONDA, {"node_type": "URBAN_NODE", "activity_type": "COMMERCIAL", "placement_reason": "ACTIVITY_CENTER"}),
    ("Kelapa Dua", KELAPA_DUA, {"node_type": "URBAN_NODE", "placement_reason": "URBAN_NODE"}),
    ("RA Fadillah", RA_FADILLAH_MID, {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("Cijantung", (106.86191, -6.31215), {"node_type": "MAJOR_DESTINATION", "activity_type": "MALL", "placement_reason": "ACTIVITY_CENTER"}),
    ("Condet", CONDET, {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("PGC", PGC, {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT", "placement_reason": "EXISTING_CONNECTION"}),
    ("Cililitan", (106.86650, -6.25200), {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("Otista", OTISTA, {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("Kampung Melayu", KAMPUNG_MELAYU, {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT", "placement_reason": "EXISTING_CONNECTION"}),
    ("Matraman", MATRAMAN, {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("Pramuka", PRAMUKA, {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT", "placement_reason": "EXISTING_CONNECTION"}),
    ("Senen", SENEN, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "INTERCHANGE", "placement_reason": "EXISTING_CONNECTION"}),
    ("Gunung Sahari", GUNUNG_SAHARI, {"node_type": "URBAN_NODE", "placement_reason": "ACTIVITY_CENTER"}),
    ("Ancol", ANCOL, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "TERMINUS", "placement_reason": "TERMINUS"}),
]


def scan_east(geom, depok_along, min_gap=1200.0, max_gap=3200.0):
    tot = length_m(geom)
    snapped = []
    for name, pt, extra in EAST_SEEDS:
        ppt, along, d, _tot, on_curve = snap_station(geom, pt)
        if d > 480:
            print(f"  seed skip {name} off {d:.0f}m")
            continue
        if along < depok_along + 350:
            continue
        rec = {
            "stop_name": name,
            "lon": ppt[0],
            "lat": ppt[1],
            "along_m": along,
            "existing": extra.get("existing", "NO"),
            "interchange": extra.get("interchange", "NO"),
            "interchange_mode": extra.get("interchange_mode", ""),
            "name_confidence": extra.get("name_confidence", "HIGH"),
            "placement_reason": extra.get("placement_reason", "ACTIVITY_CENTER"),
            "station_on_curve": "YES" if on_curve else "NO",
            "node_type": extra.get("node_type", "STATION"),
            "activity_type": extra.get("activity_type", ""),
        }
        snapped.append(rec)
    snapped.sort(key=lambda r: r["along_m"])
    kept = []
    for rec in snapped:
        if kept and rec["along_m"] - kept[-1]["along_m"] < min_gap:
            if rec.get("interchange") == "YES" and kept[-1].get("interchange") != "YES":
                kept[-1] = rec
            continue
        kept.append(rec)
    if kept:
        kept[-1]["lon"], kept[-1]["lat"] = geom[-1][0], geom[-1][1]
        kept[-1]["along_m"] = tot
        kept[-1]["placement_reason"] = "TERMINUS"
    return kept


def south_stops_from_existing(old_stops, geom, depok_along):
    feats = [f for f in old_stops if str(f["properties"].get("route_id")) == "CAS-MRT-C01"]
    out = []
    for f in sorted(feats, key=lambda x: x["properties"].get("stop_order", 0)):
        name = f["properties"].get("stop_name") or f["properties"].get("name")
        pt = f["geometry"]["coordinates"]
        ppt, along, d, _tot, on_curve = snap_station(geom, pt)
        if along > depok_along + 200:
            continue
        extra = {
            "stop_name": name,
            "lon": ppt[0],
            "lat": ppt[1],
            "along_m": along,
            "existing": f["properties"].get("existing", "NO"),
            "interchange": f["properties"].get("interchange", "NO"),
            "interchange_mode": f["properties"].get("interchange_mode", ""),
            "name_confidence": f["properties"].get("name_confidence", "HIGH"),
            "placement_reason": f["properties"].get("placement_reason", "SERVICE_NODE"),
            "station_on_curve": "YES" if on_curve else "NO",
            "node_type": f["properties"].get("node_type", "STATION"),
        }
        out.append(extra)
    if out:
        out[0]["lon"], out[0]["lat"] = geom[0][0], geom[0][1]
        out[0]["along_m"] = 0.0
        out[0]["placement_reason"] = "TERMINUS"
        out[-1]["stop_name"] = "Depok Baru"
        out[-1]["lon"], out[-1]["lat"] = DEPOK[0], DEPOK[1]
        out[-1]["along_m"] = depok_along
        out[-1]["existing"] = "YES"
        out[-1]["interchange"] = "YES"
        out[-1]["interchange_mode"] = "KRL"
        out[-1]["node_type"] = "MAJOR_TRANSIT"
        out[-1]["placement_reason"] = "EXISTING_CONNECTION"
    return out


def replace_c01_only(feats, new_feats):
    kept = []
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id") or "")
        rid = str(f["properties"].get("route_id") or f["properties"].get("id") or "")
        if fid.startswith("CAS-MRT-C01-A") or rid.startswith("CAS-MRT-C01-A"):
            kept.append(f)
            continue
        if fid.startswith("CAS-MRT-C01-BR") or rid.startswith("CAS-MRT-C01-BR"):
            kept.append(f)
            continue
        if fid == "CAS-MRT-C01" or rid == "CAS-MRT-C01":
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
    for k, h in FROZEN_OTHER.items():
        if before.get(k) != h:
            raise SystemExit(f"FROZEN drifted: {k} {before.get(k)}")
    print("TJ+LRT+C01-A+BR02+KRL frozen OK")

    c01 = next(f for f in old_routes["features"] if str(f.get("id") or f["properties"].get("route_id")) == "CAS-MRT-C01")
    old_geom = [list(p) for p in c01["geometry"]["coordinates"]]
    depok_idx = min(range(len(old_geom)), key=lambda i: haversine(old_geom[i], DEPOK))
    south = old_geom[: depok_idx + 1]
    south[-1] = list(DEPOK)
    print(f"splicing south vtx={len(south)} to Depok Baru")

    print("loading roads...")
    road_map = load_east_roads()

    print("walking Depok Baru → Ancol (koridor timur)")
    ce = east_controls()
    geom_e, notes_e, roads_e, align_e, segs_e = walk_east(ce, road_map, min_loop=2200.0)
    geom_e = inject_node(geom_e, DEPOK, max_off=400)
    geom_e = inject_node(geom_e, CONDET, max_off=800)
    geom_e = inject_node(geom_e, PGC, max_off=800)
    geom_e = inject_node(geom_e, ANCOL, max_off=400)
    geom_e = densify_line(clean_chain(geom_e), 45)

    geom = south[:-1] + geom_e
    geom = densify_line(clean_chain(geom), 45)
    geom[0] = list((106.77493, -6.28930))
    geom[-1] = list(ANCOL)
    depok_along = nearest_along(DEPOK, geom)[1]
    print(f"  full vtx={len(geom)} km={length_m(geom)/1000:.2f} depok_along={depok_along/1000:.2f}")

    d_kr = min(haversine(p, KR_FORBIDDEN) for p in geom)
    d_cir = min(haversine(p, CIRACAS_FORBIDDEN) for p in geom)
    d_pr = min(haversine(p, PASAR_REBO_FORBIDDEN) for p in geom)
    d_condet = min(haversine(p, CONDET) for p in geom)
    d_pgc = min(haversine(p, PGC) for p in geom)
    d_kd = min(haversine(p, KELAPA_DUA) for p in geom)
    print(f"  dist KR={d_kr:.0f} Ciracas={d_cir:.0f} PasarRebo={d_pr:.0f} Condet={d_condet:.0f} PGC={d_pgc:.0f} KelapaDua={d_kd:.0f}")
    assert d_kr > 1400, f"too close to Kampung Rambutan {d_kr:.0f}m"
    assert d_cir > 700, f"too close to Ciracas {d_cir:.0f}m"
    assert d_condet < 250, f"missed Condet {d_condet:.0f}m"
    assert d_pgc < 200, f"missed PGC {d_pgc:.0f}m"
    assert d_kd < 250, f"missed Kelapa Dua {d_kd:.0f}m"
    assert haversine(geom[-1], ANCOL) < 40
    assert min(haversine(p, (106.74720, -6.31250)) for p in geom) < 80, "lost Ciputat"
    max_lon_east = max(p[0] for p in geom if p[1] < -6.30 and p[1] > -6.36)
    assert max_lon_east < 106.872, f"east bulge lon {max_lon_east} looks like Raya Bogor/Cibubur"

    qa_e = qa(geom, "MAIN-EAST")
    south_st = south_stops_from_existing(old_stops["features"], geom, depok_along)
    east_st = scan_east(geom, depok_along)
    # drop east seeds that collide with Depok
    east_st = [s for s in east_st if s["along_m"] > depok_along + 400]
    stops = south_st + east_st
    forbidden_names = {"Kampung Rambutan", "Ciracas", "Pasar Rebo", "Cibubur", "Cimanggis", "Tanah Merdeka", "Kramat Jati"}
    stops = [s for s in stops if s["stop_name"] not in forbidden_names]
    assert all(s["stop_name"] not in forbidden_names for s in stops)
    print("  stations:", " → ".join(s["stop_name"] for s in stops))

    km = round(length_m(geom) / 1000, 2)
    conf = mrtb.confidence(notes_e, km, haversine((106.77493, -6.28930), ANCOL) / 1000)
    spec = dict(
        id="CAS-MRT-C01",
        name="Lebak Bulus – Ancol",
        short="Lebak Bulus – Ancol",
        from_name="Lebak Bulus",
        to_name="Ancol",
        direction="Lebak Bulus → Ancol",
        branch_id="MAIN",
        branch_name="Mainline Lebak Bulus – Ancol",
        parent_route="",
        note=NOTE,
    )
    # rebuild stop along_m unique
    for i, s in enumerate(stops):
        if i and s["along_m"] < stops[i - 1]["along_m"] + 80:
            s["along_m"] = stops[i - 1]["along_m"] + 250
            p = list(point_at(geom, s["along_m"]))
            s["lon"], s["lat"] = p[0], p[1]
    rf, km = mrtb.make_route_feature(spec, geom, stops, len(ce) + 12, conf, "VIADUCT", roads_e, NOTE, 20)
    rf["properties"]["planning_note"] = NOTE
    rf["properties"]["notes"] = NOTE
    rf["properties"]["stop_count"] = len(stops)
    sf = mrtb.make_stop_features(spec, geom, stops, conf, "VIADUCT", roads_e, NOTE, km)

    route_feats = replace_c01_only(old_routes["features"], [rf])
    stop_feats = replace_c01_only(old_stops["features"], sf)
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    for need in ("CAS-TJ07", "CAS-LRT-C02", "CAS-MRT-C01", "CAS-MRT-C01-A", "CAS-MRT-C01-BR02", "KRL-C03-N"):
        assert need in ids, f"missing {need}"

    after = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in TJ_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"TJ DRIFT {k}")
    for k, h in LRT_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"LRT DRIFT {k}")
    for k, h in FROZEN_OTHER.items():
        if after.get(k) != h:
            raise SystemExit(f"FROZEN DRIFT {k}")

    meta = [m for m in (old_meta.get("corridors") or []) if str(m.get("id")) != "CAS-MRT-C01"]
    meta_c01 = {
        "id": "CAS-MRT-C01",
        "name": "Lebak Bulus – Ancol",
        "short": "Lebak Bulus – Ancol",
        "endpoint": "Lebak Bulus – Ancol",
        "from_name": "Lebak Bulus",
        "to_name": "Ancol",
        "direction": "Lebak Bulus → Ancol",
        "mode": "mrt",
        "branch_id": "MAIN",
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": SOURCE,
        "status": "PROPOSED",
        "network_type": "MRT",
        "plan_type": "NEW_TRUNK",
        "alignment_type": "VIADUCT",
        "road_backbone": ", ".join(roads_e),
        "notes": NOTE,
        "bbox": bbox_of(geom),
    }
    # keep C01-A / BR02 / others, insert C01 near other MRT
    inserted = False
    new_meta = []
    for m in meta:
        if not inserted and str(m.get("id", "")).startswith("CAS-MRT"):
            new_meta.append(meta_c01)
            inserted = True
        new_meta.append(m)
    if not inserted:
        new_meta.append(meta_c01)

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["corridors"] = new_meta
    existing["mrt_note"] = (
        "CAS-MRT-C01 mainline Lebak Bulus–Ancol via Kelapa Dua–RA Fadillah–Condet "
        "(bukan Kampung Rambutan) + branch Sawangan–Fatmawati + branch Ciputat–BSD–ICE. "
        "Bukan MRT existing. Bukan masterplan."
    )
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_mrt_east_segments.json").write_text(json.dumps({"east": segs_e, "notes": notes_e}, ensure_ascii=False, indent=2))

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "corridors": [meta_c01],
        "qa": qa_e,
        "notes_east": notes_e,
        "forbidden_km": {"kampung_rambutan_m": round(d_kr, 1), "ciracas_m": round(d_cir, 1), "pasar_rebo_m": round(d_pr, 1)},
        "tj_frozen": TJ_HASH,
        "lrt_frozen": LRT_HASH,
        "frozen_other": FROZEN_OTHER,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "hashes": {"CAS-MRT-C01": after["CAS-MRT-C01"]},
        "stops": [s["stop_name"] for s in stops],
    }
    (OUT / "cascade_validation_mrt_east.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))

    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"CAS-MRT-C01  {km} km  stations={len(stops)}  {conf}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops))
    print("C01-A + BR02 + KRL + TJ + LRT frozen  masterplan/existing untouched")
    print("ids", ids)


if __name__ == "__main__":
    main()
