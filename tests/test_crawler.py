"""Tekstextractie en de grenzen die de site beschermen."""

from uniformiteitschecker.crawler import crawl_site, extraheer, lees_corpus, schrijf_corpus
from uniformiteitschecker.model import Pagina, Site


class NepOphaler:
    """Ophaler-vervanger die uit een dict leest en bijhoudt wat is opgevraagd."""

    def __init__(self, bestanden):
        self.bestanden = bestanden
        self.opgevraagd = []

    def haal(self, url):
        self.opgevraagd.append(url)
        return self.bestanden.get(url)


def test_extractie_laat_navigatie_en_ruis_weg(fixtures):
    site = Site(id="nww-nl", basis_url="https://voorbeeld.nl", taal="nl")
    html = (fixtures / "paspoort_nl.html").read_text(encoding="utf-8")
    pagina = extraheer(html, "https://voorbeeld.nl/a", site)

    assert pagina.titel == "Reisdocument aanvragen in het buitenland"
    assert "ambassade" in pagina.tekst
    for ruis in ("Home", "cookies", "Naar de inhoud", "Rijksoverheid", "tracking"):
        assert ruis not in pagina.tekst


def test_extractie_valt_terug_op_article(fixtures):
    site = Site(id="nww-en", basis_url="https://voorbeeld.nl", taal="en")
    html = (fixtures / "passport_en.html").read_text(encoding="utf-8")
    pagina = extraheer(html, "https://voorbeeld.nl/en", site)

    assert pagina.titel == "Applying for a travel document abroad"
    assert "Legalization" in pagina.tekst
    assert "cookies" not in pagina.tekst


def test_extractie_zonder_main_gebruikt_body():
    site = Site(id="s", basis_url="https://voorbeeld.nl", taal="nl")
    pagina = extraheer("<html><body><p>Losse tekst.</p></body></html>", "https://voorbeeld.nl/x", site)
    assert pagina.tekst == "Losse tekst."


def test_crawl_respecteert_maximum(nep_site):
    site = Site(id="s", basis_url="https://voorbeeld.nl", taal="nl", paden=["/onderwerpen"])
    bestanden = dict(nep_site)
    for url in (
        "https://voorbeeld.nl/onderwerpen/paspoort",
        "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen",
        "https://voorbeeld.nl/onderwerpen/paspoortkosten",
        "https://voorbeeld.nl/onderwerpen/legalisatie/apostille",
    ):
        bestanden[url] = "<html><body><main><h1>Kop</h1><p>Inhoud.</p></main></body></html>"

    paginas = crawl_site(site, NepOphaler(bestanden), max_paginas=2)
    assert len(paginas) == 2


def test_crawl_slaat_verboden_en_buitengesloten_urls_over(nep_site):
    """Alleen de rubriek uit 'paden', en niets wat robots.txt verbiedt."""
    site = Site(id="s", basis_url="https://voorbeeld.nl", taal="nl", paden=["/onderwerpen/paspoort"])
    bestanden = dict(nep_site)
    pagina_html = "<html><body><main><h1>Kop</h1><p>Inhoud.</p></main></body></html>"
    for url in (
        "https://voorbeeld.nl/onderwerpen/paspoort",
        "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen",
        "https://voorbeeld.nl/onderwerpen/paspoortkosten",
        "https://voorbeeld.nl/geheim/intern",
        "https://voorbeeld.nl/nieuws/2026/bericht",
    ):
        bestanden[url] = pagina_html

    ophaler = NepOphaler(bestanden)
    paginas = crawl_site(site, ophaler, max_paginas=50)

    assert {p.url for p in paginas} == {
        "https://voorbeeld.nl/onderwerpen/paspoort",
        "https://voorbeeld.nl/onderwerpen/paspoort/aanvragen",
    }
    assert "https://voorbeeld.nl/geheim/intern" not in ophaler.opgevraagd


def test_zonder_sitemap_wordt_niets_opgehaald():
    site = Site(id="s", basis_url="https://voorbeeld.nl", taal="nl", paden=["/x"])
    assert crawl_site(site, NepOphaler({}), max_paginas=10) == []


def test_corpus_rondreis(tmp_path):
    paginas = [
        Pagina(url="https://voorbeeld.nl/b", taal="nl", site="s", titel="B", tekst="Tekst b", opgehaald_op="t"),
        Pagina(url="https://voorbeeld.nl/a", taal="nl", site="s", titel="A", tekst="Tekst a", opgehaald_op="t"),
    ]
    pad = tmp_path / "corpus" / "s.jsonl"
    schrijf_corpus(paginas, pad)

    terug = lees_corpus(pad.parent)
    assert [p.url for p in terug] == ["https://voorbeeld.nl/a", "https://voorbeeld.nl/b"]
    assert terug[0].tekst == "Tekst a"


def test_leeg_corpus_schrijft_leeg_bestand(tmp_path):
    pad = tmp_path / "leeg.jsonl"
    schrijf_corpus([], pad)
    assert pad.read_text() == ""
