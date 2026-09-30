"""HTML omzetten naar een `Pagina`.

De pagina's hebben precies één `<main>`-element. Dat isoleren houdt menu's, kruimelpad
en footer buiten de analyse — anders zou elke pagina dezelfde boilerplate-afwijkingen
opleveren en verdrinkt het echte signaal.
"""

from __future__ import annotations

import re

from ..model import EXTRACTIE_VERSIE, Pagina, Rij, Sectie, Tabel
from .boom import NEGEER_INHOUD, Node, ontleed

_KOPNIVEAUS = {f"h{n}": n for n in range(1, 7)}

# Elementen die een nieuwe regel beginnen. Zinnen vergelijken gaat per regel, dus een
# opsommingsteken zonder punt mag niet aan de volgende alinea vastplakken.
_BLOKTAGS = {
    "p", "li", "ul", "ol", "div", "section", "table", "tr", "br", "blockquote",
    *_KOPNIVEAUS,
}

# De checklist-filtertool rendert zonder JavaScript een foutmelding. Die staat op elke
# pagina en is geen redactionele tekst.
_FILTERTOOL_RUIS = re.compile(
    r"Fout:\s*JavaScript staat uit.*?U ziet dan de filtertool\.", re.S
)


class ExtractieFout(Exception):
    """De markup is niet zoals verwacht.

    Bewust een harde fout: als de site verandert en we vangen dit af, levert de app
    stilzwijgend een leeg rapport op. Dat is het ergst mogelijke faalgedrag voor een
    tool die vertrouwd moet worden.
    """


def extraheer_main(html: str) -> Node:
    """Geef het ene `<main>`-element terug, of faal met uitleg."""
    wortel = ontleed(html)
    mains = wortel.vind_alle("main")
    if len(mains) != 1:
        raise ExtractieFout(
            f"verwacht precies 1 <main>-element, gevonden {len(mains)}; "
            "de opbouw van de site is mogelijk gewijzigd"
        )
    return mains[0]


def extraheer_koppen(main: Node) -> list[dict[str, object]]:
    """Alle koppen h1 t/m h6, in documentvolgorde — zo is een overgeslagen niveau te zien."""
    koppen: list[dict[str, object]] = []

    def loop(node: Node) -> None:
        for kind in node.kinderen:
            if not isinstance(kind, Node) or kind.tag in NEGEER_INHOUD:
                continue
            if kind.tag in _KOPNIVEAUS:
                tekst = kind.tekst()
                if tekst:
                    koppen.append({"niveau": _KOPNIVEAUS[kind.tag], "tekst": tekst})
            else:
                loop(kind)

    loop(main)
    return koppen


def _uitklapknop(node: Node) -> Node | None:
    """De knop die een uitklappaneel opent, als deze kop er een bevat."""
    for knop in node.vind_alle("button"):
        if knop.attrs.get("aria-controls"):
            return knop
    return None


def _is_paneel(node: Node) -> bool:
    return node.attrs.get("data-testid") == "accordion-panel" or node.attrs.get(
        "id", ""
    ).startswith("accordion-panel")


def _pseudokop(node: Node) -> str | None:
    """Een alinea die alleen uit vette tekst bestaat, gebruikt als kopje."""
    if node.tag != "p":
        return None
    elementen = [k for k in node.kinderen if isinstance(k, Node)]
    losse_tekst = "".join(k for k in node.kinderen if isinstance(k, str)).strip()
    if len(elementen) == 1 and elementen[0].tag in ("strong", "b") and not losse_tekst:
        return elementen[0].tekst() or None
    return None


def _schoon(delen: list[str]) -> str:
    tekst = _FILTERTOOL_RUIS.sub(" ", "".join(delen))
    regels = (re.sub(r"\s+([.,;:!?])", r"\1", " ".join(r.split())) for r in tekst.split("\n"))
    return "\n".join(r for r in regels if r)


def extraheer_secties(main: Node) -> list[Sectie]:
    """Deel een stappenplanpagina op in stappen en uitklapparagrafen.

    Elke `h2` opent een stap; de tekst direct eronder is een sectie zonder titel. Een
    kop met een uitklapknop (`<h3><button aria-controls=...>`) opent een
    uitklapparagraaf, waarvan de tekst in het bijbehorende paneel staat. Kopjes binnen
    een paneel blijven bij die uitklap, maar worden met hun niveau vastgelegd: of daar
    een h4 of een h3 staat, is precies wat de koppenstructuurcheck wil weten.
    """
    secties: list[Sectie] = []
    teksten: dict[int, list[str]] = {}
    panelen: dict[str, Sectie] = {}
    staat: dict[str, Sectie | None] = {"doel": None, "laatste_uitklap": None}

    def nieuw(sectie: Sectie) -> Sectie:
        secties.append(sectie)
        teksten[id(sectie)] = []
        return sectie

    def schrijf(tekst: str) -> None:
        doel = staat["doel"]
        if doel is not None:
            teksten[id(doel)].append(tekst)

    def open_uitklap(knop: Node, niveau: int) -> None:
        stap = staat["doel"].stap if staat["doel"] is not None else ""
        uitklap = nieuw(Sectie(stap=stap, titel=knop.tekst(), niveau=niveau))
        panelen[knop.attrs["aria-controls"]] = uitklap
        staat["laatste_uitklap"] = uitklap

    def loop(node: Node, in_paneel: bool) -> None:
        for kind in node.kinderen:
            if isinstance(kind, str):
                schrijf(kind)
                continue
            if kind.tag in NEGEER_INHOUD:
                continue

            if kind.tag in _KOPNIVEAUS:
                niveau = _KOPNIVEAUS[kind.tag]
                tekst = kind.tekst()
                knop = _uitklapknop(kind)
                if in_paneel:
                    doel = staat["doel"]
                    if doel is not None and tekst:
                        doel.koppen.append(
                            {"niveau": niveau, "tekst": tekst, "uitklap": knop is not None}
                        )
                    schrijf(f"\n{tekst}\n")
                elif niveau == 1:
                    continue
                elif niveau == 2:
                    staat["doel"] = nieuw(Sectie(stap=tekst))
                elif knop is not None:
                    open_uitklap(knop, niveau)
                else:
                    doel = staat["doel"]
                    if doel is not None and tekst:
                        doel.koppen.append({"niveau": niveau, "tekst": tekst, "uitklap": False})
                    schrijf(f"\n{tekst}\n")
                continue

            if kind.tag == "button" and kind.attrs.get("aria-controls") and not in_paneel:
                # Een uitklapknop die niet in een kop staat: geen kopniveau.
                open_uitklap(kind, 0)
                continue

            if _is_paneel(kind) and not in_paneel:
                paneel = panelen.get(kind.attrs.get("id", "")) or staat["laatste_uitklap"]
                vorige = staat["doel"]
                staat["doel"] = paneel
                loop(kind, True)
                staat["doel"] = vorige
                continue

            pseudo = _pseudokop(kind) if in_paneel else None
            if pseudo and staat["doel"] is not None:
                staat["doel"].koppen.append({"niveau": 0, "tekst": pseudo, "uitklap": False})

            blok = kind.tag in _BLOKTAGS
            if blok:
                schrijf("\n")
            else:
                schrijf(" ")
            loop(kind, in_paneel)
            schrijf("\n" if blok else " ")

    staat["doel"] = nieuw(Sectie(stap=""))
    loop(main, False)

    for sectie in secties:
        sectie.tekst = _schoon(teksten[id(sectie)])
    # Een lege inleiding (h1 direct gevolgd door de eerste stap) zegt niets.
    return [s for s in secties if s.titel or s.tekst or s.stap]


def extraheer_tabellen(main: Node) -> list[Tabel]:
    """Lees `<table>`-elementen als kolomkoppen plus label/waarde-rijen.

    De tarieftabellen zijn schoon semantisch: `<thead><th scope="col">` voor de
    kolommen, `<tbody><tr><td>` voor de rijen. Alleen tweekolomsrijen zijn zinvol
    (label, bedrag); andere rijvormen slaan we over in plaats van te gokken.
    """
    tabellen: list[Tabel] = []
    for index, node in enumerate(main.vind_alle("table")):
        kolomkoppen = [th.tekst() for th in node.vind_alle("th")]
        rijen: list[Rij] = []
        for tr in node.vind_alle("tr"):
            cellen = [td.tekst() for td in tr.directe_kinderen("td")]
            if len(cellen) == 2 and cellen[0] and cellen[1]:
                rijen.append(Rij(label=cellen[0], waarde_rauw=cellen[1]))
        tabellen.append(Tabel(index=index, kolomkoppen=kolomkoppen, rijen=rijen))
    return tabellen


def lees_pagina(
    html: str,
    url: str,
    *,
    familie: str,
    familie_sleutel: str,
    bron_id: str = "nww-nl",
    taal: str = "nl",
    opgehaald_op: str = "",
    http_status: int = 200,
) -> Pagina:
    """Zet ruwe HTML om in het `Pagina`-contract."""
    main = extraheer_main(html)
    koppen = extraheer_koppen(main)
    titel = next((k["tekst"] for k in koppen if k["niveau"] == 1), "")
    return Pagina(
        url=url,
        bron_id=bron_id,
        taal=taal,
        familie=familie,
        familie_sleutel=familie_sleutel,
        titel=str(titel),
        opgehaald_op=opgehaald_op,
        http_status=http_status,
        koppen=koppen,
        # `tekst` wordt in stap 1 nog niet gebruikt, maar gaat wel de snapshot in:
        # dan hoeft spoor 1 niet opnieuw te crawlen als de terminologiedetector komt.
        tekst=main.tekst(),
        tabellen=extraheer_tabellen(main),
        secties=extraheer_secties(main),
        extractie_versie=EXTRACTIE_VERSIE,
    )
