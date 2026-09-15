"""Beoordeelde signalen onderdrukken, zonder echte fouten te gaan verbergen.

Een negeerlijst is nodig — zonder is elk rapport na de eerste keer een herhaling van
wat de redactie al heeft afgewogen. Maar hij is ook gevaarlijk: een lijst die stilletijds
blijft onderdrukken terwijl de pagina verandert, verbergt op termijn echte fouten.

Daarom drie vervalregels, en onderdrukking die altijd zichtbaar is in het rapport.
"""

from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any, Iterable

import yaml

from ..model import Bevinding

NEGEERLIJST_PAD = pathlib.Path("regels/negeerlijst.yaml")


@dataclass
class Uitkomst:
    overgebleven: list[Bevinding] = field(default_factory=list)
    # Bevinding plus de entry die hem onderdrukte, zodat het rapport de reden kan tonen.
    onderdrukt: list[tuple[Bevinding, dict[str, Any]]] = field(default_factory=list)
    # Uitleg per onderdrukking die niet meer geldt. Gaat naar de waarschuwingen in het
    # rapport: een vervallen onderdrukking is iets wat de redactie moet weten.
    vervallen: list[str] = field(default_factory=list)


def laad(pad: pathlib.Path | str = NEGEERLIJST_PAD) -> list[dict[str, Any]]:
    """Lees de negeerlijst. Een ontbrekend bestand is geen fout."""
    pad = pathlib.Path(pad)
    if not pad.exists():
        return []
    inhoud = yaml.safe_load(pad.read_text(encoding="utf-8")) or {}
    return list(inhoud.get("onderdruk") or [])


def _hoort_bij(bevinding: Bevinding, entry: dict[str, Any]) -> bool:
    """Gaat deze entry over deze bevinding?

    Twee niveaus: op vingerafdruk voor één specifieke plek, of op regel plus URL-patroon
    voor een hele groep (bijvoorbeeld pagina's die worden uitgefaseerd).
    """
    if entry.get("vingerafdruk"):
        return entry["vingerafdruk"] == bevinding.vingerafdruk

    if entry.get("regel_id") and entry["regel_id"] != bevinding.regel_id:
        return False
    glob = entry.get("url_glob")
    if glob:
        return any(fnmatch(url, glob) for url in bevinding.urls)
    # Een entry zonder vingerafdruk en zonder url_glob zou alles onderdrukken.
    return False


def _als_datum(waarde: Any) -> dt.date | None:
    if isinstance(waarde, dt.datetime):
        return waarde.date()
    if isinstance(waarde, dt.date):
        return waarde
    if isinstance(waarde, str):
        try:
            return dt.date.fromisoformat(waarde)
        except ValueError:
            return None
    return None


def _waarom_vervallen(
    bevinding: Bevinding, entry: dict[str, Any], vandaag: dt.date
) -> str | None:
    """Geldt deze onderdrukking nog? Zo niet: waarom niet."""
    verwacht = entry.get("bewijs_hash")
    if verwacht and verwacht != bevinding.bewijs_hash:
        return (
            f"De onderdrukking van {bevinding.titel!r} is vervallen: de inhoud van de "
            "pagina is gewijzigd sinds de beoordeling, dus het signaal komt terug."
        )

    vervalt = _als_datum(entry.get("vervalt"))
    if vervalt and vervalt < vandaag:
        return (
            f"De onderdrukking van {bevinding.titel!r} is verlopen op "
            f"{vervalt.isoformat()} en moet opnieuw beoordeeld worden."
        )
    return None


def pas_toe(
    bevindingen: Iterable[Bevinding],
    entries: list[dict[str, Any]],
    *,
    vandaag: dt.date | None = None,
) -> Uitkomst:
    """Splits bevindingen in wat blijft staan en wat onderdrukt is."""
    vandaag = vandaag or dt.date.today()
    uitkomst = Uitkomst()

    for bevinding in bevindingen:
        entry = next((e for e in entries if _hoort_bij(bevinding, e)), None)
        if entry is None:
            uitkomst.overgebleven.append(bevinding)
            continue

        reden = _waarom_vervallen(bevinding, entry, vandaag)
        if reden:
            uitkomst.vervallen.append(reden)
            uitkomst.overgebleven.append(bevinding)
        else:
            uitkomst.onderdrukt.append((bevinding, entry))

    return uitkomst
