from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def nep_site():
    """Een sitemapopzet die via robots.txt naar een sitemap-index wijst."""
    bestanden = {
        "https://voorbeeld.nl/robots.txt": (
            "User-agent: *\n"
            "Disallow: /geheim\n"
            "Sitemap: https://voorbeeld.nl/sitemap_index.xml\n"
        ),
        "https://voorbeeld.nl/sitemap_index.xml": (FIXTURES / "sitemap_index.xml").read_text(),
        "https://voorbeeld.nl/sitemap-onderwerpen.xml": (FIXTURES / "sitemap_onderwerpen.xml").read_text(),
        "https://voorbeeld.nl/sitemap-nieuws.xml": (FIXTURES / "sitemap_nieuws.xml").read_text(),
    }
    return bestanden
