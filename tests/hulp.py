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
