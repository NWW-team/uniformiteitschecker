import unittest
from decimal import Decimal

from checker.detectie.normalisatie import (
    NOTATIE_EN,
    NOTATIE_NL,
    normaliseer_bedrag,
    normaliseer_label,
    normaliseer_waarde,
    notatie,
)


class TestBedragen(unittest.TestCase):
    def test_negeert_euroteken_en_spatie(self):
        """Canada zet het euroteken in de kolomkop; dat is geen ander bedrag."""
        for rauw in ("€ 169,15", "€169,15", "169,15", " 169,15 "):
            self.assertEqual(normaliseer_bedrag(rauw), Decimal("169.15"), rauw)

    def test_beide_notaties_leveren_dezelfde_waarde(self):
        """Kenia schrijft €169.15, de rest € 169,15 — zelfde bedrag."""
        self.assertEqual(normaliseer_bedrag("€167.80"), normaliseer_bedrag("€ 167,80"))
        self.assertEqual(
            normaliseer_bedrag("€1,139.00"), normaliseer_bedrag("€ 1.139,00")
        )

    def test_duizendscheiding(self):
        self.assertEqual(normaliseer_bedrag("€ 1.139,00"), Decimal("1139.00"))
        self.assertEqual(normaliseer_bedrag("1.139"), Decimal("1139"))

    def test_geen_bedrag(self):
        for rauw in ("", "Gratis", "diverse tarieven", "12.34.56"):
            self.assertIsNone(normaliseer_bedrag(rauw), rauw)

    def test_herkent_notatie(self):
        self.assertEqual(notatie("€ 169,15"), NOTATIE_NL)
        self.assertEqual(notatie("€169.15"), NOTATIE_EN)
        self.assertEqual(notatie("€ 1.139,00"), NOTATIE_NL)
        self.assertEqual(notatie("€1,139.00"), NOTATIE_EN)
        self.assertIsNone(notatie("Gratis"))

    def test_echte_afwijking_blijft_verschillen(self):
        """De normalisatie mag geen echte tegenstrijdigheid wegpoetsen."""
        self.assertNotEqual(normaliseer_waarde("€ 26,00"), normaliseer_waarde("€ 27,00"))


class TestLabels(unittest.TestCase):
    def test_voetnoot_hoort_niet_bij_de_identiteit(self):
        self.assertEqual(
            normaliseer_label("Schengenvisum laag tarief**"),
            normaliseer_label("Schengenvisum laag tarief"),
        )

    def test_hoofdletters_en_witruimte(self):
        self.assertEqual(
            normaliseer_label("  Paspoort   MEERDERJARIGE "),
            normaliseer_label("Paspoort meerderjarige"),
        )

    def test_verschillende_labels_blijven_verschillend(self):
        """Labeldrift moet zichtbaar blijven, niet samengevouwen worden."""
        self.assertNotEqual(
            normaliseer_label("Zakenpaspoort"),
            normaliseer_label("Zakenpaspoort (dubbel aantal visapagina's)"),
        )


if __name__ == "__main__":
    unittest.main()
