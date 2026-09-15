"""Eigen termen melden, zonder te beweren dat ze hetzelfde betekenen.

Deze detector mag gelijkenis gebruiken omdat hij niets samenvoegt: de uitkomst is een
vraag aan de redactie, niet een vergelijking van bedragen. De tests hieronder leggen
precies dat vast.
"""

import unittest

from checker.detectie.terminologie import _suggestie, detecteer
from checker.model import EIGENAAR_REDACTIE, SOORT_SCHRIJFRICHTLIJN

from . import hulp

# Kenia en canada hebben eigen termen; de andere zijn schone zusters.
ALLE = hulp.ZUSTERS + ["kenia"]


class TestSuggesties(unittest.TestCase):
    GANGBAAR = {
        "zakenpaspoort minderjarige": "Zakenpaspoort minderjarige",
        "schengenvisum laag tarief": "Schengenvisum laag tarief**",
        "inreisvisum": "Inreisvisum",
        "schengenvisum kinderen tot 6 jaar": "Schengenvisum kinderen tot 6 jaar",
    }

    def test_stelt_de_juiste_dienst_voor(self):
        self.assertEqual(
            _suggestie("zakenpaspoort minderjarigen", self.GANGBAAR),
            "Zakenpaspoort minderjarige",
        )

    def test_kruist_geen_diensten(self):
        """`Inreisvisum, laag tarief` hoort niet bij `Schengenvisum laag tarief`: het
        eerste woord benoemt de dienst."""
        self.assertEqual(
            _suggestie("inreisvisum laag tarief", self.GANGBAAR), "Inreisvisum"
        )

    def test_kruist_geen_leeftijdsklassen(self):
        """`tot 11 jaar` mag niet aan `tot 6 jaar` gekoppeld worden: de getallen
        benoemen het tarief."""
        self.assertIsNone(
            _suggestie("schengenvisum kinderen tot 11 jaar", self.GANGBAAR)
        )

    def test_geen_suggestie_als_niets_lijkt(self):
        self.assertIsNone(_suggestie("koerierskosten", self.GANGBAAR))


class TestDetector(unittest.TestCase):
    def test_meldt_per_pagina_en_niet_per_term(self):
        """Anders levert de lange staart tientallen regels in het rapport op."""
        bevindingen = detecteer(hulp.paginas(ALLE), min_eigen_labels=2)
        for bevinding in bevindingen:
            self.assertEqual(len(bevinding.urls), 1)
            self.assertIn("familie_sleutel", bevinding.locatie)

    def test_is_een_schrijfrichtlijn_voor_de_redactie(self):
        for bevinding in detecteer(hulp.paginas(ALLE), min_eigen_labels=2):
            self.assertEqual(bevinding.soort, SOORT_SCHRIJFRICHTLIJN)
            self.assertEqual(bevinding.eigenaar, EIGENAAR_REDACTIE)

    def test_zekerheid_blijft_middel(self):
        """Een eigen term kan een dienst zijn die echt alleen op die post bestaat."""
        for bevinding in detecteer(hulp.paginas(ALLE), min_eigen_labels=2):
            self.assertEqual(bevinding.zekerheid, "middel")

    def test_noemt_suggesties_expliciet_een_gelijkenis(self):
        """De app mag niet de indruk wekken dat ze weet dat het dezelfde dienst is."""
        for bevinding in detecteer(hulp.paginas(ALLE), min_eigen_labels=2):
            self.assertIn("geen", bevinding.toelichting)
            self.assertIn("vaststelling", bevinding.toelichting)
            for variant in bevinding.varianten:
                if variant["waarde"].startswith("lijkt op"):
                    self.assertNotIn("is hetzelfde", variant["waarde"])

    def test_drempel_houdt_de_staart_buiten(self):
        streng = detecteer(hulp.paginas(ALLE), min_eigen_labels=99)
        self.assertEqual(streng, [])


if __name__ == "__main__":
    unittest.main()
