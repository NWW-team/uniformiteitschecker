"""Werkbaar overzicht: de signalen zo neerzetten dat de redactie ze kan oppakken.

De app lost niets zelf op. Het rapport moet dus per bevinding laten zien wáár het
zit, wát er staat en wat de voorkeursterm is, zonder dat iemand de pagina hoeft te
openen om te snappen waar het over gaat.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import huisstijl

from .model import PAGINAS, REGELS, SIGNALEN, Bevinding, Pagina, aantal


def schrijf_json(bevindingen: list[Bevinding], pad: Path) -> None:
    pad = Path(pad)
    pad.parent.mkdir(parents=True, exist_ok=True)
    gegevens = [b.als_dict() for b in sorted(bevindingen, key=lambda b: b.sorteersleutel)]
    pad.write_text(json.dumps(gegevens, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def samenvatting(bevindingen: list[Bevinding]) -> list[tuple[str, int, int]]:
    """Per regel: (regel_id, aantal bevindingen, aantal pagina's)."""
    per_regel: Counter[str] = Counter()
    paginas_per_regel: defaultdict[str, set[str]] = defaultdict(set)
    for bevinding in bevindingen:
        per_regel[bevinding.regel_id] += 1
        paginas_per_regel[bevinding.regel_id].add(bevinding.url)
    return sorted(
        ((regel_id, aantal, len(paginas_per_regel[regel_id])) for regel_id, aantal in per_regel.items()),
        key=lambda rij: (-rij[1], rij[0]),
    )


def _markeer(fragment: str, term: str) -> str:
    """Escape het fragment en zet de gevonden term in een <mark>."""
    positie = fragment.lower().find(term.lower())
    if positie < 0:
        return escape(fragment)
    eind = positie + len(term)
    return (
        escape(fragment[:positie])
        + "<mark>"
        + escape(fragment[positie:eind])
        + "</mark>"
        + escape(fragment[eind:])
    )


def schrijf_html(
    bevindingen: list[Bevinding],
    paginas: list[Pagina],
    pad: Path,
    afbakening: dict[str, list[str]] | None = None,
) -> None:
    """Eén zelfstandig HTML-bestand, zonder externe bestanden of scripts."""
    pad = Path(pad)
    pad.parent.mkdir(parents=True, exist_ok=True)

    bevindingen = sorted(bevindingen, key=lambda b: b.sorteersleutel)
    rijen = samenvatting(bevindingen)
    per_regel: defaultdict[str, list[Bevinding]] = defaultdict(list)
    for bevinding in bevindingen:
        per_regel[bevinding.regel_id].append(bevinding)

    gecontroleerd = max((p.opgehaald_op for p in paginas), default="—")
    delen: list[str] = [
        "<!doctype html>",
        '<html lang="nl">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        "<title>Uniformiteitscheck NederlandWereldwijd</title>",
        f"<style>{huisstijl.laad_css()}</style>",
        "</head>",
        '<body class="rhc-theme">',
        '<a class="rhc-skiplink" href="#inhoud">Naar de inhoud</a>',
        '<div class="rhc-lint"></div>',
        '<div class="rhc-blad">',
        '<header class="rhc-kop">',
        "<h1>Uniformiteitscheck</h1>",
        f'<p class="rhc-inleiding">Gemaakt op {escape(datetime.now(timezone.utc).strftime("%d-%m-%Y %H:%M"))} UTC · '
        f'content opgehaald {escape(gecontroleerd)}</p>',
        "</header>",
        '<main id="inhoud">',
        '<div class="rhc-feiten">',
        f'<div class="rhc-feit"><b>{len(bevindingen)}</b><span>{SIGNALEN[len(bevindingen) != 1]}</span></div>',
        f'<div class="rhc-feit"><b>{len({b.url for b in bevindingen})}</b><span>pagina\'s met een signaal</span></div>',
        f'<div class="rhc-feit"><b>{len(paginas)}</b><span>pagina\'s gecontroleerd</span></div>',
        f'<div class="rhc-feit"><b>{len(rijen)}</b><span>{REGELS[len(rijen) != 1]} met treffers</span></div>',
        "</div>",
    ]

    if afbakening:
        onderdelen = "; ".join(
            f"{escape(site_id)}: {escape(', '.join(paden) or 'hele site')}"
            for site_id, paden in afbakening.items()
        )
        delen.append(f'<p class="rhc-groeptoelichting"><b>Afbakening:</b> {onderdelen}</p>')

    if not bevindingen:
        delen.append(
            '<section class="rhc-leeg"><h2>Geen afwijkingen gevonden</h2>'
            "<p>Geen afwijkingen gevonden in de gecontroleerde pagina's. "
            "Dat kan kloppen — of de termenlijst dekt dit onderwerp nog niet.</p></section>"
        )
    else:
        delen.append(
            "<table><thead><tr><th>Regel</th><th>Voorkeursterm</th>"
            '<th class="rhc-getal">Signalen</th><th class="rhc-getal">Pagina\'s</th></tr></thead><tbody>'
        )
        for regel_id, treffers, paginas_met in rijen:
            voorkeur = per_regel[regel_id][0].voorkeursterm
            delen.append(
                f"<tr><td>{escape(regel_id)}</td><td>{escape(voorkeur)}</td>"
                f'<td class="rhc-getal">{treffers}</td><td class="rhc-getal">{paginas_met}</td></tr>'
            )
        delen.append("</tbody></table>")

        for regel_id, treffers, paginas_met in rijen:
            groep = per_regel[regel_id]
            eerste = groep[0]
            delen.append(
                f"<h2>{escape(regel_id)} · "
                f"{aantal(treffers, *SIGNALEN)} op {aantal(paginas_met, *PAGINAS)}</h2>"
            )
            uitleg = eerste.toelichting or f"Voorkeursterm is '{eerste.voorkeursterm}'."
            delen.append(
                f'<p class="rhc-groeptoelichting">{escape(uitleg)} Op te pakken door: {escape(eerste.eigenaar)}.</p>'
            )
            for bevinding in groep:
                extra = (
                    f" · {bevinding.treffers_op_pagina}× op deze pagina"
                    if bevinding.treffers_op_pagina > 1
                    else ""
                )
                delen.append(
                    '<div class="rhc-bevinding">'
                    f'<p class="rhc-fragment">{_markeer(bevinding.fragment, bevinding.gevonden_term)}</p>'
                    '<div class="rhc-meta">'
                    f'<span class="rhc-chip rhc-neutraal">{escape(bevinding.taal)}</span>'
                    f"<span>“{escape(bevinding.gevonden_term)}” → <b>{escape(bevinding.voorkeursterm)}</b>{extra}</span>"
                    f'<a href="{escape(bevinding.url, quote=True)}">{escape(bevinding.url)}</a>'
                    "</div></div>"
                )

    delen.append("</main>")
    delen.append(
        "<footer>Gegenereerd door de uniformiteitschecker. De checker signaleert en lost "
        "niets op: een afwijking kan ook een legitiem geval zijn. Verifieer altijd via de "
        "vindplaats voordat je iets wijzigt.</footer>"
    )
    delen.append("</div></body></html>")
    pad.write_text("\n".join(delen), encoding="utf-8")
