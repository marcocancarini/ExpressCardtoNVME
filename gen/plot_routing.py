"""Salva una copia della scheda senza zone (per vedere le piste). Uso: plot_routing.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
for z in list(b.Zones()):
    b.Remove(z)
pcbnew.SaveBoard(sys.argv[2], b)
