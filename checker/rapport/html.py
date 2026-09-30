"""Bevindingen omzetten in een klikbaar overzicht met een tabblad per familie.

Het rapport groepeert primair op eigenaar, niet op ernst: "wat kan ik zelf doen" versus
"wat moet ik uitzetten" is de vraag die het werk van de redacteur bepaalt. Binnen een
groep staan de bevindingen per categorie, en alleen de bevinding klapt uit: eerst het overzicht,
dan pas het bewijs. Elke bevinding toont de afwijkende waarde naast de waarde op
zusterpagina's, zodat verifiëren tien seconden kost — vertrouwen komt uit
controleerbaarheid, niet uit zekerheid van de tool.

Het rapport is één zelfstandig HTML-bestand. Zonder JavaScript staan de tabbladen onder
elkaar en werken de uitklappers gewoon; het script voegt alleen de tabbalk en het
zoekveld toe.
"""

from __future__ import annotations

import json
import pathlib
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

import huisstijl

from ..model import (
    EIGENAAR_BEOORDELEN,
    EIGENAAR_KENNISEIGENAAR,
    EIGENAAR_REDACTIE,
    Bevinding,
)

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
        EIGENAAR_BEOORDELEN,
        "beoordelen",
        "Beoordelen: bewust of niet?",
        "Deze pagina's wijken af in opbouw of tekst. Dat is vaak bewust, bijvoorbeeld "
        "omdat een land maar één post heeft. De webredactie beoordeelt of het zo hoort.",
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

# Voor bevindingen uit een oudere run die nog geen `categorie` hebben.
CATEGORIE_PER_REGEL = {
    "zustertabel_waarden": "Bedragen die afwijken van andere landen",
    "bedragnotatie": "Bedragen in een afwijkende notatie",
}

# Volgorde van de categorieën binnen een groep; onbekende komen alfabetisch erachter.
CATEGORIE_VOLGORDE = [
    "Opbouw van het stappenplan",
    "Ontbrekende of afwijkende uitklapparagrafen",
    "Koppenstructuur",
    "Afwijkingen van standaardteksten",
    "Inhoudelijk mogelijk tegenstrijdig",
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


def _categorie(b: Bevinding) -> str:
    return b.categorie or CATEGORIE_PER_REGEL.get(b.regel_id, "Overig")


def _sorteer_categorie(naam: str) -> tuple[int, str]:
    return (CATEGORIE_VOLGORDE.index(naam) if naam in CATEGORIE_VOLGORDE else 99, naam)


def bouw_familie(
    *,
    id: str,
    naam: str,
    bevindingen: list[Bevinding],
    datum: str,
    aantal_paginas: int,
    waarschuwingen: list[str] | None = None,
    inleiding: str = "",
) -> dict:
    """Alles wat het template voor één tabblad nodig heeft."""
    groepen = []
    for eigenaar, klasse, titel, toelichting in GROEPEN:
        van_groep = [b for b in bevindingen if b.eigenaar == eigenaar]
        if not van_groep:
            continue
        per_categorie: dict[str, list[dict]] = {}
        for b in van_groep:
            varianten = _varianten(b)
            per_categorie.setdefault(_categorie(b), []).append(
                {
                    "titel": b.titel,
                    "soort": b.soort,
                    "zekerheid": b.zekerheid,
                    "telling": b.telling,
                    "varianten": varianten,
                    "zusters": b.zusters,
                    "urls": b.urls,
                    "toelichting": b.toelichting,
                    "voorgestelde_actie": b.voorgestelde_actie,
                    # Waar het zoekveld op filtert: landen, titel en URL's.
                    "zoek": " ".join(
                        [b.titel, *(v["variant"] for v in varianten), *b.urls]
                    ).casefold(),
                }
            )
        groepen.append(
            {
                "klasse": klasse,
                "titel": titel,
                "toelichting": toelichting,
                "aantal": len(van_groep),
                "categorieen": [
                    {"naam": naam, "bevindingen": per_categorie[naam]}
                    for naam in sorted(per_categorie, key=_sorteer_categorie)
                ],
            }
        )
    return {
        "id": id,
        "naam": naam,
        "datum": datum,
        "aantal_paginas": aantal_paginas,
        "aantal": len(bevindingen),
        "waarschuwingen": waarschuwingen or [],
        "inleiding": inleiding,
        "groepen": groepen,
    }


def render_rapport(families: list[dict]) -> str:
    """Render één rapport met een tabblad per familie (uit `bouw_familie`)."""
    omgeving = Environment(
        loader=FileSystemLoader(TEMPLATE_MAP),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return omgeving.get_template("rapport.html.j2").render(
        families=families,
        stijl=huisstijl.laad_css(),
        sitekop=huisstijl.sitekop(),
    )


def render(
    *,
    bevindingen: list[Bevinding],
    familie: str,
    datum: str,
    aantal_paginas: int,
    waarschuwingen: list[str] | None = None,
    naam: str = "",
    inleiding: str = "",
) -> str:
    """Rapport voor één familie — de vorm die de tests en `controleer` al kenden."""
    return render_rapport(
        [
            bouw_familie(
                id=familie,
                naam=naam or familie,
                bevindingen=bevindingen,
                datum=datum,
                aantal_paginas=aantal_paginas,
                waarschuwingen=waarschuwingen,
                inleiding=inleiding,
            )
        ]
    )


def schrijf_rapport(pad: pathlib.Path, **kwargs: object) -> pathlib.Path:
    pad.write_text(render(**kwargs), encoding="utf-8")  # type: ignore[arg-type]
    return pad


def familie_uit_findings(findings_pad: pathlib.Path, familie: dict) -> dict:
    """Lees een findings-bestand en bouw er het tabblad van `familie` mee."""
    data = json.loads(findings_pad.read_text(encoding="utf-8"))
    return bouw_familie(
        id=familie["id"],
        naam=familie.get("naam", familie["id"]),
        bevindingen=[Bevinding.uit_dict(b) for b in data["bevindingen"]],
        datum=data["datum"],
        aantal_paginas=data["aantal_paginas"],
        waarschuwingen=data.get("waarschuwingen", []),
        inleiding=familie.get("inleiding", ""),
    )


def nieuwste_findings(findings_map: pathlib.Path, familie_id: str) -> pathlib.Path | None:
    kandidaten = sorted(findings_map.glob(f"*/{familie_id}.json"))
    return kandidaten[-1] if kandidaten else None


def schrijf_samengesteld_rapport(
    pad: pathlib.Path, families: Iterable[dict], findings_map: pathlib.Path
) -> list[str]:
    """Eén rapport met een tabblad voor elke familie die bevindingen heeft.

    Geeft de id's terug van de families die zijn opgenomen. Een familie zonder
    findings-bestand (nog nooit gedraaid) valt weg in plaats van een leeg tabblad te
    tonen dat op "geen afwijkingen" lijkt.
    """
    tabbladen = []
    for familie in families:
        findings = nieuwste_findings(findings_map, familie["id"])
        if findings is not None:
            tabbladen.append(familie_uit_findings(findings, familie))
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(render_rapport(tabbladen), encoding="utf-8")
    return [t["id"] for t in tabbladen]
