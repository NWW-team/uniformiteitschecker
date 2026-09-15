"""De negeerlijst mag nooit stilletjes echte fouten gaan verbergen."""

import datetime as dt
import unittest

from checker.detectie.onderdruk import laad, pas_toe
from checker.model import Bevinding

VANDAAG = dt.date(2026, 9, 15)


def maak(waargenomen: str = "brazilie: € 26,00") -> Bevinding:
    return Bevinding(
        regel_id="zustertabel_waarden",
        soort="inhoudelijk",
        eigenaar="kenniseigenaar",
        titel="Bedrag wijkt af",
        urls=["https://www.nederlandwereldwijd.nl/consulaire-tarieven/brazilie"],
        locatie={"familie": "consulaire-tarieven", "rij_label": "Optieprocedure"},
        waargenomen=waargenomen,
    )


class TestOnderdrukken(unittest.TestCase):
    def test_onderdrukt_op_vingerafdruk(self):
        bevinding = maak()
        uitkomst = pas_toe(
            [bevinding],
            [{"vingerafdruk": bevinding.vingerafdruk, "reden": "Landspecifiek"}],
            vandaag=VANDAAG,
        )
        self.assertEqual(uitkomst.overgebleven, [])
        self.assertEqual(len(uitkomst.onderdrukt), 1)
        self.assertEqual(uitkomst.onderdrukt[0][1]["reden"], "Landspecifiek")

    def test_laat_andere_bevindingen_staan(self):
        bevinding = maak()
        uitkomst = pas_toe([bevinding], [{"vingerafdruk": "iets anders"}], vandaag=VANDAAG)
        self.assertEqual(uitkomst.overgebleven, [bevinding])

    def test_onderdrukt_op_regel_en_url_patroon(self):
        bevinding = maak()
        uitkomst = pas_toe(
            [bevinding],
            [{"regel_id": "zustertabel_waarden", "url_glob": "*/consulaire-tarieven/*"}],
            vandaag=VANDAAG,
        )
        self.assertEqual(uitkomst.overgebleven, [])

    def test_patroon_op_een_andere_regel_raakt_niets(self):
        bevinding = maak()
        uitkomst = pas_toe(
            [bevinding],
            [{"regel_id": "bedragnotatie", "url_glob": "*"}],
            vandaag=VANDAAG,
        )
        self.assertEqual(uitkomst.overgebleven, [bevinding])

    def test_entry_zonder_vingerafdruk_en_zonder_patroon_onderdrukt_niets(self):
        """Anders zou één slecht ingevulde entry het hele rapport leegmaken."""
        bevinding = maak()
        uitkomst = pas_toe([bevinding], [{"reden": "vergeten sleutel"}], vandaag=VANDAAG)
        self.assertEqual(uitkomst.overgebleven, [bevinding])


class TestVervallen(unittest.TestCase):
    def test_gewijzigde_inhoud_laat_het_signaal_terugkomen(self):
        """Dit is wat voorkomt dat de lijst op termijn echte fouten verbergt."""
        beoordeeld = maak("brazilie: € 26,00")
        gewijzigd = maak("brazilie: € 19,00")
        entries = [
            {
                "vingerafdruk": beoordeeld.vingerafdruk,
                "bewijs_hash": beoordeeld.bewijs_hash,
                "reden": "Landspecifiek tarief",
            }
        ]

        # Zolang de waarde gelijk is, blijft de onderdrukking gelden.
        self.assertEqual(pas_toe([beoordeeld], entries, vandaag=VANDAAG).overgebleven, [])

        # Wijzigt de waarde, dan komt het signaal terug -- met uitleg.
        uitkomst = pas_toe([gewijzigd], entries, vandaag=VANDAAG)
        self.assertEqual(uitkomst.overgebleven, [gewijzigd])
        self.assertEqual(len(uitkomst.vervallen), 1)
        self.assertIn("gewijzigd", uitkomst.vervallen[0])

    def test_verlopen_onderdrukking_dwingt_herbeoordeling(self):
        bevinding = maak()
        entries = [
            {
                "vingerafdruk": bevinding.vingerafdruk,
                "reden": "Tijdelijk",
                "vervalt": dt.date(2026, 1, 1),
            }
        ]
        uitkomst = pas_toe([bevinding], entries, vandaag=VANDAAG)
        self.assertEqual(uitkomst.overgebleven, [bevinding])
        self.assertIn("verlopen", uitkomst.vervallen[0])

    def test_toekomstige_vervaldatum_onderdrukt_nog(self):
        bevinding = maak()
        entries = [
            {
                "vingerafdruk": bevinding.vingerafdruk,
                "vervalt": dt.date(2027, 1, 1),
            }
        ]
        self.assertEqual(pas_toe([bevinding], entries, vandaag=VANDAAG).overgebleven, [])

    def test_vervaldatum_als_tekst_werkt_ook(self):
        """YAML levert soms een string in plaats van een datum."""
        bevinding = maak()
        entries = [{"vingerafdruk": bevinding.vingerafdruk, "vervalt": "2026-01-01"}]
        self.assertEqual(
            pas_toe([bevinding], entries, vandaag=VANDAAG).overgebleven, [bevinding]
        )


class TestLaden(unittest.TestCase):
    def test_ontbrekend_bestand_is_geen_fout(self):
        self.assertEqual(laad("bestaat/niet.yaml"), [])

    def test_leest_de_meegeleverde_negeerlijst(self):
        """Die is nog leeg, maar moet geldige YAML zijn met de juiste structuur."""
        self.assertEqual(laad(), [])


if __name__ == "__main__":
    unittest.main()
