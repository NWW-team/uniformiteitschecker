"""De afbakening is het hart van ronde 1: hier mag niets doorheen glippen."""

from uniformiteitschecker.sitemap import (
    filter_op_paden,
    lees_robots,
    padstatistiek,
    valt_onder,
    verzamel_urls,
)


def haler(bestanden):
    return lambda url: bestanden.get(url)


def test_sitemap_index_wordt_uitgeklapt(nep_site):
    urls = verzamel_urls("https://voorbeeld.nl", haler(nep_site))
    assert "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen" in urls
    assert "https://voorbeeld.nl/nieuws/2026/bericht" in urls


def test_terugval_naar_sitemap_xml_zonder_robots():
    bestanden = {
        "https://voorbeeld.nl/sitemap.xml": "<urlset><url><loc>https://voorbeeld.nl/a</loc></url></urlset>"
    }
    assert verzamel_urls("https://voorbeeld.nl", haler(bestanden)) == ["https://voorbeeld.nl/a"]


def test_terugval_naar_sitemap_index_xml():
    bestanden = {
        "https://voorbeeld.nl/sitemap_index.xml": (
            "<sitemapindex><sitemap><loc>https://voorbeeld.nl/s1.xml</loc></sitemap></sitemapindex>"
        ),
        "https://voorbeeld.nl/s1.xml": "<urlset><url><loc>https://voorbeeld.nl/b</loc></url></urlset>",
    }
    assert verzamel_urls("https://voorbeeld.nl", haler(bestanden)) == ["https://voorbeeld.nl/b"]


def test_geen_sitemap_geeft_lege_lijst():
    assert verzamel_urls("https://voorbeeld.nl", lambda url: None) == []


def test_padfilter_grenst_op_segment():
    """De valkuil: /paspoort mag /paspoortkosten niet meenemen."""
    urls = [
        "https://voorbeeld.nl/onderwerpen/paspoort",
        "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen",
        "https://voorbeeld.nl/onderwerpen/paspoortkosten",
        "https://voorbeeld.nl/nieuws/2026/bericht",
    ]
    binnen = filter_op_paden(urls, ["/onderwerpen/paspoort"])
    assert binnen == [
        "https://voorbeeld.nl/onderwerpen/paspoort",
        "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen",
    ]


def test_padfilter_accepteert_slordige_notatie():
    urls = ["https://voorbeeld.nl/onderwerpen/paspoort/aanvragen"]
    for pad in ("/onderwerpen/paspoort", "onderwerpen/paspoort", "/onderwerpen/paspoort/"):
        assert filter_op_paden(urls, [pad]) == urls


def test_meerdere_paden_tellen_allebei():
    urls = [
        "https://voorbeeld.nl/onderwerpen/paspoort/a",
        "https://voorbeeld.nl/onderwerpen/legalisatie/b",
        "https://voorbeeld.nl/nieuws/c",
    ]
    binnen = filter_op_paden(urls, ["/onderwerpen/paspoort", "/onderwerpen/legalisatie"])
    assert len(binnen) == 2


def test_robots_verbiedt_pad(nep_site):
    robots = lees_robots("https://voorbeeld.nl", haler(nep_site))
    assert not robots.can_fetch("UniformiteitscheckerBot", "https://voorbeeld.nl/geheim/intern")
    assert robots.can_fetch("UniformiteitscheckerBot", "https://voorbeeld.nl/onderwerpen/paspoort")


def test_padstatistiek_telt_en_sorteert():
    urls = [
        "https://voorbeeld.nl/onderwerpen/paspoort/a",
        "https://voorbeeld.nl/onderwerpen/paspoort/b",
        "https://voorbeeld.nl/nieuws/c",
    ]
    assert padstatistiek(urls, diepte=2)[0] == ("/onderwerpen/paspoort", 2)


def test_valt_onder_zonder_paden_is_alles():
    assert filter_op_paden(["https://voorbeeld.nl/x"], []) == ["https://voorbeeld.nl/x"]
    assert valt_onder("https://voorbeeld.nl/x", ["/"])
