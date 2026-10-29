#!/usr/bin/env python3
"""File per preventivo/ordine JLCPCB (PCB + assemblaggio) e stima del costo componenti.

Uso: python3 gen/jlc_files.py out/<variante> [quantità ...]
Legge <variante>.kicad_pcb, <variante>_BOM.csv (colonna LCSC) e fab/gerber/, scrive <variante>/jlcpcb/.
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

# Gerber + drill (senza le mappe di foratura, che l'upload JLC scambia per strati)
gz = out / f"{name}_gerber.zip"
with zipfile.ZipFile(gz, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted((d / "fab" / "gerber").iterdir()):
        if "map" not in f.name:
            z.write(f, f.name)

lcsc = {r["Designator"]: r["LCSC"] for r in csv.DictReader(open(d / f"{name}_BOM.csv"))}
board = pcbnew.LoadBoard(str(d / f"{name}.kicad_pcb"))
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}

# BOM raggruppata: solo parti con codice LCSC; le altre vanno montate a mano (DNP per JLC)
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

# CPL: coordinate KiCad (Y invertita come nell'export pos standard), lato top
with open(out / f"{name}_CPL_JLC.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for refs in groups.values():
        for ref in refs:
            fp = fps[ref]
            p = fp.GetPosition()
            w.writerow([ref, f"{pcbnew.ToMM(p.x):.3f}mm", f"{-pcbnew.ToMM(p.y):.3f}mm", "Top",
                        f"{fp.GetOrientationDegrees() % 360:.0f}"])


# Stima costo componenti (prezzi API JLC, in USD) per ogni quantità di schede
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
lines = [f"# {name} — stima per JLCPCB", "",
         f"Ingombro scheda: {size}, 2 strati, spessore 1.0 mm.",
         f"Da montare a mano (DNP per JLC): {', '.join(dnp)}", "",
         "| LCSC | Parte | Q.tà/scheda | Tipo | Giacenza | " + " | ".join(f"Costo per {q} schede" for q in qtys) + " |",
         "|---|---|---|---|---|" + "---|" * len(qtys)]
tot = {q: 0.0 for q in qtys}
ext = 0
for (val, foot, code), refs in groups.items():
    c = info[code]
    if not c:
        lines.append(f"| {code} | {val} | {len(refs)} | ? | NON TROVATO | " + " | ".join("-" for _ in qtys) + " |")
        continue
    kind = "base" if c["componentLibraryType"] == "base" else "estesa"
    ext += kind == "estesa"
    cells = []
    for q in qtys:
        n = len(refs) * q + (c.get("lossNumber") or 0)          # scarto di macchina
        n = max(n, c.get("leastPatchNumber") or 0, c.get("minPurchaseNum") or 0)
        cost = n * unit_price(c["componentPrices"], n)
        tot[q] += cost
        cells.append(f"${cost:.2f}")
    lines.append(f"| {code} | {c['componentModelEn']} ({val}) | {len(refs)} | {kind} | {c['stockCount']} | " + " | ".join(cells) + " |")
lines += ["", "| Totale componenti | " + " | ".join(f"{q} schede: ${tot[q]:.2f}" for q in qtys) + " |", "|---|" + "---|" * len(qtys),
          "", f"Parti estese: {ext} (JLC addebita un costo di setup per ogni parte estesa, tipicamente $3 l'una).",
          "Esclusi: PCB, setup assemblaggio, stencil, spedizione: li calcola il preventivo sul sito."]
(out / f"{name}_stima.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
