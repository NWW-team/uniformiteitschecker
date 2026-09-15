import unittest

from checker.detectie.opmaak import detecteer
from checker.detectie.zustertabellen import detecteer as detecteer_waarden
from checker.model import EIGENAAR_REDACTIE, SOORT_SCHRIJFRICHTLIJN

from . import hulp

# Kenia noteert bedragen in Engelse notatie; de vijf andere in Nederlandse.
MET_KENIA = hulp.ZUSTERS + ["kenia"]


class TestBedragnotatie(unittest.TestCase):
    def test_meldt_de_afwijkende_notatie_als_schrijfrichtlijn(self):
        bevindingen = detecteer(hulp.paginas(MET_KENIA))
        self.assertEqual(len(bevindingen), 1, [b.titel for b in bevindingen])
        bevinding = bevindingen[0]
        self.assertEqual(bevinding.locatie["familie_sleutel"], "kenia")
        self.assertEqual(bevinding.soort, SOORT_SCHRIJFRICHTLIJN)
        self.assertEqual(bevinding.eigenaar, EIGENAAR_REDACTIE)

    def test_bundelt_alle_bedragen_van_een_pagina_in_een_bevinding(self):
        """Op de Kenia-pagina staan ruim dertig bedragen in Engelse notatie.
        Dat is één correctie, geen dertig regels in het rapport."""
        bevinding = detecteer(hulp.paginas(MET_KENIA))[0]
        self.assertGreater(bevinding.telling["afwijkend"], 20)
        self.assertEqual(len(bevinding.urls), 1)

    def test_notatie_levert_geen_inhoudelijke_bevinding_op(self):
        """De kern van de ruisonderdrukking: €169.15 en € 169,15 zijn hetzelfde bedrag,
        dus de waardendetector mag Kenia nergens noemen."""
        for bevinding in detecteer_waarden(hulp.paginas(MET_KENIA)):
            self.assertNotIn("kenia", bevinding.waargenomen)

    def test_zwijgt_als_de_hele_familie_dezelfde_notatie_gebruikt(self):
        self.assertEqual(detecteer(hulp.paginas()), [])

    def test_zwijgt_bij_te_weinig_zusters(self):
        self.assertEqual(detecteer(hulp.paginas(["kenia", "frankrijk"])), [])


if __name__ == "__main__":
    unittest.main()
