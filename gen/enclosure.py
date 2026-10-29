#!/usr/bin/env python3
"""Astuccio stampabile 3D (trasporto/conservazione) per le schede EC2M2, con SSD montato.

Nello slot la scheda va usata nuda: l'ExpressCard è alto 5.0 mm e scheda + SSD arrivano già a ~4.85 mm.
Uso: gen/.venv/bin/python gen/enclosure.py   (servono manifold3d e trimesh) -> out/enclosure/
Scrive anche enclosure.scad con la stessa geometria, modificabile in OpenSCAD.
"""
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold

OUT = Path(__file__).resolve().parent.parent / "out" / "enclosure"

P = dict(
    board_len=70.0,    # lunghezza scheda
    clear=0.4,         # gioco per lato
    inner_h=6.0,       # altezza interna: PCB 1.0 + SSD fino a 3.85 + connettore EC, con margine
    wall=1.6,          # pareti laterali e frontale
    skin=1.2,          # fondo e coperchio
    r=2.0,             # raggio spigoli verticali esterni
    notch_w=18.0,      # tacca per le dita all'apertura
    notch_d=10.0,
    bump=0.35,         # dentini interni vicino all'apertura: tengono la scheda dentro
)


def rounded_box(x, y, z, r, seg=32):
    """Box [0,x]x[0,y]x[0,z] con spigoli verticali raggiati (hull di 4 cilindri)."""
    cyl = Manifold.cylinder(z, r, r, seg)
    parts = [cyl.translate([cx, cy, 0]) for cx in (r, x - r) for cy in (r, y - r)]
    return Manifold.batch_hull(parts)


def case(width):
    c, w, s = P["clear"], P["wall"], P["skin"]
    iw, il, ih = width + 2 * c, P["board_len"] + 2 * c, P["inner_h"]
    ow, ol, oh = iw + 2 * w, il + w, ih + 2 * s          # il lato y = ol resta aperto
    body = rounded_box(ow, ol + P["r"], oh, P["r"])      # prolungato oltre l'apertura e poi tagliato
    body = body ^ Manifold.cube([ow, ol, oh])            # intersezione: apertura piatta
    cavity = Manifold.cube([iw, il + 1, ih]).translate([w, w, s])
    # tacche per le dita su fondo e coperchio, con estremità arrotondata
    nw, nd = P["notch_w"], P["notch_d"]
    tip = Manifold.cylinder(oh + 2, nw / 2, nw / 2, 64).translate([ow / 2, ol - nd + nw / 2, -1])
    slot = Manifold.cube([nw, nd - nw / 2 + 1, oh + 2]).translate([ow / 2 - nw / 2, ol - nd + nw / 2, -1])
    notch = tip + slot
    # dentini sulle pareti laterali, 3 mm dentro l'apertura
    b = P["bump"]
    bumps = [Manifold.cube([b, 2.0, ih - 1.0]).translate([x0, ol - 5.0, s + 0.5]) for x0 in (w, w + iw - b)]
    return body - cavity - notch + bumps[0] + bumps[1], (ow, ol, oh)


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))


SCAD = """// Astuccio EC2M2 (trasporto/conservazione) - stessa geometria di gen/enclosure.py
width = {width};  // 34 o 54
board_len = {board_len}; clear = {clear}; inner_h = {inner_h};
wall = {wall}; skin = {skin}; r = {r}; notch_w = {notch_w}; notch_d = {notch_d}; bump = {bump};
iw = width + 2*clear; il = board_len + 2*clear; ih = inner_h;
ow = iw + 2*wall; ol = il + wall; oh = ih + 2*skin;
$fn = 64;
module rbox(x, y, z) hull() for (cx = [r, x-r], cy = [r, y-r]) translate([cx, cy, 0]) cylinder(h = z, r = r);
union() {{
  difference() {{
    intersection() {{ rbox(ow, ol + r, oh); cube([ow, ol, oh]); }}
    translate([wall, wall, skin]) cube([iw, il + 1, ih]);
    translate([ow/2, ol - notch_d + notch_w/2, -1]) cylinder(h = oh + 2, r = notch_w/2);
    translate([ow/2 - notch_w/2, ol - notch_d + notch_w/2, -1]) cube([notch_w, notch_d, oh + 2]);
  }}
  for (x0 = [wall, wall + iw - bump]) translate([x0, ol - 5, skin + 0.5]) cube([bump, 2, ih - 1]);
}}
"""

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for width in (34, 54):
        m, (ow, ol, oh) = case(width)
        t = to_trimesh(m)
        f = OUT / f"EC2M2_{width}_case.stl"
        t.export(f)
        print(f"{f.name}: {ow:.1f} x {ol:.1f} x {oh:.1f} mm, volume {t.volume / 1000:.1f} cm3, "
              f"watertight={t.is_watertight}")
    (OUT / "enclosure.scad").write_text(SCAD.format(width=34, **P))
