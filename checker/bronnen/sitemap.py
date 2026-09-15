"""URL's vinden via de sitemap.

`robots.txt` van beide sites verwijst naar een sitemapindex en staat het lezen van
normale pagina's toe; alleen `/zoeken?*`, `/search?*` en `/api/*` zijn uitgesloten. We
lezen dus de sitemap in plaats van links te volgen: dat is sneller, volledig, en belast
de site minder.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _locaties(xml: str, element: str) -> list[str]:
    wortel = ET.fromstring(xml.strip())
    return [
        (loc.text or "").strip()
        for loc in wortel.findall(f"sm:{element}/sm:loc", _NS)
        if (loc.text or "").strip()
    ]


def sub_sitemaps(index_xml: str) -> list[str]:
    """De sub-sitemaps uit een sitemapindex."""
    return _locaties(index_xml, "sitemap")


def pagina_urls(sitemap_xml: str) -> list[str]:
    """De pagina-URL's uit een gewone sitemap."""
    return _locaties(sitemap_xml, "url")


def filter_op_prefix(urls: list[str], pad_prefix: str) -> list[str]:
    """Houd alleen URL's waarvan het pad met `pad_prefix` begint.

    Vergelijkt op het pad na het domein, zodat een familie als
    `/consulaire-tarieven/` exact te selecteren is.
    """
    genormaliseerd = "/" + pad_prefix.strip("/") + "/"
    gevonden = [u for u in urls if _pad(u).startswith(genormaliseerd)]
    return sorted(set(gevonden))


def _pad(url: str) -> str:
    zonder_schema = url.split("://", 1)[-1]
    schuine_streep = zonder_schema.find("/")
    return zonder_schema[schuine_streep:] if schuine_streep != -1 else "/"


def familie_sleutel(url: str) -> str:
    """Het laatste padsegment — voor deze families is dat het land."""
    return _pad(url).rstrip("/").rsplit("/", 1)[-1]
