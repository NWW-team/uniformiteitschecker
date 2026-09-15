"""Afwijkingen van de schrijfrichtlijnen in de notatie van bedragen.

Deze detector bestaat omdat de normalisatie doet wat ze moet doen. Zij maakt `€167.80`
en `€ 167,80` gelijkwaardig, zodat ze niet als inhoudelijke tegenstrijdigheid worden
gemeld. Maar de notatie zélf is wel een echte afwijking, en die mag niet stilzwijgend
verdwijnen — anders verbetert de app haar eigen ruis weg inclusief het signaal.

Het is een schrijfrichtlijn-afwijking, dus de webredactie kan het zelf verbeteren: het
juiste antwoord staat vast zodra de rest van de familie het anders doet.

Eén bevinding per pagina met een telling, nooit één per rij: op de Kenia-pagina staan
ruim twintig bedragen in Engelse notatie, en dat is één correctie, geen twintig.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..model import SOORT_SCHRIJFRICHTLIJN, Bevinding, Pagina, bepaal_eigenaar
from .normalisatie import NOTATIE_NL, notatie

REGEL_ID = "bedragnotatie"

# Onder dit aandeel is er geen familienorm om aan te toetsen.
MIN_EENSGEZIND = 0.8

# Hoeveel zusterpagina's we als bewijs meegeven bij "staat elders".
AANTAL_BEWIJS = 3


def detecteer(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = 5,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Meld pagina's die bedragen anders noteren dan de rest van de familie."""
    paginas = list(paginas)
    if len(paginas) < min_zusters:
        return []

    per_pagina: dict[str, Counter] = {}
    for pagina in paginas:
        tellingen: Counter = Counter()
        for tabel in pagina.tabellen:
            for rij in tabel.rijen:
                vorm = notatie(rij.waarde_rauw)
                if vorm:
                    tellingen[vorm] += 1
        if tellingen:
            per_pagina[pagina.url] = tellingen

    if not per_pagina:
        return []

    # De norm is de notatie die de meeste pagina's overwegend gebruiken.
    overheersend = Counter(t.most_common(1)[0][0] for t in per_pagina.values())
    norm, aantal_norm = overheersend.most_common(1)[0]
    if aantal_norm / len(per_pagina) < min_eensgezind:
        return []

    # Pagina's die zelf de norm volgen: het bewijs voor "staat elders".
    norm_paginas = [
        p
        for p in paginas
        if per_pagina.get(p.url) and per_pagina[p.url].most_common(1)[0][0] == norm
    ]

    bevindingen: list[Bevinding] = []
    for pagina in sorted(paginas, key=lambda p: p.url):
        tellingen = per_pagina.get(pagina.url)
        if not tellingen:
            continue
        afwijkend = sum(n for vorm, n in tellingen.items() if vorm != norm)
        if not afwijkend:
            continue

        voorbeelden = _voorbeelden(pagina, norm)
        zusters = _zusterbewijs(norm_paginas, pagina, norm)
        bevindingen.append(
            Bevinding(
                regel_id=REGEL_ID,
                soort=SOORT_SCHRIJFRICHTLIJN,
                eigenaar=bepaal_eigenaar(SOORT_SCHRIJFRICHTLIJN),
                titel=(
                    f"{afwijkend} bedragen in afwijkende notatie op "
                    f"{pagina.familie_sleutel}"
                ),
                urls=[pagina.url],
                # Alleen de pagina, niet de losse rijen: dan blijft de vingerafdruk
                # gelijk als er een bedrag bij komt of af gaat.
                locatie={"familie": pagina.familie, "familie_sleutel": pagina.familie_sleutel},
                waargenomen=" | ".join(
                    f"{pagina.familie_sleutel}: {v}" for v in voorbeelden
                ),
                elders=_voorbeeld_norm(norm),
                zusters=zusters,
                telling={
                    "n": sum(tellingen.values()),
                    "eens": tellingen.get(norm, 0),
                    "afwijkend": afwijkend,
                },
                voorgestelde_actie=(
                    "Zet de bedragen op deze pagina in Nederlandse notatie: komma als "
                    "decimaalteken en punt als duizendscheidingsteken."
                    if norm == NOTATIE_NL
                    else "Breng de notatie op deze pagina in lijn met de rest van de familie."
                ),
                zekerheid="hoog",
                toelichting=(
                    f"{aantal_norm} van de {len(per_pagina)} landenpagina's gebruikt "
                    f"{'Nederlandse' if norm == NOTATIE_NL else 'deze'} notatie. De "
                    "bedragen zelf zijn gelijk; alleen de schrijfwijze wijkt af."
                ),
            )
        )
    return bevindingen


def _voorbeelden(pagina: Pagina, norm: str, maximum: int = 3) -> list[str]:
    gevonden: list[str] = []
    for tabel in pagina.tabellen:
        for rij in tabel.rijen:
            vorm = notatie(rij.waarde_rauw)
            if vorm and vorm != norm:
                gevonden.append(rij.waarde_rauw)
                if len(gevonden) == maximum:
                    return gevonden
    return gevonden


def _voorbeeld_norm(norm: str) -> str:
    return "€ 1.139,00" if norm == NOTATIE_NL else "€1,139.00"


def _zusterbewijs(
    norm_paginas: list[Pagina], afwijkende_pagina: Pagina, norm: str
) -> list[dict[str, str]]:
    """Zusterpagina's die de norm volgen, als bewijs voor "staat elders"."""
    bewijs: list[dict[str, str]] = []
    for zuster in sorted(norm_paginas, key=lambda p: p.url):
        if zuster.url == afwijkende_pagina.url:
            continue
        voorbeeld = _voorbeeld_in_notatie(zuster, norm)
        if voorbeeld is None:
            continue
        bewijs.append(
            {"url": zuster.url, "variant": zuster.familie_sleutel, "waarde": voorbeeld}
        )
        if len(bewijs) == AANTAL_BEWIJS:
            break
    return bewijs


def _voorbeeld_in_notatie(pagina: Pagina, norm: str) -> str | None:
    for tabel in pagina.tabellen:
        for rij in tabel.rijen:
            if notatie(rij.waarde_rauw) == norm:
                return rij.waarde_rauw
    return None
