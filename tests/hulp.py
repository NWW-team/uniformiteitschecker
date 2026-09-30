"""Fixtures inlezen. Geen enkele test raakt het netwerk."""

from __future__ import annotations

import pathlib

from checker.bronnen.extractie import lees_pagina
from checker.model import Pagina

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "paginas"

# De vijf echte landenpagina's die samen alle gevonden verschijnselen dekken:
# argentinie/frankrijk als schone zusters, duitsland met de ontbrekende spatie en
# ontbrekende visumrijen, canada met het euroteken in de kolomkop, brazilie met het
# afwijkende bedrag.
ZUSTERS = ["argentinie", "brazilie", "canada", "duitsland", "frankrijk"]


def lees_html(naam: str) -> str:
    return (FIXTURES / f"{naam}.html").read_text(encoding="utf-8")


def pagina(land: str) -> Pagina:
    return lees_pagina(
        lees_html(land),
        f"https://www.nederlandwereldwijd.nl/consulaire-tarieven/{land}",
        familie="consulaire-tarieven",
        familie_sleutel=land,
    )


def paginas(landen: list[str] | None = None) -> list[Pagina]:
    return [pagina(land) for land in (landen or ZUSTERS)]


# --- paspoort-landenpaginas -------------------------------------------------------

PASPOORT_FIXTURES = FIXTURES / "paspoort"
PASPOORT_URL = "https://www.nederlandwereldwijd.nl/paspoort-id-kaart/buitenland/paspoort-{}"


def paspoort_pagina(land: str) -> Pagina:
    """Een echte, ingekorte landenpagina uit `fixtures/paginas/paspoort/`."""
    html = (PASPOORT_FIXTURES / f"{land}.html").read_text(encoding="utf-8")
    return lees_pagina(
        html,
        PASPOORT_URL.format(land),
        familie="paspoort-landenpaginas",
        familie_sleutel=land,
    )


# De opbouw die de meeste landenpagina's delen: (stap, [(uitklaptitel, tekst)]).
STANDAARD_STAPPEN = [
    ("Stap 1: Maak uw persoonlijke checklist", []),
    (
        "Stap 2: Check de extra eisen",
        [("Documenten legaliseren", "Laat uw akte legaliseren met een apostille.")],
    ),
    ("Stap 3: Maak een afspraak", []),
    (
        "Stap 4: Ga naar uw afspraak",
        [
            (
                "Wat neem ik mee?",
                "Neem alle originele documenten uit uw persoonlijke checklist mee. "
                "De baliemedewerker maakt kopieën.",
            ),
            ("Moet ik mijn oude paspoort meteen inleveren?", "Nee. Dan kunt u deze houden."),
        ],
    ),
    (
        "Stap 5: Paspoort ophalen of laten opsturen",
        [("Ophalen", "U kunt uw nieuwe paspoort ophalen bij de ambassade.")],
    ),
]


def synthetisch(
    land: str,
    stappen=None,
    *,
    subkopniveau: int = 4,
    uitklapniveau: int = 3,
    extra_html: str = "",
) -> Pagina:
    """Een landenpagina met de standaardopbouw, aan te passen per test.

    Bouwt echte HTML met dezelfde uitklapmarkup als de site en leest die met dezelfde
    extractie in, zodat de tests het hele pad van HTML tot detectie dekken.
    """
    delen = [f"<h1>Paspoort of ID-kaart aanvragen als u in {land} woont</h1><p>Volg dit stappenplan.</p>"]
    teller = 0
    for stap, uitklappers in stappen if stappen is not None else STANDAARD_STAPPEN:
        delen.append(f"<h2>{stap}</h2><p>Inleiding bij de stap.</p>")
        for titel, tekst in uitklappers:
            teller += 1
            delen.append(
                f'<h{uitklapniveau}><button aria-controls="acc-{teller}" type="button">'
                f"<span>{titel}</span></button></h{uitklapniveau}>"
                f'<div id="acc-{teller}" data-testid="accordion-panel"><div>'
                f"<h{subkopniveau}>Afspraak wijzigen of afzeggen</h{subkopniveau}>"
                f"<p>{tekst}</p></div></div>"
            )
    delen.append(extra_html)
    return lees_pagina(
        "<main>" + "".join(delen) + "</main>",
        PASPOORT_URL.format(land.lower()),
        familie="paspoort-landenpaginas",
        familie_sleutel=land.lower(),
    )


LANDEN = [
    "Albanië", "Algerije", "Angola", "Armenië", "Aruba",
    "Bahrein", "Belize", "Benin", "Bhutan", "Bolivia",
]


def zusters(**afwijkingen) -> list[Pagina]:
    """Tien pagina's met de standaardopbouw; `afwijkingen[land]` is een dict met kwargs."""
    return [synthetisch(land, **afwijkingen.get(land, {})) for land in LANDEN]
