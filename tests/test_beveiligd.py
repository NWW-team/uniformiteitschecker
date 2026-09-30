import unittest

from checker.detectie.opmaak import detecteer as detecteer_opmaak
from checker.detectie.zustertabellen import detecteer as detecteer_waarden
from checker.rapport.html import bouw_familie, render_beveiligd, render_paneel

from . import hulp

URL = "https://voorbeeld.supabase.co"
SLEUTEL = "sb_publishable_voorbeeld"


class TestBeveiligdeVersie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paginas = hulp.paginas(hulp.ZUSTERS + ["kenia"])
        cls.bevindingen = detecteer_waarden(paginas) + detecteer_opmaak(paginas)
        cls.familie = bouw_familie(
            id="consulaire-tarieven",
            naam="Consulaire tarieven",
            bevindingen=cls.bevindingen,
            datum="2026-09-15",
            aantal_paginas=len(paginas),
        )
        cls.pagina = render_beveiligd(supabase_url=URL, supabase_sleutel=SLEUTEL)
        cls.paneel = render_paneel(cls.familie)

    def test_pagina_bevat_geen_enkel_signaal(self):
        """Het hele punt: wie niet is ingelogd, krijgt de signalen niet te zien."""
        self.assertTrue(self.bevindingen)
        self.assertNotIn("<details", self.pagina.replace('<details class="rhc-methode">', ""))
        for b in self.bevindingen:
            self.assertNotIn(b.urls[0], self.pagina)
            self.assertNotIn(b.titel, self.pagina)

    def test_bovenkant_blijft_openbaar(self):
        self.assertIn("Uniformiteitssignalen", self.pagina)
        self.assertIn("Hoe de checker afwijkingen vindt", self.pagina)

    def test_inlogknop_en_formulier_zijn_er(self):
        self.assertIn(">Inloggen</button>", self.pagina)
        self.assertIn("utrecht-button--primary-action", self.pagina)
        self.assertIn('type="password"', self.pagina)

    def test_zoekmachines_worden_gevraagd_weg_te_blijven(self):
        self.assertIn('name="robots" content="noindex, nofollow"', self.pagina)

    def test_alleen_de_publieke_sleutel_staat_in_de_pagina(self):
        self.assertIn(SLEUTEL, self.pagina)
        self.assertIn(URL, self.pagina)
        self.assertNotIn("service", SLEUTEL)

    def test_paneel_is_een_fragment_met_bevindingen_en_vaste_id(self):
        self.assertNotIn("<html", self.paneel)
        self.assertIn("Wijkt af", self.paneel)
        for b in self.bevindingen:
            self.assertIn(f'data-id="{b.vingerafdruk}"', self.paneel)

    def test_paneel_draagt_naam_en_aantal_voor_de_tabbalk(self):
        self.assertIn('data-naam="Consulaire tarieven"', self.paneel)
        self.assertIn(f'data-aantal="{len(self.bevindingen)}"', self.paneel)


if __name__ == "__main__":
    unittest.main()
