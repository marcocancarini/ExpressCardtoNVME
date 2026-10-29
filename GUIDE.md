# Guide: from checks to first boot

## 1. Pick a variant

- **34 mm:** fits any ExpressCard slot (/34 and /54).
- **54 mm:** /54 slots only (like the X230's); the wide part makes it more stable.
- **USB 5V:** only if you want to connect a small USB device (for example a wireless receiver) that stays inside
  the laptop. The boost provides 200 mA guaranteed; the slot gives about 1.3 A in total on 3.3 V, shared with the SSD.

## 2. Checks before ordering

The design has not been tested on hardware yet. These checks are cheap and avoid boards that end up in the bin.

1. **ExpressCard connector (J1).** Get the module-side connector: 26 pins, single row, 1.0 mm pitch, SMT.
   Print `out/<variant>/fab/<variant>_print_1to1.pdf` **at 100%**, without fit-to-page, and check with a
   ruler that the pad pitch is 1.0 mm. Lay the connector on the printout and check:
   - that the pins line up with the 26 pads;
   - that the body sits in the cut-out in front of the board edge;
   - **pin 1 orientation:** looking at the component side with the connector at the top, pin 1 (GND) is on the left.
     With the wrong orientation 3.3 V would end up on the signal lines.
2. **M2 nut positions.** Insert the SSD into the M.2 connector lying on the table and measure the distance between the
   centre of the connector's pegs and the centre of the SSD's notch. Compare it with the printout: the notch tolerates
   about ±0.75 mm.
3. **M.2 connector.** If you do not use the Minlenda MLD-NGFF-M-3.2H, check that the connector has the standard
   TE land pattern (2 rows 7.55 mm apart, pegs at ±10 mm) and a height of 3.2 mm.

## 3. Ordering from JLCPCB

Files in `out/<variant>/jlcpcb/`.

1. Go to jlcpcb.com → *Order now* → **Add gerber file**: upload `<variant>_gerber.zip`.
2. PCB parameters:
   - Layers **2**, PCB Thickness **1.0 mm**;
   - Surface Finish **ENIG** (recommended for the 0.5 mm pitch of the M.2; HASL works but is less flat);
   - everything else at the defaults; the design rules (0.15 mm traces and spaces, 0.3 mm holes) are within the standard process.
   - The 54 mm board is L-shaped: the price is computed on the 54 × 70 mm bounding box.
3. **PCB Assembly** → **Top** side. Upload `<variant>_BOM_JLC.csv` and `<variant>_CPL_JLC.csv`.
4. In the component preview check:
   - **U1** (TPS61240): the pin 1 dot must match the mark on the PCB;
   - **D1** (LED): the cathode must face the pad connected to the M.2 connector;
   - **J2** (M.2): the two rows of contacts must line up with the pads.
   If something is rotated by 90° or 180°, fix it directly in the preview.
5. Left out of assembly (DNP): **J1** (ExpressCard connector), **J3** (USB pads), **J4** (3V3 pad), **JP1** (solder
   jumper). The cost estimate is in `<variant>_estimate.md`.

## 4. Hand assembly

1. **J1, ExpressCard connector:** align it with the body in the front cut-out and the pins centred on the pads. Tack
   one pin on each side, check the alignment, then solder the rest. Use flux and, if bridges form, remove them with
   desoldering braid.
2. **Multimeter check**, before inserting anything into the laptop:
   - no short between 3.3 V (pads 14/15 of J1) and GND (pads 1/26);
   - continuity between the PCIe pads of J1 and those of the M.2 connector.
3. **USB (USB variants only):** solder the device's wires directly to the J3 pads, following the
   5V, −, +, G labels printed on the board. No vertical header: it would not fit in the slot.
   The separate **3V3** pad gives the slot's 3.3 V: use it only for 3.3 V devices, never together with 5V
   on the same device. GND is the G pad of J3.
4. **JP1** stays open. Close it with a blob of solder only if the SSD is not detected (see below).
5. **SSD:** insert it at an angle into the M.2 connector, push it down and fix it with an M2 × 2–3 mm screw into the nut
   for its length (2230 or 2242).

## 5. First boot on the X230

- The component side must face **down**: the top side is marked "THIS SIDE UP".
- Insert the board with the laptop off. At 70 mm it sits flush with the slot: leave some margin to grab it, or
  stick a tab of kapton tape on the back to pull it out more easily.
- On Linux:
  ```sh
  lspci -nn | grep -i -E "nvme|non-volatile"   # the SSD must show up
  sudo lspci -vv -s <address> | grep LnkSta    # negotiated link speed and width
  sudo nvme list                                # or: lsblk
  ```
- Speed is limited by the slot's single PCIe lane: about 250 MB/s at 2.5 GT/s, about 500 MB/s at 5 GT/s.
- The X230 BIOS cannot boot from NVMe: the SSD works as a data drive. To boot the system from it you need a
  bootloader on another drive.

## 6. Troubleshooting

| Symptom | What to try |
|---|---|
| SSD not detected | Reboot with the board already inserted. Close **JP1** (CLKREQ# to GND, clock always on). |
| The laptop shuts down or the slot gets disabled | Excessive current draw: some SSDs have high peaks. Try a low-power 2230 SSD and disconnect the USB. |
| USB device not seen | Check for 5 V between the 5V and G pads with the laptop on; check D− and D+ (do not swap them). |
| The LED does not light up | Normal with some SSDs: the activity signal on pin 10 is optional. |

## 7. Transport case

The STLs are in `out/enclosure/`: `EC2M2_34_case.stl` for the 34 mm board, `EC2M2_54_case.stl` for the 54 mm one.

- Print it standing on its open side, without supports. PLA or PETG, 0.2 mm layers, 3 perimeters, 20% infill.
- Slide the board in with the ExpressCard connector first: the two bumps near the opening hold it in place.
- If it is too tight or too loose, change `clear` (clearance per side) or `bump` (bumps) in `gen/enclosure.py`
  or in `enclosure.scad`, and regenerate.
- Do not use it in the slot: there is no room, the board must be inserted bare.

## 8. Modifying the design

All parameters are at the top of `gen/gen_board.py`: dimensions, connector positions, differential pair geometry
(`DP_W`, `DP_GAP`), estimated SSD position (`CARD_EDGE`). After every change:

```sh
gen/build.sh && gen/fab.sh && gen/render.sh
python3 gen/check_nets.py out/EC2M2_34/EC2M2_34.kicad_pcb
```

Design choices and calculations are documented in [HANDOFF.md](HANDOFF.md).
