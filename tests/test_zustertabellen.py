"""De test die bepaalt of de app bruikbaar is.

De negatieve asserties zijn hier belangrijker dan de positieve: een ruwe vergelijking
over deze fixtures gaf ~90 "tegenstrijdigheden" waarvan er één echt was. Als die ruis
terugkomt, is het rapport onbruikbaar en wordt de checker niet vertrouwd.
"""

import unittest

from checker.detectie.zustertabellen import detecteer
from checker.model import EIGENAAR_KENNISEIGENAAR, SOORT_INHOUDELIJK

from . import hulp


class TestZustertabellen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bevindingen = detecteer(hulp.paginas())

    def test_vindt_exact_de_echte_afwijking(self):
        """Brazilië noemt € 26,00 waar de zusterpagina's € 27,00 zeggen."""
        self.assertEqual(len(self.bevindingen), 1, [b.titel for b in self.bevindingen])
        bevinding = self.bevindingen[0]
        self.assertEqual(
            bevinding.locatie["rij_label"], "Optieprocedure: medeopterende minderjarige"
        )
        self.assertIn("brazilie", bevinding.waargenomen)
        self.assertIn("26,00", bevinding.waargenomen)
        self.assertEqual(bevinding.elders, "€ 27,00")

    def test_inhoudelijke_afwijking_gaat_naar_de_kenniseigenaar(self):
        """De app kan niet weten welk bedrag klopt, ook niet bij een meerderheid."""
        bevinding = self.bevindingen[0]
        self.assertEqual(bevinding.soort, SOORT_INHOUDELIJK)
        self.assertEqual(bevinding.eigenaar, EIGENAAR_KENNISEIGENAAR)

    def test_spreekt_zich_niet_uit_over_wat_juist_is(self):
        actie = self.bevindingen[0].voorgestelde_actie.lower()
        self.assertIn("verifieer", actie)
        self.assertNotIn("27,00", actie)

    def test_geeft_verifieerbaar_bewijs_mee(self):
        """Vertrouwen komt uit controleerbaarheid, niet uit zekerheid van de tool."""
        zusters = self.bevindingen[0].zusters
        self.assertGreaterEqual(len(zusters), 2)
        for zuster in zusters:
            self.assertTrue(zuster["url"].startswith("https://"))
            self.assertTrue(zuster["variant"])

    def test_meldt_het_ontbrekende_euroteken_niet_als_tegenstrijdigheid(self):
        """Canada schrijft 169,15 omdat de kolomkop al EUR zegt — geen ander bedrag."""
        for bevinding in self.bevindingen:
            self.assertNotIn("canada", bevinding.waargenomen)

    def test_meldt_ontbrekende_rijen_niet(self):
        """Duitsland mist alle visumrijen: legitiem, want Duitsland is Schengen."""
        for bevinding in self.bevindingen:
            self.assertNotIn("visum", bevinding.locatie["rij_label"].lower())
            self.assertNotIn("duitsland", bevinding.waargenomen)

    def test_zwijgt_bij_te_weinig_zusters(self):
        """Uit twee pagina's valt geen norm af te leiden."""
        self.assertEqual(detecteer(hulp.paginas(["brazilie", "frankrijk"])), [])

    def test_zwijgt_bij_een_verdeelde_familie(self):
        """Een familie in twee kampen is variatie, geen afwijking."""
        self.assertEqual(detecteer(hulp.paginas(), min_eensgezind=0.99), [])

    def test_locatie_bevat_niet_de_afwijkende_landen(self):
        """Anders verandert de vingerafdruk zodra één land gecorrigeerd wordt, en
        vervalt een entry op de negeerlijst ongewild."""
        locatie = self.bevindingen[0].locatie
        self.assertEqual(set(locatie), {"familie", "rij_label"})


if __name__ == "__main__":
    unittest.main()
