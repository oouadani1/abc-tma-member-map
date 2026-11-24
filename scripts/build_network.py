"""Build data/network.json, the street graph behind the map's walk / bike network view.

Input   an OSM extract of highway ways in OPL format (made by the GitHub Action, see below)
Output  data/network.json  compact graph: nodes, edges (with walk/bike mask), edge shapes

The study area is the member bounding box plus a 3.9 km buffer (15 minutes of cycling at 15 km/h).
The browser runs shortest paths on this graph, so no per-member files are needed.

  python3 scripts/build_network.py --bbox                  print "west,south,east,north"
  python3 scripts/build_network.py roads.opl [out.json]    build the graph

The Action (.github/workflows/build-network.yml) downloads the Massachusetts OSM extract from Geofabrik, cuts the
study area with osmium, converts it to OPL and runs this script. Data (c) OpenStreetMap contributors, ODbL.

Rules (simplifications): one-way streets are ignored; walking uses footways, paths, steps, and streets that allow foot
traffic; biking uses streets, cycleways and paths that allow bikes (footways only where bicycle=yes/designated).
"""
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUFFER_M = 3900
SCALE = 100000  # coordinates stored as integers of 1e-5 degrees (~1 m)

WALK_HW = {"footway", "path", "pedestrian", "steps", "residential", "living_street", "unclassified", "tertiary", "secondary",
           "primary", "trunk", "cycleway", "service", "track", "road", "primary_link", "secondary_link", "tertiary_link", "trunk_link"}
BIKE_HW = {"cycleway", "path", "track", "residential", "living_street", "unclassified", "tertiary", "secondary", "primary",
           "trunk", "service", "road", "primary_link", "secondary_link", "tertiary_link", "trunk_link", "footway", "pedestrian"}
OK = {"yes", "designated", "permissive", "official", "destination"}
SERVICE_SKIP = {"driveway", "parking_aisle", "drive-through"}


def study_bbox():
    lats, lngs = [], []
    with open(ROOT / "data" / "members.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lats.append(float(r["lat"]))
            lngs.append(float(r["lng"]))
    dlat = BUFFER_M / 111320
    dlng = BUFFER_M / (111320 * math.cos(math.radians(sum(lats) / len(lats))))
    return min(lngs) - dlng, min(lats) - dlat, max(lngs) + dlng, max(lats) + dlat


def mode_mask(t):
    """bit 1 = walkable, bit 2 = bikeable"""
    hw = t.get("highway")
    if not hw or hw in ("motorway", "motorway_link"):
        return 0
    access, service = t.get("access"), t.get("service")
    m = 0
    if hw in WALK_HW:
        ok = t.get("foot") != "no"
        if access in ("private", "no") and t.get("foot") not in OK:
            ok = False
        if hw == "service" and service in SERVICE_SKIP and t.get("foot") not in OK:
            ok = False
        if ok:
            m |= 1
    if hw in BIKE_HW:
        ok = t.get("bicycle") != "no"
        if access in ("private", "no") and t.get("bicycle") not in OK:
            ok = False
        if hw in ("footway", "pedestrian") and t.get("bicycle") not in OK:
            ok = False
        if hw == "service" and service in SERVICE_SKIP and t.get("bicycle") not in OK:
            ok = False
        if ok:
            m |= 2
    return m


_pct = re.compile(r"%([0-9a-fA-F]+)%")


def unq(s):
    return _pct.sub(lambda m: chr(int(m.group(1), 16)), s)


def parse_opl(path):
    nodes, ways = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            kind = line[:1]
            if kind not in "nw":
                continue
            tags, refs, x, y = {}, [], None, None
            for tok in line.rstrip("\n").split(" ")[1:]:
                c = tok[:1]
                if c == "T" and tok[1:]:
                    for kv in tok[1:].split(","):
                        k, _, v = kv.partition("=")
                        tags[unq(k)] = unq(v)
                elif c == "N":
                    refs = [int(r[1:]) for r in tok[1:].split(",") if r]
                elif c == "x":
                    x = float(tok[1:])
                elif c == "y":
                    y = float(tok[1:])
            if kind == "n" and x is not None and y is not None:
                nodes[int(line.split(" ", 1)[0][1:])] = (x, y)
            elif kind == "w":
                ways.append((tags, refs))
    return nodes, ways


def dist_m(a, b):
    kx = math.cos(math.radians((a[1] + b[1]) / 2)) * 111320
    return math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * 111320)


def build(nodes, ways):
    kept = []
    use = Counter()
    for tags, refs in ways:
        m = mode_mask(tags)
        refs = [r for r in refs if r in nodes]
        if not m or len(refs) < 2:
            continue
        kept.append((m, refs))
        use.update(refs)
        use[refs[0]] += 1
        use[refs[-1]] += 1
    index, out_nodes, edges, shapes = {}, [], [], []

    def nid(r):
        if r not in index:
            index[r] = len(out_nodes) // 2
            x, y = nodes[r]
            out_nodes.extend([round(x * SCALE), round(y * SCALE)])
        return index[r]

    for m, refs in kept:
        cuts = [i for i, r in enumerate(refs) if use[r] >= 2]
        for i, j in zip(cuts, cuts[1:]):
            seg = refs[i:j + 1]
            length = sum(dist_m(nodes[p], nodes[q]) for p, q in zip(seg, seg[1:]))
            inner = seg[1:-1]
            si = -1
            if inner:
                si = len(shapes)
                flat = []
                for r in inner:
                    flat.extend([round(nodes[r][0] * SCALE), round(nodes[r][1] * SCALE)])
                shapes.append(flat)
            edges.extend([nid(seg[0]), nid(seg[-1]), max(1, round(length)), m, si])
    return {"v": 1, "scale": SCALE, "nodes": out_nodes, "edges": edges, "shapes": shapes}


def main(argv):
    if "--bbox" in argv:
        print(",".join(f"{v:.5f}" for v in study_bbox()))
        return
    src = argv[0]
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "data" / "network.json"
    nodes, ways = parse_opl(src)
    g = build(nodes, ways)
    out.write_text(json.dumps(g, separators=(",", ":")), encoding="utf-8")
    walk = sum(1 for i in range(0, len(g["edges"]), 5) if g["edges"][i + 3] & 1)
    bike = sum(1 for i in range(0, len(g["edges"]), 5) if g["edges"][i + 3] & 2)
    print(f"nodes {len(g['nodes'])//2}, edges {len(g['edges'])//5} (walk {walk}, bike {bike}), shapes {len(g['shapes'])}, {out.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
