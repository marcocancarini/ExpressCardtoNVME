// Astuccio EC2M2 (trasporto/conservazione) - stessa geometria di gen/enclosure.py
width = 34;  // 34 o 54
board_len = 70.0; clear = 0.4; inner_h = 6.0;
wall = 1.6; skin = 1.2; r = 2.0; notch_w = 18.0; notch_d = 10.0; bump = 0.35;
iw = width + 2*clear; il = board_len + 2*clear; ih = inner_h;
ow = iw + 2*wall; ol = il + wall; oh = ih + 2*skin;
$fn = 64;
module rbox(x, y, z) hull() for (cx = [r, x-r], cy = [r, y-r]) translate([cx, cy, 0]) cylinder(h = z, r = r);
union() {
  difference() {
    intersection() { rbox(ow, ol + r, oh); cube([ow, ol, oh]); }
    translate([wall, wall, skin]) cube([iw, il + 1, ih]);
    translate([ow/2, ol - notch_d + notch_w/2, -1]) cylinder(h = oh + 2, r = notch_w/2);
    translate([ow/2 - notch_w/2, ol - notch_d + notch_w/2, -1]) cube([notch_w, notch_d, oh + 2]);
  }
  for (x0 = [wall, wall + iw - bump]) translate([x0, ol - 5, skin + 0.5]) cube([bump, 2, ih - 1]);
}
