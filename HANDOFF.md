# ExpressCard → M.2 NVMe (ThinkPad X230) — design notes

Generator: `gen/gen_board.py` (KiCad 10 pcbnew API) → `out/<variant>/`.
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
- B side silkscreen also has a 7mm QR to the GitHub repo (native KiCad barcode, knockout, ECC L, 0.24mm modules)
  to the right of the SSD nuts, with no stitching vias underneath; KiCad wants 1mm of clearance around it.
- Viewed from the component side, EC connector at the top: pin 1 on the left; on the 54mm board the wide part sticks out to the left.
  TO BE VERIFIED on the real connector (1:1 PDF) before ordering.
- Module-side EC connector: 26 pins, single row, 1.0mm pitch, SMT. Custom footprint (`EC2M2.pretty`):
  0.7x2.0 pads, PCB edge 1.25mm in front of the pad centre, body ±13.35mm protruding 5mm, side tabs.
- 34mm wide; 54mm L-shaped with a 34mm-wide narrow section 26mm long (conservative choice); 70mm long, flush with the slot (2242 SSD + nut end at ~62mm: practical minimum ~63mm, but below 70 the board disappears into the slot).
- M.2: TE_M.2_M_2x38-1MP_P0.5mm footprint, not rotated, close to the EC connector; SSD towards the back.
  The recommended land pattern of the Minlenda MLD-NGFF-M-3.2H (C52766481) matches (rows at 7.55mm, pegs at ±10mm).
  SSD underside at 1.25±0.10mm from the PCB (MLD datasheet).
- Pair order: EC (left→right) REF, PER, PET; M.2 (left→right) PER, PET, REF → REFCLK runs on B.Cu (2 vias/line).
- SSD mounting: Würth 9774010243R M2 SMT nuts (H1.0, C5360192) at 30 and 42mm from the SSD contact edge.
  SSD notch centre = end of the card. Contact edge estimated at CY-2.5 (notch tolerance ±0.75mm).
  H1.0 < 1.25 → the 2230 nut does not touch a 2242: both are fitted.
- 1.0mm thick, 2 layers. Height: SSD max ~3.85mm above the PCB + 1.0 → ~4.85mm.

## Impedance (gen/impedance.py, validated against a known microstrip: ~3% error)
Stackup: 2 layers 1.0mm, h≈0.93mm, er 4.5, 35µm copper, 15µm solder mask.
- Before: w0.30/s0.20/g0.25 → Zdiff ≈ 103Ω.
- Now: w0.40/s0.15/g0.25 → Zdiff ≈ 87Ω, Zcm ≈ 50Ω (PCIe 85Ω, USB 90Ω: both within ±10%).
  ~1mm neck at w0.3/0.5 pitch at the M.2 pads. Where the side pour is missing Zdiff rises to ~95Ω.
- Known limits: REFCLK on B.Cu crosses the GND plane under PER/PET; impedance not controlled by the fab.

## USB 5V
TPS61240DRVR (C59567): fixed 5V, 200mA guaranteed, load disconnect; L 1µH 1.4A (C76793), CIN/COUT 10µF.
3V3 routed on B.Cu along the left side up to the block's input via. Boost (U1, L1, C3, C4) in the free strip
to the left of the SSD, mid-board (x≈6–10, y≈36–48), same relative layout rotated by 90° (function G in gen_board.py).
J3 = 4 pads at 2.54 pitch for soldered wires (no header: it would not fit in the slot):
34mm in a column on the left side below the boost (G,+,-,5V, y≈52–60); 54mm above the 13x28mm cut-out (5V,-,+,G).
J4 = separate 3V3 pad (34mm below J3, fed on B.Cu along the left edge of the SSD; 54mm to the right of J3).

## 3D case (gen/enclosure.py → out/enclosure/)
An in-slot shell is not feasible: slot 5.0mm, board+SSD ~4.85mm. A sleeve-style transport case was made instead:
inside (W+0.8) x 70.8 x 6.0mm, 1.6 walls, 1.2 bottom/lid, finger notches, 0.35mm bumps. Printed standing up.
Budget: slot 3.3V ~1.3A total between SSD and USB.

## BOM / LCSC (verified with gen/jlc_search.py)
C1 C45783, C2 C1525, C3/C4 C19702, R1 C25117, D1 C2286, L1 C76793, U1 C59567, J2 C52766481, H1/H2 C5360192.
J1 (ExpressCard connector) not available from LCSC: buy separately and solder by hand.

## To do before ordering
- Check the real EC connector (pads, pin 1, stop) against the 1:1 PDF.
- Check the nut positions: insert the SSD into the connector and measure M.2 peg → notch centre.

## JLCPCB quote / order
`gen/fab.sh` → `out/<variant>/jlcpcb/`: `_gerber.zip` (without drill maps), `_BOM_JLC.csv`, `_CPL_JLC.csv`,
`_estimate.md` (component cost from the JLC API, including attrition and minimum purchase). DNP: J1 (EC connector), J3, J4, JP1.
PCB parameters: 2 layers, 1.0mm, min trace/space 0.15, min hole 0.3, ENIG finish recommended (0.5 pitch of the M.2).
In the PCBA preview check the rotation/polarity of U1 (pin 1), D1 (cathode) and J2.

## License
CC BY-NC-SA 4.0 (`LICENSE`): non-commercial use only.
