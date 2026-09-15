"""De siteconfiguratie bepaalt hoeveel van andermans website we aanraken."""

import pytest

from uniformiteitschecker.configuratie import ConfiguratieFout, laad_sites

GOED = """
sites:
  - id: nww-nl
    basis_url: https://www.nederlandwereldwijd.nl/
    taal: nl
    paden: [/onderwerpen/paspoort]
max_paginas_per_site: 25
"""


def schrijf(tmp_path, inhoud):
    pad = tmp_path / "sites.yaml"
    pad.write_text(inhoud, encoding="utf-8")
    return pad


def test_laadt_en_normaliseert(tmp_path):
    instellingen = laad_sites(schrijf(tmp_path, GOED))
    site = instellingen.sites[0]
    assert site.basis_url == "https://www.nederlandwereldwijd.nl"
    assert site.domein == "www.nederlandwereldwijd.nl"
    assert instellingen.max_paginas_per_site == 25
    assert instellingen.afbakening == {"nww-nl": ["/onderwerpen/paspoort"]}


def test_echte_configuratie_laadt():
    instellingen = laad_sites("config/sites.yaml")
    assert {s.id for s in instellingen.sites} == {"nww-nl", "nww-en"}
    assert {s.taal for s in instellingen.sites} == {"nl", "en"}


@pytest.mark.parametrize(
    "inhoud, verwacht",
    [
        ("sites: []", "geen 'sites'"),
        ("sites:\n  - basis_url: https://a\n    taal: nl", "'id' ontbreekt"),
        ("sites:\n  - id: a\n    basis_url: ftp://a\n    taal: nl", "http"),
        ("sites:\n  - id: a\n    basis_url: https://a\n    taal: de", "onbekend"),
        ("sites:\n  - id: a\n    basis_url: https://a\n    taal: nl\n  - id: a\n    basis_url: https://b\n    taal: en", "meer dan een keer"),
        ("sites:\n  - id: a\n    basis_url: https://a\n    taal: nl\nmax_paginas_per_site: 0", "minstens 1"),
    ],
)
def test_kapotte_configuratie_geeft_duidelijke_fout(tmp_path, inhoud, verwacht):
    with pytest.raises(ConfiguratieFout, match=verwacht):
        laad_sites(schrijf(tmp_path, inhoud))
