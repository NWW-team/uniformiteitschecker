"""Nette HTTP-client met schijfcache.

We crawlen de site van onze eigen organisatie, dus de User-Agent is herkenbaar en
herleidbaar. De cache maakt het mogelijk om de extractie en detectie vrij te itereren
zonder de site opnieuw te belasten; hij staat in `.cache/` en gaat niet de repo in.
"""

from __future__ import annotations

import hashlib
import pathlib
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "uniformiteitschecker/0.1 "
    "(+https://github.com/NWW-team/uniformiteitschecker; webredactie NederlandWereldwijd)"
)

CACHE_MAP = pathlib.Path(".cache/http")

# Eén verzoek per seconde: ruim binnen wat een site van deze omvang aankan.
PAUZE_SECONDEN = 1.0
MAX_POGINGEN = 3


class OphaalFout(Exception):
    """De pagina kon niet opgehaald worden."""


def _cachepad(url: str) -> pathlib.Path:
    return CACHE_MAP / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".html")


def haal_op(url: str, *, gebruik_cache: bool = True, pauze: float = PAUZE_SECONDEN) -> str:
    """Haal één URL op, met cache en retry.

    Retry gebruikt oplopende wachttijd; bij een 404 is opnieuw proberen zinloos, dus
    die faalt direct.
    """
    cache = _cachepad(url)
    if gebruik_cache and cache.exists():
        return cache.read_text(encoding="utf-8")

    laatste: Exception | None = None
    for poging in range(MAX_POGINGEN):
        try:
            verzoek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(verzoek, timeout=30) as antwoord:
                html = antwoord.read().decode("utf-8", "replace")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(html, encoding="utf-8")
            if pauze:
                time.sleep(pauze)
            return html
        except urllib.error.HTTPError as fout:
            if fout.code == 404:
                raise OphaalFout(f"{url}: 404 niet gevonden") from fout
            laatste = fout
        except Exception as fout:  # netwerkfouten, timeouts
            laatste = fout
        time.sleep(2 ** poging)

    raise OphaalFout(f"{url}: {laatste}")
