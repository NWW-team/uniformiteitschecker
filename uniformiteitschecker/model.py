"""Datamodel dat de drie sporen uit STRATEGY.md aan elkaar knoopt.

`Pagina` is wat het spoor "content uitlezen" oplevert, `Bevinding` wat het spoor
"afwijkingen aantonen" eruit haalt en het rapport toont.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

TALEN = ("nl", "en")


@dataclass(frozen=True, slots=True)
class Pagina:
    """Eén uitgelezen pagina, losgemaakt van de HTML waar hij uit komt."""

    url: str
    taal: str
    site: str
    titel: str
    tekst: str
    opgehaald_op: str
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            digest = hashlib.sha256(self.tekst.encode("utf-8")).hexdigest()[:16]
            object.__setattr__(self, "content_hash", digest)

    def als_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def uit_dict(cls, gegevens: dict[str, Any]) -> "Pagina":
        velden = {f: gegevens.get(f, "") for f in cls.__slots__}
        return cls(**velden)


@dataclass(frozen=True, slots=True)
class Bevinding:
    """Eén gesignaleerde afwijking, met genoeg context om hem op te pakken.

    `soort` is nu altijd "terminologie"; de inhoudelijke tegenstrijdigheden uit
    de strategie komen later als tweede soort binnen hetzelfde rapport.
    """

    soort: str
    regel_id: str
    gevonden_term: str
    voorkeursterm: str
    url: str
    taal: str
    fragment: str
    toelichting: str = ""
    eigenaar: str = "redactie"
    positie: int = 0
    treffers_op_pagina: int = 1

    def als_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def sorteersleutel(self) -> tuple[str, str, int]:
        return (self.regel_id, self.url, self.positie)


@dataclass(slots=True)
class Site:
    """Een bron uit config/sites.yaml, afgebakend tot een of meer URL-paden."""

    id: str
    basis_url: str
    taal: str
    paden: list[str] = field(default_factory=list)

    @property
    def domein(self) -> str:
        from urllib.parse import urlparse

        return urlparse(self.basis_url).netloc


def aantal(getal: int, enkelvoud: str, meervoud: str) -> str:
    """Nette Nederlandse telwoorden — redacteuren lezen deze uitvoer."""
    return f"{getal} {enkelvoud if getal == 1 else meervoud}"


PAGINAS = ("pagina", "pagina's")
SIGNALEN = ("signaal", "signalen")
REGELS = ("regel", "regels")
