# ExpressCard → M.2 NVMe (ThinkPad X230) — note di progetto

Generatore: `gen/gen_board.py` (API pcbnew KiCad 10) → `out/<variante>/`.
Varianti: {34mm, 54mm} × {senza USB, USB 5V}. Niente USB a 3.3V.

## Flusso
- `gen/build.sh [“34 nousb” …]` genera le varianti e riassume il DRC (`gen/drc_summary.py`).
- `gen/fab.sh` → `out/<variante>/fab/`: Gerber+drill zip (JLCPCB), CPL, render, PDF 1:1.
- `gen/check_nets.py <pcb>` verifica la netlist contro la mappatura attesa.
- `gen/impedance.py w,s,g` solutore 2D quasi-statico (serve `gen/.venv`, con scipy).
- `gen/jlc_search.py "keyword"` ricerca codici LCSC/JLC (giacenza, base/estesa).
- `gen/plot_routing.py` copia senza zone, per vedere le piste in SVG/PNG.

## Pinout ExpressCard (lato modulo)
1 GND, 2 USBD-, 3 USBD+, 4 CPUSB#, 5-6 RSVD, 7 SMBCLK, 8 SMBDATA, 9-10 +1.5V,
11 WAKE#, 12 +3.3VAUX, 13 PERST#, 14-15 +3.3V, 16 CLKREQ#, 17 CPPE#,
18 REFCLK-, 19 REFCLK+, 20 GND, 21 PERn0, 22 PERp0, 23 GND, 24 PETn0, 25 PETp0, 26 GND.
Lo slot non fornisce 5V → la versione USB ha un boost 3.3→5V a bordo.

## Mappatura verso M.2 M-key (diretta, niente condensatori AC: stanno su host e SSD)
PERn0 21→41, PERp0 22→43, PETn0 24→47, PETp0 25→49, REFCLK- 18→53, REFCLK+ 19→55,
PERST# 13→50, CLKREQ# 16→52 (+ JP1 a stagno opzionale verso GND), +3.3V 14,15 → 2,4,12,14,16,18,70,72,74.
LED attività: pin 10 (DAS/DSS#, open-drain) → LED rosso + 470Ω verso 3V3.
CPPE# 17 → GND (sempre). CPUSB# 4 → GND solo nelle versioni USB.
M.2 pad 51 (GND) NC: chiuso tra PETp0 e REFCLK-; la SSD ha comunque gli altri GND.

### Segnali lasciati scollegati (valutati)
- WAKE# (EC 11 ↔ M.2 54): l'host lo tira su a 3.3VAUX; la SSD è alimentata solo dal +3.3V principale, quindi a slot
  spento il pull-up alimenterebbe l'SSD spenta attraverso il pin (back-powering). Il wake da storage non serve → NC.
- SMBus (EC 7/8 ↔ M.2 40/42/44): lato M.2 è a 1.8V, lato ExpressCard a 3.3V(AUX): servirebbe un traslatore di livello;
  usato solo per gestione NVMe-MI → NC.
- +1.5V, +3.3VAUX, PEDET 69, SUSCLK 68, linee PCIe 1-3: NC.

## Meccanica / orientamento
- Lato componenti = lato rivolto VERSO IL BASSO nel portatile; sul lato B la serigrafia "QUESTO LATO IN ALTO".
- Vista lato componenti, connettore EC in alto: pin 1 a sinistra; nella 54mm la parte larga sporge a sinistra.
  DA VERIFICARE sul connettore reale (PDF 1:1) prima dell'ordine.
- Connettore EC lato modulo: 26 pin, fila singola, passo 1.0mm, SMT. Footprint custom (`EC2M2.pretty`):
  pad 0.7x2.0, bordo PCB 1.25mm davanti al centro pad, corpo ±13.35mm che sporge 5mm, linguette laterali.
- 34mm di larghezza; 54mm a L con tratto stretto da 34mm lungo 26mm (scelta conservativa); lunghezza 70mm, a filo con lo slot (SSD 2242 + dado finiscono a ~62mm: minimo pratico ~63mm, ma sotto 70 la scheda sparisce nello slot).
- M.2: footprint TE_M.2_M_2x38-1MP_P0.5mm, non ruotato, vicino al connettore EC; SSD verso il retro.
  Il land pattern consigliato del Minlenda MLD-NGFF-M-3.2H (C52766481) coincide (file a 7.55mm, pioli a ±10mm).
  Fondo SSD a 1.25±0.10mm dal PCB (datasheet MLD).
- Ordine coppie: EC (sx→dx) REF, PER, PET; M.2 (sx→dx) PER, PET, REF → REFCLK passa su B.Cu (2 via/linea).
- Fissaggio SSD: dadi SMT M2 Würth 9774010243R (H1.0, C5360192) a 30 e 42mm dal bordo contatti SSD.
  Il centro dell'intaglio della SSD = fine della scheda. Bordo contatti stimato a CY-2.5 (tolleranza dell'intaglio ±0.75mm).
  H1.0 < 1.25 → il dado 2230 non tocca una 2242: si montano entrambi.
- Spessore 1.0mm, 2 strati. Altezza: SSD max ~3.85mm sopra il PCB + 1.0 → ~4.85mm.

## Impedenza (gen/impedance.py, validato su microstrip nota: errore ~3%)
Stackup: 2 strati 1.0mm, h≈0.93mm, er 4.5, rame 35µm, solder mask 15µm.
- Prima: w0.30/s0.20/g0.25 → Zdiff ≈ 103Ω.
- Ora: w0.40/s0.15/g0.25 → Zdiff ≈ 87Ω, Zcm ≈ 50Ω (PCIe 85Ω, USB 90Ω: entrambe entro ±10%).
  Collo di ~1mm a w0.3/passo 0.5 sui pad M.2. Dove manca il pour laterale Zdiff sale a ~95Ω.
- Limiti noti: REFCLK su B.Cu attraversa il piano GND sotto PER/PET; impedenza non controllata dal fornitore.

## USB 5V
TPS61240DRVR (C59567): 5V fissi, 200mA garantiti, load disconnect; L 1µH 1.4A (C76793), CIN/COUT 10µF.
3V3 portato su B.Cu lungo il lato sinistro fino alla via d'ingresso del blocco. Boost (U1, L1, C3, C4) nella striscia
libera a sinistra della SSD (x≈6–10, y≈56–68), stessa disposizione relativa ruotata di 90° (funzione G in gen_board.py).
J3 = 4 piazzole passo 2.54 per fili saldati (niente header: non entra nello slot):
34mm in colonna sul lato sinistro (G,+,-,5V); 54mm sopra la finestra 13x28mm (5V,-,+,G).
J4 = piazzola 3V3 separata (34mm sotto J3, 54mm a destra di J3), collegata al 3V3 su B.Cu.

## Astuccio 3D (gen/enclosure.py → out/enclosure/)
Guscio nello slot non fattibile: slot 5.0mm, scheda+SSD ~4.85mm. Fatto invece un astuccio a manicotto per trasporto:
interno (W+0.8) x 70.8 x 6.0mm, pareti 1.6, fondo/coperchio 1.2, tacche per le dita, dentini 0.35mm. Stampa in piedi.
Budget: slot 3.3V ~1.3A totali tra SSD e USB.

## BOM / LCSC (verificati con gen/jlc_search.py)
C1 C45783, C2 C1525, C3/C4 C19702, R1 C25117, D1 C2286, L1 C76793, U1 C59567, J2 C52766481, H1/H2 C5360192.
J1 (connettore ExpressCard) non disponibile da LCSC: da acquistare a parte e saldare a mano.

## Da fare prima dell'ordine
- Verificare il connettore EC reale (pad, pin 1, battuta) con il PDF 1:1.
- Verificare la posizione dei dadi: inserire la SSD nel connettore e misurare piolo M.2 → centro intaglio.

## Preventivo / ordine JLCPCB
`gen/fab.sh` → `out/<variante>/jlcpcb/`: `_gerber.zip` (senza mappe di foratura), `_BOM_JLC.csv`, `_CPL_JLC.csv`,
`_stima.md` (costo componenti da API JLC, con scarto e acquisto minimo). DNP: J1 (connettore EC), J3, J4, JP1.
Parametri PCB: 2 strati, 1.0mm, min traccia/spazio 0.15, min foro 0.3, finitura ENIG consigliata (passo 0.5 del M.2).
In anteprima PCBA controllare la rotazione/polarità di U1 (pin 1), D1 (catodo) e J2.
