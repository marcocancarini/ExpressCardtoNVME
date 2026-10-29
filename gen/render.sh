#!/bin/sh
# Render 3D in docs/img. Serve la libreria 3D KiCad: pacchetto kicad-library-3d oppure KICAD10_3DMODEL_DIR=<cartella>.
cd "$(dirname "$0")/.."
mkdir -p docs/img
for d in out/EC2M2_*/; do
  v=$(basename $d); p=$d/$v.kicad_pcb
  kicad-cli pcb render --side top --quality high --background opaque -w 1200 -h 1600 -o docs/img/${v}_top.png $p >/dev/null 2>&1
  kicad-cli pcb render --side bottom --quality high --background opaque -w 1200 -h 1600 -o docs/img/${v}_bottom.png $p >/dev/null 2>&1
  kicad-cli pcb render --side top --perspective --rotate "-35,0,25" --zoom 0.9 --quality high --background opaque \
    -w 1600 -h 1200 -o docs/img/${v}_3d.png $p >/dev/null 2>&1
done
for f in docs/img/*.png; do magick $f -trim +repage -bordercolor white -border 20 $f; done
ls docs/img
