import unittest

from checker.detectie.opmaak import detecteer as detecteer_opmaak
from checker.detectie.zustertabellen import detecteer as detecteer_waarden
from checker.model import Bevinding
from checker.rapport.html import _paginas, bouw_familie, render_beveiligd, render_paneel

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

    def test_elke_afwijkende_pagina_is_een_eigen_regel_met_link_en_bewijs(self):
        for b in self.bevindingen:
            for p in _paginas(b):
                self.assertIn(f'data-url="{p["url"]}"', self.paneel)
                self.assertIn(f'data-bewijs="{p["bewijs"]}"', self.paneel)
                self.assertIn(f'href="{p["url"]}"', self.paneel)
        # De uitgeschreven URL-lijst onder het signaal is vervangen door de links in de regels.
        self.assertNotIn("rhc-paginas", self.paneel)

    def test_paneel_draagt_de_controledatum(self):
        self.assertIn('data-datum="2026-09-15"', self.paneel)

    def test_pagina_heeft_het_afhandelscript_maar_nog_geen_signalen(self):
        self.assertIn("rapport-geladen", self.pagina)
        self.assertIn("/rest/v1/afvinkingen", self.pagina)
        self.assertNotIn("service_role", self.pagina)


class TestBewijsPerPagina(unittest.TestCase):
    def _bevinding(self, waargenomen: str, urls: list[str]) -> Bevinding:
        return Bevinding(
            regel_id="r", soort="inhoudelijk", eigenaar="kenniseigenaar", titel="t",
            urls=urls, locatie={"x": 1}, waargenomen=waargenomen,
        )

    def test_bewijs_verandert_alleen_voor_de_pagina_die_wijzigt(self):
        urls = ["https://x/a", "https://x/b"]
        voor = _paginas(self._bevinding("a: € 10 | b: € 20", urls))
        na = _paginas(self._bevinding("a: € 10 | b: € 25", urls))
        self.assertEqual(voor[0]["bewijs"], na[0]["bewijs"])
        self.assertNotEqual(voor[1]["bewijs"], na[1]["bewijs"])

    def test_een_pagina_met_meerdere_waarden_blijft_een_regel(self):
        regels = _paginas(self._bevinding("a: € 1 | a: € 2 | a: € 3", ["https://x/a"]))
        self.assertEqual(len(regels), 1)
        self.assertEqual(regels[0]["waarden"], ["€ 1", "€ 2", "€ 3"])


if __name__ == "__main__":
    unittest.main()
