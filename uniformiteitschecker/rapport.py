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


STIJL = """
:root { color-scheme: light dark;
  --grond:#fbfbfa; --kaart:#fff; --tekst:#1a1a19; --zacht:#5c5c58; --lijn:#e3e3df;
  --accent:#1f4f8b; --markeer:#ffe9a8; --markeer-tekst:#3d2f00; }
@media (prefers-color-scheme: dark) { :root {
  --grond:#16171a; --kaart:#1e2024; --tekst:#e9e9e6; --zacht:#a2a29c; --lijn:#31343a;
  --accent:#8db4e8; --markeer:#5c4a10; --markeer-tekst:#ffeeb5; } }
* { box-sizing:border-box; }
body { margin:0; padding:32px 20px 64px; background:var(--grond); color:var(--tekst);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif; }
.hoofd { max-width:920px; margin:0 auto; }
h1 { font-size:1.6rem; margin:0 0 4px; letter-spacing:-.01em; }
.sub { color:var(--zacht); margin:0 0 28px; }
.feiten { display:flex; flex-wrap:wrap; gap:12px; margin-bottom:28px; }
.feit { background:var(--kaart); border:1px solid var(--lijn); border-radius:10px; padding:12px 16px; }
.feit b { display:block; font-size:1.5rem; line-height:1.2; }
.feit span { color:var(--zacht); font-size:.85rem; }
table { width:100%; border-collapse:collapse; background:var(--kaart);
  border:1px solid var(--lijn); border-radius:10px; overflow:hidden; margin-bottom:36px; }
th,td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--lijn); }
th { font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; color:var(--zacht); }
tr:last-child td { border-bottom:none; }
td.getal, th.getal { text-align:right; font-variant-numeric:tabular-nums; }
h2 { font-size:1.15rem; margin:32px 0 2px; }
h2 .telling { color:var(--zacht); font-weight:400; font-size:.9rem; }
.uitleg { color:var(--zacht); margin:0 0 14px; font-size:.92rem; }
.bevinding { background:var(--kaart); border:1px solid var(--lijn); border-left:3px solid var(--accent);
  border-radius:8px; padding:14px 16px; margin-bottom:10px; }
.fragment { margin:0 0 8px; }
mark { background:var(--markeer); color:var(--markeer-tekst); padding:0 2px; border-radius:2px; }
.meta { font-size:.85rem; color:var(--zacht); display:flex; flex-wrap:wrap; gap:10px; align-items:baseline; }
.meta a { color:var(--accent); word-break:break-all; }
.badge { border:1px solid var(--lijn); border-radius:20px; padding:1px 9px; font-size:.75rem;
  text-transform:uppercase; letter-spacing:.04em; }
.leeg { background:var(--kaart); border:1px solid var(--lijn); border-radius:10px; padding:24px; text-align:center; color:var(--zacht); }
"""


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
        "<!doctype html><html lang=nl><head><meta charset=utf-8>",
        '<meta name=viewport content="width=device-width,initial-scale=1">',
        "<title>Uniformiteitscheck NederlandWereldwijd</title>",
        f"<style>{STIJL}</style></head><body><div class=hoofd>",
        "<h1>Uniformiteitscheck</h1>",
        f"<p class=sub>Gemaakt op {escape(datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M'))} UTC · "
        f"content opgehaald {escape(gecontroleerd)}</p>",
        "<div class=feiten>",
        f"<div class=feit><b>{len(bevindingen)}</b><span>{SIGNALEN[len(bevindingen) != 1]}</span></div>",
        f"<div class=feit><b>{len({b.url for b in bevindingen})}</b><span>pagina's met een signaal</span></div>",
        f"<div class=feit><b>{len(paginas)}</b><span>pagina's gecontroleerd</span></div>",
        f"<div class=feit><b>{len(rijen)}</b><span>{REGELS[len(rijen) != 1]} met treffers</span></div>",
        "</div>",
    ]

    if afbakening:
        onderdelen = "; ".join(
            f"{escape(site_id)}: {escape(', '.join(paden) or 'hele site')}"
            for site_id, paden in afbakening.items()
        )
        delen.append(f"<p class=uitleg><b>Afbakening:</b> {onderdelen}</p>")

    if not bevindingen:
        delen.append(
            "<div class=leeg>Geen afwijkingen gevonden in de gecontroleerde pagina's. "
            "Dat kan kloppen — of de termenlijst dekt dit onderwerp nog niet.</div>"
        )
    else:
        delen.append(
            "<table><thead><tr><th>Regel</th><th>Voorkeursterm</th>"
            "<th class=getal>Signalen</th><th class=getal>Pagina's</th></tr></thead><tbody>"
        )
        for regel_id, treffers, paginas_met in rijen:
            voorkeur = per_regel[regel_id][0].voorkeursterm
            delen.append(
                f"<tr><td>{escape(regel_id)}</td><td>{escape(voorkeur)}</td>"
                f"<td class=getal>{treffers}</td><td class=getal>{paginas_met}</td></tr>"
            )
        delen.append("</tbody></table>")

        for regel_id, treffers, paginas_met in rijen:
            groep = per_regel[regel_id]
            eerste = groep[0]
            delen.append(
                f"<h2>{escape(regel_id)} <span class=telling>· "
                f"{aantal(treffers, *SIGNALEN)} op {aantal(paginas_met, *PAGINAS)}</span></h2>"
            )
            uitleg = eerste.toelichting or f"Voorkeursterm is '{eerste.voorkeursterm}'."
            delen.append(f"<p class=uitleg>{escape(uitleg)} Op te pakken door: {escape(eerste.eigenaar)}.</p>")
            for bevinding in groep:
                extra = (
                    f" · {bevinding.treffers_op_pagina}× op deze pagina"
                    if bevinding.treffers_op_pagina > 1
                    else ""
                )
                delen.append(
                    "<div class=bevinding>"
                    f"<p class=fragment>{_markeer(bevinding.fragment, bevinding.gevonden_term)}</p>"
                    "<div class=meta>"
                    f"<span class=badge>{escape(bevinding.taal)}</span>"
                    f"<span>“{escape(bevinding.gevonden_term)}” → <b>{escape(bevinding.voorkeursterm)}</b>{extra}</span>"
                    f"<a href=\"{escape(bevinding.url, quote=True)}\">{escape(bevinding.url)}</a>"
                    "</div></div>"
                )

    delen.append("</div></body></html>")
    pad.write_text("\n".join(delen), encoding="utf-8")
