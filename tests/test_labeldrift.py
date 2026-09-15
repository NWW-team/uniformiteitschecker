"""De belangrijkste test van stap 2.

`labeldrift` voegt rijen samen, en samengevoegde rijen gaan de waardendetector in. Een
foute samenvoeging laat de app dus tegenstrijdigheden verzinnen die niet bestaan. De
negatieve asserties hieronder zijn daarom belangrijker dan de positieve.

De lijst GEVAAR komt uit een echte meting: met `difflib` op ratio >= 0.85 voegt deze
familie twaalf labelparen samen, waarvan elf fout. Dit zijn ze.
"""

import unittest

from checker.detectie.labeldrift import _toelichting_is_veilig, detecteer
from checker.detectie.normalisatie import (
    labelsleutel_bereik,
    labelsleutel_kaal,
    normaliseer_label,
)
from checker.model import EIGENAAR_REDACTIE, SOORT_SCHRIJFRICHTLIJN

from . import hulp

SLEUTELFUNCTIES = (normaliseer_label, labelsleutel_bereik, labelsleutel_kaal)

# Labelparen die nooit als dezelfde rij mogen gelden.
GEVAAR = [
    ("Paspoort meerderjarige", "Paspoort minderjarige"),
    ("ID-kaart meerderjarige", "ID-kaart minderjarige"),
    (
        "Naturalisatie: gemeenschappelijk, standaard",
        "Naturalisatie: gemeenschappelijk, verlaagd",
    ),
    ("Schengenvisum kinderen tot 6 jaar", "Schengenvisum kinderen 6 t/m 11 jaar"),
    ("Paspoort minderjarige", "Zakenpaspoort minderjarige"),
    (
        "Caribisch visum kinderen 6 t/m 11 jaar",
        "Inreisvisum kinderen 6 t/m 11 jaar",
    ),
]


class TestGeenFouteSamenvoeging(unittest.TestCase):
    def test_tegengestelde_labels_krijgen_nooit_dezelfde_sleutel(self):
        for a, b in GEVAAR:
            for sleutelfunctie in SLEUTELFUNCTIES:
                with self.subTest(a=a, b=b, regel=sleutelfunctie.__name__):
                    self.assertNotEqual(sleutelfunctie(a), sleutelfunctie(b))

    def test_verschillende_examens_worden_niet_samengevoegd(self):
        """`(voor naturalisatie)` en `(MVV)` zijn andere examens met andere tarieven."""
        self.assertFalse(
            _toelichting_is_veilig(
                {"Inburgeringsexamen (voor naturalisatie)", "Inburgeringsexamen (MVV)"}
            )
        )

    def test_een_kale_variant_opent_het_gat_niet(self):
        """Het latente geval: zodra er óók een kale variant bestaat, zou de eis 'één
        kant kaal' gehaald worden en zouden alle drie samengaan. De tweede eis --
        hoogstens één verschillende toelichting -- sluit dat af."""
        self.assertFalse(
            _toelichting_is_veilig(
                {
                    "Inburgeringsexamen",
                    "Inburgeringsexamen (voor naturalisatie)",
                    "Inburgeringsexamen (MVV)",
                }
            )
        )

    def test_betekenisvolle_toelichtingen_worden_niet_samengevoegd(self):
        """Met en zonder voordruk zijn verschillende diensten met een eigen tarief."""
        self.assertFalse(
            _toelichting_is_veilig(
                {
                    "Verklaring van in leven zijn",
                    "Verklaring van in leven zijn (indien voordruk)",
                    "Verklaring van in leven zijn (indien geen voordruk)",
                }
            )
        )

    def test_een_enkele_toelichting_mag_wel(self):
        self.assertTrue(
            _toelichting_is_veilig(
                {"Zakenpaspoort", "Zakenpaspoort (dubbel aantal visapagina's)"}
            )
        )


class TestBereik(unittest.TestCase):
    def test_zelfde_bereik_anders_genoteerd(self):
        vormen = [
            "Schengenvisum kinderen 6 t/m 11 jaar",
            "Schengenvisum kinderen 6-11 jaar",
            "Schengenvisum kinderen 6 - 11 jaar",
            "Schengenvisum kinderen 6 tot en met 11 jaar",
        ]
        sleutels = {labelsleutel_bereik(v) for v in vormen}
        self.assertEqual(len(sleutels), 1, sleutels)

    def test_ander_bereik_blijft_verschillend(self):
        self.assertNotEqual(
            labelsleutel_bereik("kinderen 6 t/m 11 jaar"),
            labelsleutel_bereik("kinderen 6 t/m 12 jaar"),
        )


class TestOpFixtures(unittest.TestCase):
    def test_vindt_de_drift_op_de_duitse_pagina(self):
        """Duitsland schrijft `Zakenpaspoort (dubbel aantal visapagina's)` waar de
        zusterpagina's `Zakenpaspoort` schrijven."""
        bevindingen = detecteer(hulp.paginas(), min_paginas=3)
        titels = " | ".join(b.titel for b in bevindingen)
        self.assertIn("Zakenpaspoort", titels)
        for bevinding in bevindingen:
            self.assertEqual(bevinding.soort, SOORT_SCHRIJFRICHTLIJN)
            self.assertEqual(bevinding.eigenaar, EIGENAAR_REDACTIE)

    def test_zwijgt_bij_te_weinig_paginas(self):
        self.assertEqual(detecteer(hulp.paginas(), min_paginas=99), [])

    def test_locatie_bevat_alleen_de_gangbare_vorm(self):
        """Dan blijft de vingerafdruk gelijk als een variant gecorrigeerd wordt."""
        for bevinding in detecteer(hulp.paginas(), min_paginas=3):
            self.assertEqual(
                set(bevinding.locatie), {"familie", "regel", "gangbaar_label"}
            )


if __name__ == "__main__":
    unittest.main()
