"""Landenpagina's met een vast stappenplan met elkaar vergelijken.

De pagina's onder `/paspoort-id-kaart/buitenland/paspoort-<land>` volgen hetzelfde
stappenplan (checklist, extra eisen, afspraak, naar de afspraak, ophalen of laten
opsturen). Afwijken mag: een land met één post heeft geen stad-uitklappers, Duitsland
is Schengen. Deze detectoren zeggen daarom niet wat fout is, maar leggen vast *waar* een
land afwijkt van wat de meeste zusterpagina's doen, zodat de redactie kan beoordelen of
dat bewust is.

Vijf detectoren, allemaal met dezelfde norm als de rest van de checker (wat minstens
`min_eensgezind` van de zusters zegt) en dezelfde bundeling (één bevinding per
afwijking, met alle landen erin):

    stappenplan       ontbrekende, extra of verwisselde stappen (h2)
    uitklapparagrafen ontbrekende of anders genoemde uitklappers binnen een stap
    koppenstructuur   h3 waar h4 hoort, overgeslagen kopniveaus, tweede h1
    standaardzinnen   zinnen die vrijwel overal staan maar hier ontbreken of afwijken
    kernbeweringen    inhoudelijke keuzes uit `regels/kernbeweringen.yaml`
"""

from __future__ import annotations

import difflib
import pathlib
import re
from collections import Counter, defaultdict
from typing import Iterable

import yaml

from ..model import (
    SOORT_INHOUDELIJK,
    SOORT_SCHRIJFRICHTLIJN,
    SOORT_STRUCTUUR,
    Bevinding,
    Pagina,
    Sectie,
    bepaal_eigenaar,
)

REGEL_STAPPEN = "stappenplan"
REGEL_UITKLAPPERS = "uitklapparagrafen"
REGEL_KOPPEN = "koppenstructuur"
REGEL_ZINNEN = "standaardzinnen"
REGEL_BEWERINGEN = "kernbeweringen"

CAT_STAPPEN = "Opbouw van het stappenplan"
CAT_UITKLAPPERS = "Ontbrekende of afwijkende uitklapparagrafen"
CAT_KOPPEN = "Koppenstructuur"
CAT_ZINNEN = "Afwijkingen van standaardteksten"
CAT_BEWERINGEN = "Inhoudelijk mogelijk tegenstrijdig"

MIN_ZUSTERS = 5
MIN_EENSGEZIND = 0.8
AANTAL_BEWIJS = 3

# Zo veel koppen vergelijken we als "dezelfde titel": bijna-gelijke titels zijn een
# afwijkende schrijfwijze, geen andere uitklapper.
GELIJKENIS_TITEL = 0.8
GELIJKENIS_ZIN = 0.6

BEWERINGEN_PAD = pathlib.Path("regels/kernbeweringen.yaml")

_STAPNUMMER = re.compile(r"^stap\s*\d+\s*[:.\-–]?\s*", re.I)
_LEESTEKENS = re.compile(r"[^\w\s<>]", re.U)


# --- hulpfuncties ----------------------------------------------------------------


def landnaam(pagina: Pagina) -> str:
    """Het land uit de h1 ("... als u in Duitsland woont"), anders de URL-sleutel."""
    m = re.search(r"\bals u in (.+?) woont\b", pagina.titel) or re.search(
        r"\bin (.+?) woont\b", pagina.titel
    )
    return m.group(1) if m else pagina.familie_sleutel


def normaliseer_titel(tekst: str, land: str = "") -> str:
    """Sleutel waarop koppen van zusterpagina's aan elkaar gekoppeld worden.

    De landnaam wordt vervangen door `<land>` ("Afspraak in Duitsland" en "Afspraak in
    Brazilië" zijn dezelfde kop), en `Stap 3:` valt weg omdat de nummering meebeweegt
    met ontbrekende stappen.
    """
    if land:
        tekst = re.sub(re.escape(land), "<land>", tekst, flags=re.I)
    tekst = _STAPNUMMER.sub("", tekst.strip())
    return " ".join(_LEESTEKENS.sub(" ", tekst).casefold().split())


def _afkappen(tekst: str, maximum: int = 110) -> str:
    tekst = " ".join(tekst.split())
    return tekst if len(tekst) <= maximum else tekst[: maximum - 1].rstrip() + "…"


def _bevinding(
    *,
    regel_id: str,
    soort: str,
    categorie: str,
    titel: str,
    sleutel: str,
    afwijkend: list[tuple[Pagina, str]],
    zusters: list[tuple[Pagina, str]],
    eens: int,
    n: int,
    toelichting: str,
    actie: str,
    elders: str = "",
) -> Bevinding:
    """Eén bevinding met alle afwijkende pagina's erin, in het formaat dat het rapport kent."""
    afwijkend = sorted(afwijkend, key=lambda v: v[0].url)
    return Bevinding(
        regel_id=regel_id,
        soort=soort,
        eigenaar=bepaal_eigenaar(soort),
        categorie=categorie,
        titel=titel,
        urls=[p.url for p, _ in afwijkend],
        # De locatie bevat bewust niet de afwijkende landen: de vingerafdruk blijft dan
        # gelijk als één land is verbeterd.
        locatie={"familie": afwijkend[0][0].familie, "sleutel": sleutel},
        waargenomen=" | ".join(f"{p.familie_sleutel}: {w}" for p, w in afwijkend),
        elders=elders,
        zusters=[
            {"url": p.url, "variant": p.familie_sleutel, "waarde": w}
            for p, w in sorted(zusters, key=lambda v: v[0].url)[:AANTAL_BEWIJS]
        ],
        telling={"n": n, "eens": eens, "afwijkend": len(afwijkend)},
        voorgestelde_actie=actie,
        zekerheid="hoog" if len(afwijkend) == 1 else "middel",
        toelichting=toelichting,
    )


def _stappen(pagina: Pagina) -> list[tuple[str, str]]:
    """De stappen (h2) van een pagina in volgorde, als (sleutel, titel)."""
    land = landnaam(pagina)
    gezien: dict[str, str] = {}
    for s in pagina.secties:
        if s.stap:
            gezien.setdefault(normaliseer_titel(s.stap, land), s.stap)
    return list(gezien.items())


def _zonder_nummer(titel: str) -> str:
    """De stapkop zonder "Stap 3:", voor gebruik in een titel of zin."""
    return _STAPNUMMER.sub("", titel.strip())


def _uitklappers(pagina: Pagina) -> dict[tuple[str, str], Sectie]:
    """De uitklappers van een pagina, op (stapsleutel, titelsleutel)."""
    land = landnaam(pagina)
    return {
        (normaliseer_titel(s.stap, land), normaliseer_titel(s.titel, land)): s
        for s in pagina.secties
        if s.titel
    }


def _gelijkenis(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _norm_stappen(
    paginas: list[Pagina], min_eensgezind: float
) -> tuple[list[str], dict[str, str], dict[str, list[tuple[str, str]]]]:
    """De norm-reeks van stappen: (sleutels op volgorde, titel per sleutel, reeks per pagina)."""
    n = len(paginas)
    per_pagina = {p.url: _stappen(p) for p in paginas}
    aantal = Counter(k for reeks in per_pagina.values() for k, _ in reeks)
    titels: dict[str, str] = {}
    posities: dict[str, list[int]] = defaultdict(list)
    for reeks in per_pagina.values():
        for i, (k, t) in enumerate(reeks):
            titels.setdefault(k, t)
            posities[k].append(i)
    norm = [k for k, c in aantal.items() if c / n >= min_eensgezind]
    norm.sort(key=lambda k: sum(posities[k]) / len(posities[k]))
    return norm, titels, per_pagina


def _met_stappenplan(paginas: list[Pagina], min_eensgezind: float) -> list[Pagina]:
    """Alleen de pagina's die het stappenplan volgen.

    Een pagina zonder één van de gebruikelijke stappen (een gesloten ambassade, een land
    waar geen aanvraag mogelijk is) heeft geen stappenplan om mee te vergelijken. Die
    tellen niet mee in de norm van de andere detectoren, anders trekken tien pagina's
    zonder stappen elke telling scheef; `detecteer_stappen` meldt ze apart.
    """
    if not paginas:
        return paginas
    norm, _, per_pagina = _norm_stappen(paginas, min_eensgezind)
    norm_set = set(norm)
    return [p for p in paginas if norm_set & {k for k, _ in per_pagina[p.url]}]


# --- 1. stappenplan --------------------------------------------------------------


def detecteer_stappen(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Ontbrekende, hernoemde, extra of verwisselde stappen ten opzichte van de norm-reeks."""
    alle = list(paginas)
    if len(alle) < min_zusters:
        return []
    norm, titels, per_pagina = _norm_stappen(alle, min_eensgezind)
    norm_set = set(norm)
    paginas = [p for p in alle if norm_set & {k for k, _ in per_pagina[p.url]}]
    zonder = [p for p in alle if p not in paginas]
    n = len(paginas)
    bevindingen: list[Bevinding] = []

    if zonder:
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_STAPPEN,
                soort=SOORT_STRUCTUUR,
                categorie=CAT_STAPPEN,
                titel="Pagina volgt het stappenplan niet",
                sleutel="geen-stappenplan",
                afwijkend=[
                    (p, "geen stappen" if not per_pagina[p.url] else
                     "alleen: " + " · ".join(_afkappen(t, 40) for _, t in per_pagina[p.url]))
                    for p in zonder
                ],
                zusters=[(p, f"{len(per_pagina[p.url])} stappen") for p in paginas],
                eens=n,
                n=len(alle),
                toelichting=(
                    "Deze pagina's hebben geen van de gebruikelijke stappen, bijvoorbeeld "
                    "omdat de ambassade is gesloten. Ze zijn niet meegeteld in de andere "
                    "controles."
                ),
                actie="Beoordeel of deze pagina bewust een andere opzet heeft.",
            )
        )

    # Per pagina: welke norm-stap ontbreekt, en staat er op die plaats iets anders?
    ontbreekt: dict[str, list[Pagina]] = defaultdict(list)
    hernoemd: dict[tuple[str, str], list[Pagina]] = defaultdict(list)
    extra: dict[str, list[Pagina]] = defaultdict(list)
    for p in paginas:
        reeks = per_pagina[p.url]
        heeft = {k for k, _ in reeks}
        overig = [(k, t) for k, t in reeks if k not in norm_set]
        for k in norm:
            if k in heeft:
                continue
            # Een niet-norm stap die er sterk op lijkt is dezelfde stap onder een andere
            # naam, en dan is het geen ontbrekende plus een extra stap.
            beste = max(overig, key=lambda ot: _gelijkenis(ot[0], k), default=None)
            if beste and _gelijkenis(beste[0], k) >= GELIJKENIS_TITEL - 0.05:
                hernoemd[(k, beste[0])].append(p)
                overig.remove(beste)
            elif (i := norm.index(k)) < len(reeks) and reeks[i][0] not in norm_set \
                    and (reeks[i][0], reeks[i][1]) in overig:
                # Zelfde plek in de reeks: bewust anders geformuleerd.
                hernoemd[(k, reeks[i][0])].append(p)
                overig.remove((reeks[i][0], reeks[i][1]))
            else:
                ontbreekt[k].append(p)
        for k, _ in overig:
            if aantal_pagina(per_pagina, k) / n <= 1 - min_eensgezind:
                extra[k].append(p)

    for k in norm:
        mist = ontbreekt.get(k)
        if not mist:
            continue
        eens = [p for p in paginas if k in dict(per_pagina[p.url])]
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_STAPPEN,
                soort=SOORT_STRUCTUUR,
                categorie=CAT_STAPPEN,
                titel=f"Stap ontbreekt: {_zonder_nummer(titels[k])}",
                sleutel=f"stap-ontbreekt:{k}",
                afwijkend=[
                    (p, f"{len(per_pagina[p.url])} stappen: "
                     + " → ".join(_afkappen(t, 40) for _, t in per_pagina[p.url]))
                    for p in mist
                ],
                zusters=[(p, f"“{_afkappen(dict(per_pagina[p.url])[k], 60)}”") for p in eens],
                eens=len(eens),
                n=n,
                toelichting=(
                    f"Op {len(eens)} van de {n} landenpagina's staat de stap "
                    f"“{titels[k]}”. Dit kan bewust zijn (bijvoorbeeld bij een Schengenland), "
                    "maar het kan ook betekenen dat de stap is vergeten."
                ),
                actie="Beoordeel of de stap hier bewust ontbreekt.",
            )
        )

    for (k, andere), welke in sorted(hernoemd.items()):
        eens = [p for p in paginas if k in dict(per_pagina[p.url])]
        ratio = _gelijkenis(k, andere)
        soort = SOORT_SCHRIJFRICHTLIJN if ratio >= GELIJKENIS_TITEL - 0.05 else SOORT_STRUCTUUR
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_STAPPEN,
                soort=soort,
                categorie=CAT_STAPPEN,
                titel=f"Stap heet anders: {_zonder_nummer(titels[k])}",
                sleutel=f"stap-hernoemd:{k}:{andere}",
                afwijkend=[(p, f"“{_afkappen(dict(per_pagina[p.url])[andere], 70)}”") for p in welke],
                zusters=[(p, f"“{_afkappen(dict(per_pagina[p.url])[k], 70)}”") for p in eens],
                eens=len(eens),
                n=n,
                toelichting=(
                    f"Op {len(eens)} van de {n} pagina's heet deze stap “{titels[k]}”. "
                    + ("Een kleine afwijking in de titel." if soort == SOORT_SCHRIJFRICHTLIJN
                       else "Een andere formulering voor dezelfde stap; dat kan bewust zijn.")
                ),
                actie=("Pas de titel aan zodat hij gelijk is aan die op de andere pagina's."
                       if soort == SOORT_SCHRIJFRICHTLIJN
                       else "Beoordeel of de andere formulering bewust is."),
            )
        )

    for k, welke in sorted(extra.items()):
        zonder_stap = [p for p in paginas if p not in welke]
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_STAPPEN,
                soort=SOORT_STRUCTUUR,
                categorie=CAT_STAPPEN,
                titel=f"Extra stap: {_afkappen(_zonder_nummer(dict(per_pagina[welke[0].url])[k]), 70)}",
                sleutel=f"stap-extra:{k}",
                afwijkend=[(p, f"stap “{_afkappen(dict(per_pagina[p.url])[k], 60)}”") for p in welke],
                zusters=[(p, "heeft deze stap niet") for p in zonder_stap],
                eens=len(zonder_stap),
                n=n,
                toelichting=(
                    f"Deze stap staat op {len(welke)} van de {n} pagina's en niet in het "
                    "stappenplan van de meeste landen."
                ),
                actie="Beoordeel of deze extra stap bewust is.",
            )
        )

    verwisseld = []
    for p in paginas:
        volgorde = [k for k, _ in per_pagina[p.url] if k in norm_set]
        if volgorde != [k for k in norm if k in volgorde]:
            verwisseld.append((p, " → ".join(_afkappen(titels[k], 30) for k in volgorde)))
    if verwisseld:
        namen = {p.url for p, _ in verwisseld}
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_STAPPEN,
                soort=SOORT_STRUCTUUR,
                categorie=CAT_STAPPEN,
                titel="Stappen staan in een andere volgorde",
                sleutel="stap-volgorde",
                afwijkend=verwisseld,
                zusters=[(p, " → ".join(_afkappen(titels[k], 30) for k in norm))
                         for p in paginas if p.url not in namen],
                eens=n - len(verwisseld),
                n=n,
                toelichting="De meeste landen hanteren dezelfde volgorde van stappen.",
                actie="Beoordeel of de andere volgorde bewust is.",
            )
        )
    return bevindingen


def aantal_pagina(per_pagina: dict[str, list[tuple[str, str]]], sleutel: str) -> int:
    return sum(1 for reeks in per_pagina.values() if any(k == sleutel for k, _ in reeks))


# --- 2. uitklapparagrafen --------------------------------------------------------


def detecteer_uitklappers(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Een uitklapper die op vrijwel elke pagina van die stap staat, maar hier niet."""
    paginas = _met_stappenplan(list(paginas), min_eensgezind)
    per_pagina = {p.url: _uitklappers(p) for p in paginas}
    stappen = {p.url: {k for k, _ in _stappen(p)} for p in paginas}
    kopsleutels = {
        p.url: {normaliseer_titel(k["tekst"], landnaam(p)) for k in p.koppen} for p in paginas
    }

    # Op hoeveel pagina's staat deze uitklapper, en op hoeveel pagina's staat zijn stap?
    aantal = Counter(k for uit in per_pagina.values() for k in uit)
    stap_aantal = Counter(s for st in stappen.values() for s in st)
    bevindingen: list[Bevinding] = []

    for (stap, titel), c in sorted(aantal.items()):
        in_stap = stap_aantal[stap]
        if in_stap < min_zusters or c / in_stap < min_eensgezind or c == in_stap:
            continue

        heeft = [p for p in paginas if (stap, titel) in per_pagina[p.url]]
        mist = [p for p in paginas if stap in stappen[p.url] and (stap, titel) not in per_pagina[p.url]]
        voorbeeld = per_pagina[heeft[0].url][(stap, titel)].titel

        ontbrekend: list[tuple[Pagina, str]] = []
        anders_genoemd: list[tuple[Pagina, str]] = []
        elders: list[tuple[Pagina, str]] = []
        for p in mist:
            in_deze_stap = [t for (s, t) in per_pagina[p.url] if s == stap]
            gelijkend = max(
                in_deze_stap,
                key=lambda t: difflib.SequenceMatcher(None, t, titel).ratio(),
                default=None,
            )
            if gelijkend and difflib.SequenceMatcher(None, gelijkend, titel).ratio() >= GELIJKENIS_TITEL:
                anders_genoemd.append((p, f"“{per_pagina[p.url][(stap, gelijkend)].titel}”"))
            elif any(t == titel for (_, t) in per_pagina[p.url]):
                waar = next(s.stap for (st, t), s in per_pagina[p.url].items() if t == titel)
                elders.append((p, f"staat onder “{_afkappen(waar, 50)}”"))
            elif titel in kopsleutels[p.url]:
                continue  # staat als kop, geen uitklapper: dat is koppenstructuur
            else:
                ontbrekend.append((p, "ontbreekt"))

        stapnaam = next(s.stap for s in heeft[0].secties if normaliseer_titel(s.stap, landnaam(heeft[0])) == stap)
        bewijs = [(p, f"“{_afkappen(per_pagina[p.url][(stap, titel)].titel, 60)}”") for p in heeft]
        for lijst, soort, cat_titel, wat, actie in (
            (ontbrekend, SOORT_STRUCTUUR, "Uitklapper ontbreekt", "ontbreekt",
             "Beoordeel of de uitklapper hier bewust ontbreekt."),
            (elders, SOORT_STRUCTUUR, "Uitklapper staat onder een andere stap", "staat onder een andere stap",
             "Beoordeel of de uitklapper hier bewust onder een andere stap staat."),
            (anders_genoemd, SOORT_SCHRIJFRICHTLIJN, "Uitklapper heet anders", "heet anders",
             "Pas de titel aan zodat hij gelijk is aan die op de andere pagina's."),
        ):
            if not lijst:
                continue
            bevindingen.append(
                _bevinding(
                    regel_id=REGEL_UITKLAPPERS,
                    soort=soort,
                    categorie=CAT_UITKLAPPERS,
                    titel=f"{cat_titel}: {_afkappen(voorbeeld, 70)}",
                    sleutel=f"{wat}:{stap}:{titel}",
                    afwijkend=lijst,
                    zusters=bewijs,
                    eens=c,
                    n=in_stap,
                    toelichting=(
                        f"Bij “{_afkappen(stapnaam, 60)}” staat de uitklapper "
                        f"“{voorbeeld}” op {c} van de {in_stap} landenpagina's; hier "
                        f"{wat}."
                    ),
                    actie=actie,
                )
            )
    return bevindingen


# --- 3. koppenstructuur ----------------------------------------------------------


def _meest_voorkomend(waarden: Iterable[int]) -> tuple[int, float] | None:
    telling = Counter(waarden)
    if not telling:
        return None
    niveau, c = telling.most_common(1)[0]
    return niveau, c / sum(telling.values())


def detecteer_koppen(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Kopniveaus die afwijken van hoe de zusterpagina's het doen."""
    paginas = _met_stappenplan(list(paginas), min_eensgezind)
    n = len(paginas)
    if n < min_zusters:
        return []
    bevindingen: list[Bevinding] = []

    def meld(titel, sleutel, afwijkend, zusters, toelichting, actie):
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_KOPPEN,
                soort=SOORT_SCHRIJFRICHTLIJN,
                categorie=CAT_KOPPEN,
                titel=titel,
                sleutel=sleutel,
                afwijkend=afwijkend,
                zusters=zusters,
                eens=n - len({p.url for p, _ in afwijkend}),
                n=n,
                toelichting=toelichting,
                actie=actie,
            )
        )

    gemeld: set[tuple[str, str]] = set()
    echte_koppen = Counter(
        normaliseer_titel(str(k["tekst"]), landnaam(p)) for p in paginas for k in p.koppen
    )

    # (a) kopjes binnen een uitklapper: welk niveau is de norm, wie wijkt af?
    # Een vetgedrukte alinea telt alleen als kopje als dezelfde tekst elders echt een kop
    # is; anders is het een nadruk in lopende tekst en geen structuurfout.
    binnen = [
        (p, s, k) for p in paginas for s in p.secties if s.titel
        for k in s.koppen
        if not k.get("uitklap")
        and (k["niveau"] > 0
             or echte_koppen[normaliseer_titel(str(k["tekst"]), landnaam(p))] >= min_zusters)
    ]
    norm = _meest_voorkomend(k["niveau"] for _, _, k in binnen)
    if norm and norm[1] >= min_eensgezind and norm[0] > 0:
        norm_niveau = norm[0]
        voorbeelden = [(p, f"h{norm_niveau} “{_afkappen(k['tekst'], 40)}” in “{_afkappen(s.titel, 40)}”")
                       for p, s, k in binnen if k["niveau"] == norm_niveau]
        per_niveau: dict[int, list[tuple[Pagina, str]]] = defaultdict(list)
        for p, s, k in binnen:
            if k["niveau"] != norm_niveau:
                label = "vetgedrukte alinea" if k["niveau"] == 0 else f"h{k['niveau']}"
                per_niveau[k["niveau"]].append(
                    (p, f"{label} “{_afkappen(k['tekst'], 40)}” in “{_afkappen(s.titel, 40)}”")
                )
        for niveau, lijst in sorted(per_niveau.items()):
            label = "Vetgedrukte alinea als kopje" if niveau == 0 else f"h{niveau}"
            samengevoegd = defaultdict(list)
            for p, w in lijst:
                samengevoegd[p.url].append((p, w))
            afwijkend = [(v[0][0], "; ".join(w for _, w in v)) for v in samengevoegd.values()]
            gemeld.update(
                (p.url, normaliseer_titel(str(k["tekst"]), landnaam(p)))
                for p, _, k in binnen if k["niveau"] == niveau
            )
            meld(
                f"Kopje binnen een uitklapper is {label} in plaats van h{norm_niveau}",
                f"binnen-uitklapper:h{niveau}",
                afwijkend,
                voorbeelden[:50],
                f"In uitklapparagrafen staan kopjes bijna altijd als h{norm_niveau}. "
                "Een ander niveau geeft een afwijkende structuur voor schermlezers.",
                f"Maak van dit kopje een h{norm_niveau}.",
            )

    # (b) de titel van de uitklapper zelf.
    titels = [(p, s) for p in paginas for s in p.secties if s.titel]
    norm = _meest_voorkomend(s.niveau for _, s in titels)
    if norm and norm[1] >= min_eensgezind and norm[0] > 0:
        norm_niveau = norm[0]
        goed = [(p, f"h{norm_niveau} “{_afkappen(s.titel, 50)}”") for p, s in titels if s.niveau == norm_niveau]
        per_niveau = defaultdict(list)
        for p, s in titels:
            if s.niveau != norm_niveau:
                per_niveau[s.niveau].append((p, f"{'geen kop' if s.niveau == 0 else f'h{s.niveau}'} “{_afkappen(s.titel, 50)}”"))
        for niveau, lijst in sorted(per_niveau.items()):
            samengevoegd = defaultdict(list)
            for p, w in lijst:
                samengevoegd[p.url].append((p, w))
            gemeld.update(
                (p.url, normaliseer_titel(sec.titel, landnaam(p)))
                for p, sec in titels if sec.niveau == niveau
            )
            meld(
                f"Titel van uitklapper staat op {'geen kopniveau' if niveau == 0 else f'h{niveau}'} in plaats van h{norm_niveau}",
                f"uitklaptitel:h{niveau}",
                [(v[0][0], "; ".join(w for _, w in v)) for v in samengevoegd.values()],
                goed[:50],
                f"Uitklappers staan bijna altijd in een h{norm_niveau}.",
                f"Zet de uitklapper in een h{norm_niveau}.",
            )

    # (c) overgeslagen kopniveaus en een extra h1.
    overgeslagen: list[tuple[Pagina, str]] = []
    extra_h1: list[tuple[Pagina, str]] = []
    for p in paginas:
        vorige = 0
        sprongen = []
        h1_koppen = [k for k in p.koppen if k["niveau"] == 1]
        for k in p.koppen:
            if vorige and k["niveau"] > vorige + 1:
                sprongen.append(f"h{vorige} → h{k['niveau']} “{_afkappen(str(k['tekst']), 40)}”")
            vorige = int(k["niveau"])
        if sprongen:
            overgeslagen.append((p, "; ".join(sprongen)))
        if len(h1_koppen) > 1:
            extra_h1.append((p, f"{len(h1_koppen)}× h1"))
    for lijst, titel, sleutel, toelichting in (
        (overgeslagen, "Kopniveau overgeslagen", "overgeslagen-niveau",
         "Een kop hoort maximaal één niveau dieper te staan dan de vorige."),
        (extra_h1, "Meer dan één h1 op de pagina", "extra-h1",
         "Een pagina heeft precies één h1."),
    ):
        if lijst:
            meld(titel, sleutel, lijst,
                 [(p, "geen") for p in paginas if p.url not in {a.url for a, _ in lijst}],
                 toelichting, "Pas de koppen aan zodat de niveaus op elkaar aansluiten.")

    # (d) dezelfde kop op een ander niveau dan bij de zusters.
    per_titel: dict[str, list[tuple[Pagina, int, str]]] = defaultdict(list)
    for p in paginas:
        for k in p.koppen:
            per_titel[normaliseer_titel(str(k["tekst"]), landnaam(p))].append(
                (p, int(k["niveau"]), str(k["tekst"]))
            )
    for sleutel, vermeldingen in sorted(per_titel.items()):
        if len(vermeldingen) < min_zusters:
            continue
        norm = _meest_voorkomend(v[1] for v in vermeldingen)
        if not norm or norm[1] < min_eensgezind:
            continue
        afwijkend = [
            (p, f"h{niv} i.p.v. h{norm[0]}")
            for p, niv, _ in vermeldingen
            if niv != norm[0] and (p.url, sleutel) not in gemeld
        ]
        if afwijkend:
            eens = [(p, f"h{niv}") for p, niv, _ in vermeldingen if niv == norm[0]]
            meld(
                "Kop staat op ander niveau dan bij de andere landen: "
                + _afkappen(
                    re.sub(re.escape(landnaam(vermeldingen[0][0])), "<land>", vermeldingen[0][2], flags=re.I),
                    60,
                ),
                f"kopniveau:{sleutel}",
                afwijkend,
                eens,
                f"Op {len(eens)} van de {len(vermeldingen)} pagina's staat deze kop als h{norm[0]}.",
                f"Zet de kop op h{norm[0]}.",
            )
    return bevindingen


# --- 4. standaardzinnen ----------------------------------------------------------

_ZIN_SPLITS = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])")


def _zinnen(sectie: Sectie, land: str) -> list[tuple[str, str]]:
    """De zinnen van een sectie, als (sleutel, zoals-op-de-pagina)."""
    uit = []
    for regel in sectie.tekst.split("\n"):
        for zin in _ZIN_SPLITS.split(regel):
            zin = zin.strip()
            if len(zin) < 15:
                continue
            uit.append((normaliseer_titel(zin, land), re.sub(re.escape(land), "<land>", zin, flags=re.I)))
    return uit


def detecteer_zinnen(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Zinnen die in een uitklapper bijna overal staan, maar hier ontbreken of afwijken.

    Eén bevinding per uitklapper, met per pagina welke standaardzinnen ontbreken of
    anders staan: een pagina die een alinea weglaat, laat vaak tien zinnen weg, en tien
    losse bevindingen voor één keuze zouden het rapport dichtslibben. Alleen uitklappers
    die zelf de norm zijn tellen mee; "Afspraak maken in Algerije" is landspecifiek.
    """
    paginas = _met_stappenplan(list(paginas), min_eensgezind)
    per_sectie: dict[tuple[str, str], list[tuple[Pagina, Sectie, list[tuple[str, str]]]]] = defaultdict(list)
    stap_aantal: Counter = Counter()
    for p in paginas:
        land = landnaam(p)
        for stap in {normaliseer_titel(s.stap, land) for s in p.secties if s.stap}:
            stap_aantal[stap] += 1
        for s in p.secties:
            if s.titel:
                per_sectie[(normaliseer_titel(s.stap, land), normaliseer_titel(s.titel, land))].append(
                    (p, s, _zinnen(s, land))
                )

    bevindingen: list[Bevinding] = []
    for (stap, titel), leden in sorted(per_sectie.items()):
        if len(leden) < min_zusters or len(leden) / max(stap_aantal[stap], 1) < min_eensgezind:
            continue
        telling = Counter(k for _, _, zinnen in leden for k in {k for k, _ in zinnen})
        standaard = {k for k, c in telling.items() if c / len(leden) >= min_eensgezind}
        leesbaar = {
            k: t for _, _, zs in leden for k, t in zs if k in standaard
        }
        afwijkend: list[tuple[Pagina, str]] = []
        for p, _, zinnen in leden:
            eigen = {k for k, _ in zinnen}
            delen: list[str] = []
            for k in sorted(standaard - eigen, key=lambda k: -telling[k]):
                dichtst = difflib.get_close_matches(k, [z for z, _ in zinnen if z not in standaard], n=1, cutoff=GELIJKENIS_ZIN)
                if dichtst:
                    tekst = next(t for z, t in zinnen if z == dichtst[0])
                    delen.append(f"“{_afkappen(tekst, 90)}” i.p.v. “{_afkappen(leesbaar[k], 90)}”")
                else:
                    delen.append(f"ontbreekt: “{_afkappen(leesbaar[k], 90)}”")
            if delen:
                meer = f" (+{len(delen) - 3} meer)" if len(delen) > 3 else ""
                afwijkend.append((p, f"{len(delen)} van {len(standaard)} standaardzinnen ontbreken of wijken af: "
                    + "; ".join(delen[:3]) + meer))
        if not afwijkend:
            continue
        namen = {p.url for p, _ in afwijkend}
        uitklaptitel = leden[0][1].titel
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_ZINNEN,
                soort=SOORT_STRUCTUUR,
                categorie=CAT_ZINNEN,
                titel=f"Standaardtekst wijkt af in “{_afkappen(uitklaptitel, 60)}”",
                sleutel=f"zinnen:{stap}:{titel}",
                afwijkend=afwijkend,
                zusters=[
                    (p, f"{len(standaard)} standaardzinnen, o.a. “{_afkappen(leesbaar[sorted(standaard, key=lambda k: -telling[k])[0]], 80)}”")
                    for p, _, _ in leden if p.url not in namen
                ],
                eens=len(leden) - len(afwijkend),
                n=len(leden),
                toelichting=(
                    f"In de uitklapper “{uitklaptitel}” staan {len(standaard)} zinnen die op "
                    f"minstens {int(min_eensgezind * 100)}% van de {len(leden)} landenpagina's "
                    "letterlijk hetzelfde zijn. Op deze pagina's ontbreekt er een of staat "
                    "hij anders. Een landspecifieke aanpassing kan bewust zijn."
                ),
                actie="Beoordeel of de afwijking bewust is; herstel anders de standaardtekst.",
            )
        )
    return bevindingen


# --- 5. kernbeweringen -----------------------------------------------------------


def laad_beweringen(pad: pathlib.Path = BEWERINGEN_PAD) -> list[dict]:
    if not pad.exists():
        return []
    return yaml.safe_load(pad.read_text(encoding="utf-8")).get("beweringen", [])


def _bereik(pagina: Pagina, waar: str) -> str | None:
    """De tekst waarin een bewering wordt gezocht, of None als dat deel ontbreekt."""
    land = landnaam(pagina)
    soort, _, zoek = waar.partition(":")
    if soort == "pagina":
        return pagina.tekst
    zoek = zoek.casefold()
    delen = [
        s.tekst for s in pagina.secties
        if (soort == "uitklap" and zoek in normaliseer_titel(s.titel, land))
        or (soort == "stap" and s.stap and zoek in normaliseer_titel(s.stap, land))
    ]
    return "\n".join(delen) if delen else None


def _antwoord(tekst: str, varianten: dict[str, str], anders: str = "geen van deze") -> str:
    gevonden = []
    for naam, patroon in varianten.items():
        m = re.search(patroon, tekst, re.I | re.M)
        if m:
            gevonden.append(f"{naam} {m.group(1)}" if m.groups() and m.group(1) else naam)
    return " + ".join(gevonden) if gevonden else anders


def detecteer_beweringen(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    beweringen: list[dict] | None = None,
    **_: object,
) -> list[Bevinding]:
    """Inhoudelijke keuzes waarin een pagina anders antwoordt dan de meeste zusters.

    Wat een pagina "beweert" staat als regexen in `regels/kernbeweringen.yaml`, zodat de
    redactie er zelf een kan toevoegen. Een land dat iets anders zegt, hoeft niet fout te
    zitten; het is wel iets dat een kenniseigenaar moet beoordelen.
    """
    paginas = _met_stappenplan(list(paginas), min_eensgezind)
    bevindingen: list[Bevinding] = []
    for regel in laad_beweringen() if beweringen is None else beweringen:
        metingen = []
        for p in paginas:
            tekst = _bereik(p, regel["zoek_in"])
            if tekst is not None:
                metingen.append((p, _antwoord(tekst, regel["varianten"], regel.get("anders", "geen van deze"))))
        if len(metingen) < min_zusters:
            continue
        telling = Counter(a for _, a in metingen)
        norm, aantal = telling.most_common(1)[0]
        if aantal / len(metingen) < min_eensgezind:
            continue
        afwijkend = [(p, a) for p, a in metingen if a != norm]
        if not afwijkend:
            continue
        eens = [(p, norm) for p, a in metingen if a == norm]
        bevindingen.append(
            _bevinding(
                regel_id=REGEL_BEWERINGEN,
                soort=SOORT_INHOUDELIJK,
                categorie=CAT_BEWERINGEN,
                titel=f"{regel['titel']}: {len(afwijkend)} pagina('s) zeggen iets anders",
                sleutel=regel["id"],
                afwijkend=afwijkend,
                zusters=eens,
                eens=len(eens),
                n=len(metingen),
                elders=norm,
                toelichting=(
                    f"Op {len(eens)} van de {len(metingen)} landenpagina's geldt: {norm}. "
                    f"{regel.get('toelichting', '')}".strip()
                ),
                actie="Leg voor aan de kenniseigenaar: welk antwoord klopt, en mag het per land verschillen?",
            )
        )
    return bevindingen
