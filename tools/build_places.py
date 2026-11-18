#!/usr/bin/env python3
"""Build places.json: open ground (parks, water, meadows, fields) for greater Copenhagen + Hørsholm
from OpenStreetMap via Overpass. Runs in GitHub Actions; the app reads the file locally."""
import json, math, sys, time, urllib.parse, urllib.request, datetime

BBOX = (55.55, 12.30, 55.95, 12.70)  # south, west, north, east
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
Q = f"""[out:json][timeout:240][bbox:{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}];
(way["leisure"~"^(park|nature_reserve|recreation_ground|common)$"];
 relation["leisure"~"^(park|nature_reserve)$"];
 way["natural"~"^(water|beach|grassland|heath)$"];
 relation["natural"~"^(water|grassland|heath)$"];
 way["landuse"~"^(meadow|grass|farmland|recreation_ground)$"];
 relation["landuse"~"^(meadow|farmland)$"];
);
out tags bb;"""

def kind(t):
    if t.get("natural") == "water": return "w"
    if t.get("natural") == "beach": return "b"
    if t.get("leisure") == "park": return "p"
    if t.get("leisure") == "nature_reserve": return "r"
    if t.get("leisure") in ("recreation_ground", "common") or t.get("landuse") == "recreation_ground": return "g"
    if t.get("landuse") == "farmland": return "f"
    return "m"  # meadow / grass / grassland / heath

def area_m2(b):
    lat = math.radians((b["minlat"] + b["maxlat"]) / 2)
    return (b["maxlat"] - b["minlat"]) * 111320 * (b["maxlon"] - b["minlon"]) * 111320 * math.cos(lat)

def fetch():
    data = urllib.parse.urlencode({"data": Q}).encode()
    last = None
    for attempt in range(3):
        for url in MIRRORS:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "lunch-light/1.0 (github.com/vk7zr6rcyk-star/lunch-light)"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.load(r)
            except Exception as e:
                last = e; print(f"{url}: {e}", file=sys.stderr)
        time.sleep(30)
    raise SystemExit(f"all mirrors failed: {last}")

def build(j):
    out = []
    for e in j.get("elements", []):
        b, t = e.get("bounds"), e.get("tags") or {}
        if not b: continue
        k, a, named = kind(t), area_m2(b), bool(t.get("name"))
        # drop verges and tiny lawns; keep named parks/water a bit smaller
        if a < (2000 if named and k in "wpbr" else 8000): continue
        if t.get("access") in ("private", "no"): continue
        out.append([round(b["minlat"], 5), round(b["minlon"], 5), round(b["maxlat"], 5), round(b["maxlon"], 5), k, t.get("name", "")])
    return {"generated": datetime.date.today().isoformat(), "bbox": list(BBOX), "attribution": "© OpenStreetMap contributors, ODbL", "items": out}

if __name__ == "__main__":
    res = build(fetch())
    with open(sys.argv[1] if len(sys.argv) > 1 else "places.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(res['items'])} places written")
