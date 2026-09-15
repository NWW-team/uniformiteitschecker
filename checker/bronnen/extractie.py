"""HTML omzetten naar een `Pagina`.

De pagina's hebben precies één `<main>`-element. Dat isoleren houdt menu's, kruimelpad
en footer buiten de analyse — anders zou elke pagina dezelfde boilerplate-afwijkingen
opleveren en verdrinkt het echte signaal.
"""

from __future__ import annotations

from ..model import EXTRACTIE_VERSIE, Pagina, Rij, Tabel
from .boom import Node, ontleed


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
    koppen: list[dict[str, object]] = []
    for niveau in (1, 2, 3):
        for node in main.vind_alle(f"h{niveau}"):
            tekst = node.tekst()
            if tekst:
                koppen.append({"niveau": niveau, "tekst": tekst})
    return koppen


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
        extractie_versie=EXTRACTIE_VERSIE,
    )
