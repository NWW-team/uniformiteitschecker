"""Opdrachtregel: verken | crawl | check.

`verken` raakt alleen de sitemap aan, zodat je een rubriek kunt kiezen voordat er
ook maar één pagina wordt opgehaald.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .configuratie import laad_sites
from .model import PAGINAS, REGELS, SIGNALEN, aantal
from .crawler import Ophaler, crawl_site, lees_corpus, schrijf_corpus
from .rapport import samenvatting, schrijf_html, schrijf_json
from .regels import controleer_alles, laad_regels
from .sitemap import filter_op_paden, lees_robots, padstatistiek, verzamel_urls

STANDAARD_SITES = Path("config/sites.yaml")
STANDAARD_TERMEN = Path("config/termen.yaml")
STANDAARD_CORPUS = Path("corpus")
STANDAARD_RAPPORT = Path("rapport")
STANDAARD_CACHE = Path(".cache")


def _log_instellen(uitgebreid: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if uitgebreid else logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )


def opdracht_verken(args: argparse.Namespace) -> int:
    """Toon welke rubrieken er zijn, zonder paginacontent op te halen."""
    instellingen = laad_sites(args.sites)
    ophaler = Ophaler(cache_map=args.cache)
    gevonden = 0
    try:
        for site in instellingen.sites:
            robots = lees_robots(site.basis_url, ophaler.haal)
            urls = verzamel_urls(site.basis_url, ophaler.haal, robots)
            if not urls:
                print(f"\n{site.domein}: geen sitemap gevonden.")
                continue

            gevonden += 1
            binnen = filter_op_paden(urls, site.paden)
            print(f"\n{site.domein}  {len(urls)} URL's in de sitemap")
            if site.paden:
                print(f"  huidige afbakening ({', '.join(site.paden)}): {len(binnen)} URL's")
            print(f"  rubrieken op paddiepte {args.diepte}:")
            for prefix, telling in padstatistiek(urls, args.diepte)[: args.top]:
                print(f"    {prefix:<58} {telling:>6}")
    finally:
        ophaler.sluit()

    if not gevonden:
        print(
            "\nGeen enkele sitemap kon worden gelezen. Controleer of deze omgeving "
            "naar buiten mag; anders draait de workflow in GitHub Actions wel.",
            file=sys.stderr,
        )
        return 1

    print("\nZet de gekozen paden onder 'paden' in", args.sites)
    return 0


def opdracht_crawl(args: argparse.Namespace) -> int:
    instellingen = laad_sites(args.sites)

    # Zonder afbakening zou dit de hele site van duizenden pagina's ophalen. Dat is
    # nooit de bedoeling van een run die je per ongeluk start, dus dat moet expliciet.
    zonder_paden = [site.id for site in instellingen.sites if not site.paden]
    if zonder_paden and not args.hele_site:
        print(
            f"Geen afbakening ingesteld voor: {', '.join(zonder_paden)}.\n"
            f"Zet 'paden' in {args.sites} (draai 'verken' om te zien welke er zijn), "
            "of gebruik --hele-site als je bewust alles wilt ophalen.",
            file=sys.stderr,
        )
        return 2

    max_paginas = args.max_paginas or instellingen.max_paginas_per_site
    ophaler = Ophaler(cache_map=args.cache)
    totaal = 0
    try:
        for site in instellingen.sites:
            paginas = crawl_site(site, ophaler, max_paginas)
            schrijf_corpus(paginas, Path(args.uit) / f"{site.id}.jsonl")
            print(f"{site.id}: {len(paginas)} pagina's opgehaald")
            totaal += len(paginas)
    finally:
        ophaler.sluit()

    if not totaal:
        print("Er is niets opgehaald. Controleer de afbakening met 'verken'.", file=sys.stderr)
        return 1
    return 0


def opdracht_check(args: argparse.Namespace) -> int:
    regels = laad_regels(args.regels)
    paginas = lees_corpus(args.corpus)
    if not paginas:
        print(f"Geen pagina's gevonden in {args.corpus}. Draai eerst 'crawl'.", file=sys.stderr)
        return 1

    bevindingen = controleer_alles(paginas, regels)

    afbakening = None
    if Path(args.sites).exists():
        afbakening = laad_sites(args.sites).afbakening

    uit = Path(args.uit)
    schrijf_json(bevindingen, uit / "bevindingen.json")
    schrijf_html(bevindingen, paginas, uit / "rapport.html", afbakening)

    print(f"{aantal(len(paginas), *PAGINAS)} gecontroleerd tegen {aantal(len(regels), *REGELS)}")
    if not bevindingen:
        print("Geen afwijkingen gevonden.")
    else:
        getroffen = len({b.url for b in bevindingen})
        print(f"{aantal(len(bevindingen), *SIGNALEN)} op {aantal(getroffen, *PAGINAS)}:\n")
        for regel_id, treffers, paginas_met in samenvatting(bevindingen):
            print(
                f"  {regel_id:<40} {treffers:>4} {SIGNALEN[treffers != 1]:<8}"
                f" op {paginas_met:>3} {PAGINAS[paginas_met != 1]}"
            )
    print(f"\nRapport: {uit / 'rapport.html'}")

    return 1 if (bevindingen and args.strict) else 0


def bouw_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uniformiteitschecker",
        description="Signaleert afwijkingen in uniformiteit op de websites van NederlandWereldwijd.",
    )
    parser.add_argument("-v", "--uitgebreid", action="store_true", help="Meer logregels.")
    sub = parser.add_subparsers(dest="opdracht", required=True)

    p_verken = sub.add_parser("verken", help="Toon de rubrieken uit de sitemap; haalt geen pagina's op.")
    p_verken.add_argument("--sites", default=STANDAARD_SITES, type=Path)
    p_verken.add_argument("--cache", default=STANDAARD_CACHE, type=Path)
    p_verken.add_argument("--diepte", default=2, type=int, help="Aantal padsegmenten per rubriek.")
    p_verken.add_argument("--top", default=25, type=int, help="Hoeveel rubrieken tonen.")
    p_verken.set_defaults(functie=opdracht_verken)

    p_crawl = sub.add_parser("crawl", help="Haal de afgebakende rubriek op.")
    p_crawl.add_argument("--sites", default=STANDAARD_SITES, type=Path)
    p_crawl.add_argument("--cache", default=STANDAARD_CACHE, type=Path)
    p_crawl.add_argument("--uit", default=STANDAARD_CORPUS, type=Path)
    p_crawl.add_argument(
        "--max-paginas",
        type=int,
        default=None,
        dest="max_paginas",
        help="Overschrijf max_paginas_per_site uit de configuratie, bijvoorbeeld voor een proefrun.",
    )
    p_crawl.add_argument(
        "--hele-site",
        action="store_true",
        dest="hele_site",
        help="Haal alles op, ook zonder afbakening in 'paden'. Bewuste keuze, geen standaard.",
    )
    p_crawl.set_defaults(functie=opdracht_crawl)

    p_check = sub.add_parser("check", help="Controleer het corpus tegen de termenlijst.")
    p_check.add_argument("--corpus", default=STANDAARD_CORPUS, type=Path)
    p_check.add_argument("--regels", default=STANDAARD_TERMEN, type=Path)
    p_check.add_argument("--sites", default=STANDAARD_SITES, type=Path)
    p_check.add_argument("--uit", default=STANDAARD_RAPPORT, type=Path)
    p_check.add_argument(
        "--strict", action="store_true", help="Exitcode 1 bij bevindingen (voor gebruik in een workflow)."
    )
    p_check.set_defaults(functie=opdracht_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = bouw_parser().parse_args(argv)
    _log_instellen(args.uitgebreid)
    try:
        return args.functie(args)
    except (ValueError, OSError) as fout:
        print(f"Fout: {fout}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
