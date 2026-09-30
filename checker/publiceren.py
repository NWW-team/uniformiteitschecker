"""De signalen naar de database brengen, zodat ze achter de inlog kunnen staan.

Het rapport op internet bevat zelf geen signalen. Dit commando zet per familie het
tabblad (als HTML-fragment) in de tabel `rapport_panelen`; de pagina haalt die pas op
nadat iemand is ingelogd. Schrijven kan alleen met de servicesleutel, die hoort in een
geheime omgevingsvariabele en nooit in de repo of in de pagina.
"""

from __future__ import annotations

import os
import pathlib

import yaml

CONFIG_PAD = pathlib.Path("config/supabase.yaml")
SLEUTEL_VARIABELE = "SUPABASE_SERVICE_KEY"


def laad_config(pad: pathlib.Path = CONFIG_PAD) -> dict:
    return yaml.safe_load(pad.read_text(encoding="utf-8"))


def publiceer_panelen(
    panelen: list[dict], *, url: str, servicesleutel: str, client: object | None = None
) -> int:
    """Zet de tabbladen in de database; bestaande worden bijgewerkt. Geeft het aantal terug.

    Elk paneel is een dict met `familie`, `naam`, `datum`, `volgorde`, `aantal` en `html`.
    Tabbladen van families die niet meer bestaan blijven staan; verwijderen doen we
    bewust niet automatisch.
    """
    eigen_client = client is None
    if client is None:
        import httpx  # pas hier: alleen nodig bij echt publiceren

        client = httpx.Client(timeout=60)
    try:
        antwoord = client.post(
            f"{url.rstrip('/')}/rest/v1/rapport_panelen?on_conflict=familie",
            headers={
                "apikey": servicesleutel,
                "Authorization": f"Bearer {servicesleutel}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=panelen,
        )
        antwoord.raise_for_status()
    finally:
        if eigen_client:
            client.close()
    return len(panelen)


def servicesleutel_uit_omgeving() -> str:
    sleutel = os.environ.get(SLEUTEL_VARIABELE, "").strip()
    if not sleutel:
        raise SystemExit(
            f"Zet de servicesleutel van Supabase in de omgevingsvariabele {SLEUTEL_VARIABELE} "
            "(Supabase > Project Settings > API Keys > service_role / secret key)."
        )
    return sleutel
