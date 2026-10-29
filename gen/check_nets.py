"""Verifica la netlist della scheda generata contro la mappatura attesa. Uso: check_nets.py file.kicad_pcb"""
import sys, collections, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
usb = "USB5V" in sys.argv[1]
pads = collections.defaultdict(set)
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            pads[p.GetNetname()].add(f"{fp.GetReference()}.{p.GetNumber()}")
exp = {  # net -> pad che DEVONO esserci
    "PERn0": {"J1.21", "J2.41"}, "PERp0": {"J1.22", "J2.43"}, "PETn0": {"J1.24", "J2.47"}, "PETp0": {"J1.25", "J2.49"},
    "REFCLK-": {"J1.18", "J2.53"}, "REFCLK+": {"J1.19", "J2.55"}, "PERST#": {"J1.13", "J2.50"},
    "CLKREQ#": {"J1.16", "J2.52", "JP1.1"}, "LED#": {"J2.10", "D1.1"}, "LED_A": {"D1.2", "R1.1"},
    "+3V3": {"J1.14", "J1.15"} | {f"J2.{n}" for n in (2, 4, 12, 14, 16, 18, 70, 72, 74)} | {"C1.1", "C2.1", "R1.2"},
    "GND": {"J1.1", "J1.17", "J1.20", "J1.23", "J1.26", "JP1.2"} | {f"J2.{n}" for n in (1, 3, 9, 15, 21, 27, 33, 39, 45, 57, 71, 73, 75)},
}
if usb:
    w34 = "_34_" in sys.argv[1]  # 34: J3 = G,+,-,5V (colonna) ; 54: J3 = 5V,-,+,G (riga)
    exp["USB_D-"] = {"J1.2", "J3.3" if w34 else "J3.2"}
    exp["USB_D+"] = {"J1.3", "J3.2" if w34 else "J3.3"}
    exp["+5V"] = {"U1.2", "U1.3", "C4.1", "J3.4" if w34 else "J3.1"}
    exp["GND"] |= {"J1.4", "U1.1", "C3.2", "C4.2", "J3.1" if w34 else "J3.4"}
    exp["+3V3"] |= {"U1.4", "U1.6", "L1.2", "C3.1", "J4.1"}
    exp["SW"] = {"U1.5", "L1.1"}
ok = True
for n, s in exp.items():
    miss = s - pads.get(n, set())
    if miss:
        ok = False; print("MANCANO", n, sorted(miss))
for n in pads:
    if n not in exp:
        ok = False; print("NET inattesa", n, sorted(pads[n]))
# pin EC che devono restare NC
nc = {f"J1.{i}" for i in (5, 6, 7, 8, 9, 10, 11, 12)} | ({"J1.2", "J1.3", "J1.4"} if not usb else set())
used = set().union(*pads.values())
if nc & used:
    ok = False; print("Pin EC che dovrebbero essere NC:", sorted(nc & used))
# GND J2 nelle due versioni USB: J3 GND
print(sys.argv[1].split("/")[-1], "OK" if ok else "ERRORI", "| net:", len(pads))
