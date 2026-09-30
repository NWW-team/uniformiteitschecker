"""De detectoren voor landenpagina's met een vast stappenplan."""

import unittest

from checker.bronnen.sitemap import familie_sleutel, filter_op_prefix
from checker.detectie import register, stappenplan
from checker.model import (
    EIGENAAR_BEOORDELEN,
    EIGENAAR_KENNISEIGENAAR,
    EIGENAAR_REDACTIE,
    Pagina,
)

from . import hulp


def _titels(bevindingen):
    return [b.titel for b in bevindingen]


def _met(bevindingen, tekst):
    return [b for b in bevindingen if tekst in b.titel]


class TestExtractieVanStappen(unittest.TestCase):
    """De uitlezing op echte pagina's: stappen, uitklappers en kopniveaus."""

    def test_leest_stappen_en_uitklappers(self):
        pagina = hulp.paspoort_pagina("albanie")
        stappen = [s.stap for s in pagina.secties if s.stap and not s.titel]
        self.assertEqual(
            [s.split(":")[0] for s in stappen],
            ["Stap 1", "Stap 2", "Stap 3", "Stap 4", "Stap 5", "Contact"],
        )
        uitklappers = [s.titel for s in pagina.secties if s.titel]
        self.assertIn("Bewijs van legaal verblijf", uitklappers)
        self.assertIn("Wat neem ik mee?", uitklappers)

    def test_uitklaptekst_hoort_bij_zijn_uitklapper(self):
        pagina = hulp.paspoort_pagina("albanie")
        mee = next(s for s in pagina.secties if s.titel == "Wat neem ik mee?")
        self.assertEqual(mee.stap, "Stap 4: Ga naar uw afspraak")
        self.assertIn("De baliemedewerker maakt kopieën.", mee.tekst)
        self.assertNotIn("Ophalen", mee.tekst)

    def test_kopjes_in_een_uitklapper_bewaren_hun_niveau(self):
        pagina = hulp.paspoort_pagina("albanie")
        inleveren = next(s for s in pagina.secties if s.titel.startswith("Moet ik mijn oude"))
        self.assertEqual({k["niveau"] for k in inleveren.koppen}, {4})
        self.assertEqual(inleveren.niveau, 3)

    def test_h3_binnen_uitklapper_wordt_vastgelegd(self):
        """Thailand gebruikt een h3 ("Wanneer?") binnen de uitklapper Hua Hin."""
        pagina = hulp.paspoort_pagina("thailand")
        hua_hin = next(s for s in pagina.secties if s.titel == "Hua Hin")
        self.assertIn(3, {k["niveau"] for k in hua_hin.koppen})

    def test_filtertoolmelding_is_geen_inhoud(self):
        pagina = hulp.paspoort_pagina("albanie")
        for s in pagina.secties:
            self.assertNotIn("JavaScript staat uit", s.tekst)

    def test_pagina_zonder_stappenplan_heeft_geen_stappen(self):
        pagina = hulp.paspoort_pagina("afghanistan")
        self.assertEqual([s for s in pagina.secties if s.stap], [])

    def test_koppen_lopen_door_tot_h6_in_documentvolgorde(self):
        niveaus = [k["niveau"] for k in hulp.paspoort_pagina("albanie").koppen]
        self.assertEqual(niveaus[0], 1)
        self.assertIn(4, niveaus)

    def test_snapshot_roundtrip_behoudt_secties(self):
        pagina = hulp.paspoort_pagina("duitsland")
        import json

        terug = Pagina.uit_dict(json.loads(pagina.naar_json()))
        self.assertEqual(terug.secties, pagina.secties)

    def test_sitemapfilter_op_voorvoegsel_van_de_laatste_padnaam(self):
        urls = [
            "https://www.nederlandwereldwijd.nl/paspoort-id-kaart/buitenland/paspoort-albanie",
            "https://www.nederlandwereldwijd.nl/paspoort-id-kaart/buitenland/hoelang-duurt-het",
            "https://www.nederlandwereldwijd.nl/paspoort-id-kaart/nederland/paspoort-aanvragen",
        ]
        self.assertEqual(
            filter_op_prefix(urls, "/paspoort-id-kaart/buitenland/paspoort-"), [urls[0]]
        )
        # Een prefix met slot-slash blijft een map, zoals bij consulaire-tarieven.
        self.assertEqual(len(filter_op_prefix(urls, "/paspoort-id-kaart/")), 3)
        self.assertEqual(familie_sleutel(urls[0], "paspoort-"), "albanie")


class TestStappenplan(unittest.TestCase):
    def test_gelijke_pagina_s_geven_geen_signalen(self):
        self.assertEqual(stappenplan.detecteer_stappen(hulp.zusters()), [])

    def test_ontbrekende_stap_wordt_gebundeld_gemeld(self):
        zonder = [s for s in hulp.STANDAARD_STAPPEN if not s[0].startswith("Stap 2")]
        paginas = hulp.zusters(Aruba={"stappen": zonder}, Bahrein={"stappen": zonder})
        gevonden = _met(stappenplan.detecteer_stappen(paginas), "Stap ontbreekt")
        self.assertEqual(len(gevonden), 1)
        self.assertIn("Check de extra eisen", gevonden[0].titel)
        self.assertNotIn("Stap 2", gevonden[0].titel)
        self.assertEqual(len(gevonden[0].urls), 2)
        self.assertEqual(gevonden[0].telling["n"], 10)
        self.assertEqual(gevonden[0].eigenaar, EIGENAAR_BEOORDELEN)

    def test_stap_die_er_bijna_hetzelfde_uitziet_is_een_andere_titel(self):
        anders = [
            (s.replace("Check de extra eisen", "Check de extra eisen voor Aruba"), u)
            for s, u in hulp.STANDAARD_STAPPEN
        ]
        gevonden = stappenplan.detecteer_stappen(hulp.zusters(Aruba={"stappen": anders}))
        self.assertEqual(len(_met(gevonden, "Stap ontbreekt")), 0)
        self.assertEqual(len(_met(gevonden, "Extra stap")), 0)
        hernoemd = _met(gevonden, "Stap heet anders")
        self.assertEqual(len(hernoemd), 1)
        self.assertEqual(hernoemd[0].eigenaar, EIGENAAR_REDACTIE)

    def test_extra_stap_wordt_gemeld(self):
        met_extra = hulp.STANDAARD_STAPPEN + [("Heeft u ook een tweede nationaliteit?", [])]
        gevonden = stappenplan.detecteer_stappen(hulp.zusters(Aruba={"stappen": met_extra}))
        self.assertEqual(len(_met(gevonden, "Extra stap")), 1)

    def test_andere_volgorde_wordt_gemeld(self):
        omgekeerd = list(reversed(hulp.STANDAARD_STAPPEN))
        gevonden = stappenplan.detecteer_stappen(hulp.zusters(Aruba={"stappen": omgekeerd}))
        self.assertEqual(len(_met(gevonden, "andere volgorde")), 1)

    def test_pagina_zonder_stappenplan_telt_niet_mee_in_de_norm(self):
        leeg = hulp.synthetisch("Ambassadeland", stappen=[])
        paginas = hulp.zusters() + [leeg]
        gevonden = stappenplan.detecteer_stappen(paginas)
        self.assertEqual(_titels(gevonden), ["Pagina volgt het stappenplan niet"])
        # ... en de andere detectoren zien haar niet als "ontbrekende uitklappers".
        self.assertEqual(stappenplan.detecteer_uitklappers(paginas), [])

    def test_te_weinig_zusters_geeft_geen_norm(self):
        paginas = hulp.zusters()[:3]
        self.assertEqual(stappenplan.detecteer_stappen(paginas), [])


class TestUitklapparagrafen(unittest.TestCase):
    def test_ontbrekende_uitklapper_wordt_gemeld(self):
        zonder = [
            (s, [u for u in ups if u[0] != "Documenten legaliseren"])
            for s, ups in hulp.STANDAARD_STAPPEN
        ]
        gevonden = stappenplan.detecteer_uitklappers(hulp.zusters(Aruba={"stappen": zonder}))
        self.assertEqual(_titels(gevonden), ["Uitklapper ontbreekt: Documenten legaliseren"])
        self.assertEqual(gevonden[0].urls, [hulp.PASPOORT_URL.format("aruba")])

    def test_anders_genoemde_uitklapper_is_een_schrijfrichtlijn(self):
        anders = [
            (s, [("Document legaliseren" if t == "Documenten legaliseren" else t, x) for t, x in ups])
            for s, ups in hulp.STANDAARD_STAPPEN
        ]
        gevonden = stappenplan.detecteer_uitklappers(hulp.zusters(Aruba={"stappen": anders}))
        self.assertEqual(_titels(gevonden), ["Uitklapper heet anders: Documenten legaliseren"])
        self.assertEqual(gevonden[0].eigenaar, EIGENAAR_REDACTIE)
        self.assertIn("Document legaliseren", gevonden[0].waargenomen)

    def test_landspecifieke_uitklapper_geeft_geen_ruis(self):
        """Een uitklapper die maar op één pagina staat, is geen norm."""
        extra = [
            (s, ups + [("Alleen hier", "tekst")] if s.startswith("Stap 3") else ups)
            for s, ups in hulp.STANDAARD_STAPPEN
        ]
        self.assertEqual(stappenplan.detecteer_uitklappers(hulp.zusters(Aruba={"stappen": extra})), [])


class TestKoppenstructuur(unittest.TestCase):
    def test_h3_binnen_uitklapper_waar_h4_de_norm_is(self):
        gevonden = stappenplan.detecteer_koppen(hulp.zusters(Aruba={"subkopniveau": 3}))
        titels = _titels(gevonden)
        self.assertEqual(len(titels), 1, titels)
        self.assertIn("h3 in plaats van h4", titels[0])
        self.assertEqual(gevonden[0].eigenaar, EIGENAAR_REDACTIE)
        self.assertIn("aruba", gevonden[0].waargenomen)

    def test_titel_van_uitklapper_op_h4_in_plaats_van_h3(self):
        gevonden = stappenplan.detecteer_koppen(hulp.zusters(Aruba={"uitklapniveau": 4}))
        self.assertTrue(any("Titel van uitklapper" in t for t in _titels(gevonden)))

    def test_norm_h4_zonder_afwijking_levert_niets_op(self):
        self.assertEqual(stappenplan.detecteer_koppen(hulp.zusters()), [])

    def test_overgeslagen_kopniveau(self):
        pagina = hulp.synthetisch("Aruba", extra_html="<h2>Extra</h2><h4>Diep</h4>")
        paginas = [p for p in hulp.zusters() if p.familie_sleutel != "aruba"] + [pagina]
        gevonden = stappenplan.detecteer_koppen(paginas)
        self.assertEqual(len(_met(gevonden, "Kopniveau overgeslagen")), 1)

    def test_tweede_h1(self):
        pagina = hulp.synthetisch("Aruba", extra_html="<h1>Nog een titel</h1>")
        paginas = [p for p in hulp.zusters() if p.familie_sleutel != "aruba"] + [pagina]
        self.assertEqual(len(_met(stappenplan.detecteer_koppen(paginas), "Meer dan één h1")), 1)

    def test_vetgedrukte_alinea_als_kopje_alleen_als_de_tekst_elders_een_kop_is(self):
        vet = "<p><strong>Afspraak wijzigen of afzeggen</strong></p>"
        html = (
            "<main><h1>Paspoort of ID-kaart aanvragen als u in Aruba woont</h1>"
            "<h2>Stap 4: Ga naar uw afspraak</h2>"
            '<h3><button aria-controls="v1" type="button">Wat neem ik mee?</button></h3>'
            f'<div id="v1" data-testid="accordion-panel">{vet}<p>Tekst.</p></div></main>'
        )
        from checker.bronnen.extractie import lees_pagina

        sectie = lees_pagina(html, "x", familie="f", familie_sleutel="aruba").secties[-1]
        self.assertEqual(sectie.koppen[0]["niveau"], 0)

    def test_vetgedrukte_nadruk_in_lopende_tekst_wordt_niet_gemeld(self):
        html = (
            "<main><h1>Paspoort of ID-kaart aanvragen als u in Aruba woont</h1>"
            "<h2>Stap 4: Ga naar uw afspraak</h2>"
            '<h3><button aria-controls="v1" type="button">Wat neem ik mee?</button></h3>'
            '<div id="v1" data-testid="accordion-panel">'
            "<p><strong>Let op: dit is nadruk</strong></p><p>Tekst.</p></div></main>"
        )
        from checker.bronnen.extractie import lees_pagina

        pagina = lees_pagina(html, "x", familie="f", familie_sleutel="aruba")
        paginas = hulp.zusters()[:-1] + [pagina]
        self.assertEqual(_met(stappenplan.detecteer_koppen(paginas), "Vetgedrukte"), [])


class TestStandaardzinnen(unittest.TestCase):
    def test_ontbrekende_standaardzin_wordt_per_uitklapper_gemeld(self):
        zonder = [
            (s, [(t, "Neem alle originele documenten uit uw persoonlijke checklist mee.") if t == "Wat neem ik mee?" else (t, x) for t, x in ups])
            for s, ups in hulp.STANDAARD_STAPPEN
        ]
        gevonden = stappenplan.detecteer_zinnen(hulp.zusters(Aruba={"stappen": zonder}))
        self.assertEqual(len(gevonden), 1)
        self.assertIn("Wat neem ik mee?", gevonden[0].titel)
        self.assertIn("De baliemedewerker maakt kopieën", gevonden[0].waargenomen)
        self.assertEqual(gevonden[0].eigenaar, EIGENAAR_BEOORDELEN)

    def test_afwijkende_formulering_toont_de_andere_tekst(self):
        anders = [
            (s, [(t, x.replace("originele documenten", "documenten")) if t == "Wat neem ik mee?" else (t, x) for t, x in ups])
            for s, ups in hulp.STANDAARD_STAPPEN
        ]
        gevonden = stappenplan.detecteer_zinnen(hulp.zusters(Aruba={"stappen": anders}))
        self.assertEqual(len(gevonden), 1)
        self.assertIn("i.p.v.", gevonden[0].waargenomen)

    def test_gelijke_paginas_geven_geen_signalen(self):
        self.assertEqual(stappenplan.detecteer_zinnen(hulp.zusters()), [])


class TestKernbeweringen(unittest.TestCase):
    REGELS = [
        {
            "id": "originelen-of-kopieen",
            "titel": "Originelen of kopieën",
            "zoek_in": "uitklap:wat neem ik mee",
            "varianten": {
                "originelen": "originele documenten",
                "kopieën": r"neem[^.]*kopie",
            },
        }
    ]

    def _kopieen(self):
        return [
            (s, [(t, "Neem kopieën van al uw documenten mee.") if t == "Wat neem ik mee?" else (t, x) for t, x in ups])
            for s, ups in hulp.STANDAARD_STAPPEN
        ]

    def test_originelen_tegenover_kopieen_is_inhoudelijk(self):
        paginas = hulp.zusters(Aruba={"stappen": self._kopieen()})
        gevonden = stappenplan.detecteer_beweringen(paginas, beweringen=self.REGELS)
        self.assertEqual(len(gevonden), 1)
        self.assertEqual(gevonden[0].eigenaar, EIGENAAR_KENNISEIGENAAR)
        self.assertEqual(gevonden[0].waargenomen, "aruba: kopieën")
        self.assertEqual(gevonden[0].elders, "originelen")

    def test_zonder_duidelijke_meerderheid_geen_signaal(self):
        afwijkend = {"stappen": self._kopieen()}
        paginas = hulp.zusters(Aruba=afwijkend, Bahrein=afwijkend, Belize=afwijkend)
        self.assertEqual(stappenplan.detecteer_beweringen(paginas, beweringen=self.REGELS), [])

    def test_de_meegeleverde_regels_zijn_geldig(self):
        for regel in stappenplan.laad_beweringen():
            self.assertTrue({"id", "titel", "zoek_in", "varianten"} <= set(regel), regel)
            stappenplan._antwoord("proef", regel["varianten"])  # regexen compileren


class TestRegister(unittest.TestCase):
    def test_alle_detectoren_uit_de_familieconfig_bestaan(self):
        import pathlib
        import yaml

        config = yaml.safe_load(pathlib.Path("regels/families.yaml").read_text(encoding="utf-8"))
        for familie in config["families"]:
            for naam in familie["detectoren"]:
                self.assertIn(naam, register.namen(), familie["id"])

    def test_draait_alle_vijf_op_echte_pagina_s_zonder_fouten(self):
        paginas = [hulp.paspoort_pagina(l) for l in ("albanie", "brazilie", "duitsland", "thailand")]
        # Met vier pagina's is er te weinig om een norm uit af te leiden: stil, geen crash.
        bevindingen, waarschuwingen = register.draai(
            ["stappenplan", "uitklapparagrafen", "koppenstructuur", "standaardzinnen", "kernbeweringen"],
            paginas,
            min_zusters=5,
            min_eensgezind=0.8,
        )
        self.assertEqual(bevindingen, [])
        self.assertEqual(waarschuwingen, [])


if __name__ == "__main__":
    unittest.main()
