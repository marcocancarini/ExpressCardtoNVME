# ExpressCard → M.2 NVMe per ThinkPad X230

Adattatore che permette di usare un SSD **M.2 NVMe 2230 o 2242** (M-key o B+M-key) nello slot **ExpressCard/54**
di un ThinkPad X230 (e in generale in uno slot ExpressCard con PCIe). È una scheda nuda, senza guscio, che si infila
direttamente nello slot.

![Vista 3D della variante 54 mm con USB](docs/img/EC2M2_54_USB5V_3d.png)

> **Stato:** progetto completo e verificato al DRC, **non ancora prodotto né provato su hardware**.
> Prima di ordinare segui la sezione *Verifiche prima dell'ordine* della [guida](GUIDA.md).

## Varianti

| Variante | Formato | USB | Note |
|---|---|---|---|
| `EC2M2_34` | ExpressCard/34 (34 × 75 mm) | no | entra in slot /34 e /54 |
| `EC2M2_34_USB5V` | ExpressCard/34 | sì, 5 V | piazzole USB in fondo alla scheda |
| `EC2M2_54` | ExpressCard/54 (a L, 54 × 75 mm) | no | più stabile nello slot /54 |
| `EC2M2_54_USB5V` | ExpressCard/54 | sì, 5 V | piazzole USB + finestra per alloggiare un piccolo ricevitore USB |

| 34 mm | 34 mm + USB | 54 mm | 54 mm + USB |
|---|---|---|---|
| ![](docs/img/EC2M2_34_top.png) | ![](docs/img/EC2M2_34_USB5V_top.png) | ![](docs/img/EC2M2_54_top.png) | ![](docs/img/EC2M2_54_USB5V_top.png) |

I connettori ExpressCard e M.2 non hanno un modello 3D in libreria: nei render compaiono solo le loro piazzole.

## Caratteristiche

- **PCIe x1** dallo slot ExpressCard al connettore M.2 (M-key, altezza 3.2 mm); coppie differenziali a **~87 Ω**
  (calcolate con un solutore di campo 2D incluso, `gen/impedance.py`).
- **Fissaggio a vite** della SSD: due dadi SMT M2 (H 1.0 mm) alle posizioni 2230 e 2242.
- **LED di attività** dell'SSD e **ponticello CLKREQ#→GND** opzionale per SSD che non vengono rilevati.
- **Versioni USB:** porta USB 2.0 dello slot portata su piazzole, con **boost 3.3 → 5 V** (TPS61240, 200 mA garantiti)
  perché lo slot ExpressCard non fornisce 5 V.
- 2 strati, spessore 1.0 mm, regole compatibili con JLCPCB; BOM con codici LCSC e file pronti per l'assemblaggio.

## Contenuto del repository

```
gen/                 generatore e strumenti
  gen_board.py       crea il PCB di una variante (API Python di KiCad 10)
  build.sh           genera le 4 varianti + DRC
  fab.sh             Gerber, drill, CPL, render, PDF 1:1, file JLCPCB
  render.sh          render 3D in docs/img
  check_nets.py      verifica la netlist contro la mappatura attesa
  impedance.py       calcolo impedenza delle coppie (richiede scipy)
  jlc_search.py      ricerca codici LCSC/JLC
  jlc_files.py       BOM/CPL formato JLC + stima costo componenti
out/<variante>/      progetto KiCad (.kicad_pcb/.kicad_pro/.kicad_dru), BOM, libreria footprint
  fab/               Gerber, drill, CPL, PDF 1:1, render rapidi
  jlcpcb/            zip Gerber, BOM e CPL per JLCPCB, stima costi
docs/img/            render
GUIDA.md             verifiche, ordine, montaggio, primo avvio
HANDOFF.md           note di progetto: pinout, scelte, calcoli
```

## Rigenerare i file

Serve KiCad 10 con le librerie footprint (`kicad-library`) e Python 3.

```sh
gen/build.sh        # genera le 4 varianti e controlla il DRC
gen/fab.sh          # file di produzione e JLCPCB
gen/render.sh       # render (serve anche kicad-library-3d)
```

Per il calcolo dell'impedenza: `python3 -m venv gen/.venv && gen/.venv/bin/pip install scipy`, poi
`gen/.venv/bin/python gen/impedance.py 0.4,0.15,0.25` (larghezza, distanza tra le piste, distanza dal GND, in mm).

## Costo indicativo

Solo componenti assemblati da JLCPCB (prezzi API, ottobre 2026): circa **$10** per 5 schede senza USB, **$17** con USB,
più il PCB, il setup dell'assemblaggio e la spedizione. Dettagli in `out/<variante>/jlcpcb/<variante>_stima.md`.
Il connettore ExpressCard non è disponibile da LCSC: va acquistato a parte e saldato a mano.
