"""Datacontracten die de drie sporen koppelen.

Spoor 1 (uitlezen) produceert `Pagina`, spoor 2 (detecteren) produceert `Bevinding`,
spoor 3 (rapporteren) leest alleen `Bevinding`. De sporen praten uitsluitend via deze
twee contracten, zodat detectie en rapportage offline te ontwikkelen zijn tegen een
gecommitte snapshot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

EXTRACTIE_VERSIE = 1

# Scheidingsteken voor hashes: mag niet in labels of URL's voorkomen.
_SCHEIDING = "|~|"

# Soorten afwijking, zoals STRATEGY.md ze onderscheidt.
SOORT_SCHRIJFRICHTLIJN = "schrijfrichtlijn"
SOORT_INHOUDELIJK = "inhoudelijk"

# Wie het antwoord kan weten. Zie `bepaal_eigenaar`.
EIGENAAR_REDACTIE = "webredactie"
EIGENAAR_KENNISEIGENAAR = "kenniseigenaar"


def _hash(*delen: str) -> str:
    return hashlib.sha1(_SCHEIDING.join(delen).encode("utf-8")).hexdigest()


@dataclass
class Rij:
    """Eén rij uit een tabel: een label met een waarde."""

    label: str
    waarde_rauw: str
    waarde_genormaliseerd: str | None = None


@dataclass
class Tabel:
    index: int
    kolomkoppen: list[str] = field(default_factory=list)
    rijen: list[Rij] = field(default_factory=list)


@dataclass
class Pagina:
    """Een uitgelezen, genormaliseerde pagina — de uitvoer van spoor 1."""

    url: str
    bron_id: str
    taal: str
    familie: str
    familie_sleutel: str
    titel: str = ""
    opgehaald_op: str = ""
    http_status: int = 200
    koppen: list[dict[str, Any]] = field(default_factory=list)
    tekst: str = ""
    tabellen: list[Tabel] = field(default_factory=list)
    extractie_versie: int = EXTRACTIE_VERSIE

    def naar_json(self) -> str:
        """Eén regel JSON, met gesorteerde sleutels zodat git-diffs leesbaar blijven."""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def uit_dict(d: dict[str, Any]) -> "Pagina":
        tabellen = [
            Tabel(
                index=t["index"],
                kolomkoppen=list(t.get("kolomkoppen", [])),
                rijen=[Rij(**r) for r in t.get("rijen", [])],
            )
            for t in d.get("tabellen", [])
        ]
        return Pagina(**{**d, "tabellen": tabellen})


@dataclass
class Bevinding:
    """Eén signaal voor de redactie — de uitvoer van spoor 2.

    De app spreekt zich nooit uit over wat juist is; `voorgestelde_actie` is daarom
    altijd een handeling ("verifieer welk bedrag klopt"), nooit een inhoudelijke waarde.
    """

    regel_id: str
    soort: str
    eigenaar: str
    titel: str
    urls: list[str]
    locatie: dict[str, Any]
    waargenomen: str = ""
    elders: str = ""
    zusters: list[dict[str, str]] = field(default_factory=list)
    telling: dict[str, int] = field(default_factory=dict)
    voorgestelde_actie: str = ""
    zekerheid: str = "hoog"
    toelichting: str = ""

    @property
    def vingerafdruk(self) -> str:
        """Identiteit van 'deze plek, door deze regel gemarkeerd'.

        Bewust ZONDER de waargenomen waarde, zodat een entry op de negeerlijst blijft
        werken als de tekst licht verandert.
        """
        return _hash(self.regel_id, canonieke_locatie(self.locatie))

    @property
    def bewijs_hash(self) -> str:
        """Hash van alleen de waargenomen waarde.

        Een negeerlijst-entry mag deze vastpinnen: wijzigt de content, dan vervalt de
        onderdrukking automatisch en komt het signaal terug. Dat voorkomt dat de
        negeerlijst stilletjes echte fouten gaat verbergen.
        """
        return _hash(self.waargenomen)

    def naar_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["vingerafdruk"] = self.vingerafdruk
        d["bewijs_hash"] = self.bewijs_hash
        return d


def canonieke_locatie(locatie: dict[str, Any]) -> str:
    """Stabiele tekstvorm van een locatie, onafhankelijk van sleutelvolgorde."""
    return json.dumps(locatie, ensure_ascii=False, sort_keys=True)


def bepaal_eigenaar(soort: str) -> str:
    """Wie bepaalt wat juist is — de kernsplitsing uit STRATEGY.md.

    Een schrijfrichtlijn-afwijking kan de redactie zelf verbeteren: het juiste antwoord
    staat in de regel. Een inhoudelijke afwijking betreft een feit (bedrag, termijn,
    voorwaarde) waarbij de app niet kan weten welke kant klopt, ook niet bij 217 tegen 1.
    Geld en juridische voorwaarden wijzig je niet op statistiek.
    """
    return EIGENAAR_REDACTIE if soort == SOORT_SCHRIJFRICHTLIJN else EIGENAAR_KENNISEIGENAAR
