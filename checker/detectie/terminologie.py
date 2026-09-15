"""Termen die alleen op één landenpagina voorkomen.

Dit is het probleem dat `STRATEGY.md` noemt — "paspoort vs. reisdocument" — maar in de
tarieftabellen en op schaal. Dezelfde dienst heet op verschillende landenpagina's anders:
`Verklaring van Nederlanderschap` naast `verklaring nederlanderschap`, `verklaring omtrent
bezit Nederlanderschap`, `verklaring omtrent Nederlandse nationaliteit` en `verklaring
nationaliteit`.

Gemeten op de 218 pagina's van `consulaire-tarieven`: 81 van de 122 labelsleutels komen op
vier of minder pagina's voor, verspreid over 35 van de 114 pagina's met tabellen.

Waarom dit niet met samenvoegen werkt — en hier wél gelijkenis mag:

`labeldrift.py` voegt rijen samen en mag daarom uitsluitend deterministische regels
gebruiken; een foute samenvoeging laat de waardendetector tegenstrijdigheden verzinnen.
Deze detector voegt niets samen. Hij constateert alleen dat een term nergens anders
voorkomt, en mag daar een suggestie bij doen ("lijkt op ..."). Een verkeerde suggestie
levert een overbodige vraag op, geen verzonnen tegenstrijdigheid. Dat is het verschil
tussen gelijkenis die een vraag stelt en gelijkenis die een vergelijking maakt.
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from typing import Iterable

from ..model import SOORT_SCHRIJFRICHTLIJN, Bevinding, Pagina, bepaal_eigenaar
from .normalisatie import normaliseer_label

REGEL_ID = "eigen_terminologie"

# Een label dat op zoveel pagina's of minder voorkomt, is een eigen term.
MAX_PAGINAS_ZELDZAAM = 4

# Een label dat op zoveel pagina's of meer voorkomt, geldt als gangbaar en mag als
# suggestie dienen.
MIN_PAGINAS_GANGBAAR = 20

# Onder deze gelijkenis is een suggestie meer verwarrend dan behulpzaam.
MIN_GELIJKENIS = 0.6

# Een pagina met minder eigen termen dan dit melden we niet: één eigen term is te vaak
# een dienst die echt alleen daar bestaat, en dat zou het rapport vullen met twijfel.
MIN_EIGEN_LABELS = 3


def detecteer(
    paginas: Iterable[Pagina],
    *,
    max_paginas_zeldzaam: int = MAX_PAGINAS_ZELDZAAM,
    min_eigen_labels: int = MIN_EIGEN_LABELS,
    **_: object,
) -> list[Bevinding]:
    """Meld pagina's die rijlabels gebruiken die vrijwel nergens anders voorkomen."""
    paginas = list(paginas)
    per_sleutel: dict[str, set[str]] = defaultdict(set)
    labels_per_sleutel: dict[str, str] = {}

    for pagina in paginas:
        for tabel in pagina.tabellen:
            for rij in tabel.rijen:
                sleutel = normaliseer_label(rij.label)
                if sleutel:
                    per_sleutel[sleutel].add(pagina.url)
                    labels_per_sleutel.setdefault(sleutel, rij.label)

    if not per_sleutel:
        return []

    zeldzaam = {
        s for s, urls in per_sleutel.items() if len(urls) <= max_paginas_zeldzaam
    }
    gangbaar = {
        s: labels_per_sleutel[s]
        for s, urls in per_sleutel.items()
        if len(urls) >= MIN_PAGINAS_GANGBAAR
    }

    bevindingen: list[Bevinding] = []
    for pagina in sorted(paginas, key=lambda p: p.url):
        bevinding = _beoordeel_pagina(
            pagina, zeldzaam, gangbaar, per_sleutel, min_eigen_labels
        )
        if bevinding is not None:
            bevindingen.append(bevinding)
    return bevindingen


def _beoordeel_pagina(
    pagina: Pagina,
    zeldzaam: set[str],
    gangbaar: dict[str, str],
    per_sleutel: dict[str, set[str]],
    min_eigen_labels: int,
) -> Bevinding | None:
    eigen: list[tuple[str, str]] = []  # (rauw label, sleutel)
    totaal = 0
    gezien: set[str] = set()

    for tabel in pagina.tabellen:
        for rij in tabel.rijen:
            sleutel = normaliseer_label(rij.label)
            if not sleutel or sleutel in gezien:
                continue
            gezien.add(sleutel)
            totaal += 1
            if sleutel in zeldzaam:
                eigen.append((rij.label, sleutel))

    if len(eigen) < min_eigen_labels:
        return None

    varianten = []
    for label, sleutel in eigen:
        suggestie = _suggestie(sleutel, gangbaar)
        elders = len(per_sleutel[sleutel]) - 1
        varianten.append(
            {
                "variant": label,
                "waarde": (
                    f"lijkt op: {suggestie}" if suggestie
                    else (f"ook op {elders} andere pagina('s)" if elders else "nergens anders")
                ),
            }
        )

    return Bevinding(
        regel_id=REGEL_ID,
        soort=SOORT_SCHRIJFRICHTLIJN,
        eigenaar=bepaal_eigenaar(SOORT_SCHRIJFRICHTLIJN),
        titel=(
            f"{len(eigen)} eigen rijlabels op {pagina.familie_sleutel} "
            "die andere landenpagina's niet gebruiken"
        ),
        urls=[pagina.url],
        # Alleen de pagina: dan blijft de vingerafdruk gelijk als er een term bij komt
        # of wordt gecorrigeerd.
        locatie={"familie": pagina.familie, "familie_sleutel": pagina.familie_sleutel},
        waargenomen=" | ".join(f"{label}" for label, _ in eigen),
        elders="",
        varianten=varianten,
        zusters=[],
        telling={"n": totaal, "eens": totaal - len(eigen), "afwijkend": len(eigen)},
        voorgestelde_actie=(
            "Ga na of deze diensten elders anders heten, en breng de termen in lijn. "
            "Bestaat een dienst echt alleen hier, zet de bevinding dan op de negeerlijst."
        ),
        # Bewust geen hoge zekerheid: een eigen term kan een dienst zijn die echt alleen
        # op deze post bestaat.
        zekerheid="middel",
        toelichting=(
            f"Van de {totaal} rijlabels op deze pagina komen er {len(eigen)} op vier of "
            "minder landenpagina's voor. De suggesties hieronder zijn gelijkenis, geen "
            "vaststelling: controleer per term of het echt dezelfde dienst is."
        ),
    )


def _suggestie(sleutel: str, gangbaar: dict[str, str]) -> str | None:
    """Het meest gelijkende gangbare label, als het genoeg lijkt.

    Puur een hint voor de redacteur. Er wordt niets op samengevoegd en geen enkele
    waarde wordt hierop vergeleken, dus een verkeerde hint kost alleen een overbodige
    vraag. Twee deterministische guards houden de hints tóch bruikbaar — een hint die
    er duidelijk naast zit, ondermijnt het vertrouwen in de rest van het rapport:

    - zelfde eerste woord, want dat benoemt de dienst (`Inreisvisum, laag tarief`
      hoort niet bij `Schengenvisum laag tarief`);
    - zelfde getallen, want die benoemen vaak de leeftijdsklasse (`kinderen tot 11
      jaar` hoort niet bij `kinderen tot 6 jaar`).
    """
    getallen = _getallen(sleutel)
    eerste = sleutel.split(" ", 1)[0]

    beste: tuple[float, str] | None = None
    for gangbare_sleutel, gangbaar_label in gangbaar.items():
        if gangbare_sleutel.split(" ", 1)[0] != eerste:
            continue
        if _getallen(gangbare_sleutel) != getallen:
            continue
        ratio = difflib.SequenceMatcher(None, sleutel, gangbare_sleutel).ratio()
        if ratio >= MIN_GELIJKENIS and (beste is None or ratio > beste[0]):
            beste = (ratio, gangbaar_label)
    return beste[1] if beste else None


def _getallen(sleutel: str) -> set[str]:
    return set(re.findall(r"\d+", sleutel))
