"""Bevindingen omzetten in een klikbaar overzicht.

Het rapport groepeert primair op eigenaar, niet op ernst: "wat kan ik zelf doen" versus
"wat moet ik uitzetten" is de vraag die het werk van de redacteur bepaalt. Elke bevinding
toont de afwijkende waarde naast de waarde op zusterpagina's, zodat verifiëren tien
seconden kost — vertrouwen komt uit controleerbaarheid, niet uit zekerheid van de tool.
"""

from __future__ import annotations

import pathlib

from jinja2 import Environment, FileSystemLoader, select_autoescape

import huisstijl

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


def _varianten(bevinding: Bevinding) -> list[dict[str, str]]:
    """Haal de afwijkende pagina's met hun waarde uit `waargenomen`.

    `waargenomen` is opgebouwd als "land: waarde | land: waarde", zodat de bewijs_hash
    over alle afwijkende waarden gaat en de onderdrukking vervalt zodra er één wijzigt.
    """
    varianten = []
    for deel in bevinding.waargenomen.split(" | "):
        variant, _, waarde = deel.partition(": ")
        if waarde:
            varianten.append({"variant": variant, "waarde": waarde})
    return varianten


def render(
    *,
    bevindingen: list[Bevinding],
    familie: str,
    datum: str,
    aantal_paginas: int,
    waarschuwingen: list[str] | None = None,
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
                "bevindingen": [
                    {
                        "titel": b.titel,
                        "soort": b.soort,
                        "zekerheid": b.zekerheid,
                        "telling": b.telling,
                        "varianten": _varianten(b),
                        "zusters": b.zusters,
                        "urls": b.urls,
                        "toelichting": b.toelichting,
                        "voorgestelde_actie": b.voorgestelde_actie,
                    }
                    for b in van_groep
                ],
            }
        )

    return template.render(
        bevindingen=bevindingen,
        groepen=groepen,
        familie=familie,
        datum=datum,
        aantal_paginas=aantal_paginas,
        waarschuwingen=waarschuwingen or [],
        stijl=huisstijl.laad_css(),
    )


def schrijf_rapport(pad: pathlib.Path, **kwargs: object) -> pathlib.Path:
    pad.write_text(render(**kwargs), encoding="utf-8")  # type: ignore[arg-type]
    return pad
