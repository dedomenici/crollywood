#!/usr/bin/env python3
"""Add a tight ~1-hour preset to locations.json (+ route_60.geojson).
Orienteering: start = David Lean, finish = finale (same spot). Maximise impact subject to
walk minutes + DWELL x stops <= BUDGET. Must-keep stops get a bonus but may be dropped.
Exhaustive over all subsets up to size K of the best candidates, each ordered optimally (Held-Karp-ish brute force)."""
import json, itertools, urllib.request, time
OSRM = "https://routing.openstreetmap.de/routed-foot"
UA = {"User-Agent": "crollywood-build/1.0 (dedomenici.com)"}
BUDGET, DWELL = 60.0, 3.5
HEADLINE = {"dark-knight-rises", "opalite", "heads-of-state-sgw", "konga"}
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
D = json.load(open("locations.json"))
full = next(p for p in D["presets"] if p["id"] == "full")
byid = {s["id"]: s for s in D["stops"]}
S = [byid[i] for i in full["stop_ids"]]
src = {s["id"]: s for s in json.load(open("tools/stops_source.json"))["stops"]}
co = ";".join(f"{s['lng']},{s['lat']}" for s in S)
DU = get(f"{OSRM}/table/v1/driving/{co}?annotations=duration")["durations"]
START, FIN = 0, len(S) - 1
def value(i):
    s = src[S[i]["id"]]; v = s.get("priority", 1) ** 2 + (6 if s.get("must_keep") else 0)
    if S[i]["id"] in HEADLINE: v += 15  # the stops the tour is sold on ("from Batman to Taylor Swift", Heads of State, Konga)
    return v * (0.6 if s.get("confidence", S[i].get("confidence")) == "low" else 1)
def best_order(sub):  # exact for small sets (Held-Karp)
    sub = list(sub); n = len(sub)
    if n == 0: return [], DU[START][FIN]
    dp = {}
    for k, x in enumerate(sub): dp[(1 << k, k)] = (DU[START][x], [x])
    for m in range(1, 1 << n):
        for k in range(n):
            if (m, k) not in dp: continue
            c, path = dp[(m, k)]
            for j in range(n):
                if m & (1 << j): continue
                key = (m | 1 << j, j); nc = c + DU[sub[k]][sub[j]]
                if key not in dp or nc < dp[key][0]: dp[key] = (nc, path + [sub[j]])
    full_m = (1 << n) - 1
    return min(((dp[(full_m, k)][0] + DU[sub[k]][FIN], dp[(full_m, k)][1]) for k in range(n)), key=lambda t: t[0])[::-1]
def est(sub, walk_s): return walk_s / 60 + DWELL * (len(sub) + 1)  # start + each stop (finale = goodbye at the start spot)
cands = sorted(range(1, FIN), key=lambda i: -value(i))[:16]
best = None
for k in range(1, 10):
    found = False
    for sub in itertools.combinations(cands, k):
        v = sum(value(i) for i in sub)
        if best and v <= best[0]: continue
        order, w = best_order(sub)
        e = est(sub, w)
        if e <= BUDGET:
            found = True
            if not best or v > best[0] or (v == best[0] and e < best[2]): best = (v, order, e, w)
    print("k", k, "best so far", best and (round(best[0], 1), [S[i]["id"] for i in best[1]], round(best[2], 1)))
    if not found and k > 3: break
v, order, e, w = best
sub = [S[START]] + [S[i] for i in order] + [S[FIN]]
co2 = ";".join(f"{s['lng']},{s['lat']}" for s in sub)
r = get(f"{OSRM}/route/v1/driving/{co2}?overview=full&geometries=geojson&steps=false")["routes"][0]
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
    "preset": "60", "distance_m": round(r["distance"]), "duration_s": round(r["duration"]),
    "source": "OSRM foot profile, routing.openstreetmap.de; © OpenStreetMap contributors (ODbL)",
    "stop_order": [s["id"] for s in sub]}, "geometry": r["geometry"]}]}, open("route_60.geojson", "w"))
em = r["duration"] / 60 + DWELL * (len(sub) - 1)
p60 = {"id": "60", "label": "1 hr", "target_min": 60, "route": "route_60.geojson", "stop_ids": [s["id"] for s in sub],
       "legs_m": [round(l["distance"]) for l in r["legs"]] + [0], "distance_m": round(r["distance"]), "walk_s": round(r["duration"]),
       "est_min": round(em), "dwell_min": DWELL, "must_keep_only": False}
D["presets"] = [p60] + [p for p in D["presets"] if p["id"] != "60"]
json.dump(D, open("locations.json", "w"), indent=2, ensure_ascii=False)
print(f"1 hr preset: {len(sub)} stops, {r['distance']/1000:.2f} km, walk {r['duration']/60:.0f} min, est {em:.0f} min")
print("  ", ", ".join(p60["stop_ids"]))
print("   dropped must-keeps:", [i for i, s in src.items() if s.get("must_keep") and i not in p60["stop_ids"]])
