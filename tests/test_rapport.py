import unittest

from checker.detectie.labeldrift import detecteer as detecteer_labeldrift
from checker.detectie.opmaak import detecteer as detecteer_opmaak
from checker.detectie.terminologie import detecteer as detecteer_terminologie
from checker.detectie.zustertabellen import detecteer as detecteer_waarden
from checker.rapport.html import render

from . import hulp


class TestRapport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paginas = hulp.paginas(hulp.ZUSTERS + ["kenia"])
        cls.bevindingen = (
            detecteer_waarden(paginas)
            + detecteer_opmaak(paginas)
            + detecteer_labeldrift(paginas, min_paginas=3)
            + detecteer_terminologie(paginas, min_eigen_labels=2)
        )
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

    def test_definieert_kleuren_voor_beide_themas(self):
        """Een kleur die alleen achter een media query staat, geeft de klassieke
        onleesbare pagina: lichte tekst op lichte achtergrond."""
        self.assertIn(":root {", self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)
        self.assertIn(':root:not([data-theme="light"])', self.html)


    def test_toont_de_vingerafdruk_zodat_de_redactie_kan_onderdrukken(self):
        """Zonder vingerafdruk in het rapport kan niemand een negeerlijst-entry maken."""
        self.assertIn('class="vinger"', self.html)
        self.assertIn(self.bevindingen[0].vingerafdruk[:12], self.html)

    def test_onderdrukte_signalen_zijn_zichtbaar(self):
        """Een onzichtbare negeerlijst wordt een verborgen bug."""
        bevinding = self.bevindingen[0]
        html = render(
            bevindingen=[],
            familie="consulaire-tarieven",
            datum="2026-09-15",
            aantal_paginas=218,
            waarschuwingen=[],
            onderdrukt=[(bevinding, {"reden": "Landspecifiek tarief", "door": "redactie"})],
        )
        self.assertIn("1 signalen onderdrukt", html)
        self.assertIn("Landspecifiek tarief", html)
        self.assertIn("negeerlijst.yaml", html)

    def test_kolomkoppen_passen_bij_de_regel(self):
        """Bij eigen terminologie is er geen tegenhanger om naar te wijzen, dus
        "Staat elders" zou daar misleidend zijn."""
        self.assertIn("Eigen term op deze pagina", self.html)
        self.assertIn("Gangbare formulering", self.html)


if __name__ == "__main__":
    unittest.main()
