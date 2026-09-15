"""config/sites.yaml inlezen: welke bronnen, welke taal, welke afbakening."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .model import TALEN, Site

STANDAARD_MAX_PAGINAS = 200


class ConfiguratieFout(ValueError):
    """De siteconfiguratie klopt niet; de melding zegt wat eraan mankeert."""


@dataclass(slots=True)
class Instellingen:
    sites: list[Site]
    max_paginas_per_site: int = STANDAARD_MAX_PAGINAS

    @property
    def afbakening(self) -> dict[str, list[str]]:
        return {site.id: list(site.paden) for site in self.sites}


def laad_sites(pad: Path | str) -> Instellingen:
    pad = Path(pad)
    if not pad.exists():
        raise ConfiguratieFout(f"Siteconfiguratie niet gevonden: {pad}")

    gegevens = yaml.safe_load(pad.read_text(encoding="utf-8")) or {}
    ruwe_sites = gegevens.get("sites")
    if not ruwe_sites:
        raise ConfiguratieFout(f"{pad} bevat geen 'sites'.")

    sites: list[Site] = []
    gezien: set[str] = set()
    for nummer, ruw in enumerate(ruwe_sites, start=1):
        plek = f"site {nummer}"
        if not isinstance(ruw, dict):
            raise ConfiguratieFout(f"{plek}: moet een blok met velden zijn.")

        site_id = str(ruw.get("id", "")).strip()
        if not site_id:
            raise ConfiguratieFout(f"{plek}: 'id' ontbreekt.")
        if site_id in gezien:
            raise ConfiguratieFout(f"{plek}: id '{site_id}' komt meer dan een keer voor.")
        gezien.add(site_id)

        basis_url = str(ruw.get("basis_url", "")).strip().rstrip("/")
        if not basis_url.startswith("http"):
            raise ConfiguratieFout(f"site '{site_id}': 'basis_url' moet een http(s)-adres zijn.")

        taal = str(ruw.get("taal", "")).strip().lower()
        if taal not in TALEN:
            raise ConfiguratieFout(f"site '{site_id}': taal '{taal}' is onbekend; bekend zijn {list(TALEN)}.")

        paden = [str(p).strip() for p in (ruw.get("paden") or []) if str(p).strip()]
        sites.append(Site(id=site_id, basis_url=basis_url, taal=taal, paden=paden))

    max_paginas = int(gegevens.get("max_paginas_per_site", STANDAARD_MAX_PAGINAS))
    if max_paginas < 1:
        raise ConfiguratieFout("'max_paginas_per_site' moet minstens 1 zijn.")

    return Instellingen(sites=sites, max_paginas_per_site=max_paginas)
