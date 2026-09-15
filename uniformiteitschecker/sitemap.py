"""Sitemap ontdekken, uitklappen en afbakenen tot de gekozen rubriek.

Alle functies werken op tekst die van buiten wordt aangereikt via een `haal`-callable,
zodat ze zonder netwerk te testen zijn.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Callable, Iterable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

# Een sitemap-index verwijst naar andere sitemaps; die klappen we uit tot deze diepte.
MAX_SITEMAP_DIEPTE = 3

Haler = Callable[[str], str | None]


def lees_robots(basis_url: str, haal: Haler) -> RobotFileParser:
    """Haal robots.txt op. Onbereikbaar telt als 'niets verboden, geen sitemap'."""
    robots = RobotFileParser()
    robots.set_url(urljoin(basis_url, "/robots.txt"))
    tekst = haal(urljoin(basis_url, "/robots.txt"))
    robots.parse(tekst.splitlines() if tekst else [])
    return robots


def _parse_sitemap(xml: str) -> tuple[list[str], list[str]]:
    """Splits een sitemap in (pagina-URL's, geneste sitemap-URL's).

    Bewust met een regex in plaats van een XML-parser: sitemaps in het wild hebben
    vaker een kapot prefix of een BOM dan dat ze strikt valide zijn, en we hebben
    alleen de <loc>-waarden nodig.
    """
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, flags=re.DOTALL | re.IGNORECASE)
    is_index = re.search(r"<sitemapindex", xml, flags=re.IGNORECASE) is not None
    schoon = [loc.strip() for loc in locs if loc.strip()]
    return ([], schoon) if is_index else (schoon, [])


def _klap_uit(start_url: str, haal: Haler) -> list[str]:
    """Lees één sitemap uit en volg de sitemaps waar hij naar verwijst."""
    urls: list[str] = []
    gezien: set[str] = set()
    te_doen = [(start_url, 0)]

    while te_doen:
        sitemap_url, diepte = te_doen.pop(0)
        if sitemap_url in gezien or diepte > MAX_SITEMAP_DIEPTE:
            continue
        gezien.add(sitemap_url)

        xml = haal(sitemap_url)
        if not xml:
            continue

        pagina_urls, sub_sitemaps = _parse_sitemap(xml)
        urls.extend(pagina_urls)
        te_doen.extend((sub, diepte + 1) for sub in sub_sitemaps)

    return urls


def verzamel_urls(basis_url: str, haal: Haler, robots: RobotFileParser | None = None) -> list[str]:
    """Ontdek de sitemap en geef alle pagina-URL's terug.

    Probeert achtereenvolgens de `Sitemap:`-regels uit robots.txt, /sitemap.xml en
    /sitemap_index.xml, en stopt bij de eerste die iets oplevert. Levert geen enkele
    bron iets op, dan een lege lijst; de aanroeper meldt dat.
    """
    if robots is None:
        robots = lees_robots(basis_url, haal)

    kandidaten = list(robots.site_maps() or [])
    kandidaten += [urljoin(basis_url, pad) for pad in ("/sitemap.xml", "/sitemap_index.xml")]

    for kandidaat in _uniek(kandidaten):
        urls = _klap_uit(kandidaat, haal)
        if urls:
            return _uniek(urls)

    return []


def _uniek(urls: Iterable[str]) -> list[str]:
    gezien: set[str] = set()
    resultaat = []
    for url in urls:
        if url not in gezien:
            gezien.add(url)
            resultaat.append(url)
    return resultaat


def _normaliseer_pad(pad: str) -> str:
    pad = "/" + pad.strip().strip("/")
    return pad if pad != "/" else "/"


def valt_onder(url: str, paden: Iterable[str]) -> bool:
    """Ligt `url` onder een van de geconfigureerde paden?

    Grenst op segmentniveau: /paspoort matcht /paspoort en /paspoort/kosten,
    maar niet /paspoortkosten.
    """
    url_pad = _normaliseer_pad(urlparse(url).path)
    for pad in paden:
        prefix = _normaliseer_pad(pad)
        if prefix == "/" or url_pad == prefix or url_pad.startswith(prefix + "/"):
            return True
    return False


def filter_op_paden(urls: Iterable[str], paden: Iterable[str]) -> list[str]:
    """Beperk tot de gekozen rubriek. Zonder paden: alles (bewuste keuze van de config)."""
    paden = list(paden)
    if not paden:
        return list(urls)
    return [url for url in urls if valt_onder(url, paden)]


def padstatistiek(urls: Iterable[str], diepte: int = 2) -> list[tuple[str, int]]:
    """Tel URL's per padprefix, zodat `verken` laat zien welke rubrieken er zijn."""
    teller: Counter[str] = Counter()
    for url in urls:
        segmenten = [s for s in urlparse(url).path.split("/") if s]
        if not segmenten:
            teller["/"] += 1
            continue
        prefix = "/" + "/".join(segmenten[:diepte])
        teller[prefix] += 1
    return sorted(teller.items(), key=lambda paar: (-paar[1], paar[0]))
