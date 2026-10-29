# Guida: dalla verifica al primo avvio

## 1. Scegli la variante

- **34 mm:** entra in qualsiasi slot ExpressCard (/34 e /54).
- **54 mm:** solo slot /54 (come quello dell'X230); la parte larga la rende più stabile.
- **USB 5V:** solo se vuoi collegare un piccolo dispositivo USB (per esempio un ricevitore wireless) che resta dentro
  il portatile. Il boost fornisce 200 mA garantiti; lo slot dà circa 1.3 A in tutto sul 3.3 V, condivisi con l'SSD.

## 2. Verifiche prima dell'ordine

Il progetto non è ancora stato provato su hardware. Queste verifiche costano poco ed evitano schede da buttare.

1. **Connettore ExpressCard (J1).** Procurati il connettore lato scheda: 26 pin, fila singola, passo 1.0 mm, SMT.
   Stampa `out/<variante>/fab/<variante>_stampa_1a1.pdf` **al 100%**, senza adattare alla pagina, e controlla con un
   righello che il passo dei pad sia 1.0 mm. Appoggia il connettore sulla stampa e verifica:
   - che i piedini coincidano con i 26 pad;
   - che il corpo stia nell'incavo davanti al bordo scheda;
   - **l'orientamento del pin 1:** guardando il lato componenti con il connettore in alto, il pin 1 (GND) è a sinistra.
     Con l'orientamento sbagliato i 3.3 V finirebbero sui segnali.
2. **Posizione dei dadi M2.** Inserisci la SSD nel connettore M.2 appoggiato sul tavolo e misura la distanza fra il
   centro dei pioli del connettore e il centro dell'intaglio della SSD. Confrontala con la stampa: l'intaglio tollera
   circa ±0.75 mm.
3. **Connettore M.2.** Se non usi il Minlenda MLD-NGFF-M-3.2H, verifica che il connettore abbia il land pattern
   standard TE (2 file distanti 7.55 mm, pioli a ±10 mm) e un'altezza di 3.2 mm.

## 3. Ordine su JLCPCB

File in `out/<variante>/jlcpcb/`.

1. Vai su jlcpcb.com → *Order now* → **Add gerber file**: carica `<variante>_gerber.zip`.
2. Parametri PCB:
   - Layers **2**, PCB Thickness **1.0 mm**;
   - Surface Finish **ENIG** (consigliata per il passo 0.5 mm del M.2; HASL funziona ma è meno piana);
   - il resto ai valori predefiniti; le regole del progetto (piste e spazi 0.15 mm, fori 0.3 mm) rientrano nello standard.
   - La scheda 54 mm è a L: il prezzo si calcola sull'ingombro 54 × 75 mm.
3. **PCB Assembly** → lato **Top**. Carica `<variante>_BOM_JLC.csv` e `<variante>_CPL_JLC.csv`.
4. Nell'anteprima dei componenti controlla:
   - **U1** (TPS61240): il punto del pin 1 deve coincidere con il segno sul PCB;
   - **D1** (LED): il catodo deve stare verso il pad collegato al connettore M.2;
   - **J2** (M.2): le due file di contatti devono coincidere con le piazzole.
   Se qualcosa è ruotato di 90° o 180°, correggilo direttamente nell'anteprima.
5. Restano fuori dall'assemblaggio (DNP): **J1** (connettore ExpressCard), **J3** (piazzole USB), **JP1** (ponticello a
   stagno). La stima dei costi è in `<variante>_stima.md`.

## 4. Montaggio a mano

1. **J1, connettore ExpressCard:** allinealo con il corpo nell'incavo frontale e i piedini centrati sui pad. Fissa un
   piedino per lato, controlla l'allineamento, poi salda gli altri. Usa flussante e, se si formano ponti, rimuovili con
   la treccia dissaldante.
2. **Controllo con il tester**, prima di inserire nulla nel portatile:
   - nessun corto tra 3.3 V (pad 14/15 di J1) e GND (pad 1/26);
   - continuità tra i pad PCIe di J1 e quelli del connettore M.2.
3. **USB (solo varianti USB):** salda i fili del dispositivo direttamente sulle piazzole J3, rispettando le sigle
   5V, −, +, G stampate sulla scheda. Niente header verticale: non entrerebbe nello slot.
4. **JP1** resta aperto. Chiudilo con una goccia di stagno solo se l'SSD non viene rilevato (vedi sotto).
5. **SSD:** inseriscila inclinata nel connettore M.2, abbassala e fissala con una vite M2 × 2–3 mm nel dado della sua
   lunghezza (2230 o 2242).

## 5. Primo avvio sull'X230

- Il lato con i componenti va rivolto **verso il basso**: sul lato superiore c'è scritto "QUESTO LATO IN ALTO".
- Inserisci la scheda a portatile spento.
- Su Linux:
  ```sh
  lspci -nn | grep -i -E "nvme|non-volatile"   # l'SSD deve comparire
  sudo lspci -vv -s <indirizzo> | grep LnkSta  # velocità e larghezza del link negoziato
  sudo nvme list                                # oppure: lsblk
  ```
- La velocità è limitata dalla singola linea PCIe dello slot: circa 250 MB/s a 2.5 GT/s, circa 500 MB/s a 5 GT/s.
- Il BIOS dell'X230 non supporta l'avvio da NVMe: l'SSD funziona come disco dati. Per avviare il sistema da lì serve un
  bootloader su un altro disco.

## 6. Se qualcosa non va

| Sintomo | Cosa provare |
|---|---|
| SSD non rilevato | Riavvia con la scheda già inserita. Chiudi **JP1** (CLKREQ# a GND, clock sempre attivo). |
| Il portatile si spegne o lo slot si disattiva | Consumo eccessivo: alcuni SSD hanno picchi alti. Prova un SSD 2230 a basso consumo e scollega l'USB. |
| Dispositivo USB non visto | Verifica i 5 V tra i pad 5V e G a portatile acceso; controlla D− e D+ (non invertirli). |
| Il LED non si accende | È normale con alcuni SSD: il segnale di attività sul pin 10 è opzionale. |

## 7. Modificare il progetto

Tutti i parametri sono in testa a `gen/gen_board.py`: dimensioni, posizioni dei connettori, geometria delle coppie
(`DP_W`, `DP_GAP`), posizione stimata della SSD (`CARD_EDGE`). Dopo ogni modifica:

```sh
gen/build.sh && gen/fab.sh && gen/render.sh
python3 gen/check_nets.py out/EC2M2_34/EC2M2_34.kicad_pcb
```

Le scelte di progetto e i calcoli sono documentati in [HANDOFF.md](HANDOFF.md).
