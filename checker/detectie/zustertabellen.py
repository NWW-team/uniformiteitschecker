"""Zusterpagina's binnen een familie met elkaar vergelijken.

De site bestaat grotendeels uit getemplatiseerde landenvarianten: ~218 pagina's onder
`consulaire-tarieven/<land>`, die hetzelfde horen te zeggen. Daarmee vormen ze hun eigen
norm — wijkt één land af van de rest, dan is dat een signaal, zonder dat er een externe
bron van waarheid nodig is.

Twee dingen die deze detector bewust NIET doet:

1. **Zeggen wat fout is.** Dat tarieven gelijk zijn over landen heen is gecheckt op een
   steekproef, niet op alle 218. Er kunnen legitieme landspecifieke tarieven zijn. De
   bevinding zegt daarom "wijkt af van N andere pagina's — verifieer", nooit "fout".
2. **Ontbrekende rijen melden.** De Duitsland-pagina mist alle visumrijen, volkomen
   legitiem: Duitsland is Schengen. Een ontbrekende rij is een zwak signaal en levert
   vooral ruis; dat is werk voor later, met een eigen drempel.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from ..model import SOORT_INHOUDELIJK, Bevinding, Pagina, bepaal_eigenaar
from .normalisatie import normaliseer_label, normaliseer_waarde

REGEL_ID = "zustertabel_waarden"

# Drempels tegen ruis. Een familie die netjes in twee kampen verdeeld is, is geen fout
# maar een variant; die willen we niet melden.
MIN_ZUSTERS = 5
MIN_EENSGEZIND = 0.8

def _zekerheid(eens: int, totaal: int) -> str:
    """Hoe eensgezind zijn de zusterpagina's?

    Afgeleid uit de verhouding, niet uit het aantal afwijkers. Anders krijgt de
    Cuba/Suriname/Iran-cluster `middel` puur omdat het drie pagina's zijn, terwijl 89
    van de 92 het eens zijn -- en dat is juist een sterk signaal.
    """
    aandeel = eens / totaal
    if aandeel >= 0.95:
        return "hoog"
    return "middel" if aandeel >= 0.85 else "laag"


# Hoeveel zusterpagina's we als bewijs meegeven. Genoeg om in tien seconden te
# verifiëren, niet zoveel dat het rapport dichtslibt.
AANTAL_BEWIJS = 3


def detecteer(
    paginas: Iterable[Pagina],
    *,
    min_zusters: int = MIN_ZUSTERS,
    min_eensgezind: float = MIN_EENSGEZIND,
    **_: object,
) -> list[Bevinding]:
    """Meld per rijlabel de pagina's die een minderheidswaarde hebben."""
    paginas = list(paginas)
    per_label: dict[str, list[tuple[Pagina, str, str]]] = defaultdict(list)

    for pagina in paginas:
        for tabel in pagina.tabellen:
            for rij in tabel.rijen:
                sleutel = normaliseer_label(rij.label)
                if sleutel:
                    per_label[sleutel].append(
                        (pagina, rij.label, rij.waarde_rauw)
                    )

    bevindingen: list[Bevinding] = []
    for sleutel, vermeldingen in sorted(per_label.items()):
        bevinding = _beoordeel_label(sleutel, vermeldingen, min_zusters, min_eensgezind)
        if bevinding is not None:
            bevindingen.append(bevinding)
    return bevindingen


def _beoordeel_label(
    sleutel: str,
    vermeldingen: list[tuple[Pagina, str, str]],
    min_zusters: int,
    min_eensgezind: float,
) -> Bevinding | None:
    if len(vermeldingen) < min_zusters:
        # Te weinig zusters om een norm uit af te leiden.
        return None

    genormaliseerd = {
        pagina.url: normaliseer_waarde(rauw) for pagina, _, rauw in vermeldingen
    }
    telling = Counter(genormaliseerd.values())
    meerderheid, aantal_eens = telling.most_common(1)[0]

    if aantal_eens / len(vermeldingen) < min_eensgezind:
        # Geen duidelijke norm: dit is variatie, geen afwijking.
        return None

    afwijkend = [
        (pagina, label, rauw)
        for pagina, label, rauw in vermeldingen
        if genormaliseerd[pagina.url] != meerderheid
    ]
    if not afwijkend:
        return None

    eens = [
        (pagina, rauw)
        for pagina, _, rauw in vermeldingen
        if genormaliseerd[pagina.url] == meerderheid
    ]
    # Toon de waarde zoals die er echt staat, niet de genormaliseerde vorm.
    waarde_elders = eens[0][1]
    leesbaar_label = afwijkend[0][1]
    familie = afwijkend[0][0].familie

    varianten = [
        {"url": pagina.url, "variant": pagina.familie_sleutel, "waarde": rauw}
        for pagina, _, rauw in sorted(afwijkend, key=lambda v: v[0].url)
    ]

    return Bevinding(
        regel_id=REGEL_ID,
        soort=SOORT_INHOUDELIJK,
        eigenaar=bepaal_eigenaar(SOORT_INHOUDELIJK),
        titel=f"Bedrag wijkt af van andere landen: {leesbaar_label}",
        # Eén bevinding per rijlabel, met alle afwijkende pagina's erin. Zonder deze
        # samenvoeging levert één templatewijziging 218 losse bevindingen op.
        urls=[v["url"] for v in varianten],
        # Locatie bevat bewust niet de afwijkende landen: dan blijft de vingerafdruk
        # gelijk als één land gecorrigeerd wordt, en blijft een negeerlijst-entry werken.
        locatie={"familie": familie, "rij_label": leesbaar_label},
        waargenomen=" | ".join(f"{v['variant']}: {v['waarde']}" for v in varianten),
        elders=waarde_elders,
        varianten=varianten,
        zusters=[
            {"url": pagina.url, "variant": pagina.familie_sleutel, "waarde": rauw}
            for pagina, rauw in sorted(eens, key=lambda v: v[0].url)[:AANTAL_BEWIJS]
        ],
        telling={
            "n": len(vermeldingen),
            "eens": aantal_eens,
            "afwijkend": len(afwijkend),
        },
        voorgestelde_actie=(
            "Verifieer welk bedrag klopt en laat de afwijkende pagina('s) corrigeren."
        ),
        zekerheid=_zekerheid(aantal_eens, len(vermeldingen)),
        toelichting=(
            f"Op {aantal_eens} van de {len(vermeldingen)} landenpagina's met deze rij "
            f"staat {waarde_elders}. Dit kan ook een legitiem landspecifiek tarief zijn."
        ),
    )
