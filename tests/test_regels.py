"""Vals-positieven kosten de redactie vertrouwen; die grenzen borgen we hier."""

import pytest

from uniformiteitschecker.model import Pagina
from uniformiteitschecker.regels import (
    MAX_FRAGMENTEN_PER_PAGINA,
    Regel,
    TermenlijstFout,
    controleer,
    laad_regels,
)


def pagina(tekst: str, taal: str = "nl") -> Pagina:
    return Pagina(
        url="https://voorbeeld.nl/a", taal=taal, site="test",
        titel="Test", tekst=tekst, opgehaald_op="2026-09-15T00:00:00+00:00",
    )


@pytest.fixture
def paspoortregel() -> Regel:
    return Regel(id="reisdocument", voorkeur="reisdocument", varianten=["paspoort"], talen=["nl"])


def test_samenstelling_geeft_geen_signaal(paspoortregel):
    """'paspoortfoto' is een eigen woord, geen verkeerd gebruik van 'paspoort'."""
    assert controleer(pagina("Neem een paspoortfoto mee."), [paspoortregel]) == []


def test_hele_woorden_uit_matcht_wel_binnen_woord():
    regel = Regel(id="deel", voorkeur="x", varianten=["paspoort"], talen=["nl"], hele_woorden=False)
    assert len(controleer(pagina("Een paspoortfoto."), [regel])) == 1


def test_hoofdletters_maken_niet_uit(paspoortregel):
    bevindingen = controleer(pagina("Het Paspoort is geldig."), [paspoortregel])
    assert len(bevindingen) == 1
    assert bevindingen[0].gevonden_term == "Paspoort"


def test_regel_geldt_alleen_voor_zijn_taal(paspoortregel):
    assert controleer(pagina("Your paspoort.", taal="en"), [paspoortregel]) == []


def test_fragment_is_de_omliggende_zin(paspoortregel):
    tekst = "Eerste zin. U vraagt uw paspoort aan bij de ambassade. Derde zin."
    bevinding = controleer(pagina(tekst), [paspoortregel])[0]
    assert bevinding.fragment == "U vraagt uw paspoort aan bij de ambassade."


def test_fragment_werkt_aan_begin_en_eind(paspoortregel):
    bevinding = controleer(pagina("Paspoort aanvragen"), [paspoortregel])[0]
    assert bevinding.fragment == "Paspoort aanvragen"


def test_veel_treffers_geven_beperkt_fragmenten_maar_volledige_telling(paspoortregel):
    tekst = " ".join(f"Zin {i} over een paspoort." for i in range(10))
    bevindingen = controleer(pagina(tekst), [paspoortregel])
    assert len(bevindingen) == MAX_FRAGMENTEN_PER_PAGINA
    assert all(b.treffers_op_pagina == 10 for b in bevindingen)


def test_variant_met_streepje():
    regel = Regel(id="idkaart", voorkeur="identiteitskaart", varianten=["ID-kaart"], talen=["nl"])
    assert len(controleer(pagina("Vraag een ID-kaart aan."), [regel])) == 1


def test_langste_variant_wint():
    """Anders zou 'paspoorten' als 'paspoort' met losse 'en' worden gemeld."""
    regel = Regel(id="r", voorkeur="reisdocumenten", varianten=["paspoort", "paspoorten"], talen=["nl"])
    bevinding = controleer(pagina("Twee paspoorten."), [regel])[0]
    assert bevinding.gevonden_term == "paspoorten"


def test_echte_termenlijst_laadt(tmp_path):
    regels = laad_regels("config/termen.yaml")
    assert {r.id for r in regels} >= {"reisdocument-vs-paspoort", "legalisation-spelling"}


@pytest.mark.parametrize(
    "inhoud, verwacht",
    [
        ("regels: []", "geen 'regels'"),
        ("regels:\n  - voorkeur: a\n    varianten: [b]", "'id' ontbreekt"),
        ("regels:\n  - id: a\n    varianten: [b]", "'voorkeur' ontbreekt"),
        ("regels:\n  - id: a\n    voorkeur: b\n    varianten: []", "'varianten' is leeg"),
        ("regels:\n  - id: a\n    voorkeur: b\n    varianten: [c]\n    talen: [de]", "onbekende taal"),
        ("regels:\n  - id: a\n    voorkeur: b\n    varianten: [c]\n  - id: a\n    voorkeur: d\n    varianten: [e]", "meer dan een keer"),
    ],
)
def test_kapotte_termenlijst_geeft_duidelijke_fout(tmp_path, inhoud, verwacht):
    pad = tmp_path / "termen.yaml"
    pad.write_text(inhoud, encoding="utf-8")
    with pytest.raises(TermenlijstFout, match=verwacht):
        laad_regels(pad)


def test_ontbrekend_bestand_geeft_fout(tmp_path):
    with pytest.raises(TermenlijstFout, match="niet gevonden"):
        laad_regels(tmp_path / "bestaat-niet.yaml")
