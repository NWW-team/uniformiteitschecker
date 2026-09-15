import unittest

from checker.detectie.opmaak import detecteer as detecteer_opmaak
from checker.detectie.zustertabellen import detecteer as detecteer_waarden
from checker.rapport.html import render

from . import hulp


class TestRapport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paginas = hulp.paginas(hulp.ZUSTERS + ["kenia"])
        cls.bevindingen = detecteer_waarden(paginas) + detecteer_opmaak(paginas)
        cls.html = render(
            bevindingen=cls.bevindingen,
            familie="consulaire-tarieven",
            datum="2026-09-15",
            aantal_paginas=len(paginas),
            waarschuwingen=[],
        )

    def test_groepeert_op_wie_moet_handelen(self):
        """Dat is de vraag die het werk van de redacteur bepaalt."""
        self.assertIn("Zelf verbeteren", self.html)
        self.assertIn("Voorleggen aan kenniseigenaar", self.html)

    def test_toont_de_vindplaats_als_klikbare_link(self):
        self.assertIn(
            'href="https://www.nederlandwereldwijd.nl/consulaire-tarieven/brazilie"',
            self.html,
        )

    def test_toont_het_bewijs_naast_elkaar(self):
        self.assertIn("Wijkt af", self.html)
        self.assertIn("Staat elders", self.html)
        self.assertIn("€ 26,00", self.html)
        self.assertIn("€ 27,00", self.html)

    def test_zegt_dat_de_app_niets_oplost(self):
        self.assertIn("lost niets op", self.html)

    def test_waarschuwingen_komen_in_het_rapport(self):
        html = render(
            bevindingen=[],
            familie="consulaire-tarieven",
            datum="2026-09-15",
            aantal_paginas=0,
            waarschuwingen=["Regel X gaf 300 signalen"],
        )
        self.assertIn("Regel X gaf 300 signalen", html)

    def test_lege_uitkomst_krijgt_een_eerlijke_boodschap(self):
        html = render(
            bevindingen=[],
            familie="consulaire-tarieven",
            datum="2026-09-15",
            aantal_paginas=218,
            waarschuwingen=[],
        )
        self.assertIn("Geen afwijkingen gevonden", html)
        self.assertIn("foutloos zijn", html)

    def test_is_een_compleet_zelfstandig_document(self):
        """Zonder doctype, lang en viewport is het geen geldig, toegankelijk document."""
        self.assertIn("<!doctype html>", self.html)
        self.assertIn('<html lang="nl">', self.html)
        self.assertIn('<meta charset="utf-8">', self.html)
        self.assertIn("width=device-width", self.html)
        self.assertIn("<main", self.html)
        self.assertNotIn("fonts.googleapis.com", self.html)

    def test_volgt_de_rijkshuisstijl(self):
        self.assertIn('class="rhc-theme"', self.html)
        self.assertIn("--rhc-color-", self.html)


if __name__ == "__main__":
    unittest.main()
