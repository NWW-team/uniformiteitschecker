"""Afwijkingen aantonen: termenlijst inladen en pagina's ertegen controleren.

De termenlijst is configuratie, geen code — de redactie moet hem zonder ontwikkelaar
kunnen uitbreiden. Daarom validatie met duidelijke fouten in plaats van stil overslaan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import TALEN, Bevinding, Pagina

# Een pagina die een term twintig keer gebruikt levert geen twintig bruikbare signalen op.
MAX_FRAGMENTEN_PER_PAGINA = 3
ZIN_GRENS = re.compile(r"[.!?\n]")


class TermenlijstFout(ValueError):
    """De termenlijst klopt niet; de melding zegt welke regel en wat eraan mankeert."""


@dataclass(slots=True)
class Regel:
    id: str
    voorkeur: str
    varianten: list[str]
    talen: list[str] = field(default_factory=lambda: list(TALEN))
    toelichting: str = ""
    hele_woorden: bool = True
    eigenaar: str = "redactie"
    _patroon: re.Pattern[str] | None = None

    def __post_init__(self) -> None:
        delen = sorted((re.escape(v) for v in self.varianten), key=len, reverse=True)
        kern = "|".join(delen)
        patroon = rf"\b(?:{kern})\b" if self.hele_woorden else f"(?:{kern})"
        self._patroon = re.compile(patroon, re.IGNORECASE)

    @property
    def patroon(self) -> re.Pattern[str]:
        assert self._patroon is not None
        return self._patroon

    def geldt_voor(self, taal: str) -> bool:
        return taal in self.talen


def laad_regels(pad: Path | str) -> list[Regel]:
    """Lees config/termen.yaml en valideer hem."""
    pad = Path(pad)
    if not pad.exists():
        raise TermenlijstFout(f"Termenlijst niet gevonden: {pad}")

    gegevens = yaml.safe_load(pad.read_text(encoding="utf-8")) or {}
    ruwe_regels = gegevens.get("regels")
    if not ruwe_regels:
        raise TermenlijstFout(f"{pad} bevat geen 'regels'.")

    regels: list[Regel] = []
    gezien: set[str] = set()
    for nummer, ruw in enumerate(ruwe_regels, start=1):
        plek = f"regel {nummer}"
        if not isinstance(ruw, dict):
            raise TermenlijstFout(f"{plek}: moet een blok met velden zijn, niet {type(ruw).__name__}.")

        regel_id = str(ruw.get("id", "")).strip()
        if not regel_id:
            raise TermenlijstFout(f"{plek}: 'id' ontbreekt.")
        if regel_id in gezien:
            raise TermenlijstFout(f"{plek}: id '{regel_id}' komt meer dan een keer voor.")
        gezien.add(regel_id)

        voorkeur = str(ruw.get("voorkeur", "")).strip()
        if not voorkeur:
            raise TermenlijstFout(f"regel '{regel_id}': 'voorkeur' ontbreekt.")

        varianten = [str(v).strip() for v in (ruw.get("varianten") or []) if str(v).strip()]
        if not varianten:
            raise TermenlijstFout(f"regel '{regel_id}': 'varianten' is leeg; zonder varianten valt er niets te vinden.")

        talen = [str(t).strip().lower() for t in (ruw.get("talen") or TALEN)]
        onbekend = [t for t in talen if t not in TALEN]
        if onbekend:
            raise TermenlijstFout(
                f"regel '{regel_id}': onbekende taal {onbekend}; bekend zijn {list(TALEN)}."
            )

        regels.append(
            Regel(
                id=regel_id,
                voorkeur=voorkeur,
                varianten=varianten,
                talen=talen,
                toelichting=str(ruw.get("toelichting", "")).strip(),
                hele_woorden=bool(ruw.get("hele_woorden", True)),
                eigenaar=str(ruw.get("eigenaar", "redactie")).strip() or "redactie",
            )
        )
    return regels


def _fragment(tekst: str, start: int, eind: int) -> str:
    """De zin rond een treffer, zodat een redacteur hem kan beoordelen zonder de pagina te openen."""
    grenzen_voor = [m.end() for m in ZIN_GRENS.finditer(tekst, 0, start)]
    begin = grenzen_voor[-1] if grenzen_voor else 0
    volgende = ZIN_GRENS.search(tekst, eind)
    stop = volgende.end() if volgende else len(tekst)
    return " ".join(tekst[begin:stop].split())


def controleer(pagina: Pagina, regels: list[Regel]) -> list[Bevinding]:
    """Controleer één pagina tegen de regels die voor zijn taal gelden."""
    bevindingen: list[Bevinding] = []
    for regel in regels:
        if not regel.geldt_voor(pagina.taal):
            continue

        treffers = list(regel.patroon.finditer(pagina.tekst))
        if not treffers:
            continue

        for treffer in treffers[:MAX_FRAGMENTEN_PER_PAGINA]:
            bevindingen.append(
                Bevinding(
                    soort="terminologie",
                    regel_id=regel.id,
                    gevonden_term=treffer.group(0),
                    voorkeursterm=regel.voorkeur,
                    url=pagina.url,
                    taal=pagina.taal,
                    fragment=_fragment(pagina.tekst, treffer.start(), treffer.end()),
                    toelichting=regel.toelichting,
                    eigenaar=regel.eigenaar,
                    positie=treffer.start(),
                    treffers_op_pagina=len(treffers),
                )
            )
    return bevindingen


def controleer_alles(paginas: list[Pagina], regels: list[Regel]) -> list[Bevinding]:
    bevindingen: list[Bevinding] = []
    for pagina in paginas:
        bevindingen.extend(controleer(pagina, regels))
    return sorted(bevindingen, key=lambda b: b.sorteersleutel)
