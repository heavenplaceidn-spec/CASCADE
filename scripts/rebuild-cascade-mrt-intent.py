#!/usr/bin/env python3
"""Rebuild CAS-MRT-C01 + C01-A with locked corridor intent.

Does NOT touch KRL, TJ, LRT, masterplan, existing networks, or BR02 geometry.
Parung is a directional control (Bojongsari), not a terminus.
Stations come from mandatory nodes + spatial scan every ~2 km.
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
KRL_HASH = {"KRL-C03-N": "711afcad81d6", "KRL-C03-S": "c6ce84ce0d82"}
BR02_HASH = "31ebf64e5ec5"
READONLY_FILES = dict(mrtb.READONLY_FILES)

LEBAK_BULUS = (106.77493, -6.28930)
CIPUTAT = (106.74720, -6.31250)
SAWANGAN = (106.76372, -6.40019)
FATMAWATI = (106.79246, -6.29247)
ANCOL = (106.84646, -6.12786)
PGC = (106.86570, -6.26190)
CONDET = (106.85172, -6.27643)
KAMPUNG_MELAYU = (106.86682, -6.22467)
MANGGARAI = (106.85025, -6.21110)
PARUNG_TOWN = (106.73320, -6.42100)
PARUNG_BINGUNG = (106.74700, -6.40650)
BOJONGSARI = (106.74062, -6.39966)
CIJANTUNG = (106.86265, -6.31255)  # Mall Graha snapped to Jalan Raya Bogor
MATRAMAN = (106.85891, -6.21289)
SALEMBA = (106.85080, -6.19550)
PRAMUKA = (106.86800, -6.19250)
SENEN = (106.84410, -6.17276)
GUNUNG_SAHARI = (106.83950, -6.15200)
DEPOK_BARU = (106.82169, -6.39113)
MARGONDA = (106.83209, -6.36895)
CAWANG = (106.85867, -6.24255)
PONDOK_CABE = (106.74650, -6.36200)
MAMPANG = (106.80800, -6.39200)
OTISTA = (106.86731, -6.22721)
TANAH_MERDEKA = (106.87625, -6.30912)  # on Jalan Tanah Merdeka
KAMPUNG_RAMBUTAN = (106.88215, -6.30988)
TEBET = (106.85842, -6.22640)
CIMANGGIS = (106.86050, -6.37100)
CIBUBUR = (106.86800, -6.34800)
CIRACAS = (106.87050, -6.32900)
PASAR_REBO = (106.86489, -6.32255)  # snapped to Jalan Raya Bogor
LIMO = (106.77620, -6.35100)
CINERE = (106.78500, -6.33250)
KRUKUT = (106.79600, -6.32200)
ANDARA = (106.80362, -6.31392)
CILANDAK = (106.79995, -6.29147)
CONDET_ROAD = (106.85504, -6.27757)
RAYA_BOGOR_KR = (106.86969, -6.30001)
RAYA_BOGOR_UTARA = (106.87116, -6.28940)
KRAMAT_JATI_V = (106.86863, -6.27671)

KEEP_EXTRA = mrtb.KEEP_EXTRA + (
    "fadillah", "fadilah", "kesehatan", "matraman", "pramuka", "pendidikan",
    "cijantung", "kwitang", "suprapto", "otista", "sultan agung",
)
SKIP_EXTRA = mrtb.SKIP_EXTRA + ("otista raya gang",)
SKIP_SCAN_SUB = (
    "flyover", "pasar induk", "gelanggang", "pasar senen", "kramat jati",
    "kramatjati", "induk kramat", "simpang",
)


def geom_hash(coords):
    return hashlib.sha256(json.dumps(coords, separators=(",", ":")).encode()).hexdigest()[:12]


def file_hash(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def name_key(n):
    s = str(n).lower()
    for w in ("stasiun ", "halte ", "pasar ", "terminal "):
        s = s.replace(w, "")
    return s.strip()


def too_similar(name, existing):
    k = name_key(name)
    if not k:
        return True
    low = str(name).lower()
    if any(s in low for s in SKIP_SCAN_SUB):
        return True
    for e in existing:
        ek = name_key(e)
        if k == ek:
            return True
        shorter, longer = (k, ek) if len(k) <= len(ek) else (ek, k)
        if len(shorter) >= 6 and shorter in longer and (len(longer) - len(shorter)) <= 4:
            return True
    return False


def load_intent_roads():
    road_map = tja.load_road_map()
    extra_path = OUT / "extra_roads_mrt.geojson"
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
        merged = merge_named(parts, max_gap=320)
        if name in road_map:
            old = flatten(road_map[name]["geometry"])
            merged = merge_named(old + merged, max_gap=320)
        if not merged:
            continue
        road_map[name] = {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "MultiLineString", "coordinates": merged}
            if len(merged) > 1
            else {"type": "LineString", "coordinates": merged[0]},
        }
    return road_map


def walk_controls(controls, road_map, min_loop=2500.0):
    chain, notes, types, roads, segments = [], [], [], [], []
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
    return chain, notes, roads, "VIADUCT", segments


def load_pois():
    pois = []

    def add(name, coord, kind, base, extra=None):
        pois.append({"name": name, "coord": (float(coord[0]), float(coord[1])), "kind": kind, "base": base, "extra": extra or {}})

    for path, kind, base in (
        (PUB / "krl_stops.geojson", "KRL", 25),
        (PUB / "lrt_stops.geojson", "LRT", 22),
        (PUB / "mrt_stops.geojson", "MRT", 25),
        (PUB / "transjakarta_stops.geojson", "TJ", 12),
    ):
        if not path.exists():
            continue
        for f in json.loads(path.read_text())["features"]:
            if f.get("geometry", {}).get("type") != "Point":
                continue
            p = f.get("properties") or {}
            nm = p.get("name") or p.get("stop_name") or p.get("station_name")
            if not nm:
                continue
            extra = {}
            if kind in ("KRL", "LRT", "MRT"):
                extra = {"existing": "YES", "interchange": "YES", "interchange_mode": kind}
            add(str(nm), f["geometry"]["coordinates"], kind, base, extra)
    for name, coord, kind, base in (
        ("Mal Cijantung", CIJANTUNG, "MALL", 18),
        ("RA Fadillah", (106.85171, -6.31898), "URBAN", 12),
        ("Bojongsari", BOJONGSARI, "URBAN", 14),
        ("Parung Bingung", PARUNG_BINGUNG, "URBAN", 12),
        ("Cijantung", CIJANTUNG, "URBAN", 16),
        ("Pondok Cabe", PONDOK_CABE, "URBAN", 12),
        ("Mampang Depok", MAMPANG, "URBAN", 12),
        ("Matraman", MATRAMAN, "KRL", 25),
        ("Pramuka", PRAMUKA, "URBAN", 16),
        ("Gunung Sahari", GUNUNG_SAHARI, "URBAN", 14),
        ("Salemba", SALEMBA, "EDUCATION", 14),
        ("Cimanggis", CIMANGGIS, "URBAN", 12),
        ("Cibubur", CIBUBUR, "URBAN", 14),
        ("Ciracas", CIRACAS, "URBAN", 12),
        ("Pasar Rebo", PASAR_REBO, "URBAN", 12),
        ("Condet", CONDET, "URBAN", 16),
        ("Limo", LIMO, "URBAN", 12),
        ("Cinere", CINERE, "URBAN", 12),
        ("Pondok Jagung", (106.69800, -6.34400), "URBAN", 10),
        ("Rempoa", (106.74800, -6.32800), "URBAN", 10),
        ("Ciputat Timur", (106.75800, -6.30480), "URBAN", 10),
    ):
        add(name, coord, kind, base)
    return pois


def score_poi(poi, d_align):
    sc = poi["base"] + max(0, 15 * (1 - d_align / 600.0))
    if poi["kind"] in ("KRL", "LRT", "MRT"):
        sc += 10
    if poi["kind"] in ("MALL", "EDUCATION"):
        sc += 5
    return sc


def rec_stop(name, ppt, along, extra, score=90, reason=None, mandatory=False):
    return {
        "stop_name": name,
        "lon": ppt[0],
        "lat": ppt[1],
        "along_m": along,
        "existing": extra.get("existing", "NO"),
        "interchange": extra.get("interchange", "NO"),
        "interchange_mode": extra.get("interchange_mode", ""),
        "name_confidence": extra.get("name_confidence", "HIGH"),
        "placement_reason": reason or extra.get("placement_reason", "MANDATORY_NODE"),
        "station_on_curve": "NO",
        "node_type": extra.get("node_type", "STATION"),
        "activity_type": extra.get("activity_type", ""),
        "station_score": extra.get("station_score", score),
        "mandatory": mandatory,
    }


def nearest_from(geom, pt, min_along, tot, step=35.0):
    """Nearest point on geom with chainage >= min_along (locks corridor order)."""
    best = None
    t = max(0.0, min_along)
    while t <= tot + 1:
        p = point_at(geom, min(t, tot))
        d = haversine(p, pt)
        if best is None or d < best[0]:
            best = (d, min(t, tot), list(p))
        t += step
    if best is None:
        ppt, along, d, _ = nearest_along(pt, geom)
        return d, along, list(ppt)
    return best[0], best[1], best[2]


def scan_stations(geom, mandatory, pois, min_gap=1500.0, window=2000.0):
    tot = length_m(geom)
    placed = []
    min_along = 0.0
    for i, (name, pt, extra) in enumerate(mandatory):
        if i == 0:
            ppt, along, d = list(geom[0]), 0.0, haversine(geom[0], pt)
        elif i == len(mandatory) - 1:
            ppt, along, d = list(geom[-1]), tot, haversine(geom[-1], pt)
        else:
            d, along, ppt = nearest_from(geom, pt, min_along + 450.0, tot)
            if d > 900:
                d2, along2, ppt2, _ = nearest_along(pt, geom)
                if along2 > min_along + 200 and d2 + 80 < d:
                    d, along, ppt = d2, along2, list(ppt2)
        r = rec_stop(name, ppt, along, extra, 90, extra.get("placement_reason", "MANDATORY_NODE"), True)
        r["align_off_m"] = round(d, 1)
        placed.append(r)
        min_along = along
    placed.sort(key=lambda r: r["along_m"])
    placed[0]["lon"], placed[0]["lat"] = geom[0][0], geom[0][1]
    placed[0]["along_m"] = 0.0
    placed[-1]["lon"], placed[-1]["lat"] = geom[-1][0], geom[-1][1]
    placed[-1]["along_m"] = tot

    gaps, added = [], []
    used_names = {p["stop_name"].lower() for p in placed}

    def too_close(along, extra_list=None):
        seq = placed + added + (extra_list or [])
        return any(abs(along - p["along_m"]) < min_gap for p in seq)

    for a, b in zip(placed, placed[1:]):
        gap = b["along_m"] - a["along_m"]
        gap_rec = {"from": a["stop_name"], "to": b["stop_name"], "gap_km": round(gap / 1000, 2), "candidates": [], "selected": None, "gap_reason": ""}
        if gap < 2500:
            gaps.append(gap_rec)
            continue
        t = a["along_m"] + window
        picked = []
        while t < b["along_m"] - window * 0.7:
            best = None
            for poi in pois:
                if too_similar(poi["name"], used_names):
                    continue
                d_al, along_p, ppt, _ = nearest_along(poi["coord"], geom)
                if d_al > (700 if poi["kind"] in ("KRL", "LRT", "MRT", "MALL") else 550):
                    continue
                if along_p < a["along_m"] + 1100 or along_p > b["along_m"] - 1100:
                    continue
                if too_close(along_p, picked):
                    continue
                sc = score_poi(poi, d_al)
                if sc < 22:
                    continue
                if poi["kind"] == "TJ" and sc < 32:
                    continue
                if best is None or sc > best[0]:
                    best = (sc, poi, along_p, ppt, d_al)
            if best:
                sc, poi, along_p, ppt, d_al = best
                cand = rec_stop(poi["name"], ppt, along_p, poi["extra"], round(sc, 1), "SPATIAL_SCAN_2KM")
                cand["activity_type"] = poi["kind"]
                cand["align_off_m"] = round(d_al, 1)
                picked.append(cand)
                added.append(cand)
                used_names.add(poi["name"].lower())
                gap_rec["candidates"].append({"name": poi["name"], "score": round(sc, 1), "along_km": round(along_p / 1000, 2)})
                gap_rec["selected"] = poi["name"]
                t = along_p + window
            else:
                t += window
        if gap >= 3000 and not picked:
            gap_rec["gap_reason"] = "NO_STRONG_NODE"
        gaps.append(gap_rec)

    all_stops = sorted(placed + added, key=lambda r: r["along_m"])
    all_stops[0]["along_m"] = 0.0
    all_stops[0]["placement_reason"] = "TERMINUS"
    all_stops[-1]["along_m"] = tot
    all_stops[-1]["placement_reason"] = "TERMINUS"
    return all_stops, gaps, tot


def force_named(geom, stops, items, max_off=450, min_gap=1200):
    have = {s["stop_name"].lower() for s in stops}
    extra = []
    tot = length_m(geom)
    for name, pt, extra_p in items:
        if too_similar(name, have):
            continue
        d, along, ppt, _ = nearest_along(pt, geom)
        if d > max_off:
            continue
        if any(abs(along - s["along_m"]) < min_gap for s in stops + extra):
            continue
        extra.append(rec_stop(name, ppt, along, extra_p, 70, extra_p.get("placement_reason", "CORRIDOR_CANDIDATE")))
        have.add(name.lower())
    if extra:
        stops = sorted(stops + extra, key=lambda r: r["along_m"])
        stops[0]["along_m"] = 0.0
        stops[-1]["along_m"] = tot
    return stops


def make_stops_from_scan(spec, geom, stops, conf, alignment, roads, note, common_km):
    feats = []
    for i, s in enumerate(stops):
        order = i + 1
        dist_prev = round((s["along_m"] - stops[i - 1]["along_m"]) / 1000, 2) if i else 0.0
        dist_next = round((stops[i + 1]["along_m"] - s["along_m"]) / 1000, 2) if i < len(stops) - 1 else 0.0
        stop_type = "TERMINUS" if i in (0, len(stops) - 1) else "INTERCHANGE" if s["interchange"] == "YES" else "STATION"
        sid = f"{spec['id']}-S{order:02d}"
        props = mrtb.mrt_common(spec, common_km, len(stops), conf, alignment, roads, note)
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
                "station_score": s.get("station_score", 0),
                "distance_from_previous_stop": dist_prev,
                "distance_to_next_stop": dist_next,
                "note": "Stasiun usulan CASCADE MRT. Bukan stasiun resmi. Vertex kontrol ≠ otomatis stasiun.",
            }
        )
        feats.append(feat_pt(sid, [s["lon"], s["lat"]], props))
    return feats


def pack(spec, geom, controls, stops, notes, roads, alignment, order, tot):
    km = round(tot / 1000, 2)
    straight = haversine(controls[0][1], controls[-1][1]) / 1000
    conf = mrtb.confidence(notes, km, straight)
    rf, km = mrtb.make_route_feature(spec, geom, stops, len(controls), conf, alignment, roads, spec["note"], order)
    rf["properties"]["stop_count"] = len(stops)
    rf["properties"]["structure"] = "VIADUCT"
    sf = make_stops_from_scan(spec, geom, stops, conf, alignment, roads, spec["note"], km)
    meta = {
        "id": spec["id"],
        "name": spec["name"],
        "short": spec["short"],
        "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        "from_name": spec["from_name"],
        "to_name": spec["to_name"],
        "direction": spec["direction"],
        "mode": "mrt",
        "branch_id": spec.get("branch_id", "MAIN"),
        "length_km": km,
        "stop_count": len(stops),
        "geometry_confidence": conf,
        "source": SOURCE,
        "status": "PROPOSED",
        "network_type": spec.get("network_type", "MRT"),
        "plan_type": spec.get("plan_type", "NEW_TRUNK"),
        "alignment_type": alignment,
        "road_backbone": ", ".join(roads),
        "notes": spec["note"],
        "bbox": bbox_of(geom),
    }
    return rf, sf, km, conf, meta


def mainline_controls():
    # Vertex list = designed ROW. True/False is unused by walk; stations come from
    # mandatory + scan. Parung town is NOT in this list.
    return [
        ("Lebak Bulus", LEBAK_BULUS, ["Jalan Lebak Bulus Raya", "Jalan Ciputat Raya"], True),
        ("Lebak Bulus Selatan", (106.77250, -6.29820), ["Jalan Lebak Bulus Raya", "Jalan Ciputat Raya"], False),
        ("Ciputat Timur", (106.75800, -6.30480), ["Jalan Ciputat Raya", "Jalan Laksamana RE Martadinata"], False),
        ("Ciputat", CIPUTAT, ["Jalan Laksamana RE Martadinata", "Jalan Raya Parung—Ciputat"], True),
        ("Gaplek", (106.74900, -6.34500), ["Jalan Laksamana RE Martadinata", "Jalan Raya Parung—Ciputat"], False),
        ("Pondok Cabe koridor", PONDOK_CABE, ["Jalan Raya Parung—Ciputat"], False),
        ("Bojongsari Utara", (106.74300, -6.38000), ["Jalan Raya Parung—Ciputat"], False),
        ("Bojongsari", BOJONGSARI, ["Jalan Raya Parung—Ciputat", "Jalan Raya Sawangan"], False),
        ("Parung Bingung", PARUNG_BINGUNG, ["Jalan Raya Sawangan"], True),
        ("Sawangan", SAWANGAN, ["Jalan Raya Sawangan", "Jalan Arif Rahman Hakim"], True),
        ("Sawangan Timur", (106.79450, -6.39480), ["Jalan Raya Sawangan", "Jalan Arif Rahman Hakim"], False),
        ("Mampang Depok", MAMPANG, ["Jalan Arif Rahman Hakim", "FORCE_OSRM"], False),
        ("Depok Baru", DEPOK_BARU, ["Jalan Arif Rahman Hakim", "Jalan Margonda Raya"], True),
        ("Margonda Selatan", (106.82850, -6.38000), ["Jalan Margonda Raya", "Jalan Raya Margonda"], False),
        ("Margonda", MARGONDA, ["Jalan Margonda Raya", "Jalan Tole Iskandar"], True),
        ("Tole Iskandar", (106.84800, -6.37000), ["Jalan Tole Iskandar", "Jalan Raya Bogor"], False),
        ("Cimanggis", CIMANGGIS, ["Jalan Raya Bogor"], True),
        ("Cibubur", CIBUBUR, ["Jalan Raya Bogor"], True),
        ("Ciracas", CIRACAS, ["Jalan Raya Bogor"], True),
        ("Pasar Rebo", PASAR_REBO, ["Jalan Raya Bogor"], True),
        # Cijantung = Mall Graha ON Raya Bogor (between Pasar Rebo and PGC).
        # Written "PGC→Cijantung" would hairpin 5 km south; urban spine is south→north.
        ("Cijantung", CIJANTUNG, ["Jalan Raya Bogor"], True),
        ("Raya Bogor KR", RAYA_BOGOR_KR, ["NEW_ROW"], False),
        ("Tanah Merdeka", TANAH_MERDEKA, ["NEW_ROW"], False),
        ("Kampung Rambutan", KAMPUNG_RAMBUTAN, ["NEW_ROW"], True),
        ("Raya Bogor Utara", RAYA_BOGOR_UTARA, ["NEW_ROW", "Jalan Raya Bogor"], False),
        ("Kramat Jati vertex", KRAMAT_JATI_V, ["Jalan Raya Bogor"], False),
        ("PGC", PGC, ["Jalan Condet Raya"], True),
        ("Cililitan Condet", (106.86250, -6.26680), ["Jalan Condet Raya"], False),
        ("Batu Ampar", (106.85725, -6.27298), ["Jalan Condet Raya"], False),
        ("Condet", CONDET_ROAD, ["Jalan Condet Raya", "Jalan Dewi Sartika"], True),
        ("Condet Utara", (106.85380, -6.26820), ["Jalan Dewi Sartika"], False),
        ("Dewi Sartika", (106.85800, -6.25200), ["Jalan Dewi Sartika"], False),
        ("Cawang", CAWANG, ["Jalan Dewi Sartika", "Jalan Otto Iskandar Dinata"], True),
        ("Otista", OTISTA, ["Jalan Otto Iskandar Dinata", "Jalan Otista Raya"], False),
        ("Kampung Melayu", KAMPUNG_MELAYU, ["Jalan Otto Iskandar Dinata", "Jalan Jatinegara Barat Raya"], True),
        ("Tebet", TEBET, ["NEW_ROW", "Jalan Jatinegara Barat Raya", "Jalan Dokter Saharjo"], True),
        ("Manggarai", MANGGARAI, ["NEW_ROW"], True),
        ("Manggarai Timur", (106.85440, -6.21180), ["NEW_ROW"], False),
        ("Matraman", MATRAMAN, ["NEW_ROW"], True),
        ("Matraman Utara", (106.85680, -6.20480), ["NEW_ROW"], False),
        ("Salemba Selatan", (106.85280, -6.19900), ["NEW_ROW"], False),
        ("Salemba", SALEMBA, ["NEW_ROW"], True),
        ("Salemba Timur", (106.85720, -6.19420), ["NEW_ROW"], False),
        ("Pramuka Barat", (106.86250, -6.19320), ["NEW_ROW"], False),
        ("Pramuka", PRAMUKA, ["NEW_ROW"], True),
        ("Pramuka Utara", (106.86720, -6.18550), ["NEW_ROW"], False),
        ("Suprapto Timur", (106.86050, -6.17880), ["NEW_ROW"], False),
        ("Suprapto", (106.85500, -6.17600), ["NEW_ROW"], False),
        ("Senen Timur", (106.84880, -6.17420), ["NEW_ROW"], False),
        ("Senen", SENEN, ["NEW_ROW", "Jalan Gunung Sahari Raya"], True),
        ("Gunung Sahari Selatan", (106.84120, -6.16250), ["Jalan Gunung Sahari Raya", "NEW_ROW"], False),
        ("Gunung Sahari", GUNUNG_SAHARI, ["Jalan Gunung Sahari Raya", "NEW_ROW"], True),
        ("Kemayoran Utara", (106.84400, -6.14000), ["Jalan Gunung Sahari Raya", "Jalan Lodan Raya", "NEW_ROW"], False),
        ("Ancol", ANCOL, ["Jalan Gunung Sahari Raya", "Jalan Lodan Raya", "NEW_ROW"], True),
    ]


def branch_controls():
    return [
        ("Sawangan", SAWANGAN, ["Jalan Raya Limo", "Jalan Cinere Raya", "FORCE_OSRM"], True),
        ("Limo", LIMO, ["Jalan Raya Limo", "Jalan Cinere Raya"], False),
        ("Cinere", CINERE, ["Jalan Cinere Raya", "Jalan Raya Cinere"], True),
        ("Krukut", KRUKUT, ["Jalan Cinere Raya", "Jalan Andara"], True),
        ("Andara", ANDARA, ["Jalan Andara", "Jalan Tahi Bonar Simatupang"], True),
        ("Cilandak", CILANDAK, ["FORCE_OSRM", "Jalan Tahi Bonar Simatupang"], True),
        ("Fatmawati", FATMAWATI, ["Jalan RS Fatmawati", "Jalan Raden Ajeng Kartini"], True),
    ]


NOTE_MAIN = (
    "CAS-MRT-C01 mainline usulan CASCADE: Lebak Bulus–Ciputat (BRANCH)–arah Parung (Bojongsari, "
    "bukan terminus Parung)–Parung Bingung–Sawangan (BRANCH)–Depok Baru–Margonda–Cimanggis–Cibubur–"
    "Ciracas–Pasar Rebo–Cijantung (Mall Graha / RA Fadillah di Raya Bogor)–Kampung Rambutan–PGC–"
    "Condet (via Condet Raya, bukan diagonal)–Dewi Sartika–Otista–Kampung Melayu–Tebet–Manggarai–"
    "Matraman–Salemba–Pramuka–Senen–Gunung Sahari–Ancol. Bukan MRT existing. Bukan masterplan. "
    "Parung kota bukan stasiun. Stasiun tambahan dari spatial scan ±2 km."
)
NOTE_BRANCH = (
    "CAS-MRT-C01-A branch: Sawangan–Limo–Cinere–Krukut–Andara–Cilandak–Fatmawati. "
    "Bukan mainline. Bukan branch BSD."
)
NOTE_BR02 = (
    "CAS-MRT-C01-BR02 cabang Ciputat–Pamulang–BSD–ICE. Ciputat = BRANCH NODE mainline. "
    "Stasiun tambahan dari spatial scan ±2 km."
)


def replace_keep(feats, drop_pred, new_feats):
    return [f for f in feats if not drop_pred(f)] + new_feats


def feat_id(f):
    return str(f.get("id") or f["properties"].get("route_id") or f["properties"].get("id") or "")


def main():
    for fn, expect in READONLY_FILES.items():
        got = file_hash(PUB / fn)
        if got != expect:
            raise SystemExit(f"READONLY DRIFT {fn} {got} != {expect}")
    print("readonly hashes OK")

    old_routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    old_stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    old_meta = json.loads((PUB / "cascade_existing.json").read_text())
    before = {feat_id(f): geom_hash(f["geometry"]["coordinates"]) for f in old_routes["features"]}
    for k, h in TJ_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"TJ drifted: {k}")
    for k, h in LRT_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"LRT drifted: {k}")
    for k, h in KRL_HASH.items():
        if before.get(k) != h:
            raise SystemExit(f"KRL drifted: {k} {before.get(k)}")
    if before.get("CAS-MRT-C01-BR02") != BR02_HASH:
        raise SystemExit(f"BR02 drifted {before.get('CAS-MRT-C01-BR02')}")
    print("TJ+LRT+KRL+BR02 frozen OK")

    br02_feat = next(f for f in old_routes["features"] if feat_id(f) == "CAS-MRT-C01-BR02")
    br02_geom = [list(p) for p in br02_feat["geometry"]["coordinates"]]

    print("loading roads...")
    road_map = load_intent_roads()
    pois = load_pois()

    print("walking CAS-MRT-C01 mainline (intent)")
    main_c = mainline_controls()
    geom_m, notes_m, roads_m, align_m, segs_m = walk_controls(main_c, road_map, min_loop=6000.0)
    for pin in (CIPUTAT, SAWANGAN, CIJANTUNG, PGC, CONDET_ROAD, CAWANG, MANGGARAI, MATRAMAN, SALEMBA, PRAMUKA, SENEN, GUNUNG_SAHARI, ANCOL, PARUNG_BINGUNG, PONDOK_CABE, MAMPANG, KAMPUNG_RAMBUTAN):
        geom_m = inject_node(geom_m, pin, max_off=280.0)
    geom_m = densify_line(clean_chain(geom_m), 45)
    qa_m = qa(geom_m, "MAIN")
    d_cij = min(haversine(p, CIJANTUNG) for p in geom_m)
    print(f"  dist Cijantung {d_cij:.0f}m  Condet {min(haversine(p, CONDET) for p in geom_m):.0f}m  KR {min(haversine(p, KAMPUNG_RAMBUTAN) for p in geom_m):.0f}m")

    mandatory_m = [
        ("Lebak Bulus", LEBAK_BULUS, {"existing": "YES", "interchange": "YES", "interchange_mode": "MRT existing NS", "node_type": "TERMINUS", "placement_reason": "EXISTING_CONNECTION"}),
        ("Ciputat", CIPUTAT, {"interchange": "YES", "interchange_mode": "BRANCH BSD", "node_type": "BRANCH", "placement_reason": "BRANCH_NODE"}),
        ("Pondok Cabe", PONDOK_CABE, {"node_type": "URBAN_NODE", "placement_reason": "PARUNG_DIRECTION"}),
        ("Bojongsari", BOJONGSARI, {"node_type": "URBAN_NODE", "placement_reason": "PARUNG_DIRECTION"}),
        ("Parung Bingung", PARUNG_BINGUNG, {"node_type": "URBAN_NODE", "placement_reason": "CORRIDOR_CANDIDATE"}),
        ("Sawangan", SAWANGAN, {"interchange": "YES", "interchange_mode": "BRANCH Fatmawati", "node_type": "BRANCH", "placement_reason": "BRANCH_NODE"}),
        ("Mampang Depok", MAMPANG, {"node_type": "URBAN_NODE"}),
        ("Depok Baru", DEPOK_BARU, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "MAJOR_TRANSIT"}),
        ("Margonda", MARGONDA, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL Pondok Cina", "node_type": "MAJOR_TRANSIT"}),
        ("Cimanggis", CIMANGGIS, {"node_type": "URBAN_NODE"}),
        ("Cibubur", CIBUBUR, {"node_type": "MAJOR_DESTINATION"}),
        ("Ciracas", CIRACAS, {"node_type": "URBAN_NODE"}),
        ("Pasar Rebo", PASAR_REBO, {"node_type": "URBAN_NODE"}),
        ("Cijantung", CIJANTUNG, {"node_type": "MAJOR_DESTINATION", "activity_type": "MALL", "placement_reason": "RA_FADILLAH_CORRIDOR"}),
        ("Kampung Rambutan", KAMPUNG_RAMBUTAN, {"existing": "YES", "interchange": "YES", "interchange_mode": "LRT / TJ", "node_type": "MAJOR_TRANSIT"}),
        ("PGC", PGC, {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT"}),
        ("Condet", CONDET_ROAD, {"node_type": "MAJOR_DESTINATION"}),
        ("Cawang", CAWANG, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "MAJOR_TRANSIT", "placement_reason": "DEWI_SARTIKA_CORRIDOR"}),
        ("Kampung Melayu", KAMPUNG_MELAYU, {"existing": "YES", "interchange": "YES", "interchange_mode": "TransJakarta", "node_type": "MAJOR_TRANSIT"}),
        ("Tebet", TEBET, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL"}),
        ("Manggarai", MANGGARAI, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "INTERCHANGE"}),
        ("Matraman", MATRAMAN, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "MAJOR_TRANSIT"}),
        ("Salemba", SALEMBA, {"node_type": "EDUCATION", "activity_type": "HEALTH"}),
        ("Pramuka", PRAMUKA, {"node_type": "URBAN_NODE", "activity_type": "COMMERCIAL"}),
        ("Senen", SENEN, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL"}),
        ("Gunung Sahari", GUNUNG_SAHARI, {"node_type": "URBAN_NODE", "placement_reason": "GUNUNG_SAHARI_CORRIDOR"}),
        ("Ancol", ANCOL, {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "TERMINUS"}),
    ]
    stops_m, gaps_m, tot_m = scan_stations(geom_m, mandatory_m, pois)
    stops_m = force_named(
        geom_m,
        stops_m,
        [
            ("Ciputat Timur", (106.75800, -6.30480), {"node_type": "URBAN_NODE"}),
            ("Bojongsari Utara", (106.74300, -6.38000), {"node_type": "URBAN_NODE", "placement_reason": "PARUNG_DIRECTION"}),
            ("Sawangan Timur", (106.79450, -6.39480), {"node_type": "URBAN_NODE"}),
            ("Cibubur Junction", (106.86425, -6.35950), {"node_type": "URBAN_NODE"}),
            ("Tanah Merdeka", TANAH_MERDEKA, {"node_type": "URBAN_NODE"}),
        ],
        max_off=700,
        min_gap=1200,
    )

    spec_m = dict(id="CAS-MRT-C01", name="Lebak Bulus – Ancol", short="Lebak Bulus – Ancol", from_name="Lebak Bulus", to_name="Ancol", direction="Lebak Bulus → Ancol", branch_id="MAIN", branch_name="Mainline Lebak Bulus – Ancol", parent_route="", network_type="MRT", plan_type="NEW_TRUNK", note=NOTE_MAIN)
    rf_m, sf_m, km_m, conf_m, meta_m = pack(spec_m, geom_m, main_c, stops_m, notes_m, roads_m, align_m, 20, tot_m)

    print("walking CAS-MRT-C01-A Fatmawati branch")
    br_c = branch_controls()
    geom_b, notes_b, roads_b, align_b, segs_b = walk_controls(br_c, road_map, min_loop=1800.0)
    geom_b = inject_node(geom_b, SAWANGAN, max_off=800)
    geom_b = inject_node(geom_b, FATMAWATI, max_off=800)
    geom_b = densify_line(clean_chain(geom_b), 45)
    qa_b = qa(geom_b, "BRANCH")
    mandatory_b = [
        ("Sawangan", SAWANGAN, {"interchange": "YES", "interchange_mode": "BRANCH", "node_type": "BRANCH", "placement_reason": "BRANCH_NODE"}),
        ("Fatmawati", FATMAWATI, {"existing": "YES", "interchange": "YES", "interchange_mode": "MRT existing NS", "node_type": "TERMINUS"}),
    ]
    stops_b, gaps_b, tot_b = scan_stations(geom_b, mandatory_b, pois, min_gap=1400.0)
    stops_b = force_named(
        geom_b,
        stops_b,
        [
            ("Limo", (106.77620, -6.35100), {"node_type": "URBAN_NODE"}),
            ("Cinere", (106.78500, -6.33250), {"node_type": "URBAN_NODE"}),
            ("Krukut", (106.79600, -6.32200), {"node_type": "URBAN_NODE"}),
            ("Andara", (106.80362, -6.31392), {"node_type": "URBAN_NODE"}),
            ("Cilandak", (106.79995, -6.29147), {"node_type": "URBAN_NODE"}),
        ],
        min_gap=700,
    )
    spec_b = dict(id="CAS-MRT-C01-A", name="Sawangan – Fatmawati", short="Sawangan – Fatmawati", from_name="Sawangan", to_name="Fatmawati", direction="Sawangan → Fatmawati", branch_id="A", branch_name="Branch Sawangan – Cinere – Fatmawati", parent_route="CAS-MRT-C01", network_type="BRANCH", plan_type="NEW_TRUNK", note=NOTE_BRANCH)
    rf_b, sf_b, km_b, conf_b, meta_b = pack(spec_b, geom_b, br_c, stops_b, notes_b, roads_b, align_b, 21, tot_b)

    print("scanning CAS-MRT-C01-BR02 (geometry frozen)")
    mandatory_br = [
        ("Ciputat", CIPUTAT, {"interchange": "YES", "interchange_mode": "CAS-MRT-C01 mainline", "node_type": "BRANCH", "placement_reason": "BRANCH_NODE"}),
        ("Taman Kota 2", (106.68165, -6.32869), {"node_type": "MAJOR_DESTINATION", "activity_type": "PARK_TOD"}),
        ("Rawa Buntu", (106.67505, -6.31551), {"existing": "YES", "interchange": "YES", "interchange_mode": "KRL", "node_type": "INTERCHANGE"}),
        ("ICE BSD Hall 10", (106.63657, -6.30068), {"node_type": "TERMINUS", "activity_type": "MAJOR_DESTINATION"}),
    ]
    stops_br, gaps_br, tot_br = scan_stations(br02_geom, mandatory_br, pois, min_gap=1400.0)
    stops_br = force_named(
        br02_geom,
        stops_br,
        [
            ("Pamulang", (106.73800, -6.34300), {"node_type": "URBAN_NODE"}),
            ("Siliwangi", (106.71509, -6.34575), {"node_type": "URBAN_NODE"}),
            ("BSD CBD", (106.65437, -6.30126), {"node_type": "MAJOR_DESTINATION", "activity_type": "CBD"}),
        ],
    )
    spec_br = dict(id="CAS-MRT-C01-BR02", name="Ciputat – Pamulang – BSD – ICE", short="Ciputat – ICE BSD", from_name="Ciputat", to_name="ICE BSD Hall 10", direction="Ciputat → ICE BSD Hall 10", branch_id="BR02", branch_name="Branch Ciputat–Pamulang–BSD–ICE", parent_route="CAS-MRT-C01", network_type="BRANCH", plan_type="NEW_TRUNK", note=NOTE_BR02)
    km_br = round(tot_br / 1000, 2)
    sf_br = make_stops_from_scan(spec_br, br02_geom, stops_br, "HIGH", "VIADUCT", ["Jalan Laksamana RE Martadinata", "Jalan Siliwangi", "Jalan Pahlawan Seribu", "Jalan BSD Grand Boulevard"], NOTE_BR02, km_br)

    assert haversine(geom_m[0], LEBAK_BULUS) < 40
    assert haversine(geom_m[-1], ANCOL) < 80
    assert haversine(geom_b[0], SAWANGAN) < 40
    assert haversine(geom_b[-1], FATMAWATI) < 80
    assert min(haversine(p, CIPUTAT) for p in geom_m) < 80
    assert min(haversine(p, SAWANGAN) for p in geom_m) < 80
    assert min(haversine(p, CIJANTUNG) for p in geom_m) < 200
    assert min(haversine(p, PGC) for p in geom_m) < 150
    assert min(haversine(p, CONDET_ROAD) for p in geom_m) < 200
    assert min(haversine(p, MATRAMAN) for p in geom_m) < 350
    assert min(haversine(p, PRAMUKA) for p in geom_m) < 450
    assert min(haversine(p, GUNUNG_SAHARI) for p in geom_m) < 450
    assert min(haversine(p, PARUNG_BINGUNG) for p in geom_m) < 400
    d_parung = min(haversine(p, PARUNG_TOWN) for p in geom_m)
    assert d_parung > 900, f"entered Parung town {d_parung:.0f}m"
    assert min(p[1] for p in geom_m) > -6.415
    assert min(p[1] for p in geom_m) < -6.395
    d_fat_main = min(haversine(p, FATMAWATI) for p in geom_m)
    assert d_fat_main > 1500
    names_m = [s["stop_name"] for s in stops_m]
    print("STOPS", " → ".join(names_m))
    print("ALONG", " | ".join(f"{s['stop_name']} {s['along_m']/1000:.2f}" for s in stops_m))
    assert "Kramat Jati" not in names_m
    assert not any(n == "Parung" for n in names_m)
    assert "Ciputat" in names_m and "Sawangan" in names_m and "Cijantung" in names_m
    def idx(n):
        return next(i for i, s in enumerate(stops_m) if s["stop_name"] == n)
    assert idx("Ciputat") < idx("Parung Bingung") < idx("Sawangan")
    assert idx("Cijantung") < idx("PGC") < idx("Condet")
    assert idx("Manggarai") < idx("Matraman") < idx("Salemba") < idx("Pramuka") < idx("Senen") < idx("Gunung Sahari") < idx("Ancol")
    for need in ("Pondok Cabe", "Bojongsari", "Mampang Depok", "Cimanggis", "Ciracas", "Pasar Rebo"):
        assert need in names_m, f"missing scan/mandatory {need}"
    d_saw = haversine(geom_b[0], min(geom_m, key=lambda p: haversine(p, SAWANGAN)))
    d_cip = haversine(br02_geom[0], min(geom_m, key=lambda p: haversine(p, CIPUTAT)))
    print(f"  Sawangan {d_saw:.0f}m Ciputat {d_cip:.0f}m Parung town {d_parung:.0f}m")
    print(f"  Cijantung {min(haversine(p, CIJANTUNG) for p in geom_m):.0f}m Matraman {min(haversine(p, MATRAMAN) for p in geom_m):.0f}m Pramuka {min(haversine(p, PRAMUKA) for p in geom_m):.0f}m")

    def drop_route(f):
        return feat_id(f) in ("CAS-MRT-C01", "CAS-MRT-C01-A")

    def drop_stop(f):
        rid = str(f["properties"].get("route_id") or "")
        i = feat_id(f)
        return rid in ("CAS-MRT-C01", "CAS-MRT-C01-A", "CAS-MRT-C01-BR02") or i.startswith("CAS-MRT-C01-S") or i.startswith("CAS-MRT-C01-A") or i.startswith("CAS-MRT-C01-BR02")

    route_feats = replace_keep(old_routes["features"], drop_route, [rf_m, rf_b])
    for f in route_feats:
        if feat_id(f) == "CAS-MRT-C01-BR02":
            f["properties"]["stop_count"] = len(stops_br)
            f["properties"]["notes"] = NOTE_BR02
            f["properties"]["planning_note"] = NOTE_BR02
    stop_feats = replace_keep(old_stops["features"], drop_stop, sf_m + sf_b + sf_br)
    ids = [feat_id(f) for f in route_feats]
    for need in ("CAS-TJ07", "CAS-LRT-C02", "CAS-MRT-C01", "CAS-MRT-C01-A", "CAS-MRT-C01-BR02", "KRL-C03-N", "KRL-C03-S"):
        assert need in ids, f"missing {need}"

    after = {feat_id(f): geom_hash(f["geometry"]["coordinates"]) for f in route_feats}
    for k, h in {**TJ_HASH, **LRT_HASH, **KRL_HASH}.items():
        if after.get(k) != h:
            raise SystemExit(f"FROZEN DRIFT {k}")
    if after.get("CAS-MRT-C01-BR02") != BR02_HASH:
        raise SystemExit(f"BR02 GEOM DRIFT {after.get('CAS-MRT-C01-BR02')}")

    meta = [m for m in (old_meta.get("corridors") or []) if not str(m.get("id", "")).startswith("CAS-MRT")]
    meta.extend([meta_m, meta_b])
    br02_meta = next((m for m in (old_meta.get("corridors") or []) if m.get("id") == "CAS-MRT-C01-BR02"), None)
    if br02_meta:
        br02_meta = dict(br02_meta)
        br02_meta["stop_count"] = len(stops_br)
        br02_meta["notes"] = NOTE_BR02
        meta.append(br02_meta)

    (PUB / "cascade_candidates.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (PUB / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    (OUT / "cascade_routes.geojson").write_text(json.dumps(fc(route_feats), ensure_ascii=False))
    (OUT / "cascade_stops.geojson").write_text(json.dumps(fc(stop_feats), ensure_ascii=False))
    existing = dict(old_meta)
    existing["source"] = SOURCE
    existing["corridors"] = meta
    existing["mrt_note"] = "CAS-MRT-C01 mainline (Parung=arah) + Fatmawati branch + BSD branch. Scan ±2 km. Bukan existing. Bukan masterplan."
    (PUB / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_existing.json").write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    (OUT / "cascade_mrt_segments.json").write_text(json.dumps({"main": segs_m, "branch": segs_b}, ensure_ascii=False, indent=2))
    (OUT / "cascade_mrt_scan.json").write_text(
        json.dumps(
            {
                "main_stops": [s["stop_name"] for s in stops_m],
                "main_gaps": gaps_m,
                "branch_stops": [s["stop_name"] for s in stops_b],
                "br02_stops": [s["stop_name"] for s in stops_br],
                "parung_town_distance_m": round(d_parung, 1),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    src_path = PUB / "sources.json"
    sources = json.loads(src_path.read_text())
    for row in sources:
        if row.get("dataset") == "cascade_candidates":
            row["count"] = len(route_feats)
        if row.get("dataset") == "cascade_stops":
            row["count"] = len(stop_feats)
    src_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))

    val = {
        "corridors": [meta_m, meta_b],
        "qa": {"MAIN": qa_m, "BRANCH": qa_b},
        "notes_main": notes_m[-24:],
        "notes_branch": notes_b[-12:],
        "tj_frozen": TJ_HASH,
        "lrt_frozen": LRT_HASH,
        "krl_frozen": KRL_HASH,
        "br02_frozen": BR02_HASH,
        "masterplan_untouched": True,
        "existing_untouched": True,
        "parung_is_terminus": False,
        "parung_town_distance_m": round(d_parung, 1),
        "sawangan_shared_m": round(d_saw, 1),
        "ciputat_shared_m": round(d_cip, 1),
        "fatmawati_vs_main_m": round(d_fat_main, 1),
        "hashes": {"CAS-MRT-C01": after["CAS-MRT-C01"], "CAS-MRT-C01-A": after["CAS-MRT-C01-A"], "CAS-MRT-C01-BR02": after["CAS-MRT-C01-BR02"]},
    }
    (OUT / "cascade_validation_mrt.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))
    for fn, expect in READONLY_FILES.items():
        if file_hash(PUB / fn) != expect:
            raise SystemExit(f"READONLY TOUCHED {fn}")

    print("\n=== SUMMARY ===")
    print(f"CAS-MRT-C01      {km_m} km  stations={len(stops_m)}  {conf_m}")
    print("   ", " → ".join(s["stop_name"] for s in stops_m))
    print(f"CAS-MRT-C01-A    {km_b} km  stations={len(stops_b)}  {conf_b}")
    print("   ", " → ".join(s["stop_name"] for s in stops_b))
    print(f"CAS-MRT-C01-BR02 {km_br} km  stations={len(stops_br)}  geom FROZEN")
    print("   ", " → ".join(s["stop_name"] for s in stops_br))
    print(f"Parung town {d_parung:.0f}m  TJ+LRT+KRL+BR02 frozen")


if __name__ == "__main__":
    main()
