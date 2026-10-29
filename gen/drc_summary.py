import json, sys, collections
d = json.load(open(sys.argv[1]))
vs = d.get("violations", []) + d.get("unconnected_items", [])
c = collections.Counter(v["type"] for v in vs)
print(f"== {sys.argv[2]}: {len(vs)} errors {dict(c)}")
for v in vs[:int(sys.argv[3]) if len(sys.argv) > 3 else 12]:
    print(" ", v["type"], "|", " / ".join(f"{i['description'][:60]}@({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in v["items"]))
