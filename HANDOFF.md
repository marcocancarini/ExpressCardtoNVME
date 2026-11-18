# ExpressCard → M.2 NVMe (ThinkPad X230) — design notes

Generator: `gen/gen_board.py` (KiCad 10 pcbnew API) → `out/<variant>/`. Footprint libraries from kicad-library
(`/usr/share/kicad/footprints`, or `KICAD_FPLIB=<dir>`).
Variants: {34mm, 54mm} × {no USB, USB 5V}. No 3.3V USB.

## Workflow
- `gen/build.sh ["34 nousb" …]` generates the variants and summarises the DRC (`gen/drc_summary.py`).
- `gen/fab.sh` → `out/<variant>/fab/`: Gerber+drill zip (JLCPCB), CPL, renders, 1:1 PDF.
- `gen/check_nets.py <pcb>` checks the netlist against the expected mapping.
- `gen/impedance.py w,s,g` 2D quasi-static solver (needs `gen/.venv`, with scipy).
- `gen/jlc_search.py "keyword"` LCSC/JLC part search (stock, basic/extended).
- `gen/plot_routing.py` copy without zones, to see the traces in SVG/PNG.

## ExpressCard pinout (module side)
1 GND, 2 USBD-, 3 USBD+, 4 CPUSB#, 5-6 RSVD, 7 SMBCLK, 8 SMBDATA, 9-10 +1.5V,
11 WAKE#, 12 +3.3VAUX, 13 PERST#, 14-15 +3.3V, 16 CLKREQ#, 17 CPPE#,
18 REFCLK-, 19 REFCLK+, 20 GND, 21 PERn0, 22 PERp0, 23 GND, 24 PETn0, 25 PETp0, 26 GND.
The slot does not provide 5V → the USB version has an on-board 3.3→5V boost.

## Mapping to M.2 M-key (direct, no AC capacitors: they are on the host and the SSD)
PERn0 21→41, PERp0 22→43, PETn0 24→47, PETp0 25→49, REFCLK- 18→53, REFCLK+ 19→55,
PERST# 13→50, CLKREQ# 16→52 (+ optional JP1 solder jumper to GND), +3.3V 14,15 → 2,4,12,14,16,18,70,72,74.
Activity LED: pin 10 (DAS/DSS#, open-drain) → red LED + 470Ω to 3V3.
CPPE# 17 → GND (always). CPUSB# 4 → GND only in the USB versions.
M.2 pad 51 (GND) NC: boxed in between PETp0 and REFCLK-; the SSD has the other GNDs anyway.

### Signals left unconnected (evaluated)
- WAKE# (EC 11 ↔ M.2 54): the host pulls it up to 3.3VAUX; the SSD is powered only from the main +3.3V, so with the
  slot off the pull-up would feed the unpowered SSD through the pin (back-powering). Wake from storage is not needed → NC.
- SMBus (EC 7/8 ↔ M.2 40/42/44): 1.8V on the M.2 side, 3.3V(AUX) on the ExpressCard side: a level shifter would be needed;
  only used for NVMe-MI management → NC.
- +1.5V, +3.3VAUX, PEDET 69, SUSCLK 68, PCIe lanes 1-3: NC.

## Mechanics / orientation
- Component side = side facing DOWN in the laptop; B side silkscreen "THIS SIDE UP".
- B side silkscreen also has a 7mm QR (8mm does not fit the 1mm keepout between nut holes and edge) to the GitHub repo (native KiCad barcode, knockout, ECC L, 0.24mm modules)
  to the right of the SSD nuts, with no stitching vias underneath; KiCad wants 1mm of clearance around it.
- Viewed from the component side, EC connector at the top: pin 1 on the left; on the 54mm board the wide part sticks out to the left.
  Consistent with the 10030570 drawing (recommended layout, top view: P1 on the right with the connector at the
  bottom = on the left with the connector at the top); still check it on the real part (1:1 PDF).
- Module-side EC connector: **FCI/Amphenol 10030570**, footprint from the customer drawing 10030570 rev M
  ("recommended PCB layout", archived at portal.fciconnect.com/Comergent//fci/drawing/10030570.pdf):
  26 pads 0.70x2.00, pitch 1.00, from 0.25 to 2.25 behind the PCB edge (pad centre 1.25 behind it).
  The housing *is* the module front: 34.0 wide, 5.0 tall, 11.0 deep; the PCB edge stops 9.0 behind the mating face,
  the housing side walls go on 2.0 behind it.
  PCB outline per the drawing: two arms 0.9 wide (inner span 28.60, outer 30.40) and 5.75 long (5.80 +0/-0.10)
  slide into the housing rails; R0.6 inner corners at the edge; the board stays 30.40 wide up to 2.25 behind the
  edge, then widens to 34 with a 45° chamfer (the drawing narrows here for the module shield: not needed).
  No stitching vias under the housing side walls.
- **Thickness and height (the constraint that drives the design).** The drawing specifies a **0.60mm PCB**
  (the arms go into the rails) and the connector holds it at mid-height of the 5.0mm envelope. From section C-C
  (scale 5:1) the solder-tail plane = PCB top is ~3.0mm − offset above the envelope bottom; the part number picks
  the offset (DIM "C"): -1xxx +0.00, -2xxx +0.30, -3xxx +0.60, **-6xxx +1.15**. Room above the component side:
  ~2.0 / 2.3 / 2.6 / **3.15mm**; below the PCB: ~2.4 / 2.1 / 1.8 / **1.25mm**.
  The old 3.2H M.2 connector + SSD needs ~3.6–3.85mm: it did not fit with any version. → J1 = **10030570-6xxxLF**
  and a 2.3H M.2 connector (SSD top ≤ 2.75mm, ~0.4mm margin). The common 10030570-2112LF (offset +0.30)
  is NOT suitable (2.3mm of room). Measurements read off the drawing: verify with the real part (sacrificial boards).
- Module length 70mm from the housing front, flush with the slot: board from y=-0.75 (arm tips) to y=66.
  34mm wide; 54mm L-shaped with a 34mm-wide narrow section 26mm long from the module front (conservative choice).
- M.2: **HOAUC HYCW25M-05NGFF-230B** (C41430851, M-key, 2.3H, single-sided SSDs only: top-side components ≤ 1.5mm,
  nothing on the underside). Its recommended layout is the TE land pattern (TE_M.2_M_2x38-1MP_P0.5mm: rows at 7.55mm,
  pegs at ±10mm y+1.5, MP pads 1.2x2.75 at ±10.35) except the right peg hole, 1.60 instead of 1.80 (set in gen_board.py).
  Not rotated, close to the EC connector; SSD towards the back. SSD underside ~0.3–0.45mm above the PCB (0.30 min).
- Pair order: EC (left→right) REF, PER, PET; M.2 (left→right) PER, PET, REF → REFCLK runs on B.Cu (2 vias/line).
- SSD mounting: Würth 9774010243R M2 SMT nuts (H1.0) at 30 and 42mm from the SSD contact edge, on the **bottom
  side** (no room on top: SSD underside ~0.4mm above the PCB), hand-soldered (DNP for JLC, which assembles the top only).
  Board bottom ~1.25mm above the envelope with the -6xxx connector → nut H1.0 fits with ~0.25mm margin.
  M2x3 screw from the top through the SSD notch and the 3.0mm hole; an M2 washer ≤0.4mm under the SSD avoids bending it.
  Nuts optional: if the 0.25mm margin turns out not to be there, leave them out (hole only) and hold the SSD with kapton.
  On top they cannot go (SSD underside 0.30 min): no SMT nut is that thin.
  SSD notch centre = end of the card. Contact edge estimated at CY-2.5 (notch tolerance ±0.75mm).
- 0.6mm thick, 2 layers. Height: PCB top at ~1.85mm, SSD top ≤ 1.85 + 2.75 = 4.6mm < 5.0.

## Impedance (gen/impedance.py, validated against a known microstrip: ~3% error)
Stackup: 2 layers 0.6mm, h≈0.53mm, er 4.5, 35µm copper, 15µm solder mask (`impedance.py w,s,g,h`).
- 1.0mm board (old): w0.40/s0.15/g0.25 → Zdiff ≈ 87Ω.
- 0.6mm board (now): w0.40/s0.15/g0.25 → Zdiff ≈ 86Ω, Zcm ≈ 43Ω (PCIe 85Ω, USB 90Ω: both within ±10%).
  The coplanar GND at 0.25 dominates, so the thinner board changes Zdiff very little; geometry unchanged.
  ~1mm neck at w0.3/0.5 pitch at the M.2 pads. Where the side pour is missing Zdiff rises to ~95Ω.
- Known limits: REFCLK on B.Cu crosses the GND plane under PER/PET; impedance not controlled by the fab.

## USB 5V
TPS61240DRVR (C59567): fixed 5V, 200mA guaranteed, load disconnect; L 1µH 1.4A TDK MLP2016 (C76793, 2.0x1.6mm,
land per datasheet: 0.8x1.6 pads, 1.0 gap, footprint EC2M2:L_TDK_MLP2016), CIN/COUT 10µF.
3V3 routed on B.Cu along the left side up to the block's input via. Boost (U1, L1, C3, C4) in the free strip
to the left of the SSD, mid-board (x≈6–10, y≈36–48), same relative layout rotated by 90° (function G in gen_board.py).
J3 = 4 pads at 2.54 pitch for soldered wires (no header: it would not fit in the slot):
34mm in a column on the left side below the boost (G,+,-,5V, y≈52–60); 54mm above the 13x28mm cut-out (5V,-,+,G; cut-out y 34.5–62.5).
J4 = separate 3V3 pad (34mm below J3, fed on B.Cu along the left edge of the SSD; 54mm to the right of J3).

## 3D case (gen/enclosure.py → out/enclosure/)
An in-slot shell is not feasible: the EC housing already takes the whole 5.0mm. A sleeve-style transport case was made instead:
inside (W+0.8) x 70.8 x 6.0mm, 1.6 walls, 1.2 bottom/lid, finger notches, 0.35mm bumps. Printed standing up.
Budget: slot 3.3V ~1.3A total between SSD and USB.

## BOM / LCSC (verified with gen/jlc_search.py)
C1 C45783, C2 C1525, C3/C4 C19702, R1 C25117, D1 C2286, L1 C76793, U1 C59567, J2 C41430851 (HYCW25M 2.3H).
H1/H2 (C5360192) on the bottom, hand-soldered. J1 (ExpressCard connector, 10030570-6xxxLF) not available from LCSC: buy separately and solder by hand.

## To do before ordering
- Check the real EC connector against the 1:1 PDF: pads, pin 1, arms in the rails with a 0.6mm board, and that the
  part is a -6xxxLF (tail offset +1.15). With another offset the SSD does not fit in the slot height.
- Check the nut positions: insert the SSD into the connector and measure M.2 peg → notch centre.

## JLCPCB quote / order
`gen/fab.sh` → `out/<variant>/jlcpcb/`: `_gerber.zip` (without drill maps), `_BOM_JLC.csv`, `_CPL_JLC.csv`,
`_estimate.md` (component cost from the JLC API, including attrition and minimum purchase). DNP: J1 (EC connector), J3, J4, JP1,
H1/H2 (bottom side). PCB parameters: 2 layers, **0.6mm**, min trace/space 0.15, min hole 0.3, ENIG finish recommended (0.5 pitch of the M.2).
In the PCBA preview check the rotation/polarity of U1 (pin 1), D1 (cathode) and J2.

## License
CC BY-NC-SA 4.0 (`LICENSE`): non-commercial use only.
