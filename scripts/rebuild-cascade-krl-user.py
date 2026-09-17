#!/usr/bin/env python3
"""Replace ALL CASCADE KRL with the three user GeoJSON alignments.

Does not touch MRT / LRT / TransJakarta / existing KRL / masterplan geometries.
Stations every ~2 km, named from local desa. Dramaga (IPB) is mandatory.
Corners are Chaikin-smoothed then clamped back onto the user path.
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "cascade"
ATT = ROOT / "attachments"
COLOR = "#D62F7F"
CRS = "EPSG:4326"
RETRIEVED = "2026-09-16"
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (krl-rebuild)"}
R = 6371000.0

TANGERANG = (106.6307174, -6.1768139)
PARUNG_PANJANG = (106.568689, -6.3442507)
MAJA = (106.3949324, -6.3318303)
IPB_DRAMAGA = (106.7292, -6.5574)

SRC = "CASCADE KRL — trase user GeoJSON, stasiun desa per 2 km"
DISC = "Usulan CASCADE. Bukan KRL existing. Bukan masterplan. Bukan DED."

# Keep interchange names identical to existing KRL so the multimodal graph clusters them.
FORCED = {
    "Tangerang": TANGERANG,
    "Parung Panjang": PARUNG_PANJANG,
    "Maja": MAJA,
    "Dramaga": IPB_DRAMAGA,
}


def hav(a, b):
    to = math.radians
    dlon = to(b[0] - a[0])
    dlat = to(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(to(a[1])) * math.cos(to(b[1])) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def length_m(coords):
    return sum(hav(coords[i - 1], coords[i]) for i in range(1, len(coords)))


def flatten_fc(path: Path):
    data = json.loads(path.read_text())
    parts = []
    for ft in data["features"]:
        g = ft["geometry"]
        if g["type"] == "LineString":
            parts.append([(float(x), float(y)) for x, y in g["coordinates"]])
        elif g["type"] == "MultiLineString":
            for ring in g["coordinates"]:
                parts.append([(float(x), float(y)) for x, y in ring])
    if not parts:
        raise SystemExit(f"no lines in {path}")
    chain = list(parts[0])
    for nxt in parts[1:]:
        if hav(chain[-1], nxt[0]) <= hav(chain[-1], nxt[-1]):
            use = nxt
        else:
            use = list(reversed(nxt))
        if hav(chain[-1], use[0]) < 5:
            chain.extend(use[1:])
        else:
            chain.extend(use)
    out = [chain[0]]
    for p in chain[1:]:
        if hav(out[-1], p) >= 2:
            out.append(p)
    return out


def densify(coords, step=70.0):
    out = [coords[0]]
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        d = hav(a, b)
        n = max(1, int(d / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def chaikin(coords, rounds=2):
    pts = coords
    for _ in range(rounds):
        nxt = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            nxt.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            nxt.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        nxt.append(pts[-1])
        pts = nxt
    return pts


def nearest_on(coords, pt):
    best_i, best_d = 0, 1e18
    for i, c in enumerate(coords):
        d = hav(c, pt)
        if d < best_d:
            best_i, best_d = i, d
    return best_i, best_d, coords[best_i]


def project_back(smoothed, original, max_off=90.0):
    """Keep smoothing from drifting off the user path."""
    out = []
    for p in smoothed:
        i, d, q = nearest_on(original, p)
        out.append(p if d <= max_off else q)
    cleaned = [out[0]]
    for p in out[1:]:
        if hav(cleaned[-1], p) >= 4:
            cleaned.append(p)
    return cleaned


def snap_end(coords, pt, which="start"):
    coords = list(coords)
    if which == "start":
        coords[0] = pt
        # drop near-duplicates after snap
        while len(coords) > 2 and hav(coords[0], coords[1]) < 8:
            coords.pop(1)
    else:
        coords[-1] = pt
        while len(coords) > 2 and hav(coords[-1], coords[-2]) < 8:
            coords.pop(-2)
    return coords


def inject(coords, pt, max_off=2500.0):
    i, d, _ = nearest_on(coords, pt)
    if d > max_off:
        return coords, False
    # put the station ON the alignment, not off-line
    on = coords[i]
    if hav(coords[i], on) > 1:
        coords = coords[:i] + [on] + coords[i:]
    return coords, True


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
            span = cdist[i] - cdist[i - 1] or 1
            t = (dist - cdist[i - 1]) / span
            a, b = coords[i - 1], coords[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), i
    return coords[-1], len(coords) - 1


NOM_CACHE = {}


def reverse_name(lon, lat):
    key = (round(lon, 4), round(lat, 4))
    if key in NOM_CACHE:
        return NOM_CACHE[key]
    q = urllib.parse.urlencode({
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "format": "json",
        "zoom": 16,
        "addressdetails": 1,
        "accept-language": "id",
    })
    url = f"https://nominatim.openstreetmap.org/reverse?{q}"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode())
        addr = data.get("address") or {}
        name = (
            addr.get("village")
            or addr.get("town")
            or addr.get("suburb")
            or addr.get("hamlet")
            or addr.get("municipality")
            or addr.get("city_district")
            or addr.get("county")
            or ""
        )
        name = str(name).replace("Kelurahan ", "").replace("Desa ", "").strip()
    except Exception:
        name = ""
    NOM_CACHE[key] = name
    time.sleep(1.05)
    return name


def title_id(s):
    s = (s or "").strip()
    if not s:
        return s
    skip = {"dan", "di", "ke", "dari"}
    parts = []
    for w in s.replace("_", " ").split():
        parts.append(w if w.lower() in skip else w[:1].upper() + w[1:])
    return " ".join(parts)


def stations_every_2km(coords, forced_named, start_name, end_name):
    """forced_named: list of (name, xy) to inject/include."""
    geom = list(coords)
    for name, xy in forced_named:
        geom, ok = inject(geom, xy, 4500.0)
    cdist = cum(geom)
    total = cdist[-1]
    wanted = [0.0]
    t = 2000.0
    while t < total - 900:
        wanted.append(t)
        t += 2000.0
    wanted.append(total)

    # pull forced stations onto the 2 km set (replace nearest slot if <900 m)
    forced_dist = []
    for name, xy in forced_named:
        i, d, on = nearest_on(geom, xy)
        if d > 4000 and name != "Dramaga":
            continue
        forced_dist.append((cdist[min(i, len(cdist) - 1)], name, on))
    for fd, name, on in forced_dist:
        close = min(wanted, key=lambda w: abs(w - fd))
        if abs(close - fd) < 900:
            wanted[wanted.index(close)] = fd
        else:
            wanted.append(fd)
    wanted = sorted(set(round(w, 1) for w in wanted))

    used_names = []
    stops = []
    for order, dist in enumerate(wanted, start=1):
        xy, idx = point_at(geom, dist, cdist)
        name = None
        for fd, fn, fon in forced_dist:
            if abs(fd - dist) < 80:
                name = fn
                xy = fon
                break
        if order == 1:
            name = start_name
            xy = geom[0]
        if order == len(wanted):
            name = end_name
            xy = geom[-1]
        if not name:
            raw = reverse_name(xy[0], xy[1])
            name = title_id(raw) or f"KM {int(round(dist / 1000))}"
        # avoid duplicate consecutive names
        base = name
        n = 2
        while any(u.lower() == name.lower() for u in used_names):
            if abs(dist - 0) < 1 or abs(dist - total) < 1:
                break
            raw2 = reverse_name(xy[0] + 0.002 * n, xy[1])
            cand = title_id(raw2)
            name = cand if cand and cand.lower() not in {x.lower() for x in used_names} else f"{base} {n}"
            n += 1
            if n > 4:
                break
        used_names.append(name)
        stops.append({
            "name": name,
            "xy": (round(xy[0], 6), round(xy[1], 6)),
            "order": order,
            "km": round(dist / 1000, 2),
        })
    # re-number
    for i, s in enumerate(stops, start=1):
        s["order"] = i
    return geom, stops


def feat_line(gid, coords, props):
    return {
        "type": "Feature",
        "id": gid,
        "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]},
        "properties": props,
    }


def feat_pt(gid, xy, props):
    return {
        "type": "Feature",
        "id": gid,
        "geometry": {"type": "Point", "coordinates": [round(xy[0], 6), round(xy[1], 6)]},
        "properties": props,
    }


def common_props(spec, km, n_stops, verts, extra=None):
    p = {
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
        "mode": "krl",
        "status": "CASCADE_EXTENSION",
        "status_label": "Usulan CASCADE · perpanjangan KRL",
        "cascade_status": "CASCADE_EXTENSION",
        "network_type": "TRUNK",
        "plan_type": "EXTENSION",
        "existing": "NO",
        "parent_route": "",
        "length_km": round(km, 2),
        "stop_count": n_stops,
        "geometry_confidence": "HIGH",
        "road_alignment_confidence": "HIGH",
        "alignment_confidence": "HIGH",
        "alignment_type": "RAIL_CORRIDOR",
        "rail_backbone": spec["rail_backbone"],
        "color": COLOR,
        "crs": CRS,
        "source": SRC,
        "source_type": "USER_GEOJSON",
        "geometry_source": spec["geometry_source"],
        "planning_note": spec["note"],
        "disclaimer": DISC,
        "updated_at": RETRIEVED,
        "notes": spec["note"],
        "route_order": spec["route_order"],
        "vertex_count": verts,
        "digitization_level": "L3",
        "endpoint": f"{spec['from_name']} – {spec['to_name']}",
        "structure": "AT_GRADE",
        "interchange_count": spec.get("interchange_count", 1),
    }
    if extra:
        p.update(extra)
    return p


def make_stops(spec, stops, km, verts):
    feats = []
    n = len(stops)
    hubs = {"Tangerang", "Parung Panjang", "Maja", "Dramaga"}
    existing = {"Tangerang", "Parung Panjang", "Maja"}
    for s in stops:
        sid = f"{spec['id']}-S{s['order']:02d}"
        is_end = s["order"] in (1, n)
        p = common_props(spec, km, n, verts)
        p.update({
            "id": spec["id"],
            "stop_id": sid,
            "stop_order": s["order"],
            "stop_name": s["name"],
            "name": s["name"],
            "stop_type": "TERMINUS" if is_end else ("INTERCHANGE" if s["name"] in hubs else "STATION"),
            "node_type": "BRANCH" if s["name"] == "Tangerang" else ("INTERCHANGE" if s["name"] in hubs else "STOP"),
            "existing": "YES" if s["name"] in existing else "NO",
            "interchange": "YES" if s["name"] in hubs else "NO",
            "is_interchange": "YES" if s["name"] in hubs else "NO",
            "km_from_start": s["km"],
        })
        feats.append(feat_pt(sid, s["xy"], p))
    return feats


def replace_krl(feats):
    kept = []
    for f in feats:
        p = f.get("properties") or {}
        mode = str(p.get("mode") or "").lower()
        rid = str(f.get("id") or p.get("route_id") or p.get("id") or "")
        if mode == "krl" or rid.startswith("KRL-C03") or rid.startswith("CAS-KRL"):
            continue
        kept.append(f)
    return kept


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def prepare_line(raw, snap_start=None, snap_end=None):
    raw = densify(raw, 90)
    sm = chaikin(raw, 2)
    sm = densify(sm, 55)
    sm = project_back(sm, raw, 85)
    if snap_start:
        sm = snap_end and snap_end  # noqa - keep mypy quiet
    return sm


def build_geom(raw, start=None, end=None):
    raw = densify(raw, 90)
    sm = chaikin(raw, 2)
    sm = densify(sm, 55)
    sm = project_back(sm, raw, 85)
    if start:
        sm = snap_end(sm, start, "start")
    if end:
        sm = snap_end(sm, end, "end")
    return sm


def main():
    n_raw = flatten_fc(ATT / "KRL_TANGERANG_ARAH_UTARA_VIA_MAUK.geojson")
    s_raw = flatten_fc(ATT / "KRL_TANGERANG_ARAH_SELATAN_VIA_BITUNG.geojson")
    w_raw = flatten_fc(ATT / "KRL_SENTUL_JASINGA_MAJA.geojson")

    n_geom = build_geom(n_raw, TANGERANG, None)
    s_geom = build_geom(s_raw, TANGERANG, PARUNG_PANJANG)
    w_geom = build_geom(w_raw, None, MAJA)

    # name north terminus from OSM
    north_end_name = title_id(reverse_name(*n_geom[-1])) or "Kronjo Barat"
    west_start_name = title_id(reverse_name(*w_geom[0])) or "Sentul"

    spec_n = dict(
        id="KRL-C03-N",
        corridor_id="CAS-KRL-C03",
        corridor_name="CASCADE KRL Barat Tangerang",
        name=f"Tangerang – Mauk – {north_end_name}",
        short=f"Tangerang – {north_end_name}",
        from_name="Tangerang",
        to_name=north_end_name,
        direction=f"Tangerang → {north_end_name}",
        branch_id="N",
        branch_name="Branch utara Tangerang–Mauk",
        route_order=30,
        rail_backbone="Ekstensi dari Stasiun Tangerang existing via Mauk, mengikuti trase user",
        geometry_source="User GeoJSON KRL_TANGERANG_ARAH_UTARA_VIA_MAUK; Chaikin smooth clamped to path",
        note=(
            "KRL-C03-N usulan CASCADE mengikuti GeoJSON user: Tangerang (satu node transit dengan "
            "KRL existing dan KRL-C03-S) ke utara via Mauk. Stasiun tiap ±2 km memakai nama desa setempat. "
            "Bukan KRL Duri–Tangerang existing. Bukan masterplan."
        ),
        interchange_count=1,
    )
    spec_s = dict(
        id="KRL-C03-S",
        corridor_id="CAS-KRL-C03",
        corridor_name="CASCADE KRL Barat Tangerang",
        name="Tangerang – Bitung – Parung Panjang",
        short="Tangerang – Parung Panjang",
        from_name="Tangerang",
        to_name="Parung Panjang",
        direction="Tangerang → Parung Panjang",
        branch_id="S",
        branch_name="Branch selatan Tangerang–Bitung–Parung Panjang",
        route_order=31,
        rail_backbone="Ekstensi dari Stasiun Tangerang via Bitung, menyambung Stasiun Parung Panjang existing",
        geometry_source="User GeoJSON KRL_TANGERANG_ARAH_SELATAN_VIA_BITUNG; Chaikin smooth clamped to path",
        note=(
            "KRL-C03-S usulan CASCADE mengikuti GeoJSON user: Tangerang (node transit yang sama) "
            "selatan via Bitung ke Parung Panjang (interchange KRL Rangkasbitung existing). "
            "Stasiun tiap ±2 km memakai nama desa setempat. Bukan masterplan."
        ),
        interchange_count=2,
    )
    spec_w = dict(
        id="KRL-C04",
        corridor_id="CAS-KRL-C04",
        corridor_name="CASCADE KRL Sentul – Jasinga – Maja",
        name=f"{west_start_name} – Dramaga – Jasinga – Maja",
        short=f"{west_start_name} – Maja",
        from_name=west_start_name,
        to_name="Maja",
        direction=f"{west_start_name} → Maja",
        branch_id="",
        branch_name="",
        route_order=32,
        rail_backbone="Koridor baru Sentul–Dramaga IPB–Leuwiliang–Jasinga–Maja, menyambung KRL Rangkasbitung di Maja",
        geometry_source="User GeoJSON KRL_SENTUL_JASINGA_MAJA; Chaikin smooth clamped to path",
        note=(
            "KRL-C04 usulan CASCADE mengikuti GeoJSON user. Stasiun Dramaga wajib di depan IPB, "
            "stasiun lain tiap ±2 km memakai nama desa (termasuk Leuwiliang). "
            "Terminus Maja menumpang stasiun KRL existing. Bukan masterplan. Bukan DED."
        ),
        interchange_count=2,
    )

    print("naming stations (Nominatim, ~1 req/s)…")
    n_geom, n_stops = stations_every_2km(
        n_geom,
        [("Tangerang", TANGERANG), ("Mauk", (106.5230, -6.0660))],
        "Tangerang",
        north_end_name,
    )
    s_geom, s_stops = stations_every_2km(
        s_geom,
        [("Tangerang", TANGERANG), ("Parung Panjang", PARUNG_PANJANG)],
        "Tangerang",
        "Parung Panjang",
    )
    w_geom, w_stops = stations_every_2km(
        w_geom,
        [
            (west_start_name, w_geom[0]),
            ("Dramaga", IPB_DRAMAGA),
            ("Leuwiliang", (106.6320, -6.5670)),
            ("Jasinga", (106.4520, -6.4550)),
            ("Maja", MAJA),
        ],
        west_start_name,
        "Maja",
    )

    # force Dramaga name on nearest stop to IPB
    di, dd, _ = nearest_on([s["xy"] for s in w_stops], IPB_DRAMAGA)
    if dd < 2500:
        w_stops[di]["name"] = "Dramaga"

    packs = [
        (spec_n, n_geom, n_stops),
        (spec_s, s_geom, s_stops),
        (spec_w, w_geom, w_stops),
    ]

    new_routes, new_stops = [], []
    for spec, geom, stops in packs:
        km = length_m(geom) / 1000
        verts = len(geom)
        spec["to_name"] = stops[-1]["name"]
        spec["from_name"] = stops[0]["name"]
        spec["name"] = f"{stops[0]['name']} – {stops[-1]['name']}" if spec["id"] != "KRL-C04" else spec["name"]
        if spec["id"] == "KRL-C04":
            spec["name"] = f"{stops[0]['name']} – Dramaga – Jasinga – Maja"
        p = common_props(spec, km, len(stops), verts)
        new_routes.append(feat_line(spec["id"], geom, p))
        new_stops.extend(make_stops(spec, stops, km, verts))
        print(f"{spec['id']} {km:.2f} km  {len(stops)} stasiun  {verts} verts")
        print("   " + " – ".join(s["name"] for s in stops))

    routes = json.loads((PUB / "cascade_candidates.geojson").read_text())
    stops = json.loads((PUB / "cascade_stops.geojson").read_text())
    meta = json.loads((PUB / "cascade_existing.json").read_text())
    routes["features"] = replace_krl(routes["features"]) + new_routes
    stops["features"] = replace_krl(stops["features"]) + new_stops

    meta_corr = [c for c in meta.get("corridors", []) if str(c.get("id") or "").startswith("KRL-") is False and str(c.get("mode") or "") != "krl"]
    # also drop old KRL ids explicitly
    meta_corr = [c for c in meta_corr if not str(c.get("id") or "").startswith("KRL-C03")]
    for spec, geom, st in packs:
        meta_corr.append({
            "id": spec["id"],
            "name": spec["name"],
            "short": spec["short"],
            "endpoint": f"{st[0]['name']} – {st[-1]['name']}",
            "from_name": st[0]["name"],
            "to_name": st[-1]["name"],
            "direction": spec["direction"],
            "mode": "krl",
            "branch_id": spec.get("branch_id", ""),
            "length_km": round(length_m(geom) / 1000, 2),
            "stop_count": len(st),
            "geometry_confidence": "HIGH",
            "source": SRC,
            "status": "CASCADE_EXTENSION",
            "network_type": "TRUNK",
            "plan_type": "EXTENSION",
            "alignment_type": "RAIL_CORRIDOR",
            "notes": spec["note"],
        })
    meta["corridors"] = meta_corr
    meta["krl_note"] = (
        "CASCADE KRL diganti trase user: KRL-C03-N Tangerang utara via Mauk, "
        "KRL-C03-S Tangerang selatan via Bitung ke Parung Panjang, "
        "KRL-C04 Sentul–Dramaga IPB–Jasinga–Maja. Stasiun desa per 2 km. "
        "Transit di Tangerang, Parung Panjang, Maja, Dramaga."
    )
    meta["retrieved"] = RETRIEVED

    write_json(PUB / "cascade_candidates.geojson", routes)
    write_json(OUT / "cascade_routes.geojson", routes)
    write_json(PUB / "cascade_stops.geojson", stops)
    write_json(OUT / "cascade_stops.geojson", stops)
    write_json(PUB / "cascade_existing.json", meta)

    sources = json.loads((PUB / "sources.json").read_text())
    for s in sources:
        if s.get("dataset") == "cascade_candidates":
            s["count"] = len(routes["features"])
            s["notes"] = (
                "CAS-TJ01..11 + CAS-LRT + CAS-MRT + KRL-C03-N/S + KRL-C04. "
                "KRL CASCADE = trase user GeoJSON, stasiun desa per 2 km, Dramaga IPB wajib."
            )
        if s.get("dataset") == "cascade_stops":
            s["count"] = len(stops["features"])
            s["notes"] = "Halte/stasiun usulan. Nama desa setempat. Bukan stasiun resmi."
    write_json(PUB / "sources.json", sources)

    # provenance copy
    for fn in (
        "KRL_TANGERANG_ARAH_UTARA_VIA_MAUK.geojson",
        "KRL_TANGERANG_ARAH_SELATAN_VIA_BITUNG.geojson",
        "KRL_SENTUL_JASINGA_MAJA.geojson",
    ):
        (OUT / fn).write_text((ATT / fn).read_text())

    print("routes", len(routes["features"]), "stops", len(stops["features"]))
    print("DONE")


if __name__ == "__main__":
    main()
