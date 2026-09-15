"""Gedeelde Rijkshuisstijl-CSS voor beide rapportsporen.

Eén stijlblok, ingeladen door zowel `checker/rapport/html.py` als
`uniformiteitschecker/rapport.py`, zodat de twee rapporten niet meer elk hun eigen,
onderling afwijkende palet hebben. Zie `rijkshuisstijl.css` voor de herkomst van de
tokens.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_CSS_PAD = Path(__file__).parent / "rijkshuisstijl.css"


@lru_cache(maxsize=1)
def laad_css() -> str:
    """Lees de gedeelde stijl. Gecachet: beide rapporten lezen dezelfde string."""
    return _CSS_PAD.read_text(encoding="utf-8")
