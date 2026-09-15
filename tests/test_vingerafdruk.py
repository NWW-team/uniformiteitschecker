"""Het vingerafdrukcontract is de basis van de negeerlijst.

Daarom staat het expliciet vastgelegd: de identiteit van een bevinding is "deze plek,
door deze regel gemarkeerd" — niet de waarde die er toevallig staat.
"""

import unittest

from checker.model import Bevinding


def maak(**overschrijf) -> Bevinding:
    standaard = dict(
        regel_id="zustertabel_waarden",
        soort="inhoudelijk",
        eigenaar="kenniseigenaar",
        titel="Bedrag wijkt af",
        urls=["https://www.nederlandwereldwijd.nl/consulaire-tarieven/brazilie"],
        locatie={"familie": "consulaire-tarieven", "rij_label": "Optieprocedure"},
        waargenomen="brazilie: € 26,00",
    )
    return Bevinding(**{**standaard, **overschrijf})


class TestVingerafdruk(unittest.TestCase):
    def test_blijft_gelijk_als_de_waarde_verandert(self):
        """Anders breekt een entry op de negeerlijst bij elke tekstwijziging."""
        self.assertEqual(
            maak().vingerafdruk,
            maak(waargenomen="brazilie: € 28,50").vingerafdruk,
        )

    def test_blijft_gelijk_bij_andere_sleutelvolgorde(self):
        self.assertEqual(
            maak().vingerafdruk,
            maak(locatie={"rij_label": "Optieprocedure", "familie": "consulaire-tarieven"}).vingerafdruk,
        )

    def test_verandert_bij_andere_locatie(self):
        self.assertNotEqual(
            maak().vingerafdruk,
            maak(locatie={"familie": "consulaire-tarieven", "rij_label": "Paspoort"}).vingerafdruk,
        )

    def test_verandert_bij_andere_regel(self):
        self.assertNotEqual(maak().vingerafdruk, maak(regel_id="bedragnotatie").vingerafdruk)

    def test_bewijs_hash_volgt_juist_wel_de_waarde(self):
        """Zo kan een negeerlijst-entry vervallen zodra de content wijzigt, in plaats
        van stilletjes een echte fout te blijven verbergen."""
        self.assertNotEqual(
            maak().bewijs_hash,
            maak(waargenomen="brazilie: € 28,50").bewijs_hash,
        )
        self.assertEqual(maak().bewijs_hash, maak().bewijs_hash)

    def test_beide_hashes_staan_in_de_uitvoer(self):
        d = maak().naar_dict()
        self.assertIn("vingerafdruk", d)
        self.assertIn("bewijs_hash", d)


if __name__ == "__main__":
    unittest.main()
