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


_GLOBE = (
    '<svg class="rhc-sitekop__globe" viewBox="0 0 48 48" width="44" height="44" '
    'aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2">'
    '<circle cx="24" cy="24" r="20"/>'
    '<ellipse cx="24" cy="24" rx="8.5" ry="20"/>'
    '<path d="M4 24h40M7 14h34M7 34h34"/></svg>'
)


def sitekop(ondertitel: str = "Uniformiteitschecker") -> str:
    """Blauwe sitekop met wereldbol, in de stijl van nederlandwereldwijd.nl."""
    return (
        '<header class="rhc-sitekop"><div class="rhc-sitekop__binnen">'
        f'<span class="rhc-sitekop__logo">{_GLOBE}'
        '<span class="rhc-sitekop__naam">Nederland<br>Wereldwijd</span></span>'
        f'<span class="rhc-sitekop__sub">{ondertitel}</span>'
        "</div></header>"
    )
