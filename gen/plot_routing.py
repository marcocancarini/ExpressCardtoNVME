"""Saves a copy of the board without zones (to see the traces). Usage: plot_routing.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
for z in list(b.Zones()):
    b.Remove(z)
pcbnew.SaveBoard(sys.argv[2], b)
