# Kje Groverjev algoritem preneha delovati na IBM Heron?

Seminarska naloga pri predmetu NPMP (skupina 16). Groverjev algoritem za *n* = 2…6 kubitov
poženemo na idealnem simulatorju, na digitalnih dvojčkih, zgrajenih iz kalibracijskih podatkov,
in na kvantnem procesorju IBM `ibm_marrakesh` (Heron). Iščemo prag *n*\*, pri katerem verjetnost
uspeha pade pod dvakratnik naključnega ugibanja, in preverimo, ali ga dvojčki napovejo.

## Vsebina

| pot | opis |
|---|---|
| `grover_ibm.ipynb` | zvezek s celotnim potekom: vezja, pošiljanje na QPU, simulacije, povzetek in grafi |
| `grover_ibm.py` | pomožne funkcije: Groverjevo vezje, dvojčki (`NoiseModel.from_backend` + razporejanje), metrike |
| `slike.py` | iz `results/` nariše slike poročila v `porocilo/Skupina16/img/` in izpiše vrednosti za tabele |
| `calibration/` | kalibracijski CSV-ji, preneseni s platforme IBM Quantum (uporabljeni v zagonih) |
| `results/` | rezultati treh zagonov na QPU (glej spodaj) |
| `porocilo/` | LaTeX predloga zbornika s poglavjem `Skupina16/`; `g16.pdf` je prevedeno poglavje |
| `prosojnice/` | prosojnice za predstavitev (Beamer) |
| `requirements.txt` | različice paketov |

## Namestitev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Za dostop do procesorja ustvarite datoteko `.env` (v tem ali nadrejenem direktoriju) z API ključem
IBM Quantum:

```
IBM_KEY=<vaš API ključ>
```

Brez nje se uporabi račun, shranjen s `QiskitRuntimeService.save_account(...)`.
Datoteka `.env` ni v repozitoriju.

## Ponovitev poskusov

Zvezek odprite z jedrom iz `.venv`. Celice so neodvisni koraki; v razdelku 1 poženite **eno** od
celic *nova vezja* ali *shranjena vezja*.

**Nov zagon (porabi čas na QPU):**

1. S platforme IBM Quantum prenesite svež kalibracijski CSV za `ibm_marrakesh` v `calibration/`.
2. Poženite razdelke 0 → 1 (*nova vezja*, **ne** *shranjena vezja*) → 2 (*pošlji nalogo*) → 3 → 4 → 5.
   *Nova vezja* shrani vezja, meta podatke in posnetek žive kalibracije pod novo oznako `TAG`.

**Analiza obstoječega zagona (brez QPU):** v celici *shranjena vezja* vpišite oznako (npr.
`20261122-184732`), nato poženite *naloži nalogo*, *rezultat*, simulacije in povzetek.

## Zagoni na QPU

Vsi zagoni: `ibm_marrakesh`, 10 000 ponovitev na vezje, 10 vezij v eni nalogi
(*n* = 2…6, optimizacijski stopnji transpilerja 1 in 3).

| oznaka | job ID | opomba |
|---|---|---|
| `20261122-012230` | `dc13bvqnj2vs73der8b0` | stopnji 1 in 3 izbereta kubite neodvisno |
| `20261122-015016` | `dc13ouds2omc738a4g90` | skupna postavitev kubitov za obe stopnji |
| `20261122-184732` | `dc1ilganj2vs73dfdb8g` | glavni zagon: skupna postavitev, posnetek žive kalibracije, vsi dvojčki z upoštevanim čakanjem |

V prvih dveh zagonih je `twin_backend` še star dvojček (`AerSimulator.from_backend` brez čakanja);
za primerjavo dvojčkov uporabite zadnji zagon.

Datoteke posameznega zagona v `results/`:

| datoteka | vsebina |
|---|---|
| `<TAG>_circuits.qpy` | prevedena vezja, kot so bila poslana na QPU |
| `<TAG>_meta.json` | oznaka procesorja, ponovitve, ciljna stanja, postavitve, lastnosti vezij, poti do kalibracije, job ID |
| `<TAG>_live_calibration.csv` | posnetek žive kalibracije ob gradnji vezij (samo zadnji zagon) |
| `<TAG>_qpu_counts.json` | štetja z QPU |
| `<TAG>_counts.json` | štetja vseh virov (idealno, dvojčki, QPU) |
| `<TAG>_summary.csv` | P(označeno stanje) in uteženi Jaccard po virih |

## Dvojčki

Vsi uporabljajo `NoiseModel.from_backend` (Qiskit Aer) na vezjih, razporejenih z ALAP, tako da
kubiti med čakanjem dekoherirajo (ukaz `delay`). Razlikujejo se samo po izvoru kalibracije:

| vir | kalibracija |
|---|---|
| `twin_backend` | posnetek žive kalibracije ob gradnji vezij |
| `twin_csv` | CSV s platforme IBM |
| `twin_fake` | `FakeMarrakesh` iz `qiskit_ibm_runtime` (starejši posnetek) |
| `twin_csv_noidle` | kontrola: `twin_csv` brez čakanja |

## Poročilo in prosojnice

```bash
python slike.py                 # slike iz results/ v porocilo/Skupina16/img/
cd porocilo
latexmk -pdf g16.tex            # samo poglavje skupine 16 (g16.pdf)
latexmk -pdf editor.tex         # celoten zbornik
cd ../prosojnice
latexmk -pdf prosojnice.tex
```

Potrebni paketi (Debian/Ubuntu): `texlive-latex-extra texlive-science texlive-lang-european
texlive-fonts-recommended latexmk`.
