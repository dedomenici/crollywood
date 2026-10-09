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
fin = [i for i, s in enumerate(stops) if s["id"] == "finale"]
if fin: order = [i for i in order if i != fin[0]] + fin
ordered = [stops[i] for i in order]
# route geometry
close = src.get("close_loop", True)   # False when the last stop is an explicit finale at the start venue
coords = ";".join(f"{s['lng']},{s['lat']}" for s in (ordered + [ordered[0]] if close else ordered))
r = get(f"{OSRM}/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=false")
route = r["routes"][0]
for i, s in enumerate(ordered):
    s["order"] = i + 1
    s["clip"] = f"media/clips/{s['id']}.mp4"
    s["audio"] = f"media/audio/{s['id']}.mp3"
    s["leg_to_next_m"] = round(route["legs"][i]["distance"]) if i < len(route["legs"]) else 0
    # where the walking route actually passes the stop (pins often sit inside buildings / malls)
    wp = r["waypoints"][i]
    s["route_snap"] = {"lat": round(wp["location"][1], 6), "lng": round(wp["location"][0], 6), "offset_m": round(wp.get("distance", 0))}
gj = {"type": "FeatureCollection", "features": [{"type": "Feature",
      "properties": {"name": "Crollywood walking loop", "distance_m": round(route["distance"]), "duration_s": round(route["duration"]),
                     "source": "OSRM foot profile, routing.openstreetmap.de; © OpenStreetMap contributors (ODbL)",
                     "stop_order": [s["id"] for s in ordered]},
      "geometry": route["geometry"]}]}
json.dump(gj, open("route.geojson", "w"))
out = dict(src["meta"]); out["route_distance_m"] = round(route["distance"]); out["route_duration_s"] = round(route["duration"]); out["stops"] = ordered
json.dump(out, open("locations.json", "w"), indent=2, ensure_ascii=False)
print(f"{n} stops, loop {route['distance']/1000:.2f} km, ~{route['duration']/60:.0f} min walking")
for s in ordered: print(f"{s['order']:>2} {s['id']:<28} -> {s['leg_to_next_m']} m")

# ---------------------------------------------------------------------------
# Duration presets: choose a subset of stops per time budget, order it, route it
# ---------------------------------------------------------------------------
def build_presets():
    presets = src.get("presets") or []
    if not presets: return
    dwell = src.get("dwell_min_per_stop", 4)
    S = out["stops"]                       # full tour, already ordered (finale last)
    ids = [s["id"] for s in S]
    co = ";".join(f"{s['lng']},{s['lat']}" for s in S)
    T = get(f"{OSRM}/table/v1/driving/{co}?annotations=duration,distance")
    DU, DI = T["durations"], T["distances"]
    START, FIN = 0, len(S) - 1
    def tour_cost(t):  # t: list of indices starting with START, excluding FIN (FIN == START location)
        return sum(DU[t[k]][t[k + 1]] for k in range(len(t) - 1)) + DU[t[-1]][FIN]
    def optimise(t):
        best = tour_cost(t); m = len(t); improved = True
        while improved:
            improved = False
            for i in range(1, m - 1):
                for j in range(i + 1, m):
                    c = t[:i] + t[i:j + 1][::-1] + t[j + 1:]
                    cc = tour_cost(c)
                    if cc < best - 1e-6: t, best, improved = c, cc, True
            for i in range(1, m):
                x = t[i]; rest = t[:i] + t[i + 1:]
                for j in range(1, len(rest) + 1):
                    c = rest[:j] + [x] + rest[j:]
                    cc = tour_cost(c)
                    if cc < best - 1e-6: t, best, improved = c, cc, True; break
                if improved: break
        return t, best
    def est_min(t, walk_s): return walk_s / 60 + dwell * (len(t))   # dwell at every stop after the start, incl. finale
    must = [i for i, s in enumerate(S) if s.get("must_keep") and i not in (START, FIN)]
    base, base_c = optimise([START] + must)
    results = []
    for p in presets:
        if p.get("target_min") is None:
            order = list(range(len(S)))
        else:
            t, c = base[:], base_c
            while True:
                best = None
                for x in range(1, FIN):
                    if x in t: continue
                    # cheapest insertion
                    ins = min((tour_cost(t[:j] + [x] + t[j:]), j) for j in range(1, len(t) + 1))
                    nt = t[:ins[1]] + [x] + t[ins[1]:]
                    if est_min(nt, ins[0]) > p["target_min"]: continue
                    added = max(0.5, (ins[0] - c) / 60 + dwell)
                    score = S[x].get("priority", 1) ** 2 / added
                    if best is None or score > best[0]: best = (score, x, nt)
                if not best: break
                t, c = optimise(best[2])
            order = t + [FIN]
        sub = [S[i] for i in order]
        co2 = ";".join(f"{s['lng']},{s['lat']}" for s in sub)
        r2 = get(f"{OSRM}/route/v1/driving/{co2}?overview=full&geometries=geojson&steps=false")["routes"][0]
        fname = f"route_{p['id']}.geojson"
        json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
            "preset": p["id"], "distance_m": round(r2["distance"]), "duration_s": round(r2["duration"]),
            "source": "OSRM foot profile, routing.openstreetmap.de; © OpenStreetMap contributors (ODbL)",
            "stop_order": [s["id"] for s in sub]}, "geometry": r2["geometry"]}]}, open(fname, "w"))
        em = est_min(sub[:-1], r2["duration"])
        results.append({"id": p["id"], "label": p["label"], "target_min": p.get("target_min"), "route": fname,
                        "stop_ids": [s["id"] for s in sub], "legs_m": [round(l["distance"]) for l in r2["legs"]] + [0],
                        "distance_m": round(r2["distance"]), "walk_s": round(r2["duration"]), "est_min": round(em),
                        "must_keep_only": p.get("target_min") is not None and len(sub) == len(must) + 2})
        time.sleep(0.5)
    out["dwell_min_per_stop"] = dwell
    out["presets"] = results
    out["default_preset"] = "full"
    json.dump(out, open("locations.json", "w"), indent=2, ensure_ascii=False)
    must_min = round(est_min([START] + base[1:] , base_c))
    print(f"\nmust-keep-only tour: {len(must)+2} stops, ~{must_min} min")
    for r_ in results:
        print(f"preset {r_['label']:>7}: {len(r_['stop_ids']):>2} stops, {r_['distance_m']/1000:.2f} km, walk {r_['walk_s']/60:.0f} min, est {r_['est_min']} min"
              + (" (must-keep only)" if r_['must_keep_only'] else ""))
        print("     ", ", ".join(r_["stop_ids"]))
build_presets()
