"""Dezelfde rij, verschillend opgeschreven.

Drie deterministische regels, oplopend in risico. Bewust géén fuzzy matching: op deze
familie voegt `difflib` met ratio >= 0.85 twaalf labelparen samen waarvan elf fout, en
niet onschuldig fout. `Paspoort meerderjarige` en `Paspoort minderjarige` schelen twee
letters en zijn tegengesteld; `Naturalisatie: standaard` en `verlaagd` hebben
verschillende tarieven; `kinderen tot 6 jaar` en `6 t/m 11 jaar` zijn andere
leeftijdsklassen.

Samengevoegde rijen gaan de waardendetector in. Een foute samenvoeging laat de app dus
tegenstrijdigheden *verzinnen* die niet bestaan — het ergste wat deze tool kan doen.
Vandaar de regel die het ontwerp stuurt: gelijkenis mag een vraag stellen, nooit een
vergelijking maken. Hier wordt samengevoegd, dus hier geldt alleen determinisme.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Callable, Iterable

from ..model import SOORT_SCHRIJFRICHTLIJN, Bevinding, Pagina, bepaal_eigenaar
from .normalisatie import (
    heeft_haakjes,
    labelsleutel_bereik,
    labelsleutel_kaal,
    normaliseer_label,
)

REGEL_ID = "labeldrift"

# De tekst binnen haakjes, om te tellen hoeveel verschillende toelichtingen er zijn.
_HAAKJES_TEKST = re.compile(r"\(([^)]*)\)")

# Minimaal aantal pagina's waarop een labelgroep voorkomt voordat we er iets over zeggen.
MIN_PAGINAS = 5

# Per regel: sleutelfunctie, titel en of beide kanten haakjes mogen hebben.
REGELS: list[tuple[str, Callable[[str], str], str]] = [
    (
        "schrijfwijze",
        normaliseer_label,
        "Zelfde rij, verschillende schrijfwijze",
    ),
    (
        "getalbereik",
        labelsleutel_bereik,
        "Zelfde leeftijdsbereik, verschillend genoteerd",
    ),
    (
        "toelichting",
        labelsleutel_kaal,
        "Zelfde rij, op sommige pagina's met een toelichting erbij",
    ),
]


def detecteer(
    paginas: Iterable[Pagina],
    *,
    min_paginas: int = MIN_PAGINAS,
    **_: object,
) -> list[Bevinding]:
    """Meld labels die hetzelfde aanduiden maar verschillend zijn opgeschreven."""
    paginas = list(paginas)
    vermeldingen = _vermeldingen(paginas)
    if not vermeldingen:
        return []

    bevindingen: list[Bevinding] = []
    # Een groep die een eerdere, veiliger regel al heeft gemeld, niet opnieuw melden.
    gemeld: set[frozenset[str]] = set()

    for regel_naam, sleutelfunctie, titel in REGELS:
        for labels in _groepen(vermeldingen, sleutelfunctie, regel_naam):
            sleutel = frozenset(labels)
            if sleutel in gemeld or any(sleutel <= eerder for eerder in gemeld):
                continue
            bevinding = _maak_bevinding(
                labels, vermeldingen, regel_naam, titel, min_paginas
            )
            if bevinding is not None:
                gemeld.add(sleutel)
                bevindingen.append(bevinding)

    return bevindingen


def _vermeldingen(paginas: list[Pagina]) -> dict[str, list[Pagina]]:
    """Per rauw label: op welke pagina's het voorkomt."""
    per_label: dict[str, list[Pagina]] = defaultdict(list)
    for pagina in paginas:
        gezien: set[str] = set()
        for tabel in pagina.tabellen:
            for rij in tabel.rijen:
                if normaliseer_label(rij.label) and rij.label not in gezien:
                    gezien.add(rij.label)
                    per_label[rij.label].append(pagina)
    return per_label


def _groepen(
    vermeldingen: dict[str, list[Pagina]],
    sleutelfunctie: Callable[[str], str],
    regel_naam: str,
) -> list[set[str]]:
    """Groepeer rauwe labels die onder deze regel dezelfde sleutel krijgen."""
    per_sleutel: dict[str, set[str]] = defaultdict(set)
    for label in vermeldingen:
        per_sleutel[sleutelfunctie(label)].add(label)

    groepen = []
    for labels in per_sleutel.values():
        if len(labels) < 2:
            continue
        if regel_naam == "toelichting" and not _toelichting_is_veilig(labels):
            continue
        groepen.append(labels)
    return groepen


def _toelichting_is_veilig(labels: set[str]) -> bool:
    """Mag de haakjesregel deze labels als dezelfde rij behandelen?

    Twee eisen, beide nodig:

    1. Minstens één variant heeft géén haakjes. Anders worden
       `Inburgeringsexamen (voor naturalisatie)` en `Inburgeringsexamen (MVV)`
       samengevoegd, en dat zijn verschillende examens.
    2. Er is hoogstens één verschillende toelichting. Komen er twee of meer voor, dan
       coderen de haakjes vrijwel zeker een echt onderscheid -- zoals
       `Verklaring van in leven zijn (indien voordruk ...)` tegenover
       `(indien geen voordruk ...)`, met elk een eigen tarief. Deze eis sluit ook het
       geval af waarin er naast twee toelichtingen tóch een kale variant opduikt: eis 1
       zou dan gehaald worden, en zonder deze eis zouden alle drie samengaan.
    """
    if not any(not heeft_haakjes(label) for label in labels):
        return False
    toelichtingen = {
        tekst for label in labels for tekst in _HAAKJES_TEKST.findall(label)
    }
    return len(toelichtingen) <= 1


def _maak_bevinding(
    labels: set[str],
    vermeldingen: dict[str, list[Pagina]],
    regel_naam: str,
    titel: str,
    min_paginas: int,
) -> Bevinding | None:
    gesorteerd = sorted(labels, key=lambda l: (-len(vermeldingen[l]), l))
    totaal = sum(len(vermeldingen[l]) for l in gesorteerd)
    if totaal < min_paginas:
        return None

    gangbaar, *afwijkend = gesorteerd
    paginas_gangbaar = vermeldingen[gangbaar]
    aantal_gangbaar = len(paginas_gangbaar)
    if aantal_gangbaar <= 1:
        # Geen gangbare vorm om naar te verwijzen; dit is variatie, geen drift.
        return None

    varianten = [
        {
            "variant": vermeldingen[label][0].familie_sleutel
            if len(vermeldingen[label]) == 1
            else f"{len(vermeldingen[label])} pagina's",
            "waarde": label,
        }
        for label in afwijkend
    ]
    urls = [p.url for label in afwijkend for p in vermeldingen[label]]
    familie = paginas_gangbaar[0].familie

    return Bevinding(
        regel_id=REGEL_ID,
        soort=SOORT_SCHRIJFRICHTLIJN,
        eigenaar=bepaal_eigenaar(SOORT_SCHRIJFRICHTLIJN),
        titel=f"{titel}: {gangbaar}",
        urls=sorted(set(urls)),
        # Alleen de gangbare vorm in de locatie: dan blijft de vingerafdruk gelijk als
        # er een variant bij komt of wordt gecorrigeerd.
        locatie={
            "familie": familie,
            "regel": regel_naam,
            "gangbaar_label": gangbaar,
        },
        waargenomen=" | ".join(f"{v['variant']}: {v['waarde']}" for v in varianten),
        elders=gangbaar,
        varianten=varianten,
        zusters=[
            {
                "url": p.url,
                "variant": p.familie_sleutel,
                "waarde": gangbaar,
            }
            for p in paginas_gangbaar[:3]
        ],
        telling={
            "n": totaal,
            "eens": aantal_gangbaar,
            "afwijkend": totaal - aantal_gangbaar,
        },
        voorgestelde_actie=(
            "Kies welke formulering de standaard is en pas de afwijkende pagina('s) aan."
        ),
        zekerheid="hoog" if regel_naam != "toelichting" else "middel",
        toelichting=(
            f"{aantal_gangbaar} pagina's schrijven {gangbaar!r}. "
            + "; ".join(
                f"{len(vermeldingen[l])}x {l!r}" for l in afwijkend
            )
            + (
                ". Een toelichting tussen haakjes kan ook bedoeld zijn: controleer of "
                "het echt om dezelfde rij gaat."
                if regel_naam == "toelichting"
                else "."
            )
        ),
    )
