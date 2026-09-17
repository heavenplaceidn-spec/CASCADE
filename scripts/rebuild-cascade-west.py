#!/usr/bin/env python3
"""Rebuild CASCADE KRL-C03-N / KRL-C03-S and add CAS-MRT-C01-BR02.

Does NOT touch: masterplan, existing transport, CAS-TJ, CAS-LRT, CAS-MRT-C01, CAS-MRT-C01-A.

Fixes vs prior west pass:
- Taman Kota 2 is the Tekno / Jl. Tekno Widya park (106.68165, -6.32869), NOT Taman Kota 1.
- KRL leaves Stasiun Tangerang on NEW_ROW (rail continuation), not Imam Bonjol south-loop.
- KRL-S stays on Curug–Legok–Parung Panjang, not Legok–Karawaci into BSD internals.
- MRT BR02: Siliwangi west → TK2 south → Pahlawan Seribu north to Rawa Buntu → Grand Boulevard to ICE.
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
MRT_HASH = {"CAS-MRT-C01": "dc113144e7e7", "CAS-MRT-C01-A": "ae3767b7fef3"}
READONLY_FILES = dict(mrtb.READONLY_FILES)

TANGERANG = (106.63072, -6.17681)
PARUNG_PANJANG = (106.56869, -6.34425)
RAWA_BUNTU = (106.67505, -6.31551)
CIPUTAT = (106.74720, -6.31250)
ICE_BSD = (106.63657, -6.30068)
TAMAN_KOTA_2 = (106.68165, -6.32869)
BSD_CBD = (106.65437, -6.30126)
RAJEG = (106.51823, -6.11275)
MAUK = (106.51287, -6.05161)
KUTABUMI = (106.56390, -6.15086)
CIMONE = (106.61078, -6.19167)
BITUNG = (106.57500, -6.20800)
CURUG = (106.56595, -6.23906)
LEGOK = (106.57466, -6.30248)
PAMULANG = (106.73800, -6.34300)
SILIWANGI = (106.71509, -6.34575)

KEEP_EXTRA = (
    "kutabumi", "kutajaya", "rajeg", "mauk", "gatot", "curug", "legok",
    "parung panjang", "siliwangi", "pahlawan", "boulevard", "serpong",
    "sutopo", "bonjol", "martadinata", "kemis", "imam", "ciputat",
    "pamulang", "tekno", "buaran", "ciater", "pelayangan", "utama",
    "plp", "bitung", "cimone",
)
SKIP_EXTRA = ("anggur", "apel", "sriwijaya", "sdn", "gang", "alpukat", "durian", "jati raya", "havena", "briza")

SRC_KRL = "CASCADE KRL C03 — perpanjangan barat, bukan masterplan, bukan KRL existing"
SRC_MRT = "CASCADE MRT C01-BR02 — cabang Ciputat–BSD–ICE, bukan masterplan, bukan MRT existing"


def geom_hash(coords):
    return hashlib.sha256(json.dumps(coords, separators=(",", ":")).encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def load_west_roads():
    road_map = mrtb.load_mrt_roads()
    extra_path = OUT / "extra_roads_west.geojson"
    extra = json.loads(extra_path.read_text()) if extra_path.exists() else {"features": []}
    buckets = {}
    for f in extra["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        name = (f.get("properties") or {}).get("name") or "extra"
        low = name.lower()
        if any(s in low for s in SKIP_EXTRA):
            continue
        if not any(k in low for k in KEEP_EXTRA):
            continue
        buckets.setdefault(name, []).extend(flatten(g))
    for name, parts in buckets.items():
        merged = merge_named(parts, max_gap=360)
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            merged = merge_named(old + merged, max_gap=360)
        if not merged:
            continue
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "MultiLineString", "coordinates": merged} if len(merged) > 1 else {"type": "LineString", "coordinates": merged[0]},
        }
    return road_map


def crossing_of(a_name, b_name, rname):
    low = f"{a_name} {b_name} {rname or ''}".lower()
    if any(k in low for k in ("bitung", "curug", "tol", "serang", "kunciran")):
        return "GRADE_SEPARATED"
    if any(k in low for k in ("rawa buntu", "pahlawan", "boulevard", "ice")):
        return "VIADUCT"
    return "AT_GRADE"


def walk_controls(controls, road_map, min_loop=2200.0):
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
        if (
            atype != "NEW_ROW"
            and rname
            and rname not in roads
            and rname not in ("FORCE_OSRM", "NEW_ROW", "osrm", "new_row", "link")
        ):
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
                "alignment_type": atype if atype != "NEW_ROW" else "RAIL_CORRIDOR",
                "length_km": round(length_m(sl) / 1000, 2),
                "crossing_type": crossing_of(a_name, b_name, rname),
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
    n_new = types.count("NEW_ROW")
    alignment = "NEW_ROW" if n_new > len(types) / 2 else "RAIL_CORRIDOR"
    return chain, notes, roads, alignment, segments


def build_stops(geom, stations):
    out = []
    tot = length_m(geom)
    for i, (sname, spt, extra) in enumerate(stations):
        ppt, along, d, _tot, on_curve = snap_station(geom, spt)
        if out and along < out[-1]["along_m"] + 80:
            along = min(tot - 20, out[-1]["along_m"] + 250)
            ppt = list(point_at(geom, along))
        rec = {
            "stop_name": sname,
            "lon": ppt[0],
            "lat": ppt[1],
            "along_m": along,
            "existing": extra.get("existing", "NO"),
            "interchange": extra.get("interchange", "NO"),
            "interchange_mode": extra.get("interchange_mode", ""),
            "name_confidence": extra.get("name_confidence", "HIGH"),
            "placement_reason": extra.get("placement_reason", "SERVICE_NODE"),
            "station_on_curve": "YES" if on_curve else "NO",
            "node_type": extra.get("node_type", "STATION"),
            "activity_type": extra.get("activity_type", ""),
        }
        out.append(rec)
    out[0]["lon"], out[0]["lat"] = geom[0][0], geom[0][1]
    out[0]["along_m"] = 0.0
    out[0]["placement_reason"] = "TERMINUS" if out[0].get("node_type") == "TERMINUS" else out[0]["placement_reason"]
    out[-1]["lon"], out[-1]["lat"] = geom[-1][0], geom[-1][1]
    out[-1]["along_m"] = tot
    out[-1]["placement_reason"] = "TERMINUS"
    return out, tot


def confidence(notes, km, straight_km):
    conf = "HIGH"
    new_n = sum(1 for n in notes if n.startswith("NEW_ROW"))
    if new_n >= 5:
        conf = "MEDIUM"
    if new_n >= 9:
        conf = "REVIEW"
    if straight_km > 0 and km > 2.8 * straight_km:
        conf = "MEDIUM"
        notes.append(f"length {km} vs straight {straight_km:.1f}")
    return conf


def common_props(spec, km, n_stops, conf, alignment, roads, note):
    return {
        "id": spec["id"],
        "route_id": spec["id"],
        "corridor_id": spec["corridor_id"],
        "corridor_name": spec["corridor_name"],
        "branch_id": spec.get("branch_id", ""),
        "branch_name": spec.get("branch_name", ""),
        "name": spec["name"],
        "short": spec["short"],
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "start_name": spec["from_name"],
        "end_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": spec["mode"],
        "status": spec["status"],
        "status_label": spec["status_label"],
        "cascade_status": spec["status"],
        "network_type": spec.get("network_type", "TRUNK"),
        "plan_type": spec.get("plan_type", "NEW_TRUNK"),
        "existing": "NO",
        "parent_route": spec.get("parent_route", ""),
        "length_km": km,
        "stop_count": n_stops,
        "geometry_confidence": conf,
        "road_alignment_confidence": conf,
        "alignment_confidence": conf,
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "rail_backbone": spec.get("rail_backbone", ""),
        "color": COLOR,
        "crs": CRS,
        "source": spec["source"],
        "source_type": "AI_RECONSTRUCTED",
        "geometry_source": "OSM named arterials + OSRM road-follow; NEW_ROW / RAIL_CORRIDOR if road network fails",
        "planning_note": note,
        "disclaimer": spec["disclaimer"],
        "updated_at": RETRIEVED,
        "notes": note,
    }


def make_route(spec, geom, stops, vertices_n, conf, alignment, roads, note, order):
    km = round(length_m(geom) / 1000, 2)
    props = common_props(spec, km, len(stops), conf, alignment, roads, note)
    props.update(
        {
            "route_order": order,
            "vertex_count": len(geom),
            "control_vertex_count": vertices_n,
            "interchange_count": sum(1 for s in stops if s["interchange"] == "YES"),
            "digitization_level": "L3",
            "endpoint": f"{spec['from_name']} – {spec['to_name']}",
            "structure": spec.get("structure", "AT_GRADE"),
        }
    )
    return feat_line(spec["id"], geom, props), km


def make_stops(spec, geom, stops, conf, alignment, roads, note, common_km):
    feats = []
    for i, s in enumerate(stops):
        order = i + 1
        dist_prev = round((s["along_m"] - stops[i - 1]["along_m"]) / 1000, 2) if i else 0.0
        dist_next = round((stops[i + 1]["along_m"] - s["along_m"]) / 1000, 2) if i < len(stops) - 1 else 0.0
        stop_type = "TERMINUS" if i in (0, len(stops) - 1) else "INTERCHANGE" if s["interchange"] == "YES" else "STATION"
        sid = f"{spec['id']}-S{order:02d}"
        props = common_props(spec, common_km, len(stops), conf, alignment, roads, note)
        props.update(
            {
                "stop_id": sid,
                "stop_order": order,
                "stop_name": s["stop_name"],
                "name": s["stop_name"],
                "stop_type": stop_type,
                "node_type": s.get("node_type") or stop_type,
                "existing": s["existing"],
                "interchange": s["interchange"],
                "interchange_mode": s["interchange_mode"],
                "station_on_curve": s["station_on_curve"],
                "placement_reason": s["placement_reason"],
                "name_confidence": s["name_confidence"],
                "activity_type": s.get("activity_type", ""),
                "distance_from_previous_stop": dist_prev,
                "distance_to_next_stop": dist_next,
                "note": spec.get("stop_note", "Stasiun usulan CASCADE. Bukan stasiun resmi. Vertex kontrol ≠ otomatis stasiun."),
            }
        )
        feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
    return feats


def pack(spec, geom, controls, stations, notes, roads, alignment, order):
    stops, tot = build_stops(geom, stations)
    km = round(tot / 1000, 2)
    straight = haversine(controls[0][1], controls[-1][1]) / 1000
    conf = confidence(notes, km, straight)
    rf, km = make_route(spec, geom, stops, len(controls), conf, alignment, roads, spec["note"], order)
    sf = make_stops(spec, geom, stops, conf, alignment, roads, spec["note"], km)
    meta = {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": spec["mode"],
        "branch_id": spec.get("branch_id", ""),
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": spec["source"],
        "status": spec["status"],
        "network_type": spec.get("network_type", "TRUNK"),
        "plan_type": spec.get("plan_type", "NEW_TRUNK"),
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "notes": spec["note"],
        "bbox": bbox_of(geom),
    }
    return rf, sf, stops, km, conf, meta


def krl_north_controls():
    # Rail continuation west of Stasiun Tangerang, then Pasar Kemis / Kutabumi / Rajeg / Mauk.
    # NEW_ROW first hop: do NOT use Imam Bonjol (that road is south of the station → visual loop).
    return [
        ("Tangerang", TANGERANG, ["NEW_ROW", "Jalan Imam Bonjol"], True),
        ("Tangerang Barat", (106.61820, -6.17580), ["NEW_ROW", "Jalan Gatot Subroto"], False),
        ("Poris", (106.59850, -6.17150), ["NEW_ROW"], False),
        ("Kunciran Barat", (106.58000, -6.16620), ["NEW_ROW", "Jalan Raya Kutabumi - Kutajaya"], False),
        ("Pasar Kemis", (106.55981, -6.16100), ["Jalan Raya Kutabumi - Kutajaya", "NEW_ROW"], False),
        ("Kutabumi", KUTABUMI, ["NEW_ROW", "Jalan Raya Rajeg", "Jalan Raya Kutabumi - Kutajaya"], True),
        ("Sukamantri", (106.54500, -6.14000), ["NEW_ROW", "Jalan Raya Rajeg"], False),
        ("Rajeg Selatan", (106.53200, -6.12800), ["Jalan Raya Rajeg", "Jalan Raya Rajeg - Mauk", "NEW_ROW"], False),
        ("Rajeg", RAJEG, ["Jalan Raya Rajeg - Mauk", "Jalan Raya Rajeg", "NEW_ROW"], True),
        ("Tamiang", (106.52000, -6.08700), ["Jalan Raya Rajeg - Mauk", "Jalan Raya Rajeg", "NEW_ROW"], False),
        ("Mauk", MAUK, ["NEW_ROW", "Jalan Raya Rajeg"], True),
    ]


def krl_south_controls():
    # Tangerang SW along Gatot Subroto to Cimone / Bitung, then PLP Curug south, then
    # Curug–Legok–Parung Panjang. Do not use Jalan Raya Legok-Karawaci (pulls east toward BSD).
    return [
        ("Tangerang", TANGERANG, ["NEW_ROW", "Jalan Imam Bonjol"], True),
        ("Cikokol Selatan", (106.62200, -6.18400), ["NEW_ROW", "Jalan Gatot Subroto"], False),
        ("Cimone", CIMONE, ["Jalan Gatot Subroto", "NEW_ROW"], True),
        ("Cimone Barat", (106.59000, -6.19800), ["Jalan Gatot Subroto", "NEW_ROW"], False),
        ("Bitung", BITUNG, ["NEW_ROW", "Jalan Gatot Subroto", "Jalan Raya PLP Curug"], True),
        ("Bitung Selatan", (106.56500, -6.22300), ["NEW_ROW", "Jalan Raya PLP Curug"], False),
        ("Curug", CURUG, ["NEW_ROW", "Jalan Raya PLP Curug", "Jalan Raya Curug KM 2"], True),
        ("Binong", (106.57000, -6.27000), ["NEW_ROW", "Jalan Raya Curug"], False),
        ("Legok", LEGOK, ["NEW_ROW", "Jalan Raya Curug"], True),
        ("Parung Panjang Utara", (106.57200, -6.32300), ["NEW_ROW", "Jalan Raya Curug"], False),
        ("Parung Panjang", PARUNG_PANJANG, ["NEW_ROW"], True),
    ]


def mrt_bsd_controls():
    # Ciputat (mainline) → Martadinata → Pamulang → Siliwangi west → Taman Kota 2 (Tekno)
    # → Pahlawan Seribu north to Rawa Buntu → west Grand Boulevard → CBD → ICE.
    return [
        ("Ciputat", CIPUTAT, ["Jalan Laksamana RE Martadinata", "Jalan Ciputat Raya"], True),
        ("Ciputat Selatan", (106.74850, -6.32800), ["Jalan Laksamana RE Martadinata", "FORCE_OSRM"], False),
        ("Pamulang", PAMULANG, ["Jalan Siliwangi", "Jalan Laksamana RE Martadinata", "FORCE_OSRM"], True),
        ("Siliwangi", SILIWANGI, ["Jalan Siliwangi", "NEW_ROW"], True),
        ("Pondok Jagung", (106.69800, -6.34400), ["NEW_ROW", "Jalan Buaran Raya", "Jalan Siliwangi"], False),
        ("Taman Kota 2", TAMAN_KOTA_2, ["Jalan Tekno Widya", "Jalan Buaran Raya", "Jalan Pahlawan Seribu", "NEW_ROW"], True),
        ("Rawa Buntu", RAWA_BUNTU, ["Jalan Pahlawan Seribu", "Jalan Letnan Sutopo", "FORCE_OSRM"], True),
        ("Pelayangan", (106.66800, -6.30400), ["Jalan Pahlawan Seribu", "Jalan BSD Grand Boulevard", "FORCE_OSRM"], False),
        ("Boulevard BSD Timur", (106.66200, -6.29820), ["Jalan BSD Grand Boulevard", "Jalan Pahlawan Seribu"], False),
        ("BSD CBD", BSD_CBD, ["Jalan BSD Grand Boulevard", "FORCE_OSRM"], True),
        ("ICE BSD Hall 10", ICE_BSD, ["Jalan BSD Grand Boulevard"], True),
    ]


NOTE_N = (
    "KRL-C03-N usulan CASCADE: Tangerang (node cabang, menumpang stasiun KRL existing)–Kutabumi–Rajeg–Mauk. "
    "Perpanjangan barat sebagai RAIL_CORRIDOR / NEW_ROW sejajar koridor Pasar Kemis, bukan Imam Bonjol. "
    "Bukan KRL Tangerang existing Duri–Tangerang. Bukan masterplan. "
    "Tangerang adalah BRANCH_NODE yang sama dengan KRL-C03-S."
)
NOTE_S = (
    "KRL-C03-S usulan CASCADE: Tangerang (node cabang yang sama)–Cimone–Bitung–Curug–Legok–Parung Panjang "
    "(interchange KRL Rangkasbitung existing). Bukan masterplan Parung Panjang–Citayam. "
    "Tidak mengikuti jalan internal cluster BSD dan tidak memakai Jalan Raya Legok-Karawaci. "
    "Bitung adalah node koridor Gatot Subroto / Raya Curug, bukan trase di jalan tol. "
    "Crossing tol Jakarta–Merak di Bitung–Curug: GRADE_SEPARATED."
)
NOTE_BR02 = (
    "CAS-MRT-C01-BR02 cabang usulan CASCADE: Ciputat (node pada mainline CAS-MRT-C01)–Pamulang–"
    "Jalan Siliwangi–Taman Kota 2 BSD (Taman Tekno / Jl. Tekno Widya, bukan Taman Kota 1)–"
    "Rawa Buntu (interchange KRL existing)–Jalan Pelayangan–Boulevard BSD Timur–BSD CBD–ICE BSD Hall 10. "
    "Bukan perpanjangan MRT NS existing. Bukan masterplan. Bukan branch Sawangan–Fatmawati. "
    "Tidak memaksa trase ke jalan internal cluster BSD; backbone Siliwangi / Pahlawan Seribu / Grand Boulevard."
)


def replace_ids(feats, prefixes, new_feats):
    kept = []
    for f in feats:
        fid = str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id") or "")
        rid = str(f["properties"].get("route_id") or "")
        if any(fid.startswith(p) or rid.startswith(p) for p in prefixes):
            continue
        kept.append(f)
    return kept + new_feats


def north_spec():
    return dict(
        id="KRL-C03-N",
        corridor_id="CAS-KRL-C03",
        corridor_name="CASCADE KRL Barat Tangerang",
        name="Tangerang – Kutabumi – Rajeg – Mauk",
        short="Tangerang – Mauk",
        from_name="Tangerang",
        to_name="Mauk",
        direction="Tangerang → Mauk",
        branch_id="N",
        branch_name="Branch utara Tangerang–Mauk",
        parent_route="",
        mode="krl",
        status="CASCADE_EXTENSION",
        status_label="Usulan CASCADE · perpanjangan KRL",
        network_type="TRUNK",
        plan_type="EXTENSION",
        structure="AT_GRADE",
        rail_backbone="Ekstensi dari Stasiun Tangerang existing; ROW baru sejajar koridor Pasar Kemis–Rajeg–Mauk",
        source=SRC_KRL,
        disclaimer="Usulan CASCADE. Bukan KRL existing Duri–Tangerang. Bukan masterplan. Bukan DED.",
        stop_note="Stasiun usulan perpanjangan KRL CASCADE. Bukan stasiun resmi.",
        note=NOTE_N,
    )


def south_spec():
    return dict(
        id="KRL-C03-S",
        corridor_id="CAS-KRL-C03",
        corridor_name="CASCADE KRL Barat Tangerang",
        name="Tangerang – Cimone – Bitung – Curug – Legok – Parung Panjang",
        short="Tangerang – Parung Panjang",
        from_name="Tangerang",
        to_name="Parung Panjang",
        direction="Tangerang → Parung Panjang",
        branch_id="S",
        branch_name="Branch selatan Tangerang–Parung Panjang",
        parent_route="",
        mode="krl",
        status="CASCADE_EXTENSION",
        status_label="Usulan CASCADE · perpanjangan KRL",
        network_type="TRUNK",
        plan_type="EXTENSION",
        structure="AT_GRADE",
        rail_backbone="Ekstensi dari Stasiun Tangerang; menyambung Stasiun Parung Panjang existing",
        source=SRC_KRL,
        disclaimer="Usulan CASCADE. Bukan KRL existing. Bukan masterplan Parung Panjang–Citayam. Bukan DED.",
        stop_note="Stasiun usulan perpanjangan KRL CASCADE. Bukan stasiun resmi.",
        note=NOTE_S,
    )


def br02_spec():
    return dict(
        id="CAS-MRT-C01-BR02",
        corridor_id="CAS-MRT-C01",
        corridor_name="CASCADE MRT Lebak Bulus – Ancol",
        name="Ciputat – Pamulang – BSD – ICE",
        short="Ciputat – ICE BSD",
        from_name="Ciputat",
        to_name="ICE BSD Hall 10",
        direction="Ciputat → ICE BSD Hall 10",
        branch_id="BR02",
        branch_name="Branch Ciputat–Pamulang–BSD–ICE",
        parent_route="CAS-MRT-C01",
        mode="mrt",
        status="PROPOSED",
        status_label="Usulan CASCADE · MRT",
        network_type="BRANCH",
        plan_type="NEW_TRUNK",
        structure="VIADUCT",
        rail_backbone="",
        source=SRC_MRT,
        disclaimer="Usulan CASCADE. Bukan MRT Jakarta existing. Bukan masterplan. Bukan DED. Bukan branch Fatmawati.",
        stop_note="Stasiun usulan CASCADE MRT. Bukan stasiun resmi. Vertex kontrol ≠ otomatis stasiun.",
        note=NOTE_BR02,
    )


def main():
    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY DRIFT {fn} {got} != {expect}")
    print("readonly hashes OK")

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())
    before = {}
    for f in old_routes["features"]:
        rid = str(f.get("id") or f["properties"].get("route_id"))
        before[rid] = geom_hash(f["geometry"]["coordinates"])
    for k, h in TJ_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"TJ drifted: {k} {before.get(k)}")
    for k, h in LRT_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"LRT drifted: {k} {before.get(k)}")
    for k, h in MRT_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"MRT drifted: {k} {before.get(k)}")
    print("CAS-TJ + CAS-LRT + CAS-MRT-C01/A hashes frozen OK")

    print("loading roads...")
    road_map = load_west_roads()

    print("walking KRL-C03-N Tangerang–Mauk")
    cn = krl_north_controls()
    geom_n, notes_n, roads_n, align_n, segs_n = walk_controls(cn, road_map, min_loop=1800.0)
    geom_n = inject_node(geom_n, TANGERANG, max_off=800)
    geom_n = densify_line(clean_chain(geom_n), 45)
    qa_n = qa(geom_n, "KRL-N")
    stations_n = [
        ("Tangerang", TANGERANG, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL existing Tangerang", "node_type": "BRANCH", "placement_reason": "EXISTING_CONNECTION"}),
        ("Kutabumi", KUTABUMI, {"node_type": "URBAN_NODE"}),
        ("Rajeg", RAJEG, {"node_type": "URBAN_NODE"}),
        ("Mauk", MAUK, {"node_type": "TERMINUS"}),
    ]
    rf_n, sf_n, stops_n, km_n, conf_n, meta_n = pack(north_spec(), geom_n, cn, stations_n, notes_n, roads_n, "RAIL_CORRIDOR", 30)

    print("walking KRL-C03-S Tangerang–Parung Panjang")
    cs = krl_south_controls()
    geom_s, notes_s, roads_s, align_s, segs_s = walk_controls(cs, road_map, min_loop=1800.0)
    geom_s = inject_node(geom_s, TANGERANG, max_off=800)
    geom_s = inject_node(geom_s, PARUNG_PANJANG, max_off=1200)
    geom_s = densify_line(clean_chain(geom_s), 45)
    qa_s = qa(geom_s, "KRL-S")
    stations_s = [
        ("Tangerang", TANGERANG, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL existing Tangerang", "node_type": "BRANCH", "placement_reason": "EXISTING_CONNECTION"}),
        ("Cimone", CIMONE, {"node_type": "URBAN_NODE"}),
        ("Bitung", BITUNG, {"node_type": "URBAN_NODE"}),
        ("Curug", CURUG, {"node_type": "URBAN_NODE"}),
        ("Legok", LEGOK, {"node_type": "URBAN_NODE"}),
        ("Parung Panjang", PARUNG_PANJANG, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL existing Rangkasbitung", "node_type": "INTERCHANGE", "placement_reason": "EXISTING_CONNECTION"}),
    ]
    rf_s, sf_s, stops_s, km_s, conf_s, meta_s = pack(south_spec(), geom_s, cs, stations_s, notes_s, roads_s, "RAIL_CORRIDOR", 31)

    print("walking CAS-MRT-C01-BR02 Ciputat–ICE BSD")
    cb = mrt_bsd_controls()
    geom_b, notes_b, roads_b, align_b, segs_b = walk_controls(cb, road_map, min_loop=1600.0)
    geom_b = inject_node(geom_b, CIPUTAT, max_off=800)
    geom_b = inject_node(geom_b, RAWA_BUNTU, max_off=1500)
    geom_b = inject_node(geom_b, ICE_BSD, max_off=800)
    geom_b = densify_line(clean_chain(geom_b), 45)
    qa_b = qa(geom_b, "MRT-BR02")
    stations_b = [
        ("Ciputat", CIPUTAT, {"interchange": "YES", "interchange_mode": "CAS-MRT-C01 mainline", "node_type": "BRANCH", "placement_reason": "EXISTING_CONNECTION"}),
        ("Pamulang", PAMULANG, {"node_type": "URBAN_NODE"}),
        ("Siliwangi", SILIWANGI, {"node_type": "URBAN_NODE"}),
        ("Taman Kota 2", TAMAN_KOTA_2, {"node_type": "MAJOR_DESTINATION", "activity_type": "PARK_TOD"}),
        ("Rawa Buntu", RAWA_BUNTU, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL existing Rangkasbitung", "node_type": "INTERCHANGE", "placement_reason": "EXISTING_CONNECTION"}),
        ("BSD CBD", BSD_CBD, {"node_type": "MAJOR_DESTINATION", "activity_type": "CBD"}),
        ("ICE BSD Hall 10", ICE_BSD, {"node_type": "TERMINUS", "activity_type": "MAJOR_DESTINATION"}),
    ]
    rf_b, sf_b, stops_b, km_b, conf_b, meta_b = pack(br02_spec(), geom_b, cb, stations_b, notes_b, roads_b, "VIADUCT", 22)

    assert haversine(geom_n[0], TANGERANG) < 40, "north start not Tangerang"
    assert haversine(geom_s[0], TANGERANG) < 40, "south start not Tangerang"
    d_share = haversine(geom_n[0], geom_s[0])
    assert d_share < 40, f"Tangerang split nodes {d_share:.0f}m"
    assert haversine(geom_n[-1], MAUK) < 120, "north end not Mauk"
    assert haversine(geom_s[-1], PARUNG_PANJANG) < 80, "south end not Parung Panjang"
    assert haversine(geom_b[0], CIPUTAT) < 40, "BR02 start not Ciputat"
    assert haversine(geom_b[-1], ICE_BSD) < 120, "BR02 end not ICE"
    assert min(haversine(p, RAWA_BUNTU) for p in geom_b) < 250, "BR02 missed Rawa Buntu"
    assert min(haversine(p, TAMAN_KOTA_2) for p in geom_b) < 250, "BR02 missed Taman Kota 2"
    assert min(p[1] for p in geom_n) < -6.04, "north must reach Mauk"
    assert min(p[1] for p in geom_s) < -6.33, "south must reach Parung Panjang"
    assert max(p[0] for p in geom_b) > 106.74, "BR02 must start near Ciputat"
    assert min(p[0] for p in geom_b) < 106.64, "BR02 must reach ICE west"
    # no Imam Bonjol south-loop on KRL-N
    early_n = geom_n[: max(8, len(geom_n) // 12)]
    assert min(p[1] for p in early_n) > -6.182, f"KRL-N loops south of Tangerang {min(p[1] for p in early_n)}"
    # Taman Kota 2 is south of Rawa Buntu, not Taman Kota 1 at -6.288
    tk2_hit = min(geom_b, key=lambda p: haversine(p, TAMAN_KOTA_2))
    assert tk2_hit[1] < -6.318, f"TK2 snapped too far north {tk2_hit}"
    assert max(p[1] for p in geom_b) < -6.286, f"BR02 went to Taman Kota 1 / north BSD {max(p[1] for p in geom_b)}"
    # KRL-S must not enter BSD cluster longitudes
    assert max(p[0] for p in geom_s) < 106.640, f"KRL-S entered BSD lon {max(p[0] for p in geom_s)}"
    assert all(s["stop_name"] != "Kramat Jati" for s in stops_n + stops_s + stops_b)
    print(f"  Tangerang shared {d_share:.0f}m  Rawa Buntu {min(haversine(p, RAWA_BUNTU) for p in geom_b):.0f}m  TK2 {min(haversine(p, TAMAN_KOTA_2) for p in geom_b):.0f}m")

    prefixes = ("KRL-C03", "CAS-MRT-C01-BR02", "CAS-KRL")
    route_feats = replace_ids(old_routes["features"], prefixes, [rf_n, rf_s, rf_b])
    stop_feats = replace_ids(old_stops["features"], prefixes, sf_n + sf_s + sf_b)
    ids = [str(f.get("id") or f["properties"].get("route_id")) for f in route_feats]
    for need in ("CAS-TJ07", "CAS-LRT-C02", "CAS-MRT-C01", "CAS-MRT-C01-A", "KRL-C03-N", "KRL-C03-S", "CAS-MRT-C01-BR02"):
        assert need in ids, f"missing {need}"

    meta = [m for m in (old_meta.get("corridors") or []) if not str(m.get("id", "")).startswith(("KRL-C03", "CAS-MRT-C01-BR02", "CAS-KRL"))]
    meta.extend([meta_n, meta_s, meta_b])

    after = {str(f.get("id") or f["properties"].get("route_id")): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in TJ_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"TJ DRIFT after west write: {k}")
    for k, h in LRT_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"LRT DRIFT after west write: {k}")
    for k, h in MRT_HASH.items():
        if after.get(k) != h:
            raise SystemExit(f"MRT DRIFT after west write: {k}")

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["source"] = "CASCADE KRL C03 + MRT C01-BR02 — usulan analisis"
    existing["corridors"] = meta
    existing["krl_note"] = "KRL-C03-N Tangerang–Mauk dan KRL-C03-S Tangerang–Parung Panjang. Bukan existing. Bukan masterplan."
    existing["mrt_note"] = (
        "CAS-MRT-C01 mainline Lebak Bulus–Ancol + branch Sawangan–Fatmawati + branch Ciputat–BSD–ICE. "
        "Bukan MRT existing. Bukan masterplan."
    )
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_west_segments.json").write_text(
        json.dumps({"north": segs_n, "south": segs_s, "mrt_br02": segs_b}, ensure_ascii=False, indent=2)
    )

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
            row["notes"] = (
                "CAS-TJ01..11 + CAS-LRT-C02/C04 + CAS-MRT-C01/A/BR02 + KRL-C03-N/S. "
                "Usulan CASCADE. Bukan masterplan. #D62F7F."
            )
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "corridors": [meta_n, meta_s, meta_b],
        "qa": {"KRL-N": qa_n, "KRL-S": qa_s, "MRT-BR02": qa_b},
        "notes_north": notes_n[-20:],
        "notes_south": notes_s[-20:],
        "notes_br02": notes_b[-20:],
        "tj_frozen": TJ_HASH,
        "lrt_frozen": LRT_HASH,
        "mrt_frozen": MRT_HASH,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "tangerang_shared_m": round(d_share, 1),
        "fixes": [
            "Taman Kota 2 = Tekno Widya 106.68165,-6.32869 (bukan Taman Kota 1)",
            "KRL-N keluar Tangerang NEW_ROW barat, bukan loop Imam Bonjol",
            "KRL-S tidak memakai Legok-Karawaci / jalan internal BSD",
        ],
        "hashes": {
            "KRL-C03-N": after["KRL-C03-N"],
            "KRL-C03-S": after["KRL-C03-S"],
            "CAS-MRT-C01-BR02": after["CAS-MRT-C01-BR02"],
        },
    }
    (OUT / "cascade_validation_west.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))

    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"KRL-C03-N         {km_n} km  stations={len(stops_n)}  {conf_n}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops_n))
    print(f"KRL-C03-S         {km_s} km  stations={len(stops_s)}  {conf_s}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops_s))
    print(f"CAS-MRT-C01-BR02  {km_b} km  stations={len(stops_b)}  {conf_b}")
    print("   stops:", " → ".join(s["stop_name"] for s in stops_b))
    print("TJ+LRT+MRT C01/A frozen OK  masterplan/existing untouched")
    print("ids", ids)


if __name__ == "__main__":
    main()
