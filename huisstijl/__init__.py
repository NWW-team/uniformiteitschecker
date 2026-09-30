"""Gedeelde Rijkshuisstijl-CSS voor beide rapportsporen.

Eén stijlblok, ingeladen door zowel `checker/rapport/html.py` als
`uniformiteitschecker/rapport.py`. Het bestaat uit de officiële, onveranderde
Rijkshuisstijl Community (design tokens, componenten-CSS en het lettertype, zie
`vendor/LEESMIJ.md`) plus `rapport.css` voor de indeling van het rapport.

Rapporten zijn één zelfstandig HTML-bestand: de CSS en het lettertype worden ingesloten
(base64), zodat er geen los verzoek naar een CDN of ander bestand nodig is. De tokens
staan op de klasse `hemelblauw`, die op `<body>` moet staan.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

MAP = Path(__file__).parent
_VENDOR = MAP / "vendor"

#: Klasse voor `<body>`: zonder deze zijn alle --rhc-variabelen leeg.
THEMA_KLASSE = "hemelblauw"

# Alleen de latin-subset, in de drie gewichten die de tokens gebruiken.
_LETTERS = (400, 600, 700)


def _lettertype_css() -> str:
    blokken = []
    for gewicht in _LETTERS:
        data = (_VENDOR / "fonts" / f"fira-sans-latin-{gewicht}-normal.woff2").read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        blokken.append(
            '@font-face{font-family:"Fira Sans";font-style:normal;font-display:swap;'
            f"font-weight:{gewicht};src:url(data:font/woff2;base64,{b64}) format(\"woff2\");}}"
        )
    return "\n".join(blokken)


@lru_cache(maxsize=1)
def laad_css() -> str:
    """Lettertype, tokens, componenten en rapportindeling als één string. Gecachet."""
    delen = [
        _lettertype_css(),
        (_VENDOR / "rhc-tokens-hemelblauw.css").read_text(encoding="utf-8"),
        (_VENDOR / "rhc-components.css").read_text(encoding="utf-8"),
        (MAP / "rapport.css").read_text(encoding="utf-8"),
    ]
    return "\n".join(delen)


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
