#!/usr/bin/env python3
"""Build locations.json + route.geojson from tools/stops_source.json.
- downloads location photos to media/photos/<id>.jpg (Wikimedia Commons, CC licensed)
- gets a foot-walking distance matrix from OSRM (routing.openstreetmap.de/routed-foot)
- orders stops into a loop starting/ending at start_id (2-opt / or-opt heuristic)
- fetches the street-accurate route geometry and writes route.geojson
Run from the crollywood folder:  python3 tools/build.py   (add --no-reorder to keep source order)"""
import json, os, random, sys, urllib.request, time
UA = {"User-Agent": "crollywood-build/1.0 (Richard DeDomenici walking tour)"}
OSRM = "https://routing.openstreetmap.de/routed-foot"
def get(url, raw=False):
    for i in range(4):
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            return d if raw else json.loads(d)
        except Exception as e:
            print("retry", url[:90], e); time.sleep(2 + i * 2)
    raise SystemExit("failed: " + url)

src = json.load(open("tools/stops_source.json"))
stops = src["stops"]
# photos
os.makedirs("media/photos", exist_ok=True)
for s in stops:
    im = s.get("image")
    if im and im.get("url"):
        p = f"media/photos/{s['id']}.jpg"
        if not os.path.exists(p):
            open(p, "wb").write(get(im["url"], raw=True)); time.sleep(0.5)
        im["src"] = p
# distance matrix
coords = ";".join(f"{s['lng']},{s['lat']}" for s in stops)
tab = get(f"{OSRM}/table/v1/driving/{coords}?annotations=distance")
D = tab["distances"]
n = len(stops); start = next(i for i, s in enumerate(stops) if s["id"] == src["start_id"])
def cost(t): return sum(D[t[i]][t[(i + 1) % len(t)]] for i in range(len(t)))
def improve(t):
    best = cost(t); improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):            # 2-opt (keep index 0 = start fixed)
            for j in range(i + 1, n):
                c = t[:i] + t[i:j + 1][::-1] + t[j + 1:]
                cc = cost(c)
                if cc < best - 1e-6: t, best, improved = c, cc, True
        for L in (1, 2, 3):                   # or-opt
            for i in range(1, n - L + 1):
                seg = t[i:i + L]; rest = t[:i] + t[i + L:]
                for j in range(1, len(rest) + 1):
                    for sg in (seg, seg[::-1]):
                        c = rest[:j] + sg + rest[j:]
                        cc = cost(c)
                        if cc < best - 1e-6: t, best, improved = c, cc, True; break
                    if improved: break
                if improved: break
            if improved: break
    return t, best
if "--no-reorder" in sys.argv:
    order = list(range(n))
else:
    random.seed(1); bestT, bestC = None, 1e18
    for k in range(40):
        rest = [i for i in range(n) if i != start]; random.shuffle(rest)
        t, c = improve([start] + rest)
        if c < bestC: bestT, bestC = t, c
    # pick the direction (clockwise vs anticlockwise) - both equal length; keep as found
    order = bestT
ordered = [stops[i] for i in order]
# route geometry
coords = ";".join(f"{s['lng']},{s['lat']}" for s in ordered + [ordered[0]])
r = get(f"{OSRM}/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=false")
route = r["routes"][0]
for i, s in enumerate(ordered):
    s["order"] = i + 1
    s["clip"] = f"media/clips/{s['id']}.mp4"
    s["audio"] = f"media/audio/{s['id']}.mp3"
    s["leg_to_next_m"] = round(route["legs"][i]["distance"])
gj = {"type": "FeatureCollection", "features": [{"type": "Feature",
      "properties": {"name": "Crollywood walking loop", "distance_m": round(route["distance"]), "duration_s": round(route["duration"]),
                     "source": "OSRM foot profile, routing.openstreetmap.de; © OpenStreetMap contributors (ODbL)",
                     "stop_order": [s["id"] for s in ordered]},
      "geometry": route["geometry"]}]}
json.dump(gj, open("route.geojson", "w"))
out = dict(src["meta"]); out["route_distance_m"] = round(route["distance"]); out["stops"] = ordered
json.dump(out, open("locations.json", "w"), indent=2, ensure_ascii=False)
print(f"{n} stops, loop {route['distance']/1000:.2f} km, ~{route['duration']/60:.0f} min walking")
for s in ordered: print(f"{s['order']:>2} {s['id']:<28} -> {s['leg_to_next_m']} m")
