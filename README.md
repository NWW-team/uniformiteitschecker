# Uniformiteitschecker NederlandWereldwijd

Signaleert afwijkingen in uniformiteit op de websites van NederlandWereldwijd, zodat de
webredactie niet hoeft te wachten tot een collega een tegenstrijdigheid meldt.

De checker **lost niets op**. Wat juist is bepaalt de webredactie of een kenniseigenaar;
de app zorgt alleen dat afwijkingen bovenkomen. Zie [STRATEGY.md](STRATEGY.md) voor het
waarom.

## Hoe het werkt

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

## Gebruik

Geen installatiestap nodig: Python 3.11 met `PyYAML` en `Jinja2`, verder alleen de
standaardbibliotheek.

```bash
# Ophalen, detecteren en rapport maken (eerst klein proberen kan met --limiet)
python -m checker controleer --familie consulaire-tarieven

# Opnieuw detecteren op een bestaande snapshot, zonder netwerk
python -m checker controleer --vanuit-snapshot data/snapshots/<datum>/consulaire-tarieven.jsonl

# Controleren of de site nog is zoals de app verwacht
python -m checker invarianten

# Tests (netwerkvrij)
python -m unittest discover -s tests -t .
```

Het rapport komt in `uitvoer/rapport.html` en is bedoeld om als Artifact gepubliceerd te
worden, zodat de redactie het in de browser opent en kan delen.

## Opbouw

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

## Ruis is het hoofdprobleem

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

## Status

Eerste versie: één familie (`consulaire-tarieven`), handmatig te starten. Volgende
stappen staan in het bouwplan — negeerlijst in gebruik nemen, labeldrift, een tweede
familie, terminologielexicon over de hele site, en daarna NL↔EN en semantische
tegenstrijdigheid.

Twee dingen die buiten de code geregeld moeten worden: afstemmen met de beheerder van
nederlandwereldwijd.nl voordat we structureel wekelijks 218 pagina's ophalen, en
vaststellen wie de kenniseigenaar voor consulaire tarieven is — zonder naam blijft
"voorleggen aan kenniseigenaar" een lege categorie.
