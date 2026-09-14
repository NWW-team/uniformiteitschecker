---
name: Uniformiteitschecker NederlandWereldwijd
last_updated: 2026-09-14
---

# Uniformiteitschecker NederlandWereldwijd — Strategie

## Doelprobleem

Op onze Nederlandstalige en anderstalige website (elk ca. 5000 pagina's) en de interne
voorlichterswebsite staat soms tegenstrijdige informatie of worden verschillende termen
gebruikt (paspoort vs. reisdocument, legalisation vs. legalization). Dat is voor de
webredactie niet makkelijk op te sporen: we horen het pas als iemand, meestal een collega,
het aankaart, en wie het tóch wil controleren moet afbakenen — bijvoorbeeld alleen de top 10
meest bezochte pagina's woordje voor woordje zelf lezen.

## Onze aanpak

De app kijkt naar beide soorten afwijkingen — tegen de schrijfrichtlijnen in, én inhoudelijk
tegenstrijdig — en kaart die proactief aan, maar lost ze niet zelf op. Wat juist is bepaalt de
webredactie of een kenniseigenaar; de app zorgt dat we niet langer afwachten tot het gemeld
wordt.

_Randvoorwaarden en aannames:_ we bouwen met Claude Code in de browser, code in GitHub, geen
lokale ontwikkelomgeving. Of de interne voorlichterswebsite uitgelezen mag worden is nog
onbevestigd; lukt dat niet, dan volstaan de twee publieke websites. Hosting binnen de
organisatie is niet vanzelfsprekend, dus tot toegang en toestemming rond zijn werken we met
publieke of fictieve data.

## Voor wie

**Primair:** Webredacteuren van NederlandWereldwijd — ze huren de app in om bijvoorbeeld 1x
per week te zien waar fouten zitten en deze te verbeteren, zonder zelf 10.000 pagina's te
lezen.

## Sporen

### Content uitlezen

Het ophalen en vergelijkbaar maken van content uit de bronnen: de twee publieke websites,
en de voorlichterswebsite als dat mag.

_Waarom het de aanpak dient:_ zonder uitleesbare content valt er niets te signaleren — dit is
de basis waar de rest op staat.

### Afwijkingen aantonen

Het detecteren van afwijkingen in uniformiteit en het benoemen van het soort: tegenstrijdigheid
in terminologie/schrijfrichtlijnen of een inhoudelijke tegenstrijdigheid, met de locatie/URL
erbij.

_Waarom het de aanpak dient:_ dit is de toegevoegde waarde — hier komt het signaal vandaan dat
we nu pas via een melding krijgen.

### Werkbaar overzicht voor de redactie

De manier waarop signalen bij de redacteur landen, zodat duidelijk is wat we zelf kunnen
verbeteren en wat we moeten voorleggen aan een kenniseigenaar.

_Waarom het de aanpak dient:_ de app lost niets zelf op, dus het signaal moet direct oppakbaar
zijn — anders verandert er niets aan het werk.
