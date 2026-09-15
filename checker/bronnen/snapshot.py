"""Snapshot schrijven en lezen.

De genormaliseerde snapshot gaat wél de repo in (ruwe HTML niet): hij is klein,
diffbaar, en is het enige dat spoor 2 en 3 nodig hebben. Daarmee zijn detectie en
rapportage volledig offline te ontwikkelen tegen exact de data waarop het vorige
rapport gebaseerd was — wat het ephemeral-container-probleem oplost.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

from ..model import Pagina
from . import sitemap
from .extractie import lees_pagina
from .ophalen import haal_op

SNAPSHOT_MAP = pathlib.Path("data/snapshots")


def vandaag() -> str:
    return dt.date.today().isoformat()


def bouw_snapshot(familie: dict, *, limiet: int | None = None,
                  gebruik_cache: bool = True) -> tuple[list[Pagina], list[str]]:
    """Haal een familie op en zet hem om in `Pagina`-objecten.

    Geeft de pagina's terug plus een lijst met problemen; één onleesbare pagina mag een
    run van 218 pagina's niet laten klappen, maar moet wel zichtbaar blijven.
    """
    index_xml = haal_op(familie["sitemap"], gebruik_cache=gebruik_cache, pauze=0)
    urls = sitemap.filter_op_prefix(sitemap.pagina_urls(index_xml), familie["pad_prefix"])
    if limiet is not None:
        urls = urls[:limiet]

    nu = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    paginas: list[Pagina] = []
    problemen: list[str] = []

    for url in urls:
        try:
            html = haal_op(url, gebruik_cache=gebruik_cache)
            paginas.append(
                lees_pagina(
                    html,
                    url,
                    familie=familie["id"],
                    familie_sleutel=sitemap.familie_sleutel(url),
                    bron_id=familie.get("bron_id", "nww-nl"),
                    taal=familie.get("taal", "nl"),
                    opgehaald_op=nu,
                )
            )
        except Exception as fout:
            problemen.append(f"{url}: {fout}")

    return paginas, problemen


def schrijf(paginas: list[Pagina], familie_id: str, *, datum: str | None = None) -> pathlib.Path:
    """Schrijf de snapshot als JSONL, gesorteerd op URL voor leesbare git-diffs."""
    map_ = SNAPSHOT_MAP / (datum or vandaag())
    map_.mkdir(parents=True, exist_ok=True)
    pad = map_ / f"{familie_id}.jsonl"
    regels = [p.naar_json() for p in sorted(paginas, key=lambda p: p.url)]
    pad.write_text("\n".join(regels) + "\n", encoding="utf-8")
    return pad


def lees(pad: str | pathlib.Path) -> list[Pagina]:
    """Lees een snapshot terug — de ingang voor offline ontwikkelen."""
    regels = pathlib.Path(pad).read_text(encoding="utf-8").splitlines()
    return [Pagina.uit_dict(json.loads(r)) for r in regels if r.strip()]


def nieuwste_snapshot(familie_id: str) -> pathlib.Path | None:
    """Het meest recente snapshotbestand voor een familie, of None."""
    kandidaten = sorted(SNAPSHOT_MAP.glob(f"*/{familie_id}.jsonl"))
    return kandidaten[-1] if kandidaten else None
