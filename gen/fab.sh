#!/bin/sh
# Output di produzione per ogni variante in out/<nome>/fab (Gerber+drill zippati per JLCPCB, CPL, render)
cd "$(dirname "$0")/.."
for d in out/EC2M2_*/; do
  n=$(basename $d); f=$d/fab; rm -rf $f; mkdir -p $f/gerber
  kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --no-protel-ext -o $f/gerber $d/$n.kicad_pcb >/dev/null
  kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o $f/gerber $d/$n.kicad_pcb >/dev/null
  python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1], \"zip\", sys.argv[2])" $f/${n}_gerber $f/gerber
  kicad-cli pcb export pos --side front --format csv --units mm -o $f/${n}_CPL.csv $d/$n.kicad_pcb >/dev/null
  for s in top bottom; do
    kicad-cli pcb render --side $s --quality basic -w 900 -h 1300 -o $f/${n}_$s.png $d/$n.kicad_pcb >/dev/null 2>&1
  done
  kicad-cli pcb export pdf --layers F.Cu,F.Silkscreen,F.Fab,Edge.Cuts --mode-single --black-and-white -o $f/${n}_stampa_1a1.pdf $d/$n.kicad_pcb >/dev/null 2>&1
  echo "$n: $(ls $f | tr '\n' ' ')"
  python3 gen/jlc_files.py $d 5 10 >/dev/null 2>&1
done
