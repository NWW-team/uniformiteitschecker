"""Bevindingen omzetten in een klikbaar overzicht.

Het rapport groepeert primair op eigenaar, niet op ernst: "wat kan ik zelf doen" versus
"wat moet ik uitzetten" is de vraag die het werk van de redacteur bepaalt. Elke bevinding
toont wat afwijkt naast wat er elders staat, zodat verifiëren tien seconden kost —
vertrouwen komt uit controleerbaarheid, niet uit zekerheid van de tool.
"""

from __future__ import annotations

import pathlib
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..model import EIGENAAR_KENNISEIGENAAR, EIGENAAR_REDACTIE, Bevinding

TEMPLATE_MAP = pathlib.Path(__file__).parent / "templates"

GROEPEN = [
    (
        EIGENAAR_REDACTIE,
        "zelf",
        "Zelf verbeteren",
        "Het juiste antwoord staat in de schrijfrichtlijn of blijkt uit de "
        "zusterpagina's. De webredactie kan dit zelf corrigeren.",
    ),
    (
        EIGENAAR_KENNISEIGENAAR,
        "voorleggen",
        "Voorleggen aan kenniseigenaar",
        "Dit betreft een feit — een bedrag, termijn of voorwaarde. De checker kan niet "
        "weten welke kant klopt, ook niet bij een grote meerderheid: geld en juridische "
        "voorwaarden wijzig je niet op statistiek.",
    ),
]

# Kolomkoppen per regel. Elke detector meldt iets anders, dus "Wijkt af / Staat elders"
# klopt niet overal: bij terminologie is er geen tegenhanger om naar te wijzen.
KOPPEN: dict[str, tuple[str, str | None]] = {
    "zustertabel_waarden": ("Wijkt af", "Staat elders"),
    "bedragnotatie": ("Voorbeelden op deze pagina", "Notatie in de rest van de familie"),
    "labeldrift": ("Afwijkende formulering", "Gangbare formulering"),
    "eigen_terminologie": ("Eigen term op deze pagina", None),
}


def _voor_template(bevinding: Bevinding) -> dict[str, Any]:
    kop_afwijkend, kop_elders = KOPPEN.get(
        bevinding.regel_id, ("Wijkt af", "Staat elders")
    )
    return {
        "titel": bevinding.titel,
        "soort": bevinding.soort,
        "zekerheid": bevinding.zekerheid,
        "telling": bevinding.telling,
        "varianten": bevinding.varianten,
        "zusters": bevinding.zusters,
        "elders": bevinding.elders,
        "kop_afwijkend": kop_afwijkend,
        "kop_elders": kop_elders,
        "urls": bevinding.urls,
        "toelichting": bevinding.toelichting,
        "voorgestelde_actie": bevinding.voorgestelde_actie,
        # Zichtbaar in het rapport, want zonder vingerafdruk kan de redactie geen
        # entry op de negeerlijst aanmaken.
        "vingerafdruk": bevinding.vingerafdruk,
    }


def render(
    *,
    bevindingen: list[Bevinding],
    familie: str,
    datum: str,
    aantal_paginas: int,
    waarschuwingen: list[str] | None = None,
    onderdrukt: list[tuple[Bevinding, dict[str, Any]]] | None = None,
) -> str:
    omgeving = Environment(
        loader=FileSystemLoader(TEMPLATE_MAP),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = omgeving.get_template("rapport.html.j2")

    groepen = []
    for eigenaar, klasse, titel, toelichting in GROEPEN:
        van_groep = [b for b in bevindingen if b.eigenaar == eigenaar]
        if not van_groep:
            continue
        groepen.append(
            {
                "klasse": klasse,
                "titel": titel,
                "toelichting": toelichting,
                "bevindingen": [_voor_template(b) for b in van_groep],
            }
        )

    return template.render(
        bevindingen=bevindingen,
        groepen=groepen,
        familie=familie,
        datum=datum,
        aantal_paginas=aantal_paginas,
        waarschuwingen=waarschuwingen or [],
        onderdrukt=[
            {"titel": b.titel, "reden": e.get("reden", ""), "door": e.get("door", "")}
            for b, e in (onderdrukt or [])
        ],
    )


def schrijf_rapport(pad: pathlib.Path, **kwargs: Any) -> pathlib.Path:
    pad.write_text(render(**kwargs), encoding="utf-8")
    return pad
