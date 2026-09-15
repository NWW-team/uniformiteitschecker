"""Content uitlezen: beleefd ophalen en omzetten naar platte tekst.

De app leest een publieke website van een ander team. Daarom: robots.txt volgen,
één verzoek per seconde, een herkenbare User-Agent, een harde bovengrens op het
aantal pagina's, en een cache op schijf zodat herhaald analyseren geen nieuw
verkeer veroorzaakt.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .model import Pagina, Site
from .sitemap import filter_op_paden, lees_robots, verzamel_urls

log = logging.getLogger(__name__)

USER_AGENT = (
    "UniformiteitscheckerBot/0.1 (webredactie NederlandWereldwijd; "
    "+https://github.com/NWW-team/uniformiteitschecker)"
)
WACHTTIJD_SECONDEN = 1.0
MAX_POGINGEN = 4

# Blokken die op elke pagina hetzelfde zijn; die zouden anders elke term dubbel tellen.
STRUCTUUR_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "aside", "form", "iframe")
RUIS_WOORDEN = ("cookie", "skiplink", "skip-link", "breadcrumb", "kruimelpad", "menu", "social")
INHOUD_SELECTORS = ("main", "[role=main]", "article", "#content", ".content", "#main")


@dataclass(slots=True)
class Ophaler:
    """HTTP-client die zich aan de afspraken houdt en antwoorden bewaart."""

    cache_map: Path
    wachttijd: float = WACHTTIJD_SECONDEN
    client: httpx.Client | None = None
    _laatste_verzoek: float = 0.0

    def __post_init__(self) -> None:
        self.cache_map = Path(self.cache_map)
        self.cache_map.mkdir(parents=True, exist_ok=True)
        if self.client is None:
            self.client = httpx.Client(
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
                follow_redirects=True,
            )

    def _cache_paden(self, url: str) -> tuple[Path, Path]:
        sleutel = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_map / f"{sleutel}.html", self.cache_map / f"{sleutel}.json"

    def _wacht(self) -> None:
        verstreken = time.monotonic() - self._laatste_verzoek
        if verstreken < self.wachttijd:
            time.sleep(self.wachttijd - verstreken)
        self._laatste_verzoek = time.monotonic()

    def haal(self, url: str) -> str | None:
        """Haal een URL op. Geeft None bij een fout, zodat één kapotte pagina de run niet sloopt."""
        inhoud_pad, meta_pad = self._cache_paden(url)
        headers: dict[str, str] = {}
        if meta_pad.exists() and inhoud_pad.exists():
            meta = json.loads(meta_pad.read_text(encoding="utf-8"))
            if meta.get("etag"):
                headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                headers["If-Modified-Since"] = meta["last_modified"]

        for poging in range(MAX_POGINGEN):
            self._wacht()
            try:
                antwoord = self.client.get(url, headers=headers)
            except httpx.HTTPError as fout:
                log.warning("Ophalen mislukt (%s): %s", url, fout)
                if poging == MAX_POGINGEN - 1:
                    return self._uit_cache(inhoud_pad)
                time.sleep(2**poging)
                continue

            if antwoord.status_code == 304:
                log.debug("Ongewijzigd, uit cache: %s", url)
                return self._uit_cache(inhoud_pad)

            if antwoord.status_code == 429 or antwoord.status_code >= 500:
                pauze = float(antwoord.headers.get("Retry-After", 2**poging))
                log.warning("Status %s op %s, wacht %.0fs", antwoord.status_code, url, pauze)
                time.sleep(pauze)
                continue

            if antwoord.status_code >= 400:
                log.warning("Status %s op %s, overgeslagen", antwoord.status_code, url)
                return None

            inhoud_pad.write_text(antwoord.text, encoding="utf-8")
            meta_pad.write_text(
                json.dumps(
                    {
                        "url": url,
                        "etag": antwoord.headers.get("ETag", ""),
                        "last_modified": antwoord.headers.get("Last-Modified", ""),
                        "opgehaald_op": _nu(),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return antwoord.text

        return self._uit_cache(inhoud_pad)

    @staticmethod
    def _uit_cache(inhoud_pad: Path) -> str | None:
        return inhoud_pad.read_text(encoding="utf-8") if inhoud_pad.exists() else None

    def sluit(self) -> None:
        if self.client is not None:
            self.client.close()


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_ruis(tag) -> bool:
    kenmerken = " ".join(
        [" ".join(tag.get("class", [])), tag.get("id", ""), tag.get("data-module", "")]
    ).lower()
    return any(woord in kenmerken for woord in RUIS_WOORDEN)


def extraheer(html: str, url: str, site: Site) -> Pagina:
    """Zet ruwe HTML om in platte tekst, zonder navigatie en andere paginaruis."""
    soep = BeautifulSoup(html, "html.parser")

    for tag in soep.find_all(STRUCTUUR_TAGS):
        tag.decompose()
    for tag in soep.find_all(True):
        if _is_ruis(tag):
            tag.decompose()

    inhoud = None
    for selector in INHOUD_SELECTORS:
        inhoud = soep.select_one(selector)
        if inhoud is not None:
            break
    if inhoud is None:
        inhoud = soep.body or soep

    kop = inhoud.find("h1") or soep.find("h1")
    titel = kop.get_text(" ", strip=True) if kop else (soep.title.get_text(strip=True) if soep.title else "")

    regels = [regel.strip() for regel in inhoud.get_text("\n").splitlines()]
    tekst = "\n".join(regel for regel in regels if regel)

    return Pagina(url=url, taal=site.taal, site=site.id, titel=titel, tekst=tekst, opgehaald_op=_nu())


def crawl_site(site: Site, ophaler: Ophaler, max_paginas: int) -> list[Pagina]:
    """Haal de afgebakende rubriek van één site op."""
    robots = lees_robots(site.basis_url, ophaler.haal)
    alle_urls = verzamel_urls(site.basis_url, ophaler.haal, robots)
    if not alle_urls:
        log.error("Geen sitemap gevonden voor %s; niets opgehaald", site.basis_url)
        return []

    urls = filter_op_paden(alle_urls, site.paden)
    toegestaan = [url for url in urls if robots.can_fetch(USER_AGENT, url)]
    if len(toegestaan) < len(urls):
        log.info("%d URL's overgeslagen vanwege robots.txt", len(urls) - len(toegestaan))

    log.info(
        "%s: %d URL's in de sitemap, %d binnen de afbakening, maximaal %d worden opgehaald",
        site.id, len(alle_urls), len(toegestaan), max_paginas,
    )

    paginas = []
    for url in sorted(toegestaan)[:max_paginas]:
        html = ophaler.haal(url)
        if html:
            paginas.append(extraheer(html, url, site))
    return paginas


def schrijf_corpus(paginas: list[Pagina], pad: Path) -> None:
    """Eén pagina per regel, gesorteerd op URL, zodat runs onderling diffbaar zijn."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    regels = [
        json.dumps(pagina.als_dict(), ensure_ascii=False, sort_keys=True)
        for pagina in sorted(paginas, key=lambda p: p.url)
    ]
    pad.write_text("\n".join(regels) + ("\n" if regels else ""), encoding="utf-8")


def lees_corpus(map_pad: Path) -> list[Pagina]:
    """Lees alle *.jsonl uit een corpusmap."""
    paginas = []
    for bestand in sorted(Path(map_pad).glob("*.jsonl")):
        for regel in bestand.read_text(encoding="utf-8").splitlines():
            if regel.strip():
                paginas.append(Pagina.uit_dict(json.loads(regel)))
    return paginas
