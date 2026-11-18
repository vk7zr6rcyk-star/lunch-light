#!/usr/bin/env python3
"""Build places.json — open ground (parks, water, meadows, fields) for greater Copenhagen + Hørsholm —
from an OpenStreetMap extract exported by osmium as GeoJSON sequence. Runs in GitHub Actions.
Usage: build_places.py open.geojsonseq places.json"""
import json, math, sys, datetime

BBOX = (55.55, 12.30, 55.95, 12.70)  # south, west, north, east

def kind(t):
    if t.get("natural") == "water": return "w"
    if t.get("natural") == "beach": return "b"
    if t.get("leisure") == "park": return "p"
    if t.get("leisure") == "nature_reserve": return "r"
    if t.get("leisure") in ("recreation_ground", "common") or t.get("landuse") == "recreation_ground": return "g"
    if t.get("landuse") == "farmland": return "f"
    return "m"  # meadow / grass / grassland / heath

def rings(geom):
    if geom["type"] == "Polygon": return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon": return [p[0] for p in geom["coordinates"]]
    return []

def ring_area_m2(ring):
    if len(ring) < 4: return 0.0
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx, ky = 111320 * math.cos(lat0), 111320
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        s += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(s) / 2

def build(lines):
    out, seen = [], set()
    for line in lines:
        line = line.strip().lstrip("\x1e")
        if not line: continue
        f = json.loads(line)
        t, g = f.get("properties") or {}, f.get("geometry") or {}
        rs = rings(g)
        if not rs: continue
        if t.get("access") in ("private", "no"): continue
        k, named = kind(t), bool(t.get("name"))
        area = sum(ring_area_m2(r) for r in rs)
        if area < (2000 if named and k in "wpbr" else 8000): continue  # drop verges and tiny lawns
        xs = [p[0] for r in rs for p in r]; ys = [p[1] for r in rs for p in r]
        item = [round(min(ys), 5), round(min(xs), 5), round(max(ys), 5), round(max(xs), 5), k, t.get("name", "")]
        key = tuple(item)
        if key in seen: continue
        seen.add(key); out.append(item)
    return {"generated": datetime.date.today().isoformat(), "bbox": list(BBOX),
            "attribution": "© OpenStreetMap contributors, ODbL", "items": out}

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        res = build(fh)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(res['items'])} places written")
