#!/usr/bin/env python3
"""3D-printable case (transport/storage) for the EC2M2 boards, with the SSD installed.

In the slot the board must be used bare: the ExpressCard slot is 5.0 mm tall and board + SSD already reach ~4.85 mm.
Usage: gen/.venv/bin/python gen/enclosure.py   (needs manifold3d and trimesh) -> out/enclosure/
Also writes enclosure.scad with the same geometry, editable in OpenSCAD.
"""
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold

OUT = Path(__file__).resolve().parent.parent / "out" / "enclosure"

P = dict(
    board_len=70.0,    # board length
    clear=0.4,         # clearance per side
    inner_h=6.0,       # inner height: PCB 1.0 + SSD up to 3.85 + EC connector, with margin
    wall=1.6,          # side and front walls
    skin=1.2,          # bottom and lid
    r=2.0,             # radius of the outer vertical edges
    notch_w=18.0,      # finger notch at the opening
    notch_d=10.0,
    bump=0.35,         # small inner bumps near the opening: keep the board inside
)


def rounded_box(x, y, z, r, seg=32):
    """Box [0,x]x[0,y]x[0,z] with rounded vertical edges (hull of 4 cylinders)."""
    cyl = Manifold.cylinder(z, r, r, seg)
    parts = [cyl.translate([cx, cy, 0]) for cx in (r, x - r) for cy in (r, y - r)]
    return Manifold.batch_hull(parts)


def case(width):
    c, w, s = P["clear"], P["wall"], P["skin"]
    iw, il, ih = width + 2 * c, P["board_len"] + 2 * c, P["inner_h"]
    ow, ol, oh = iw + 2 * w, il + w, ih + 2 * s          # the y = ol side stays open
    body = rounded_box(ow, ol + P["r"], oh, P["r"])      # extended past the opening and then cut
    body = body ^ Manifold.cube([ow, ol, oh])            # intersection: flat opening
    cavity = Manifold.cube([iw, il + 1, ih]).translate([w, w, s])
    # finger notches on bottom and lid, with a rounded end
    nw, nd = P["notch_w"], P["notch_d"]
    tip = Manifold.cylinder(oh + 2, nw / 2, nw / 2, 64).translate([ow / 2, ol - nd + nw / 2, -1])
    slot = Manifold.cube([nw, nd - nw / 2 + 1, oh + 2]).translate([ow / 2 - nw / 2, ol - nd + nw / 2, -1])
    notch = tip + slot
    # bumps on the side walls, 3 mm inside the opening
    b = P["bump"]
    bumps = [Manifold.cube([b, 2.0, ih - 1.0]).translate([x0, ol - 5.0, s + 0.5]) for x0 in (w, w + iw - b)]
    return body - cavity - notch + bumps[0] + bumps[1], (ow, ol, oh)


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))


SCAD = """// EC2M2 case (transport/storage) - same geometry as gen/enclosure.py
width = {width};  // 34 or 54
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
