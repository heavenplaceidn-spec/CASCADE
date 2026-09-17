#!/usr/bin/env python3
"""PASS 13 — rebuild TransJakarta existing 1–14 from Jakarta Satu + OSM roads."""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace")
JS = Path("/tmp/cascade-data/jakartasatu")
OSM_ROADS = Path("/tmp/cascade-data/osm/roads-major.json")
OUT = ROOT / "public" / "data"

TJ_COLOR = "#5865C7"
SRC_RUTE = "Jakarta Satu / Jaklingko Rute_TJ FeatureServer"
SRC_HALTE = "Jakarta Satu / Jaklingko Perhentian_TJ FeatureServer"
SRC_SEQ = "Jakarta Satu / Jaklingko Stop_Sequence_Transjakarta"
SRC_URL = "https://jakartasatu.jakarta.go.id/server/rest/services/Jaklingko"
STOP_TOL_M = 150.0

CORRIDORS = {
    1: {
        "name": "Koridor 1",
        "from": "Blok M",
        "to": "Kota",
        "endpoint": "Blok M - Kota",
        "ruas": [
            "Blok M",
            "Jl. Sultan Hasanuddin",
            "Jl. Sisingamangaraja",
            "Jl. Jenderal Sudirman",
            "Jl. M.H. Thamrin",
            "Jl. Medan Merdeka Barat",
            "Jl. Majapahit",
            "Jl. Hayam Wuruk",
            "Jl. Gajah Mada",
            "Jl. Pintu Besar Selatan",
            "Kota",
        ],
        "geometry_type": "road",
    },
    2: {
        "name": "Koridor 2",
        "from": "Pulo Gadung",
        "to": "Monas",
        "endpoint": "Pulo Gadung - Monas",
        "ruas": [
            "Pulo Gadung",
            "Jl. Perintis Kemerdekaan",
            "Jl. Jenderal Ahmad Yani",
            "Jl. Pramuka",
            "Jl. Salemba Raya",
            "Jl. Kramat Raya",
            "Jl. Senen Raya",
            "Jl. Letjen Suprapto",
            "Jl. Gunung Sahari Raya",
            "Lapangan Banteng / Juanda",
            "Jl. Ir. H. Juanda",
            "Monas",
        ],
        "geometry_type": "road",
    },
    3: {
        "name": "Koridor 3",
        "from": "Kalideres",
        "to": "Monas",
        "endpoint": "Kalideres - Monas via Veteran",
        "ruas": [
            "Terminal Kalideres",
            "Jl. Daan Mogot",
            "Jl. Kyai Tapa",
            "Jl. Tomang Raya",
            "Jl. Letjen S. Parman",
            "Tanah Abang",
            "Jl. KH Hasyim Ashari",
            "Harmoni",
            "Jl. Veteran",
            "Jl. Medan Merdeka Barat",
            "Monas",
        ],
        "geometry_type": "road",
    },
    4: {
        "name": "Koridor 4",
        "from": "Pulo Gadung",
        "to": "Galunggung",
        "endpoint": "Pulo Gadung - Galunggung",
        "ruas": [
            "Pulo Gadung",
            "Jl. Bekasi Raya",
            "Jl. Pemuda",
            "Jl. Pramuka",
            "Jl. Matraman Raya",
            "Jl. Slamet Riyadi",
            "Jl. Manggarai Utara",
            "Jl. Sultan Agung",
            "Jl. Galunggung",
            "Galunggung",
        ],
        "geometry_type": "road",
        "notes": "Lintasan sementara Matraman; arah balik berbeda di sekitar Manggarai.",
    },
    5: {
        "name": "Koridor 5",
        "from": "Kampung Melayu",
        "to": "Ancol",
        "endpoint": "Kampung Melayu - Ancol",
        "ruas": [
            "Kampung Melayu",
            "Jl. Jatinegara Barat",
            "Jl. Jatinegara Timur",
            "Jl. Matraman Raya",
            "Jl. Salemba Raya",
            "Jl. Kramat Raya",
            "Jl. Pasar Senen",
            "Jl. Gunung Sahari Raya",
            "Pademangan",
            "Ancol",
        ],
        "geometry_type": "road",
    },
    6: {
        "name": "Koridor 6",
        "from": "Ragunan",
        "to": "Galunggung",
        "endpoint": "Ragunan - Galunggung",
        "ruas": [
            "Ragunan",
            "Jl. Harsono RM",
            "Jl. Warung Jati Barat",
            "Jl. Warung Buncit",
            "Jl. Mampang Prapatan",
            "Jl. H.R. Rasuna Said",
            "Jl. Kendal",
            "Jl. Latuharhari",
            "Jl. Sultan Agung",
            "Jl. Galunggung",
            "Galunggung",
        ],
        "geometry_type": "road",
    },
    7: {
        "name": "Koridor 7",
        "from": "Kampung Melayu",
        "to": "Kampung Rambutan",
        "endpoint": "Kampung Melayu - Kampung Rambutan",
        "ruas": [
            "Kampung Melayu",
            "Jl. Otto Iskandardinata",
            "Jl. MT Haryono",
            "Jl. Mayjen Sutoyo",
            "Jl. Raya Bogor",
            "Jl. Gedong",
            "Kampung Rambutan",
        ],
        "geometry_type": "road",
        "halte": [
            "Kampung Melayu",
            "Bidara Cina",
            "Gelanggang Remaja",
            "Cawang Baru",
            "Cawang",
            "BNN",
            "Cawang UKI",
            "Cililitan",
            "PGC",
            "Kramat Jati",
            "Pasar Induk",
            "Trikora",
            "Flyover Raya Bogor",
            "Tanah Merdeka",
            "Kampung Rambutan",
        ],
    },
    8: {
        "name": "Koridor 8",
        "from": "Lebak Bulus",
        "to": "Pasar Baru",
        "endpoint": "Lebak Bulus - Pasar Baru",
        "ruas": [
            "Lebak Bulus",
            "Jl. Pasar Jumat",
            "Jl. Ciputat Raya",
            "Jl. Metro Pondok Indah",
            "Jl. Sultan Iskandar Muda",
            "Jl. Teuku Nyak Arief",
            "Jl. Permata Hijau",
            "Jl. Panjang",
            "Jl. Daan Mogot",
            "Jl. Prof. Dr. Latumenten",
            "Jl. Kyai Tapa",
            "Jl. Tanjung Duren Raya",
            "Jl. Tomang Raya",
            "Jl. K.H. Hasyim Ashari",
            "Jl. Pecenongan",
            "Jl. Ir. H. Juanda",
            "Pasar Baru",
        ],
        "geometry_type": "road",
    },
    9: {
        "name": "Koridor 9",
        "from": "Pinang Ranti",
        "to": "Pluit",
        "endpoint": "Pinang Ranti - Pluit",
        "ruas": [
            "Pinang Ranti",
            "Jl. Pondok Gede Raya",
            "Tol Jagorawi",
            "Jl. Mayjen Sutoyo",
            "Jl. MT Haryono",
            "Jl. Gatot Subroto",
            "Jl. Letjen S. Parman",
            "Jl. Satria / Prof. Dr. Makaliwe",
            "Jl. Prof. Dr. Latumenten",
            "Jl. Jembatan Dua",
            "Jl. Jembatan Tiga",
            "Jl. Pluit Selatan",
            "Jl. Pluit Putra / Pluit Putri",
            "Pluit",
        ],
        "geometry_type": "road",
        "has_toll": True,
    },
    10: {
        "name": "Koridor 10",
        "from": "Tanjung Priok",
        "to": "PGC",
        "endpoint": "Tanjung Priok - PGC",
        "ruas": [
            "Tanjung Priok",
            "Jl. Enggano",
            "Jl. Laksamana Yos Sudarso",
            "Jl. Jenderal Ahmad Yani",
            "Jl. Pramuka / Rawamangun",
            "Jl. Bekasi Timur Raya",
            "Jl. DI Panjaitan",
            "Jl. Mayjen Sutoyo",
            "Jl. Dewi Sartika",
            "PGC Cililitan",
        ],
        "geometry_type": "road",
    },
    11: {
        "name": "Koridor 11",
        "from": "Pulo Gebang",
        "to": "Kampung Melayu",
        "endpoint": "Pulo Gebang - Kampung Melayu",
        "ruas": [
            "Terminal Pulo Gebang",
            "Jl. Sentra Primer Timur",
            "Jl. Dr. Sumarno",
            "Jl. Penggilingan Raya",
            "Jl. I Gusti Ngurah Rai",
            "Jl. Bekasi Timur Raya",
            "Jl. Bekasi Barat Raya",
            "Jl. Jatinegara Barat / Jatinegara Timur",
            "Kampung Melayu",
        ],
        "geometry_type": "road",
    },
    12: {
        "name": "Koridor 12",
        "from": "Pluit",
        "to": "Tanjung Priok",
        "endpoint": "Pluit - Tanjung Priok",
        "ruas": [
            "Pluit",
            "Jl. Jembatan Tiga Raya",
            "Jl. Pluit Selatan Raya",
            "Jl. Pluit Timur Raya",
            "Jl. Gedong Panjang",
            "Jl. Kopi",
            "Kota Tua",
            "Jl. Mangga Dua Raya",
            "Jl. Gunung Sahari Raya",
            "Jl. Angkasa",
            "Jl. HBR Motik",
            "Jl. Danau Sunter Barat",
            "Jl. Danau Sunter Utara",
            "Sunter Kelapa Gading",
            "Jl. Laksamana Yos Sudarso",
            "Plumpang",
            "Walikota Jakarta Utara",
            "Jl. Enggano",
            "Tanjung Priok",
        ],
        "geometry_type": "road",
        "notes": "Poros operasional Penjaringan–Sunter; jaringan penuh sampai Tanjung Priok.",
    },
    13: {
        "name": "Koridor 13",
        "from": "Ciledug / Puri Beta",
        "to": "Tegal Mampang",
        "endpoint": "Ciledug / Puri Beta - Tegal Mampang",
        "ruas": [
            "Ciledug / Puri Beta",
            "Jl. Ciledug Raya",
            "Jl. Kebayoran Lama",
            "Cipulir",
            "Jl. Kyai Maja",
            "Jl. Sisingamangaraja",
            "Jl. Trunojoyo",
            "Jl. Wolter Monginsidi",
            "Jl. Kapten Tendean",
            "Tegal Mampang",
        ],
        "geometry_type": "elevated",
    },
    14: {
        "name": "Koridor 14",
        "from": "JIS",
        "to": "Senen",
        "endpoint": "JIS - Senen",
        "ruas": [
            "JIS",
            "Jembatan Item",
            "Jl. Danau Sunter Utara",
            "Danau Agung",
            "Jl. Landasan Pacu",
            "JIExpo Kemayoran",
            "Kemayoran",
            "Tanah Tinggi",
            "Pasar Senen",
            "Jl. Senen Raya",
            "Senen",
        ],
        "geometry_type": "road",
    },
}


def haversine(a, b):
    R = 6371000.0
    lon1, lat1 = a[0], a[1]
    lon2, lat2 = b[0], b[1]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def parts_of(g):
    if not g:
        return []
    t = g.get("type")
    if t == "LineString":
        return [g["coordinates"]]
    if t == "MultiLineString":
        return g["coordinates"]
    return []


def length_m(g):
    s = 0.0
    for part in parts_of(g):
        for i in range(1, len(part)):
            s += haversine(part[i - 1], part[i])
    return s


def endpoints(g):
    parts = parts_of(g)
    if not parts or not parts[0]:
        return None, None
    return parts[0][0][:2], parts[-1][-1][:2]


def is_loop(g, tol=80):
    a, b = endpoints(g)
    if not a or not b:
        return True
    return haversine(a, b) < tol


def xy(c):
    return (float(c[0]), float(c[1]))


def dist_point_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return haversine(p, a)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    # approximate metres via haversine to interpolated lonlat
    q = (ax + t * dx, ay + t * dy)
    return haversine(p, q)


def dist_point_line(p, g):
    best = 1e12
    for part in parts_of(g):
        for i in range(1, len(part)):
            d = dist_point_seg(p, xy(part[i - 1]), xy(part[i]))
            if d < best:
                best = d
    return best


def clean_name(n):
    n = (n or "").strip()
    n = re.sub(r"\s+", " ", n)
    return n


def is_archived(name):
    return bool(re.search(r"archive|arsip", name or "", re.I))


def parse_corridor_tokens(text):
    out = []
    for tok in re.split(r"[,\s/]+", str(text or "")):
        tok = tok.strip()
        if tok.isdigit():
            n = int(tok)
            if 1 <= n <= 14:
                out.append(n)
    return sorted(set(out))


def choose_route_feature(feats):
    scored = []
    for f in feats:
        g = f.get("geometry") or {}
        L = length_m(g)
        npts = sum(len(p) for p in parts_of(g))
        loop = is_loop(g)
        named = f["properties"].get("TPRUTE") not in (None, "BRT")
        score = npts + (0 if loop else 400) + (80 if named else 0) + L / 50
        scored.append((score, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def simplify(coords, eps=0.00012):
    if len(coords) <= 4:
        return [xy(c) for c in coords]

    def _perp(p, a, b):
        ax, ay = a
        bx, by = b
        px, py = p
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def rec(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        mid = max(range(1, len(pts) - 1), key=lambda i: _perp(pts[i], a, b))
        d = _perp(pts[mid], a, b)
        if d > eps:
            left = rec(pts[: mid + 1])
            right = rec(pts[mid:])
            return left[:-1] + right
        return [a, b]

    pts = [xy(c) for c in coords]
    return rec(pts)


def load_json(p):
    return json.loads(Path(p).read_text())


def main():
    rute = load_json(JS / "rute_tj_1_14.geojson")
    halte = load_json(JS / "halte_koridor.geojson")
    seq = load_json(JS / "stopseq_1_14.geojson")

    by_no = defaultdict(list)
    for f in rute["features"]:
        no = int(str(f["properties"]["KODRUTE"]))
        by_no[no].append(f)

    route_feats = []
    segment_feats = []
    catalog = []
    geom_by_no = {}
    report = {"corridors": {}, "halte": {}, "roads": {}, "issues": []}

    for no in range(1, 15):
        meta = CORRIDORS[no]
        feats = by_no.get(no, [])
        if not feats:
            report["issues"].append(f"K{no} missing Jakarta Satu geometry")
            continue
        chosen = choose_route_feature(feats)
        g = chosen["geometry"]
        # drop empty / tiny parts
        parts = [p for p in parts_of(g) if len(p) >= 2]
        if len(parts) == 1:
            geom = {"type": "LineString", "coordinates": [[c[0], c[1]] for c in parts[0]]}
        else:
            geom = {"type": "MultiLineString", "coordinates": [[[c[0], c[1]] for c in p] for p in parts]}
        km = round(length_m(geom) / 1000.0, 2)
        loop = is_loop(geom)
        if loop:
            report["issues"].append(f"K{no} geometry start≈end (round-trip stored as one feature), length_km={km}")
        geom_by_no[no] = geom
        ruas_txt = " > ".join(meta["ruas"])
        props = {
            "id": f"tj-k{no}",
            "corridor_id": f"K{no}",
            "corridor_no": no,
            "corridor_nos": f",{no},",
            "name": meta["name"],
            "route_name": meta["name"],
            "endpoint": meta["endpoint"],
            "from_name": meta["from"],
            "to_name": meta["to"],
            "ruas": ruas_txt,
            "mode": "TransJakarta",
            "status": "existing",
            "status_label": "Jaringan saat ini",
            "source": SRC_RUTE,
            "source_type": "official",
            "source_url": SRC_URL + "/Rute_TJ/FeatureServer/3",
            "operator": "TransJakarta",
            "length_km": km,
            "geometry_type": meta["geometry_type"],
            "has_toll": bool(meta.get("has_toll")),
            "color": TJ_COLOR,
        }
        if meta.get("notes"):
            props["notes"] = meta["notes"]
        route_feats.append({"type": "Feature", "id": f"tj-k{no}", "geometry": geom, "properties": props})

        for i, part in enumerate(parts):
            seg_g = {"type": "LineString", "coordinates": [[c[0], c[1]] for c in part]}
            segment_feats.append(
                {
                    "type": "Feature",
                    "id": f"tj-k{no}-s{i}",
                    "geometry": seg_g,
                    "properties": {
                        "id": f"tj-k{no}-s{i}",
                        "corridor_id": f"K{no}",
                        "corridor_no": no,
                        "corridor_nos": f",{no},",
                        "name": meta["name"],
                        "route_name": meta["name"],
                        "segment_index": i,
                        "mode": "TransJakarta",
                        "status": "existing",
                        "source": SRC_RUTE,
                        "source_type": "official",
                        "length_km": round(length_m(seg_g) / 1000.0, 3),
                        "geometry_type": meta["geometry_type"],
                    },
                }
            )

        report["corridors"][no] = {
            "n_source_features": len(feats),
            "chosen_tprute": chosen["properties"].get("TPRUTE"),
            "geom": geom["type"],
            "parts": len(parts),
            "length_km": km,
            "loop": loop,
            "npts": sum(len(p) for p in parts),
        }

    # Stop sequences → corridor membership + prev/next
    seq_by_stop = defaultdict(set)
    seq_rows = defaultdict(list)  # (no, arah) -> ordered unique names
    seq_points = {}
    for f in seq["features"]:
        p = f["properties"]
        no = int(str(p.get("KODRUTE") or 0) or 0)
        if no < 1 or no > 14:
            continue
        sid = str(p.get("IDSTOP") or "")
        name = clean_name(p.get("NMPRHNTIAN"))
        arah = str(p.get("KETERAGAN") or "PERGI").upper()
        urut = int(p.get("URUTAN") or 0)
        if sid:
            seq_by_stop[sid].add(no)
        seq_rows[(no, arah)].append((urut, sid, name))
        if sid and f.get("geometry") and sid not in seq_points:
            seq_points[sid] = {
                "geometry": f["geometry"],
                "name": name,
                "idstop": sid,
            }

    seq_order = {}
    for key, rows in seq_rows.items():
        rows = sorted(rows, key=lambda x: x[0])
        # unique by stop id keeping order
        seen = set()
        ordered = []
        for urut, sid, name in rows:
            if sid in seen:
                continue
            seen.add(sid)
            ordered.append((sid, name))
        seq_order[key] = ordered

    def prev_next(sid, corridors):
        prevs, nexts = [], []
        for no in corridors:
            for arah in ("PERGI", "PULANG"):
                ordered = seq_order.get((no, arah), [])
                ids = [x[0] for x in ordered]
                if sid not in ids:
                    continue
                i = ids.index(sid)
                if i > 0:
                    prevs.append(ordered[i - 1][1])
                if i < len(ordered) - 1:
                    nexts.append(ordered[i + 1][1])
        def uniq(xs):
            out = []
            for x in xs:
                if x and x not in out:
                    out.append(x)
            return out
        return uniq(prevs), uniq(nexts)

    # Halte: official corridor shelters + sequence stops
    halte_by_id = {}
    for f in halte["features"]:
        p = f["properties"]
        sid = str(p.get("IDSTOP") or "")
        name = clean_name(p.get("NMPRHNTIAN"))
        if not sid or is_archived(name):
            continue
        nos = parse_corridor_tokens(p.get("KORIDOR"))
        nos += parse_corridor_tokens(p.get("OPRRUTE"))
        nos = sorted(set(n for n in nos if 1 <= n <= 14))
        halte_by_id[sid] = {
            "id": sid,
            "name": name,
            "geometry": f["geometry"],
            "koridor_field": p.get("KORIDOR"),
            "oprrute": p.get("OPRRUTE") or "",
            "kecamatan": p.get("WADMKC") or "",
            "kota": p.get("WADMKK") or "",
            "tipe": p.get("TPHALTE") or p.get("TPPRHNTIAN") or "Halte",
            "status_ops": p.get("STSOPRS") or "",
            "corridors": set(nos),
        }

    for sid, info in seq_points.items():
        if sid not in halte_by_id:
            name = info["name"]
            if is_archived(name):
                continue
            halte_by_id[sid] = {
                "id": sid,
                "name": name,
                "geometry": info["geometry"],
                "koridor_field": "",
                "oprrute": "",
                "kecamatan": "",
                "kota": "",
                "tipe": "Halte",
                "status_ops": "",
                "corridors": set(),
                "from_seq": True,
            }
        halte_by_id[sid]["corridors"] |= seq_by_stop.get(sid, set())

    stop_feats = []
    rejected = []
    used_xy = []

    def too_close(pt, existing, lim=12):
        for e in existing:
            if haversine(pt, e) < lim:
                return True
        return False

    for sid, h in sorted(halte_by_id.items()):
        g = h["geometry"]
        if not g or g.get("type") != "Point":
            rejected.append((sid, h["name"], "not-point"))
            continue
        pt = xy(g["coordinates"])
        corridors = sorted(n for n in h["corridors"] if n in geom_by_no)
        if not corridors:
            # try nearest corridor
            best = None
            for no, geom in geom_by_no.items():
                d = dist_point_line(pt, geom)
                if best is None or d < best[0]:
                    best = (d, no)
            if best and best[0] <= STOP_TOL_M:
                corridors = [best[1]]
            else:
                rejected.append((sid, h["name"], f"no-corridor d={best[0] if best else None}"))
                continue
        # spatial: must be near at least one assigned corridor
        near = []
        for no in corridors:
            d = dist_point_line(pt, geom_by_no[no])
            if d <= STOP_TOL_M:
                near.append(no)
        if not near:
            # keep if very close to any TJ corridor (interchange tagging mismatch)
            best = min(dist_point_line(pt, geom) for geom in geom_by_no.values())
            if best > STOP_TOL_M:
                rejected.append((sid, h["name"], f"far {best:.0f}m"))
                continue
            near = corridors
        corridors = sorted(set(near))
        prevs, nexts = prev_next(sid, corridors)
        nos_csv = ",".join(str(n) for n in corridors)
        padded = "," + nos_csv + ","
        # do not collapse directional platforms (Arah Utara/Selatan)
        stop_feats.append(
            {
                "type": "Feature",
                "id": sid,
                "geometry": {"type": "Point", "coordinates": [pt[0], pt[1]]},
                "properties": {
                    "id": sid,
                    "stop_id": sid,
                    "name": h["name"],
                    "stop_name": h["name"],
                    "route_name": h["name"],
                    "corridor_id": ",".join(f"K{n}" for n in corridors),
                    "corridor_no": corridors[0],
                    "corridor_nos": padded,
                    "koridor_label": ", ".join(str(n) for n in corridors),
                    "mode": "TransJakarta",
                    "status": "existing",
                    "status_label": "Jaringan saat ini",
                    "source": SRC_HALTE if not h.get("from_seq") else SRC_SEQ,
                    "source_type": "official",
                    "source_url": SRC_URL + "/Perhentian_TJ/FeatureServer/0",
                    "operator": "TransJakarta",
                    "prev_stop": " · ".join(prevs[:3]) if prevs else "",
                    "next_stop": " · ".join(nexts[:3]) if nexts else "",
                    "tipe": h["tipe"],
                    "kecamatan": h["kecamatan"],
                    "kota": h["kota"],
                    "interchange": len(corridors) > 1,
                    "color": TJ_COLOR,
                },
            }
        )
        used_xy.append(pt)

    # attach halte counts to routes
    halte_count = defaultdict(int)
    for f in stop_feats:
        for n in parse_corridor_tokens(f["properties"]["koridor_label"]):
            halte_count[n] += 1
    for f in route_feats:
        no = f["properties"]["corridor_no"]
        f["properties"]["stop_count"] = halte_count.get(no, 0)
        catalog.append(
            {
                "corridor_no": no,
                "id": f["properties"]["id"],
                "name": f["properties"]["name"],
                "endpoint": f["properties"]["endpoint"],
                "from_name": f["properties"]["from_name"],
                "to_name": f["properties"]["to_name"],
                "ruas": CORRIDORS[no]["ruas"],
                "length_km": f["properties"]["length_km"],
                "stop_count": f["properties"]["stop_count"],
                "geometry_type": f["properties"]["geometry_type"],
                "has_toll": f["properties"]["has_toll"],
                "status": "existing",
                "source": SRC_RUTE,
            }
        )

    # Roads context from OSM major named highways (merged by name — konteks, bukan TJ)
    road_feats = []
    if OSM_ROADS.exists():
        osm = load_json(OSM_ROADS)
        keep_hw = {"motorway", "trunk", "primary"}
        by_name = defaultdict(list)
        hw_rank = {"motorway": 0, "trunk": 1, "primary": 2}
        name_hw = {}
        for el in osm.get("elements", []):
            if el.get("type") != "way":
                continue
            tags = el.get("tags") or {}
            hw = tags.get("highway")
            name = tags.get("name")
            if hw not in keep_hw or not name:
                continue
            geom = el.get("geometry") or []
            if len(geom) < 2:
                continue
            coords = simplify([(p["lon"], p["lat"]) for p in geom], 0.00022)
            if len(coords) < 2:
                continue
            by_name[name].append(coords)
            prev = name_hw.get(name)
            if prev is None or hw_rank[hw] < hw_rank[prev]:
                name_hw[name] = hw
        for i, (name, parts) in enumerate(sorted(by_name.items())):
            # drop tiny one-part stubs
            parts = [p for p in parts if len(p) >= 2]
            if not parts:
                continue
            if len(parts) == 1:
                geom = {"type": "LineString", "coordinates": parts[0]}
            else:
                geom = {"type": "MultiLineString", "coordinates": parts}
            if length_m(geom) < 250:
                continue
            road_feats.append(
                {
                    "type": "Feature",
                    "id": f"rd-{i}",
                    "geometry": geom,
                    "properties": {
                        "id": f"rd-{i}",
                        "name": name,
                        "route_name": name,
                        "highway": name_hw.get(name, "primary"),
                        "mode": "road",
                        "status": "context",
                        "status_label": "Jalan - konteks",
                        "source": "OpenStreetMap",
                        "source_type": "osm",
                        "license": "ODbL",
                    },
                }
            )

    report["halte"] = {
        "source_koridor": len(halte["features"]),
        "accepted": len(stop_feats),
        "rejected": len(rejected),
        "rejected_sample": rejected[:20],
        "per_corridor": dict(halte_count),
    }
    report["roads"] = {"count": len(road_feats), "source": "OSM Overpass named motorway/trunk/primary"}
    report["segments"] = {"count": len(segment_feats)}
    report["crs"] = "EPSG:4326"
    report["color"] = TJ_COLOR

    OUT.mkdir(parents=True, exist_ok=True)

    def dump(name, feats):
        p = OUT / name
        p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
        print(name, len(feats), "bytes", p.stat().st_size)

    dump("transjakarta_routes.geojson", route_feats)
    dump("transjakarta_stops.geojson", stop_feats)
    dump("transjakarta_segments.geojson", segment_feats)
    dump("roads.geojson", road_feats)
    (OUT / "tj_existing.json").write_text(json.dumps({"corridors": catalog, "color": TJ_COLOR, "crs": "EPSG:4326"}, ensure_ascii=False, indent=2))

    sources_path = OUT / "sources.json"
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else []
    # replace TJ + roads entries
    skip = {"transjakarta_routes", "transjakarta_stops", "transjakarta_segments", "roads", "tj_existing"}
    sources = [s for s in sources if s.get("dataset") not in skip]
    sources = [
        {
            "dataset": "transjakarta_routes",
            "source": SRC_RUTE,
            "url": SRC_URL + "/Rute_TJ/FeatureServer/3",
            "source_type": "official",
            "license": "Pemerintah Provinsi DKI Jakarta / Jakarta Satu",
            "geometry_type": "LineString/MultiLineString",
            "crs": "EPSG:4326",
            "count": len(route_feats),
            "notes": "BRT koridor 1–14 existing. Satu geometri per koridor. Bukan usulan CASCADE.",
        },
        {
            "dataset": "transjakarta_stops",
            "source": SRC_HALTE,
            "url": SRC_URL + "/Perhentian_TJ/FeatureServer/0",
            "source_type": "official",
            "license": "Pemerintah Provinsi DKI Jakarta / Jakarta Satu",
            "geometry_type": "Point",
            "crs": "EPSG:4326",
            "count": len(stop_feats),
            "notes": "Hanya halte koridor BRT, difilter spasial <150 m dari jaringan 1–14.",
        },
        {
            "dataset": "transjakarta_segments",
            "source": SRC_RUTE,
            "source_type": "official",
            "geometry_type": "LineString",
            "crs": "EPSG:4326",
            "count": len(segment_feats),
        },
        {
            "dataset": "roads",
            "source": "OpenStreetMap named motorway/trunk/primary",
            "source_type": "osm",
            "license": "ODbL",
            "geometry_type": "LineString",
            "crs": "EPSG:4326",
            "count": len(road_feats),
            "notes": "Konteks jalan abu-abu. Bukan jaringan TransJakarta.",
        },
    ] + sources
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2))
    (OUT / "tj_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
    print("rejected", len(rejected), "stops", len(stop_feats), "routes", len(route_feats), "roads", len(road_feats))


if __name__ == "__main__":
    main()
