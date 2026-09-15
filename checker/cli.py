"""Commandoregel van de uniformiteitschecker.

    python -m checker controleer --familie consulaire-tarieven --limiet 25
    python -m checker controleer --vanuit-snapshot data/snapshots/2026-09-15/...jsonl
    python -m checker invarianten
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

from .bronnen import snapshot
from .bronnen.extractie import extraheer_main, extraheer_tabellen
from .bronnen.ophalen import haal_op
from .bronnen.sitemap import filter_op_prefix, pagina_urls, sub_sitemaps
from .detectie import onderdruk, register
from .rapport.html import schrijf_rapport

REGELS_MAP = pathlib.Path("regels")
FINDINGS_MAP = pathlib.Path("data/findings")
RAPPORT_PAD = pathlib.Path("uitvoer/rapport.html")

# Steekproef voor het invariantencommando. De drempels zijn gemeten, niet gegokt:
# van de 218 landenpagina's heeft 52% een tarieftabel en 48% niet (landen zonder
# Nederlandse post die deze diensten levert), met gemiddeld 30 rijen per pagina die
# er wel een heeft. De drempels liggen daar ruim onder, zodat normale variatie de
# check niet laat afgaan maar een gebroken extractie (0 rijen) wel.
STEEKPROEF = 10
MIN_AANDEEL_MET_TABELLEN = 0.3
MIN_RIJEN_STEEKPROEF = 60


def laad_families() -> dict[str, dict]:
    config = yaml.safe_load((REGELS_MAP / "families.yaml").read_text(encoding="utf-8"))
    return {f["id"]: f for f in config["families"]}


def _cmd_controleer(args: argparse.Namespace) -> int:
    families = laad_families()

    if args.vanuit_snapshot:
        paginas = snapshot.lees(args.vanuit_snapshot)
        if not paginas:
            print("Snapshot is leeg.", file=sys.stderr)
            return 1
        familie = families[paginas[0].familie]
        problemen: list[str] = []
        snapshot_pad = pathlib.Path(args.vanuit_snapshot)
        print(f"Snapshot gelezen: {len(paginas)} pagina's uit {snapshot_pad}")
    else:
        if args.familie not in families:
            print(
                f"Onbekende familie {args.familie!r}; bekend: {sorted(families)}",
                file=sys.stderr,
            )
            return 1
        familie = families[args.familie]
        print(f"Pagina's ophalen voor familie {familie['id']}...")
        paginas, problemen = snapshot.bouw_snapshot(familie, limiet=args.limiet)
        if not paginas:
            print("Geen pagina's opgehaald.", file=sys.stderr)
            return 1
        snapshot_pad = snapshot.schrijf(paginas, familie["id"])
        print(f"Snapshot geschreven: {snapshot_pad} ({len(paginas)} pagina's)")

    for probleem in problemen:
        print(f"  probleem: {probleem}", file=sys.stderr)

    gevonden, waarschuwingen = register.draai(
        familie["detectoren"],
        paginas,
        min_zusters=familie.get("min_zusters", 5),
        min_eensgezind=familie.get("min_eensgezind", 0.8),
        max_paginas_zeldzaam=familie.get("max_paginas_zeldzaam", 4),
        min_eigen_labels=familie.get("min_eigen_labels", 3),
    )

    # De negeerlijst werkt op de bevindingen, niet in de detectoren: zo blijft
    # zichtbaar wat er onderdrukt is en waarom.
    uitkomst = onderdruk.pas_toe(gevonden, onderdruk.laad())
    bevindingen = uitkomst.overgebleven
    waarschuwingen = waarschuwingen + uitkomst.vervallen

    datum = snapshot_pad.parent.name
    findings_map = FINDINGS_MAP / datum
    findings_map.mkdir(parents=True, exist_ok=True)
    findings_pad = findings_map / f"{familie['id']}.json"
    findings_pad.write_text(
        json.dumps(
            {
                "familie": familie["id"],
                "datum": datum,
                "aantal_paginas": len(paginas),
                "waarschuwingen": waarschuwingen + problemen,
                "bevindingen": [b.naar_dict() for b in bevindingen],
                "onderdrukt": [
                    {**b.naar_dict(), "onderdrukt_om": e.get("reden", "")}
                    for b, e in uitkomst.onderdrukt
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    RAPPORT_PAD.parent.mkdir(parents=True, exist_ok=True)
    schrijf_rapport(
        RAPPORT_PAD,
        bevindingen=bevindingen,
        familie=familie["id"],
        datum=datum,
        aantal_paginas=len(paginas),
        waarschuwingen=waarschuwingen + problemen,
        onderdrukt=uitkomst.onderdrukt,
    )

    print(f"Bevindingen : {len(bevindingen)}")
    if uitkomst.onderdrukt:
        print(f"  onderdrukt: {len(uitkomst.onderdrukt)} via regels/negeerlijst.yaml")
    print(f"  geschreven: {findings_pad}")
    print(f"  rapport   : {RAPPORT_PAD}")
    for w in waarschuwingen:
        print(f"  let op: {w}")
    return 0


def _cmd_invarianten(args: argparse.Namespace) -> int:
    """Controleer of de site nog is zoals de app verwacht.

    Zonder deze check levert een frontend-update stilzwijgend een leeg rapport op — het
    ergst mogelijke faalgedrag voor een tool die vertrouwd moet worden. Daarom faalt dit
    commando hard en met uitleg.
    """
    familie = laad_families()[args.familie]
    fouten: list[str] = []

    index = haal_op("https://www.nederlandwereldwijd.nl/sitemap.xml", pauze=0)
    subs = sub_sitemaps(index)
    print(f"sub-sitemaps          : {len(subs)}")
    if len(subs) < 3:
        fouten.append(f"verwacht >=3 sub-sitemaps, gevonden {len(subs)}")

    urls = pagina_urls(haal_op(familie["sitemap"], pauze=0))
    print(f"URL's in paginasitemap: {len(urls)}")
    if len(urls) < 4000:
        fouten.append(f"verwacht >=4000 pagina-URL's, gevonden {len(urls)}")

    familie_urls = filter_op_prefix(urls, familie["pad_prefix"])
    print(f"URL's in familie      : {len(familie_urls)}")
    if len(familie_urls) < 200:
        fouten.append(
            f"verwacht >=200 URL's onder {familie['pad_prefix']}, "
            f"gevonden {len(familie_urls)}"
        )

    # Spreid de steekproef over de familie in plaats van de eerste paar landen te
    # pakken: niet elke landenpagina heeft tarieftabellen (Afghanistan heeft er geen),
    # dus een strengere eis per pagina zou legitieme variatie als storing melden.
    stap = max(1, len(familie_urls) // STEEKPROEF)
    steekproef = familie_urls[::stap][:STEEKPROEF]
    met_tabellen = 0
    totaal_rijen = 0

    for url in steekproef:
        try:
            main = extraheer_main(haal_op(url))
        except Exception as fout:
            fouten.append(f"{url}: {fout}")
            continue
        tabellen = extraheer_tabellen(main)
        rijen = sum(len(t.rijen) for t in tabellen)
        totaal_rijen += rijen
        if tabellen:
            met_tabellen += 1
        print(f"  {url.rsplit('/', 1)[-1]}: {len(tabellen)} tabellen, {rijen} rijen")

    print(f"pagina's met tabellen : {met_tabellen} van {len(steekproef)}")
    print(f"rijen in steekproef   : {totaal_rijen}")

    # Waar het echt om gaat: levert de extractie nog data op? Zo niet, dan is de
    # opbouw van de site gewijzigd en zou de app stilzwijgend een leeg rapport geven.
    if met_tabellen < len(steekproef) * MIN_AANDEEL_MET_TABELLEN:
        fouten.append(
            f"slechts {met_tabellen} van {len(steekproef)} pagina's leverde tabellen "
            f"op; normaal is dat ongeveer de helft"
        )
    if totaal_rijen < MIN_RIJEN_STEEKPROEF:
        fouten.append(
            f"verwacht >={MIN_RIJEN_STEEKPROEF} rijen in de steekproef, "
            f"gevonden {totaal_rijen}"
        )

    if fouten:
        print("\nINVARIANTEN GESCHONDEN -- de site is mogelijk gewijzigd:", file=sys.stderr)
        for f in fouten:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nAlle invarianten in orde.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m checker",
        description="Signaleert afwijkingen in uniformiteit op de websites van NederlandWereldwijd.",
    )
    sub = parser.add_subparsers(dest="commando", required=True)

    p = sub.add_parser("controleer", help="pagina's ophalen, afwijkingen detecteren, rapport maken")
    p.add_argument("--familie", default="consulaire-tarieven")
    p.add_argument("--limiet", type=int, default=None, help="alleen de eerste N pagina's")
    p.add_argument(
        "--vanuit-snapshot",
        default=None,
        help="detecteer op een bestaande snapshot, zonder netwerk",
    )
    p.set_defaults(func=_cmd_controleer)

    p = sub.add_parser("invarianten", help="controleer of de site nog is zoals verwacht")
    p.add_argument("--familie", default="consulaire-tarieven")
    p.set_defaults(func=_cmd_invarianten)

    args = parser.parse_args(argv)
    return args.func(args)
