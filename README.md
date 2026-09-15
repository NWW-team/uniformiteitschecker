# Uniformiteitschecker NederlandWereldwijd

Signaleert waar op nederlandwereldwijd.nl en netherlandsworldwide.nl van de
schrijfrichtlijnen wordt afgeweken, zodat de webredactie het niet pas hoort als
iemand het meldt.

De app **lost niets op**. Wat juist is bepaalt de redactie of een kenniseigenaar;
de app zorgt alleen dat afwijkingen zichtbaar worden. Zie [STRATEGY.md](STRATEGY.md).

## Wat er nu in zit

Ronde 1 dekt de drie sporen uit de strategie in hun kleinste bruikbare vorm:

| Spoor | Nu | Nog niet |
| --- | --- | --- |
| Content uitlezen | Sitemap uitlezen en één rubriek ophalen, per site afgebakend op URL-pad | De hele site, de interne voorlichterswebsite |
| Afwijkingen aantonen | Terminologie tegen een termenlijst, met de vindplaats erbij | Inhoudelijke tegenstrijdigheden tussen pagina's |
| Werkbaar overzicht | HTML-rapport per regel, met URL, zinsfragment en voorkeursterm | Koppeling met het redactieproces |

**De afbakening is expres klein.** `crawl` weigert te starten als er geen `paden`
in `config/sites.yaml` staan — een run die per ongeluk duizenden pagina's ophaalt
hoort niet te kunnen.

## Gebruik

```bash
pip install -e .

# 1. Welke rubrieken zijn er? Leest alleen de sitemap, haalt geen pagina's op.
python -m uniformiteitschecker verken

# 2. Zet de gekozen paden in config/sites.yaml, haal die rubriek op.
python -m uniformiteitschecker crawl --max-paginas 50

# 3. Controleer tegen de termenlijst en schrijf het rapport.
python -m uniformiteitschecker check
```

Dat levert `rapport/rapport.html` (voor de redactie) en `rapport/bevindingen.json`
(voor verdere verwerking).

### Draaien tegen de echte sites

Niet elke ontwikkelomgeving mag naar buiten. Daarom draait de crawl via GitHub
Actions: **Actions → Uniformiteitscheck → Run workflow**, eerst met stap `verken`,
daarna met `crawl+check`. Het rapport staat onder de artifacts van die run.

## Configuratie

Twee bestanden, allebei bedoeld om zonder ontwikkelaar aan te passen:

- **`config/sites.yaml`** — welke sites, welke taal, en onder `paden` welk deel van
  de site meedoet.
- **`config/termen.yaml`** — de termenlijst: per regel de voorkeursterm, de
  varianten die een signaal geven, en een toelichting die de redacteur helpt
  beoordelen. `hele_woorden: true` voorkomt dat `paspoortfoto` meetelt als
  `paspoort`.

Een regel toevoegen is een blok erbij; `python -m uniformiteitschecker check` zegt
meteen of de lijst nog klopt.

## Afspraken bij het ophalen

We lezen de website van een ander team. Daarom: `robots.txt` volgen, één verzoek
per seconde, een herkenbare User-Agent, een harde bovengrens op het aantal
pagina's, en een cache op schijf zodat opnieuw analyseren geen nieuw verkeer geeft.

## Ontwikkelen

```bash
pip install -e ".[dev]"
pytest -q
```

De tests draaien zonder netwerk: sitemaps, HTML en een mini-corpus staan als
fixtures in `tests/fixtures/`.
