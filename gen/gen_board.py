#!/usr/bin/env python3
"""Generatore PCB ExpressCard -> M.2 NVMe (ThinkPad X230).

Uso: python3 gen_board.py <34|54> <nousb|usb5v> <cartella_output>
Coordinate in mm, vista dal lato componenti (F.Cu), y verso il basso,
origine = fronte del connettore ExpressCard, angolo sinistro della parte da 34mm.
Vedi HANDOFF.md per le scelte di progetto.
"""
import math
import sys
from pathlib import Path

import pcbnew

FPLIB = "/usr/share/kicad/footprints/"
MM = pcbnew.FromMM

WIDTH, USB = int(sys.argv[1]), sys.argv[2] == "usb5v"
OUT = Path(sys.argv[3])
NAME = f"EC2M2_{WIDTH}" + ("_USB5V" if USB else "")

# --- parametri meccanici ---------------------------------------------------
BOARD_LEN = 70.0         # fronte connettore -> retro scheda: a filo con lo slot (SSD 2242 + dado finiscono a ~62mm)
EDGE_Y = 5.0             # bordo PCB dietro al corpo del connettore EC
NOTCH = (2.8, 31.2)      # incavo per il corpo del connettore EC (±13.35 + gioco)
EC_X0, EC_Y = 17.0, 6.25 # centro fila pad EC
NARROW_LEN = 26.0        # 54mm: lunghezza tratto da 34mm (scelta conservativa)
EXT_X = -20.0            # 54mm: bordo sinistro della parte larga
CX, CY = 21.5, 20.4      # origine footprint M.2 (TE, non ruotato: SSD verso +y)
CARD_EDGE = CY - 2.5     # bordo contatti della SSD inserita (stima; l'intaglio della vite tollera ±0.75mm)
DP_W, DP_GAP = 0.4, 0.15 # coppie differenziali: Zdiff ~87 ohm con GND coplanare a 0.25 (gen/impedance.py)
THICK = 1.0

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetBoardThickness(MM(THICK))
ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth = MM(0.15)
ds.m_ViasMinSize = MM(0.5)
ds.m_MinThroughDrill = MM(0.3)
ds.m_CopperEdgeClearance = MM(0.2)
ds.m_HoleToHoleMin = MM(0.25)
ds.m_HoleClearance = MM(0.2)
ds.m_MinClearance = MM(0.15)
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(MM(0.15))
nc.SetTrackWidth(MM(0.25))
nc.SetViaDiameter(MM(0.6))
nc.SetViaDrill(MM(0.3))

V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


# --- footprint --------------------------------------------------------------
fps = {}


def place(lib, name, ref, value, x, y, rot=0, padnets=None):
    fp = pcbnew.FootprintLoad(FPLIB + lib + ".pretty", name)
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)
    fp.Reference().SetTextSize(V(0.8, 0.8))
    fp.Reference().SetTextThickness(MM(0.12))
    for p in fp.Pads():
        if padnets and p.GetNumber() in padnets:
            p.SetNet(net(padnets[p.GetNumber()]))
    fps[ref] = fp
    return fp


def pad(ref, num):
    p = [q for q in fps[ref].Pads() if q.GetNumber() == num][0]
    pos = p.GetPosition()
    return (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))


def ec_connector():
    """Connettore ExpressCard lato modulo: 26 pad SMT, passo 1.0mm (verificare pad e battuta sul datasheet del connettore usato)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("EC2M2", "ExpressCard_Module_1x26_P1.0mm"))
    fp.SetReference("J1")
    fp.SetValue("ExpressCard 26P")
    fp.SetAttributes(pcbnew.FP_SMD)
    board.Add(fp)
    fp.SetPosition(V(EC_X0, EC_Y))
    for n in range(1, 27):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(n))
        p.SetShape(pcbnew.PAD_SHAPE_RECT)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask())
        p.SetSize(V(0.7, 2.0))
        fp.Add(p)
        p.SetFPRelativePosition(V(n - 13.5, 0))
    for layer, w, pts in ((pcbnew.F_Fab, 0.1, [(-13.35, -EC_Y), (13.35, -EC_Y), (13.35, EDGE_Y - EC_Y), (-13.35, EDGE_Y - EC_Y)]),
                          (pcbnew.F_CrtYd, 0.05, [(-13.6, -EC_Y - 0.25), (13.6, -EC_Y - 0.25), (13.6, 1.25), (-13.6, 1.25)])):
        for a, b in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(EC_X0 + a[0], EC_Y + a[1]))
            s.SetEnd(V(EC_X0 + b[0], EC_Y + b[1]))
            s.SetLayer(layer)
            s.SetWidth(MM(w))
            fp.Add(s)
    fp.Reference().SetPosition(V(EC_X0, 2.5))
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fps["J1"] = fp
    return fp


# --- rame -------------------------------------------------------------------
def track(netname, pts, w=0.25, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(*a))
        t.SetEnd(V(*b))
        t.SetWidth(MM(w))
        t.SetLayer(layer)
        t.SetNet(net(netname))
        board.Add(t)


def via(netname, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(x, y))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(MM(d))
    v.SetDrill(MM(drill))
    v.SetNet(net(netname))
    board.Add(v)


def offset(pts, off):
    """Polilinea parallela (giunzioni a spigolo vivo); off>0 = lato sinistro rispetto al verso di percorrenza
    (normale (-dy, dx)), cioè la linea 'n' della coppia quando si scende verso +y."""
    def nrm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy)
        return (-dy / l, dx / l)
    ns = [nrm(a, b) for a, b in zip(pts, pts[1:])]
    out = [(pts[0][0] + off * ns[0][0], pts[0][1] + off * ns[0][1])]
    for i in range(1, len(pts) - 1):
        n1, n2 = ns[i - 1], ns[i]
        k = off / (1 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((pts[i][0] + k * (n1[0] + n2[0]), pts[i][1] + k * (n1[1] + n2[1])))
    out.append((pts[-1][0] + off * ns[-1][0], pts[-1][1] + off * ns[-1][1]))
    return out


def pair(nn, np_, center, w=DP_W, gap=DP_GAP, layer=pcbnew.F_Cu):
    o = (w + gap) / 2
    track(nn, offset(center, o), w, layer)
    track(np_, offset(center, -o), w, layer)


# --- bordo scheda -----------------------------------------------------------
def edge_poly(pts):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)


def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(V(size, size))
    t.SetTextThickness(MM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def silk_rect(x0, y0, x1, y1, layer=pcbnew.F_SilkS):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(MM(0.15)); board.Add(s)


front = [(0, 0), (NOTCH[0], 0), (NOTCH[0], EDGE_Y), (NOTCH[1], EDGE_Y), (NOTCH[1], 0), (34, 0)]
if WIDTH == 54:
    outline = front + [(34, BOARD_LEN), (EXT_X, BOARD_LEN), (EXT_X, NARROW_LEN), (0, NARROW_LEN)]
else:
    outline = front + [(34, BOARD_LEN), (0, BOARD_LEN)]
edge_poly(outline)

# Dadi SMT M2 per la vite della SSD: il centro dell'intaglio coincide con la fine della scheda (2230 / 2242).
# Altezza 1.0mm: il fondo della SSD sta a 1.25mm dal PCB, così il dado 2230 non tocca una 2242.
for i, L in enumerate((30, 42)):
    place("Mounting_Wuerth", "Mounting_Wuerth_WA-SMSI-M2_H1mm_9774010243", f"H{i + 1}", "M2 SMT nut H1.0",
          CX, CARD_EDGE + L).Reference().SetVisible(False)
    text(f"22{L}", CX + 5.0, CARD_EDGE + L, 1.2)
for a, b in (((CX - 11.2, CY + 4.8), (CX - 11.2, 62.4)), ((CX + 11.2, CY + 4.8), (CX + 11.2, 62.4)), ((CX - 11.2, 62.4), (CX + 11.2, 62.4))):
    sh = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(*a)); sh.SetEnd(V(*b)); sh.SetLayer(pcbnew.F_SilkS); sh.SetWidth(MM(0.15)); board.Add(sh)

# --- componenti -------------------------------------------------------------
ec_padnets = {"1": "GND", "13": "PERST#", "14": "+3V3", "15": "+3V3", "16": "CLKREQ#", "17": "GND",
              "18": "REFCLK-", "19": "REFCLK+", "20": "GND", "21": "PERn0", "22": "PERp0", "23": "GND",
              "24": "PETn0", "25": "PETp0", "26": "GND"}
if USB:
    ec_padnets.update({"2": "USB_D-", "3": "USB_D+", "4": "GND"})  # CPUSB# a GND abilita la porta USB
j1 = ec_connector()
for p in j1.Pads():
    if p.GetNumber() in ec_padnets:
        p.SetNet(net(ec_padnets[p.GetNumber()]))

m2nets = {"41": "PERn0", "43": "PERp0", "47": "PETn0", "49": "PETp0", "53": "REFCLK-", "55": "REFCLK+",
          "50": "PERST#", "52": "CLKREQ#", "10": "LED#", "MP": "GND"}
for n in (1, 3, 9, 15, 21, 27, 33, 39, 45, 57, 71, 73, 75):  # 51: chiuso tra PETp0 e REFCLK-, resta NC
    m2nets[str(n)] = "GND"
for n in (2, 4, 12, 14, 16, 18, 70, 72, 74):
    m2nets[str(n)] = "+3V3"
place("Connector_PCBEdge", "TE_M.2_M_2x38-1MP_P0.5mm", "J2", "M.2 M-key H3.2", CX, CY, 0, m2nets)

place("Capacitor_SMD", "C_0805_2012Metric", "C1", "22uF", 8.0, 23.3, 90, {"1": "+3V3", "2": "GND"})
place("Capacitor_SMD", "C_0402_1005Metric", "C2", "100nF", 6.0, 23.5, 90, {"1": "+3V3", "2": "GND"})
place("Resistor_SMD", "R_0402_1005Metric", "R1", "470", 6.5, 28.6, 90, {"1": "LED_A", "2": "+3V3"})
place("LED_SMD", "LED_0603_1608Metric", "D1", "LED red", 8.0, 30.6, 180, {"1": "LED#", "2": "LED_A"})
place("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "JP1", "CLKREQ-GND", 13.5, 10.5, 0,
      {"1": "CLKREQ#", "2": "GND"})

# --- connessioni EC -> M.2 --------------------------------------------------
x = lambda n: EC_X0 + n - 13.5        # x del pad n del connettore EC
EB = EC_Y + 1.0                       # bordo inferiore dei pad EC
ODD, EVEN = CY - 3.775, CY + 3.775    # centri file M.2

# GND dei pad EC -> via sul piano B.Cu
track("GND", [(x(1), EC_Y), (3.4, EC_Y)], 0.5); via("GND", 3.4, 6.6)
for n, vy in ((17, 8.1), (20, 8.1), (23, 8.2), (26, 8.1)):
    track("GND", [(x(n), EB), (x(n), vy)], 0.5); via("GND", x(n), vy)
if USB:
    track("GND", [(x(4), EB), (x(4), 8.1)], 0.4); via("GND", x(4), 8.1)

# PCIe RX (host->SSD) e TX: coppie su F.Cu, w0.3 / gap0.2
for (n_, p_, a, b) in (("PERn0", "PERp0", 21, 22), ("PETn0", "PETp0", 24, 25)):
    track(n_, [(x(a), EB), (x(a), 7.6), (x(a) + 0.5 - (DP_W + DP_GAP) / 2, 7.85)], 0.3)
    track(p_, [(x(b), EB), (x(b), 7.6), (x(b) - 0.5 + (DP_W + DP_GAP) / 2, 7.85)], 0.3)
NECK = ODD - 1.4   # la coppia si restringe al passo 0.5 dei pad M.2
for n_, p_, cx_, path in (("PERn0", "PERp0", 22.5, [(25.0, 7.85), (25.0, 8.2), (22.5, 10.7)]),
                          ("PETn0", "PETp0", 24.0, [(28.0, 7.85), (28.0, 9.7), (24.0, 13.7)])):
    pair(n_, p_, path + [(cx_, NECK)])
    o = (DP_W + DP_GAP) / 2
    track(n_, [(cx_ - o, NECK), (cx_ - 0.25, NECK + 0.4), (cx_ - 0.25, ODD)], 0.3)
    track(p_, [(cx_ + o, NECK), (cx_ + 0.25, NECK + 0.4), (cx_ + 0.25, ODD)], 0.3)

# REFCLK: passa sotto PER/PET su B.Cu e risale tra le due file del connettore M.2
track("REFCLK-", [(x(18), EB), (x(18), 8.3)], 0.3); via("REFCLK-", x(18), 8.3)
track("REFCLK+", [(x(19), EB), (x(19), 8.3)], 0.3); via("REFCLK+", x(19), 8.3)
track("REFCLK-", [(21.5, 8.3), (21.5, 9.0), (25.0, 12.5), (25.0, 18.4)], 0.3, pcbnew.B_Cu)
track("REFCLK+", [(22.5, 8.3), (22.5, 9.0), (26.0, 12.5), (26.0, 18.4)], 0.3, pcbnew.B_Cu)
via("REFCLK-", 25.0, 18.4); via("REFCLK+", 26.0, 18.4)
track("REFCLK-", [(25.0, 18.4), (25.0, 18.0), (25.25, 17.75), (25.25, ODD)], 0.25)
track("REFCLK+", [(26.0, 18.4), (26.0, 18.0), (25.75, 17.5), (25.75, ODD)], 0.25)

# GND della fila dispari M.2 -> via nel corridoio sotto il connettore
for xs in ((12.25, 12.75), (14.25,), (15.75,), (20.25,), (21.75,), (23.25,), (29.75, 30.25, 30.75)):
    vx = sum(xs) / len(xs)
    for px in xs:
        track("GND", [(px, ODD), (px, 17.7), (vx, 18.3)], 0.25)
    via("GND", vx, 18.3)

# Segnali lenti: attorno al lato sinistro del M.2 e dentro il corridoio tra le file
track("PERST#", [(x(13), EB), (x(13), 8.3), (10.0, 8.3), (8.8, 9.5), (8.8, 20.5), (24.5, 20.5), (24.5, EVEN)], 0.2)
track("CLKREQ#", [(x(16), EB), (x(16), 9.0), (10.9, 9.0), (9.6, 10.3), (9.6, 19.7), (25.0, 19.7), (25.0, EVEN)], 0.2)
track("CLKREQ#", [pad("JP1", "1"), (12.85, 9.0)], 0.25)
track("GND", [pad("JP1", "2"), (14.15, 12.0)], 0.4); via("GND", 14.15, 12.0)

# +3V3: pad EC 14/15 -> via 0.8/0.4 -> B.Cu 1.0mm -> riga sotto la fila pari -> via ai pad
P3V = dict(d=0.8, drill=0.4)
for n in (14, 15):
    track("+3V3", [(x(n), EB), (x(n), 8.1)], 0.6); via("+3V3", x(n), 8.1, **P3V)
track("+3V3", [(17.5, 8.1), (18.0, 8.6), (18.5, 8.1)], 1.0, pcbnew.B_Cu)
track("+3V3", [(18.0, 8.6), (18.0, 25.8)], 1.0, pcbnew.B_Cu)
track("+3V3", [(6.5, 25.8), (30.0, 25.8)], 1.0, pcbnew.B_Cu)
for vx, xs in ((12.75, (12.5, 13.0)), (15.25, (15.0, 15.5)), (16.25, (16.0, 16.5)), (30.0, (29.5, 30.0, 30.5))):
    for px in xs:
        track("+3V3", [(px, EVEN), (px, EVEN + 0.6), (vx, 25.8)], 0.3)
    via("+3V3", vx, 25.8, **P3V)

# Condensatori di disaccoppiamento
track("+3V3", [pad("C1", "1"), (8.0, 25.8)], 0.6); via("+3V3", 8.0, 25.8, **P3V)
track("GND", [pad("C1", "2"), (8.0, 21.3)], 0.6); via("GND", 8.0, 21.3)
track("+3V3", [pad("C2", "1"), (6.5, 25.8)], 0.4); via("+3V3", 6.5, 25.8, **P3V)
track("GND", [pad("C2", "2"), (6.0, 22.0)], 0.4); via("GND", 6.0, 22.0)

# LED attività (DAS/DSS#, open-drain attivo basso)
track("+3V3", [(6.5, 25.8), (6.5, 27.2)], 1.0, pcbnew.B_Cu); via("+3V3", 6.5, 27.2, **P3V)
track("+3V3", [(6.5, 27.2), pad("R1", "2")], 0.3)
track("LED_A", [pad("R1", "1"), pad("D1", "2")], 0.25)
track("LED#", [(14.5, EVEN), (14.5, 29.3), (13.2, 30.6), pad("D1", "1")], 0.25)

# --- USB con boost 5V -------------------------------------------------------
if USB:
    o = (DP_W + DP_GAP) / 2
    track("USB_D-", [(x(2), EB), (x(2), 7.6), (x(2) + 0.5 - o, 7.85)], 0.3)
    track("USB_D+", [(x(3), EB), (x(3), 7.6), (x(3) - 0.5 + o, 7.85)], 0.3)
    if WIDTH == 34:
        # piazzole in colonna sul lato sinistro, accanto al M.2
        J3 = [(4.6, 40.0, "GND"), (4.6, 42.54, "USB_D+"), (4.6, 45.08, "USB_D-"), (4.6, 47.62, "+5V")]
        J3_ROT, LBL = 0, (2.0, 0.0)
        J4 = (8.5, 54.0)
        pair("USB_D-", "USB_D+", [(6.0, 7.85), (6.0, 8.2), (2.0, 12.2), (2.0, 41.5)])
        track("USB_D+", [(2.0 + o, 41.5), (2.0 + o, 42.54), (4.6, 42.54)], DP_W)
        track("USB_D-", [(2.0 - o, 41.5), (2.0 - o, 45.08), (4.6, 45.08)], DP_W)
    else:
        J3 = [(-14.6, 31.5, "+5V"), (-12.06, 31.5, "USB_D-"), (-9.52, 31.5, "USB_D+"), (-6.98, 31.5, "GND")]
        J3_ROT, LBL = 90, (0.0, -2.0)
        J4 = (-2.5, 31.5)
        pair("USB_D-", "USB_D+", [(6.0, 7.85), (6.0, 8.2), (2.0, 12.2), (2.0, 27.0), (1.0, 28.0), (-8.5, 28.0)])
        track("USB_D+", [(-8.5, 28.0 + o), (-9.52, 28.0 + o), (-9.52, 31.5)], DP_W)
        track("USB_D-", [(-8.5, 28.0 - o), (-12.06, 28.0 - o), (-12.06, 31.5)], DP_W)
    # piazzole passo 2.54 per fili saldati: un header verticale non entrerebbe nello slot
    j3 = place("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical", "J3", "USB pads", J3[0][0], J3[0][1], J3_ROT,
               {str(i + 1): nn for i, (_, _, nn) in enumerate(J3)})
    j3.Reference().SetVisible(False)
    j3.Models().clear()
    for px, py, nn in J3:
        text({"GND": "G", "USB_D-": "-", "USB_D+": "+", "+5V": "5V"}[nn], px + LBL[0], py + LBL[1], 0.9)
    if WIDTH == 34:
        text("USB", J3[0][0], J3[0][1] - 2.2, 0.9)
    else:
        text("USB 2.0 (5V)", (J3[0][0] + J3[3][0]) / 2, J3[0][1] - 3.6, 0.9)
    # piazzola 3.3V separata (lontana dal 5V per non confonderle)
    j4 = place("Connector_PinHeader_2.54mm", "PinHeader_1x01_P2.54mm_Vertical", "J4", "3V3 pad", *J4, 0, {"1": "+3V3"})
    j4.Reference().SetVisible(False)
    j4.Models().clear()
    text("3V3", J4[0], J4[1] + 2.0 if WIDTH == 34 else J4[1] - 2.0, 0.9)
    track("+3V3", [J4, (6.5, J4[1])], 0.6, pcbnew.B_Cu)

    # TPS61240 (5V fissi, 200mA garantiti) alimentato da +3V3, blocco compatto sotto la fine della SSD
    UY = 66.2
    place("Package_SON", "WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm", "U1", "TPS61240DRV", 18.0, UY, 0,
          {"1": "GND", "2": "+5V", "3": "+5V", "4": "+3V3", "5": "SW", "6": "+3V3", "7": "GND"})
    place("Inductor_SMD", "L_0805_2012Metric", "L1", "1uH", 21.5, UY, 0, {"1": "SW", "2": "+3V3"})
    place("Capacitor_SMD", "C_0603_1608Metric", "C3", "10uF", 24.2, 65.4, 270, {"1": "+3V3", "2": "GND"})
    place("Capacitor_SMD", "C_0603_1608Metric", "C4", "10uF", 15.2, 66.5, 90, {"1": "+5V", "2": "GND"})
    for p in fps["U1"].Pads():
        if p.GetNumber() == "":
            p.SetNet(net("GND"))
    # alimentazione: B.Cu lungo il lato sinistro, poi sotto la fine della SSD
    track("+3V3", [(6.5, 27.2), (6.5, 62.9), (25.6, 62.9), (25.6, 64.6)], 1.0, pcbnew.B_Cu)
    via("+3V3", 25.6, 64.6, **P3V)
    track("+3V3", [pad("U1", "6"), (18.887, 64.6), (25.6, 64.6)], 0.4)
    track("+3V3", [pad("L1", "2"), (22.562, 64.6)], 0.4)
    track("+3V3", [pad("U1", "4"), (18.887, 67.5), (23.3, 67.5), (23.3, 64.6)], 0.3)   # EN = VIN
    track("SW", [pad("U1", "5"), pad("L1", "1")], 0.4)
    track("GND", [pad("C3", "2"), (24.2, 67.4)], 0.5); via("GND", 24.2, 67.4)
    track("+5V", [pad("U1", "3"), (16.5, UY + 0.65), (16.5, UY), pad("U1", "2")], 0.3)
    track("+5V", [(16.5, UY + 0.65), pad("C4", "1")], 0.5)
    track("GND", [pad("U1", "1"), (18.0, UY - 0.65)], 0.3)
    track("GND", [pad("U1", "1"), (16.4, 64.8)], 0.3); via("GND", 16.4, 64.8)
    track("GND", [pad("C4", "2"), (15.2, 64.6)], 0.5); via("GND", 15.2, 64.6)
    c4 = pad("C4", "1")
    if WIDTH == 34:
        track("+5V", [c4, (14.2, 68.3), (4.6, 68.3), (4.6, 47.62)], 0.5)
    else:
        track("+5V", [c4, (14.2, 68.3), (-18.5, 68.3), (-18.5, 33.4), (-14.6, 33.4), (-14.6, 31.5)], 0.5)
        # finestra per alloggiare un piccolo ricevitore USB senza involucro
        edge_poly([(-16.0, 36.0), (-3.0, 36.0), (-3.0, 64.0), (-16.0, 64.0)])

# --- serigrafia ---------------------------------------------------------------
text("M-KEY  2230/2242", CX, CARD_EDGE + 22, 1.2)
text("NVMe SSD", CX, CARD_EDGE + 24.5, 1.2)
text("CLKREQ>GND", 13.5, 12.6, 0.7)
text("ACT", 8.0, 32.1, 0.7)
text("1", x(1), 8.9, 0.8)
text(f"{NAME}", 17.0 if WIDTH == 34 else 7.0, BOARD_LEN - 1.7, 1.0, pcbnew.B_SilkS)
text("THIS SIDE UP", 17.0, 30.0, 1.6, pcbnew.B_SilkS)
text("QUESTO LATO IN ALTO", 17.0, 33.0, 1.2, pcbnew.B_SilkS)
text("ExpressCard to M.2 NVMe", 17.0, 37.0, 1.0, pcbnew.B_SilkS)
text("ThinkPad X230", 17.0, 39.0, 1.0, pcbnew.B_SilkS)

for ref in ("C1", "C2", "R1", "D1", "JP1", "U1", "L1", "C3", "C4"):
    if ref in fps:
        fps[ref].Reference().SetLayer(pcbnew.F_Fab)

# --- piani GND su entrambe le facce ------------------------------------------
xs = [p[0] for p in outline]
bx0, bx1 = min(xs) - 1, max(xs) + 1


def gnd_zone(layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net("GND"))
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.2))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.35))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    for px, py in ((bx0, -1), (bx1, -1), (bx1, BOARD_LEN + 1), (bx0, BOARD_LEN + 1)):
        ol.Append(MM(px), MM(py))
    board.Add(z)
    return z


zones = [gnd_zone(pcbnew.F_Cu), gnd_zone(pcbnew.B_Cu)]
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())


def in_fill(px, py, r=0.75):
    vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    if any(math.hypot(pcbnew.ToMM(v.x) - px, pcbnew.ToMM(v.y) - py) < 1.2 for v in vias):
        return False
    pts = [(px, py)] + [(px + r * math.cos(a), py + r * math.sin(a)) for a in [i * math.pi / 4 for i in range(8)]]
    return all(z.HitTestFilledArea(z.GetLayer(), V(*q), 0) for z in zones for q in pts)


# via di cucitura GND dove entrambi i piani sono pieni
step = 2.5
yy = 1.5
while yy < BOARD_LEN:
    xx = bx0 + 1.5
    while xx < bx1:
        if in_fill(xx, yy):
            via("GND", xx, yy)
        xx += step
    yy += step
filler.Fill(board.Zones())

OUT.mkdir(parents=True, exist_ok=True)
pcb = OUT / f"{NAME}.kicad_pcb"
pcbnew.SaveBoard(str(pcb), board)
# regole di progetto (compatibili JLCPCB 2 strati): stanno nel .kicad_pro
import json
pro = {
    "meta": {"filename": f"{NAME}.kicad_pro", "version": 3},
    "board": {"design_settings": {
        "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2},
        "rules": {"min_clearance": 0.15, "min_copper_edge_clearance": 0.2, "min_hole_clearance": 0.2,
                  "min_hole_to_hole": 0.25, "min_through_hole_diameter": 0.3, "min_track_width": 0.15,
                  "min_via_diameter": 0.5, "min_via_annular_width": 0.1, "min_connection": 0.0,
                  "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.1,
                  "solder_mask_to_copper_clearance": 0.0},
        "track_widths": [0.0, 0.2, 0.25, 0.3, 0.5, 1.0],
        "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}],
        "diff_pair_dimensions": [{"gap": 0.0, "via_gap": 0.0, "width": 0.0}, {"gap": 0.2, "via_gap": 0.25, "width": 0.3}],
    }},
    "net_settings": {"meta": {"version": 4}, "classes": [{
        "name": "Default", "clearance": 0.15, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3,
        "diff_pair_width": 0.3, "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0,
        "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}]},
}
(OUT / f"{NAME}.kicad_pro").write_text(json.dumps(pro, indent=2))
# il land pattern Würth del dado SMT ha l'anello di rame a ridosso del foro (da datasheet): esenzione mirata
(OUT / f"{NAME}.kicad_dru").write_text(
    '(version 1)\n(rule "Dado SMT M2: anello vicino al foro"\n'
    '  (condition "A.memberOfFootprint(\'H*\') && B.memberOfFootprint(\'H*\')")\n'
    '  (constraint hole_clearance (min 0mm)))\n')

# libreria di progetto con il footprint custom del connettore ExpressCard
lib = OUT / "EC2M2.pretty"
lib.mkdir(exist_ok=True)
ecfp = pcbnew.FOOTPRINT(fps["J1"])
ecfp.SetPosition(V(0, 0)); ecfp.SetOrientationDegrees(0)
ecfp.Move(V(-EC_X0, -EC_Y))
for p in ecfp.Pads():
    p.SetNetCode(0)
pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(str(lib), ecfp)
(OUT / "fp-lib-table").write_text('(fp_lib_table\n  (version 7)\n  (lib (name "EC2M2")(type "KiCad")(uri "${KIPRJMOD}/EC2M2.pretty")(options "")(descr "ExpressCard"))\n)\n')

# BOM (formato JLCPCB: Comment, Designator, Footprint, LCSC). Codici verificati con gen/jlc_search.py
LCSC = {"C1": "C45783", "C2": "C1525", "C3": "C19702", "C4": "C19702", "R1": "C25117", "D1": "C2286",
        "L1": "C76793", "U1": "C59567", "J2": "C52766481", "H": "C5360192"}
MPN = {"J1": "ExpressCard 26P lato modulo SMT, passo 1.0 (es. Amphenol 10030570-2113LF, JAE PX10) - VERIFICARE footprint",
       "J2": "M.2 M-key H3.2 Minlenda MLD-NGFF-M-3.2H (land pattern = TE 2199230)",
       "U1": "TPS61240DRVR", "L1": "1uH 0805 1.4A 90mohm MLP2016S1R0MT0S1", "C1": "22uF 25V X5R 0805",
       "C2": "100nF 0402", "C3": "10uF 10V X5R 0603", "C4": "10uF 10V X5R 0603", "R1": "470R 0402",
       "D1": "LED rosso 0603 (Vf~2V)", "JP1": "ponticello a stagno (aperto)", "J3": "piazzole per fili saldati (niente header: non entrerebbe nello slot)",
       "H": "Wurth 9774010243R dado SMT M2 H1.0 (alt. Sinhoo SMTSO2010CTJ C2916319, verificare land)"}
import csv
with open(OUT / f"{NAME}_BOM.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Note"])
    for ref in sorted(fps):
        fp = fps[ref]
        w.writerow([fp.GetValue(), ref, fp.GetFPID().GetLibItemName().wx_str(), LCSC.get(ref.rstrip("0123456789") if ref.startswith("H") else ref, ""), MPN.get("H" if ref.startswith("H") else ref, "")])
print(pcb)
