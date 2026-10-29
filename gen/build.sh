#!/bin/sh
# Genera le 4 varianti e riassume il DRC. Uso: gen/build.sh [variante...]  (es. "34 nousb")
cd "$(dirname "$0")/.."
[ $# -eq 0 ] && set -- "34 nousb" "34 usb5v" "54 nousb" "54 usb5v"
for v in "$@"; do
  set -- $v
  n="EC2M2_$1"; [ "$2" = usb5v ] && n="${n}_USB5V"
  python3 gen/gen_board.py $1 $2 out/$n >/dev/null || exit 1
  kicad-cli pcb drc --format json --severity-error --refill-zones -o out/$n/drc.json out/$n/$n.kicad_pcb >/dev/null 2>&1
  python3 gen/drc_summary.py out/$n/drc.json "$n"
done
