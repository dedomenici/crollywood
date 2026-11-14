#!/usr/bin/env python3
"""Build 15 / 30 / 60 / 90 minute presets into locations.json.

Uses the same per-stop dwell as the full tour (tools/stops_source.json
dwell_min_per_stop). Estimate is walk minutes + dwell * (n_stops - 1).

  90: every stop, David Lean → finale, the new slider max.
  60 and 30: loops that start at David Lean and end at the finale,
             choosing the subset that maximises film/clip content
             within the time budget (must-keeps are preferred, not forced).
  15: the tightest geographic cluster that fits the budget. It does not
      have to start at David Lean.
"""
import itertools, json, math, shutil, time, urllib.request
from pathlib import Path

OSRM = "https://routing.openstreetmap.de/routed-foot"
UA = {"User-Agent": "crollywood-build/1.0 (crollywood@dedomenici.com)"}
HEADLINE = {"dark-knight-rises", "whitgift-inside", "heads-of-state-sgw", "konga"}


def get(url):
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception as e:
            print("retry", url[:90], e); time.sleep(2 + i * 2)
    raise SystemExit("failed: " + url)


def haversine(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


src = json.load(open("tools/stops_source.json"))
D = json.load(open("locations.json"))
dwell = float(src.get("dwell_min_per_stop") or D.get("dwell_min_per_stop") or 2.9)
byid = {s["id"]: s for s in D["stops"]}
src_by = {s["id"]: s for s in src["stops"]}
# Full walking order, finale last
S = D["stops"]
n = len(S)
START, FIN = 0, n - 1
assert S[START]["id"] == "david-lean" and S[FIN]["id"] == "finale"

co = ";".join(f"{s['lng']},{s['lat']}" for s in S)
tab = get(f"{OSRM}/table/v1/driving/{co}?annotations=duration,distance")
DU, DI = tab["durations"], tab["distances"]


def nclips(s):
    c = 0
    for f in s.get("films") or []:
        if f.get("clip"):
            c += 1
        c += len(f.get("clips") or [])
        if f.get("youtube") or f.get("youtubeId"):
            c += 1
    return c


def value(i):
    s, src_s = S[i], src_by[S[i]["id"]]
    v = 4 * len(s.get("films") or []) + 3 * nclips(s)
    v += src_s.get("priority", 1) ** 2
    if src_s.get("must_keep"):
        v += 10
    if S[i]["id"] in HEADLINE:
        v += 12
    return v


def est(n_stops, walk_s):
    return walk_s / 60.0 + dwell * (n_stops - 1)


def best_order_loop(sub):
    """Exact path START -> perm(sub) -> FIN. sub is a list of intermediate indices."""
    sub = list(sub)
    k = len(sub)
    if k == 0:
        return [], DU[START][FIN]
    dp = {}
    for i, x in enumerate(sub):
        dp[(1 << i, i)] = (DU[START][x], [x])
    for m in range(1, 1 << k):
        for i in range(k):
            if (m, i) not in dp:
                continue
            c, path = dp[(m, i)]
            for j in range(k):
                if m & (1 << j):
                    continue
                key = (m | (1 << j), j)
                nc = c + DU[sub[i]][sub[j]]
                if key not in dp or nc < dp[key][0]:
                    dp[key] = (nc, path + [sub[j]])
    full = (1 << k) - 1
    return min(((dp[(full, i)][0] + DU[sub[i]][FIN], dp[(full, i)][1]) for i in range(k)),
               key=lambda t: t[0])[::-1]


def best_open_path(sub):
    """Shortest Hamiltonian path through sub (any start/end). Returns (order, walk_s)."""
    sub = list(sub)
    k = len(sub)
    if k == 1:
        return sub, 0.0
    if k == 2:
        return ([sub[0], sub[1]], DU[sub[0]][sub[1]]) if DU[sub[0]][sub[1]] <= DU[sub[1]][sub[0]] else ([sub[1], sub[0]], DU[sub[1]][sub[0]])
    best = None
    # Held-Karp over all starts
    for si, start in enumerate(sub):
        others = [x for j, x in enumerate(sub) if j != si]
        mids = others
        kk = len(mids)
        dp = {}
        for i, x in enumerate(mids):
            dp[(1 << i, i)] = (DU[start][x], [x])
        for m in range(1, 1 << kk):
            for i in range(kk):
                if (m, i) not in dp:
                    continue
                c, path = dp[(m, i)]
                for j in range(kk):
                    if m & (1 << j):
                        continue
                    key = (m | (1 << j), j)
                    nc = c + DU[mids[i]][mids[j]]
                    if key not in dp or nc < dp[key][0]:
                        dp[key] = (nc, path + [mids[j]])
        full = (1 << kk) - 1
        w, path = min((dp[(full, i)][0], dp[(full, i)][1]) for i in range(kk))
        cand = (w, [start] + path)
        if best is None or cand[0] < best[0]:
            best = cand
    return best[1], best[0]


def write_route(pid, stops):
    co2 = ";".join(f"{s['lng']},{s['lat']}" for s in stops)
    r = get(f"{OSRM}/route/v1/driving/{co2}?overview=full&geometries=geojson&steps=false")["routes"][0]
    fname = f"route_{pid}.geojson"
    json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "preset": pid, "distance_m": round(r["distance"]), "duration_s": round(r["duration"]),
        "source": "OSRM foot profile, routing.openstreetmap.de; © OpenStreetMap contributors (ODbL)",
        "stop_order": [s["id"] for s in stops]}, "geometry": r["geometry"]}]}, open(fname, "w"))
    return r, fname


def pack(pid, label, target, stops, r, fname):
    n_s = len(stops)
    em = est(n_s, r["duration"])
    return {
        "id": pid, "label": label, "target_min": target, "route": fname,
        "stop_ids": [s["id"] for s in stops],
        "legs_m": [round(l["distance"]) for l in r["legs"]] + [0],
        "distance_m": round(r["distance"]), "walk_s": round(r["duration"]),
        "est_min": round(em), "dwell_min": dwell, "must_keep_only": False,
    }


# ---- 90: full tour (copy geometry from the already-built route.geojson) ----
full_stops = S
# re-route to get a dedicated file, or copy route.geojson
shutil.copyfile("route.geojson", "route_90.geojson")
# patch the preset property
gj = json.load(open("route_90.geojson"))
gj["features"][0]["properties"]["preset"] = "90"
json.dump(gj, open("route_90.geojson", "w"))
r90 = {"distance": D["route_distance_m"], "duration": D["route_duration_s"],
       "legs": [{"distance": s.get("leg_to_next_m") or 0} for s in full_stops[:-1]]}
p90 = pack("90", "1½ hrs", 90, full_stops, r90, "route_90.geojson")
# exact est from stored walk
p90["est_min"] = round(est(len(full_stops), D["route_duration_s"]))
print(f"90: {len(full_stops)} stops, {p90['distance_m']/1000:.2f} km, walk {p90['walk_s']/60:.1f} min, est {p90['est_min']} min")
print("   ", ", ".join(p90["stop_ids"]))

# ---- 60 and 30: maximise content, loop David Lean → finale ----
inter = list(range(1, FIN))  # all intermediate stops


def best_loop(budget, label):
    best = None  # (value, n, -est, order, walk)
    # cap k by a rough dwell bound
    max_k = 0
    for k in range(1, len(inter) + 1):
        # even with 0 walk, need dwell*(k+1) because n_stops = k+2 (start+fin)
        if est(k + 2, 0) <= budget + 0.05:
            max_k = k
    print(f"\n{label}: searching loops with up to {max_k} intermediate stops (budget {budget})")
    # Prefer high-value candidates first; exhaustive over combinations of size k
    ranked = sorted(inter, key=lambda i: -value(i))
    for k in range(1, max_k + 1):
        found = 0
        # If C(n,k) is large, only search the top candidates
        pool = ranked if math.comb(len(ranked), k) <= 3000 else ranked[:14]
        if math.comb(len(pool), k) > 8000:
            pool = ranked[:12]
        for sub in itertools.combinations(pool, k):
            v = sum(value(i) for i in sub)
            # skip if even a better-valued set already found and this can't beat it
            # (still allow equal value with better tightness later)
            order, w = best_order_loop(sub)
            e = est(k + 2, w)
            if e > budget + 0.05:
                continue
            found += 1
            cand = (v, k, -e, order, w)
            if best is None or cand[:3] > best[:3]:
                best = cand
        print(f"  k={k} feasible={found} best_v={best[0] if best else None} "
              f"ids={([S[i]['id'] for i in best[3]] if best and len(best[3])==k else '—')}")
    if not best:
        raise SystemExit(f"no feasible {label} loop")
    v, k, neg_e, order, w = best
    stops = [S[START]] + [S[i] for i in order] + [S[FIN]]
    r, fname = write_route(str(int(budget)), stops)
    # use the real routed duration for the published estimate
    p = pack(str(int(budget)), label, int(budget), stops, r, fname)
    print(f"{int(budget)}: {len(stops)} stops, {p['distance_m']/1000:.2f} km, "
          f"walk {p['walk_s']/60:.1f} min, est {p['est_min']} min, content={v}")
    print("   ", ", ".join(p["stop_ids"]))
    dropped = [S[i]["id"] for i in inter if src_by[S[i]["id"]].get("must_keep") and i not in order]
    print("    dropped must-keeps:", dropped)
    return p


p60 = best_loop(60, "1 hr")
p30 = best_loop(30, "30 min")

# ---- 15: tightest geographic cluster (open path, any start) ----
# Exclude finale as a distinct visit unless the cluster also includes David Lean
# (finale is the same doorway); we never add finale to a non-cinema cluster.
candidates = list(range(0, FIN))  # all unique locations, not the duplicate finale


def diameter(idxs):
    pts = [(S[i]["lat"], S[i]["lng"]) for i in idxs]
    m = 0
    for a, b in itertools.combinations(pts, 2):
        m = max(m, haversine(a, b))
    return m


best15 = None  # (-n, walk_s, diameter, order)
print("\n15: searching tightest cluster")
for k in range(2, 6):
    found = 0
    for sub in itertools.combinations(candidates, k):
        order, w = best_open_path(sub)
        e = est(k, w)
        if e > 15.05:
            continue
        found += 1
        dia = diameter(sub)
        # Most stops that fit the 15-min budget, then the tightest (shortest
        # walk, then smallest geographic diameter) among those.
        cand = (-k, w, dia, order)
        if best15 is None or cand[:3] < best15[:3]:
            best15 = cand
    print(f"  k={k} feasible={found} best={([S[i]['id'] for i in best15[3]] if best15 else None)}")

if not best15:
    raise SystemExit("no feasible 15-min cluster")
neg_k, w, dia, order = best15
# If the tightest cluster includes David Lean, start there when that still fits.
if START in order and order[0] != START:
    rest = [i for i in order if i != START]
    # shortest path START -> perm(rest)
    best_dl = None
    import itertools as _it
    for perm in _it.permutations(rest):
        path = [START] + list(perm)
        ww = sum(DU[path[j]][path[j + 1]] for j in range(len(path) - 1))
        if best_dl is None or ww < best_dl[0]:
            best_dl = (ww, path)
    if best_dl and est(len(order), best_dl[0]) <= 15.05:
        print(f"  starting at David Lean still fits ({best_dl[0]/60:.1f} min walk)")
        order, w = best_dl[1], best_dl[0]
stops15 = [S[i] for i in order]
# Only append the finale (same doorway) if we already start at the cinema and it fits.
if order[0] == START:
    extra_w = DU[order[-1]][FIN]
    if est(len(order) + 1, w + extra_w) <= 15.05:
        stops15 = stops15 + [S[FIN]]
        print("  adding finale closer (still within 15 min)")
r15, f15 = write_route("15", stops15)
p15 = pack("15", "15 min", 15, stops15, r15, f15)
print(f"15: {len(stops15)} stops, {p15['distance_m']/1000:.2f} km, "
      f"walk {p15['walk_s']/60:.1f} min, est {p15['est_min']} min, "
      f"diameter {dia:.0f} m")
print("   ", ", ".join(p15["stop_ids"]))
print("    start:", stops15[0]["name"], "end:", stops15[-1]["name"])

# Write presets in slider order: 15, 30, 60, 90
D["dwell_min_per_stop"] = dwell
D["default_preset"] = "90"
D["presets"] = [p15, p30, p60, p90]
json.dump(D, open("locations.json", "w"), indent=2, ensure_ascii=False)
print("\nWrote locations.json presets:", [p["id"] for p in D["presets"]])
for p in D["presets"]:
    print(f"  {p['label']:>7}: {len(p['stop_ids']):>2} stops, {p['distance_m']/1000:.2f} km, "
          f"walk {p['walk_s']/60:.1f} min, est {p['est_min']} min")
