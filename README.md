# Uniformiteitschecker NederlandWereldwijd

Signaleert waar op nederlandwereldwijd.nl en netherlandsworldwide.nl van de
uniformiteit wordt afgeweken, zodat de webredactie het niet pas hoort als iemand
het meldt.

De app **lost niets op**. Wat juist is bepaalt de webredactie of een
kenniseigenaar; de app zorgt alleen dat afwijkingen zichtbaar worden. Zie
[STRATEGY.md](STRATEGY.md) voor het waarom.

## Twee ingangen

De repo bevat twee checks die elkaar aanvullen. Ze delen de strategie, maar niet
de code: ze stellen een andere vraag en hebben een andere bron van waarheid.

| | `uniformiteitschecker/` — termenlijst | `checker/` — zusterpagina's |
|---|---|---|
| Vraag | Staat er een afgeraden term op de site? | Wijkt één landenpagina af van de rest? |
| Norm | `config/termen.yaml`, door de redactie beheerd | de zusterpagina's zelf, geen externe bron nodig |
| Bereik | elke rubriek die je in `config/sites.yaml` afbakent | één familie tegelijk: `consulaire-tarieven` en `paspoort-landenpaginas` |
| Uitvoer | `rapport/rapport.html` + `rapport/bevindingen.json` | `uitvoer/rapport.html`, één tabblad per familie |

Beide draaien netwerkvrij te testen en beide melden alleen; geen van beide
schrijft iets terug naar de site.

## Spoor 1 — terminologie tegen een termenlijst

Ronde 1 dekt de drie sporen uit de strategie in hun kleinste bruikbare vorm:

| Spoor | Nu | Nog niet |
| --- | --- | --- |
| Content uitlezen | Sitemap uitlezen en één rubriek ophalen, per site afgebakend op URL-pad | De hele site, de interne voorlichterswebsite |
| Afwijkingen aantonen | Terminologie tegen een termenlijst, met de vindplaats erbij | Inhoudelijke tegenstrijdigheden tussen pagina's |
| Werkbaar overzicht | HTML-rapport per regel, met URL, zinsfragment en voorkeursterm | Koppeling met het redactieproces |

**De afbakening is expres klein.** `crawl` weigert te starten als er geen `paden`
in `config/sites.yaml` staan — een run die per ongeluk duizenden pagina's ophaalt
hoort niet te kunnen.

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

### Configuratie

Twee bestanden, allebei bedoeld om zonder ontwikkelaar aan te passen:

- **`config/sites.yaml`** — welke sites, welke taal, en onder `paden` welk deel van
  de site meedoet.
- **`config/termen.yaml`** — de termenlijst: per regel de voorkeursterm, de
  varianten die een signaal geven, en een toelichting die de redacteur helpt
  beoordelen. `hele_woorden: true` voorkomt dat `paspoortfoto` meetelt als
  `paspoort`.

Een regel toevoegen is een blok erbij; `python -m uniformiteitschecker check` zegt
meteen of de lijst nog klopt.

### Draaien tegen de echte sites

Niet elke ontwikkelomgeving mag naar buiten. Daarom draait de crawl via GitHub
Actions: **Actions → Uniformiteitscheck → Run workflow**, eerst met stap `verken`,
daarna met `crawl+check`. Het rapport staat onder de artifacts van die run.

## Spoor 2 — zusterpagina's tegen elkaar

De site bestaat grotendeels uit getemplatiseerde landenvarianten: ~218 pagina's onder
`consulaire-tarieven/<land>` die hetzelfde horen te zeggen. Daarmee vormen ze hun eigen
norm — wijkt één land af van de rest, dan is dat een signaal, zonder dat er een externe
bron van waarheid nodig is.

Twee soorten afwijking, met verschillende eigenaar:

| Soort | Voorbeeld | Wie handelt |
|---|---|---|
| `schrijfrichtlijn` | Kenia noteert `€169.15` waar de rest `€ 169,15` schrijft | webredactie: zelf verbeteren |
| `inhoudelijk` | Brazilië noemt `€ 26,00` waar 85 landen `€ 27,00` zeggen | kenniseigenaar: voorleggen |

Geld en juridische voorwaarden wijzig je niet op statistiek, dus bij een inhoudelijke
afwijking zegt de app nooit wat fout is — alleen dat het afwijkt, met het bewijs erbij.

```bash
# Ophalen, detecteren en rapport maken (eerst klein proberen kan met --limiet)
python -m checker controleer --familie consulaire-tarieven

# Opnieuw detecteren op een bestaande snapshot, zonder netwerk
python -m checker controleer --vanuit-snapshot data/snapshots/<datum>/consulaire-tarieven.jsonl

# Alleen het rapport (alle families, één tabblad per familie) opnieuw bouwen, zonder netwerk
python -m checker rapport --naar docs/index.html

# Controleren of de site nog is zoals de app verwacht
python -m checker invarianten
```

Het rapport komt in `uitvoer/rapport.html` en is bedoeld om als Artifact gepubliceerd te
worden, zodat de redactie het in de browser opent en kan delen.

### Familie `paspoort-landenpaginas`

De ~218 pagina's onder `/paspoort-id-kaart/buitenland/paspoort-<land>` volgen hetzelfde
stappenplan (checklist, extra eisen, afspraak, naar de afspraak, ophalen of laten
opsturen). Afwijken is vaak bewust, dus deze familie legt vooral vast *waar* een land
afwijkt, in vijf detectoren (`checker/detectie/stappenplan.py`):

| Detector | Vindt |
|---|---|
| `stappenplan` | ontbrekende, hernoemde, extra of verwisselde stappen; pagina's zonder stappenplan |
| `uitklapparagrafen` | een uitklapper die op vrijwel elke pagina staat maar hier ontbreekt of anders heet |
| `koppenstructuur` | h3 waar h4 de norm is, uitklaptitels op een ander niveau, overgeslagen niveaus, tweede h1 |
| `standaardzinnen` | zinnen die vrijwel overal letterlijk staan maar hier ontbreken of afwijken |
| `kernbeweringen` | inhoudelijke keuzes die tegenstrijdig kunnen zijn: originelen of kopieën, verwerkingstijd, ophaaltermijn, ... |

Wat een pagina "beweert" staat in `regels/kernbeweringen.yaml`; een regel toevoegen is een
blok YAML. Structuurafwijkingen komen in de groep *Beoordelen: bewust of niet?*, omdat het
juiste antwoord er niet uit de zusterpagina's volgt.

### Opbouw

Drie sporen, gekoppeld via twee datacontracten op schijf. Spoor 1 kent geen regels,
spoor 2 kent geen HTTP, spoor 3 kent geen HTML — daardoor zijn detectie en rapportage
volledig offline te ontwikkelen tegen een gecommitte snapshot.

```
checker/bronnen/    spoor 1: sitemap, ophalen, <main> en tabellen uitlezen  -> Pagina
checker/detectie/   spoor 2: normaliseren en zusterpagina's vergelijken     -> Bevinding
checker/rapport/    spoor 3: bevindingen -> klikbaar overzicht
regels/             families, drempels en de negeerlijst (data, geen code)
data/snapshots/     genormaliseerde pagina's per run (in git: klein en diffbaar)
tests/fixtures/     echte pagina's, ingekort tot <main>; tests raken het netwerk niet
```

Ruwe HTML gaat **niet** de repo in (staat in `.cache/`, opnieuw op te halen). De
genormaliseerde snapshot wél: die is klein, diffbaar, en maakt runs reproduceerbaar.

### Ruis is het hoofdprobleem

Een checker die de redactie niet vertrouwt, wordt niet gebruikt. Een naïeve vergelijking
gaf in de verkenning ~90 "tegenstrijdigheden" waarvan er één echt was. Wat dat oplost:

- **Normaliseren vóór vergelijken.** `€169.15`, `€ 169,15` en `169,15` zijn hetzelfde
  bedrag. Notatieverschillen worden apart gemeld als schrijfrichtlijn, niet als
  tegenstrijdigheid — zo verdwijnt het signaal niet, maar overstemt het ook niets.
- **Drempels.** Minimaal 5 zusterpagina's met dezelfde rij, en minimaal 80% eensgezind.
  Een familie die in twee kampen verdeeld is, is variatie en geen fout.
- **Bundelen.** Eén bevinding per rij of per pagina, nooit één per regel in een tabel.
  Op de Kenia-pagina staan 32 bedragen in afwijkende notatie: dat is één correctie.
- **Zwakke signalen weglaten.** Ontbrekende rijen worden niet gemeld: Duitsland mist alle
  visumrijen omdat het Schengen is, en 48% van de landenpagina's heeft geen tarieftabel.
- **Bewijs meegeven.** Elke bevinding toont de waarde op zusterpagina's, zodat
  verifiëren tien seconden kost. Vertrouwen komt uit controleerbaarheid.

## Signalen achter een inlog

De pagina in `docs/index.html` bevat zelf **geen signalen**. De bovenkant (titel, uitleg,
methode) is openbaar; de signalen staan in Supabase en worden pas opgehaald nadat iemand
is ingelogd. Zo staat er niets in de broncode van de pagina.

```bash
python -m checker rapport --beveiligd --naar docs/index.html   # pagina met inlog
python -m checker publiceer                                     # signalen naar de database
```

- **Inloggen**: één gezamenlijke inlog voor het team (Supabase Auth, e-mail en
  wachtwoord). Meerdere mensen kunnen tegelijk ingelogd zijn en werken.
- **Wie er in mag**: alleen e-mailadressen in de tabel `teamleden`. Dat geldt ook als
  iemand toch een account zou kunnen aanmaken.
- **Publiceren** kan alleen met de geheime servicesleutel, in de omgevingsvariabele
  `SUPABASE_SERVICE_KEY` (of het GitHub-geheim met dezelfde naam, voor de workflow
  *Signalen publiceren*). Die sleutel hoort nooit in de repo.
- `config/supabase.yaml` bevat alleen de URL en de publishable key; die horen in de
  pagina te staan.
- De tabel `afvinkingen` is klaar voor het markeren van bevindingen als opgelost; elk
  bevinding heeft een vaste `data-id` in de pagina.

Let op: `data/findings/` en `data/snapshots/` staan in git. Is de repo openbaar, dan zijn de
signalen daar alsnog te lezen.

## Huisstijl

Beide rapporten gebruiken de [Rijkshuisstijl Community](https://github.com/nl-design-system/rijkshuisstijl-community),
de implementatie van de Rijkshuisstijl op de NL Design System-architectuur, op dezelfde
manier als [social-media-postmaker](https://github.com/NWW-team/social-media-postmaker):
de officiële bestanden worden meegeleverd, niet nagebouwd.

- `huisstijl/vendor/` — onveranderd uit npm: design tokens (lintkleur hemelblauw),
  componenten-CSS (`utrecht-*`/`rhc-*`: link, tabel, tekstveld) en Fira Sans. Herkomst,
  versies en licenties staan in `huisstijl/vendor/LEESMIJ.md`.
- `huisstijl/rapport.css` — alleen de indeling van het rapport, uitsluitend op
  `--rhc-*`-tokens.
- `huisstijl/__init__.py` voegt alles (lettertype als base64) samen tot één stijlblok dat
  in het rapport wordt ingelijnd, zodat een rapport één zelfstandig HTML-bestand blijft
  zonder CDN. De tokens staan op de klasse `hemelblauw`, die op `<body>` moet staan.

Een andere lintkleur is een ander tokenbestand uit `@rijkshuisstijl-community/design-tokens`
plus een andere klasse (`THEMA_KLASSE`). Het huisstijllettertype RijksSansVF zit er wel in (`huisstijl/vendor/fonts/`), met Fira Sans als
terugval. Het is licentieplichtig en alleen bedoeld voor medewerkers van de Rijksoverheid:
deel de repo en de rapporten dus niet daarbuiten.

## Afspraken bij het ophalen

We lezen de website van een ander team. Daarom: `robots.txt` volgen, één verzoek
per seconde, een herkenbare User-Agent, een harde bovengrens op het aantal
pagina's, en een cache op schijf zodat opnieuw analyseren geen nieuw verkeer geeft.

## Ontwikkelen

```bash
pip install -e ".[dev]"
pytest -q
```

`pytest` draait beide sporen: de pytest-tests van de termenlijstcheck en de
unittest-tests van de zusterpaginacheck. De tests raken het netwerk niet —
sitemaps, HTML, een mini-corpus en ingekorte landenpagina's staan als fixtures in
`tests/fixtures/`.

## Status

Spoor 2 heeft twee families (`consulaire-tarieven` en `paspoort-landenpaginas`),
handmatig te starten, en een rapport met een tabblad per familie. Volgende stappen staan in het bouwplan — negeerlijst in gebruik nemen,
labeldrift, meer families, terminologielexicon over de hele site, en daarna NL↔EN en
semantische tegenstrijdigheid.

Twee dingen die buiten de code geregeld moeten worden: afstemmen met de beheerder van
nederlandwereldwijd.nl voordat we structureel wekelijks 218 pagina's ophalen, en
vaststellen wie de kenniseigenaar voor consulaire tarieven is — zonder naam blijft
"voorleggen aan kenniseigenaar" een lege categorie.
