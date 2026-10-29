#!/usr/bin/env python3
"""Files for a JLCPCB quote/order (PCB + assembly) and component cost estimate.

Usage: python3 gen/jlc_files.py out/<variant> [quantity ...]
Reads <variant>.kicad_pcb, <variant>_BOM.csv (LCSC column) and fab/gerber/, writes <variant>/jlcpcb/.
"""
import csv
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).parent))
from jlc_search import search  # noqa: E402

d = Path(sys.argv[1])
qtys = [int(q) for q in sys.argv[2:]] or [5, 10]
name = d.name
out = d / "jlcpcb"
out.mkdir(exist_ok=True)

# Gerber + drill (without the drill maps, which the JLC upload mistakes for layers)
gz = out / f"{name}_gerber.zip"
with zipfile.ZipFile(gz, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted((d / "fab" / "gerber").iterdir()):
        if "map" not in f.name:
            z.write(f, f.name)

lcsc = {r["Designator"]: r["LCSC"] for r in csv.DictReader(open(d / f"{name}_BOM.csv"))}
board = pcbnew.LoadBoard(str(d / f"{name}.kicad_pcb"))
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}

# Grouped BOM: only parts with an LCSC code; the others are fitted by hand (DNP for JLC)
groups = defaultdict(list)
dnp = []
for ref, fp in sorted(fps.items()):
    code = lcsc.get(ref, "")
    if code:
        groups[(fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str(), code)].append(ref)
    else:
        dnp.append(ref)
with open(out / f"{name}_BOM_JLC.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, foot, code), refs in groups.items():
        w.writerow([val, ",".join(refs), foot, code])

# CPL: KiCad coordinates (Y inverted as in the standard pos export), top side
with open(out / f"{name}_CPL_JLC.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for refs in groups.values():
        for ref in refs:
            fp = fps[ref]
            p = fp.GetPosition()
            w.writerow([ref, f"{pcbnew.ToMM(p.x):.3f}mm", f"{-pcbnew.ToMM(p.y):.3f}mm", "Top",
                        f"{fp.GetOrientationDegrees() % 360:.0f}"])


# Component cost estimate (JLC API prices, in USD) for each board quantity
def unit_price(prices, n):
    for t in sorted(prices, key=lambda t: t["startNumber"]):
        if t["startNumber"] <= n and (t["endNumber"] == -1 or n <= t["endNumber"]):
            return t["productPrice"]
    return sorted(prices, key=lambda t: t["startNumber"])[0]["productPrice"]


info = {}
for (_, _, code) in groups:
    hit = [c for c in search(code, 3) if c["componentCode"] == code]
    info[code] = hit[0] if hit else None

bw = board.GetBoardEdgesBoundingBox()
size = f"{pcbnew.ToMM(bw.GetWidth()):.1f} x {pcbnew.ToMM(bw.GetHeight()):.1f} mm"
lines = [f"# {name} — JLCPCB estimate", "",
         f"Board size: {size}, 2 layers, 1.0 mm thick.",
         f"Fitted by hand (DNP for JLC): {', '.join(dnp)}", "",
         "| LCSC | Part | Qty/board | Type | Stock | " + " | ".join(f"Cost for {q} boards" for q in qtys) + " |",
         "|---|---|---|---|---|" + "---|" * len(qtys)]
tot = {q: 0.0 for q in qtys}
ext = 0
for (val, foot, code), refs in groups.items():
    c = info[code]
    if not c:
        lines.append(f"| {code} | {val} | {len(refs)} | ? | NOT FOUND | " + " | ".join("-" for _ in qtys) + " |")
        continue
    kind = "basic" if c["componentLibraryType"] == "base" else "extended"
    ext += kind == "extended"
    cells = []
    for q in qtys:
        n = len(refs) * q + (c.get("lossNumber") or 0)          # machine attrition
        n = max(n, c.get("leastPatchNumber") or 0, c.get("minPurchaseNum") or 0)
        cost = n * unit_price(c["componentPrices"], n)
        tot[q] += cost
        cells.append(f"${cost:.2f}")
    lines.append(f"| {code} | {c['componentModelEn']} ({val}) | {len(refs)} | {kind} | {c['stockCount']} | " + " | ".join(cells) + " |")
lines += ["", "| Components total | " + " | ".join(f"{q} boards: ${tot[q]:.2f}" for q in qtys) + " |", "|---|" + "---|" * len(qtys),
          "", f"Extended parts: {ext} (JLC charges a setup fee for each extended part, typically $3 each).",
          "Not included: PCB, assembly setup, stencil, shipping: the quote on the website computes them."]
(out / f"{name}_estimate.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
