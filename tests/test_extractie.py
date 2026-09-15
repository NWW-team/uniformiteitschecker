import unittest

from checker.bronnen.extractie import ExtractieFout, extraheer_main, lees_pagina

from . import hulp


class TestExtractie(unittest.TestCase):
    def test_leest_tabellen_uit_echte_pagina(self):
        pagina = hulp.pagina("duitsland")
        self.assertEqual(pagina.titel, "Consulaire tarieven in Duitsland")
        self.assertEqual(len(pagina.tabellen), 5)
        self.assertEqual(sum(len(t.rijen) for t in pagina.tabellen), 28)

    def test_leest_label_en_waarde(self):
        eerste = hulp.pagina("duitsland").tabellen[0]
        self.assertEqual(eerste.kolomkoppen, ["Paspoort en identiteitskaart", "EUR"])
        self.assertEqual(eerste.rijen[0].label, "Paspoort meerderjarige")
        self.assertEqual(eerste.rijen[0].waarde_rauw, "€ 169,15")

    def test_slaat_geneste_tags_in_labels_plat(self):
        """`<span lang="fr">Laissez-passer</span> of noodpaspoort` is één label."""
        labels = [
            rij.label
            for tabel in hulp.pagina("duitsland").tabellen
            for rij in tabel.rijen
        ]
        self.assertIn("Laissez-passer of noodpaspoort", labels)

    def test_bewaart_de_rauwe_notatie(self):
        """De afwijkende schrijfwijze moet intact blijven, niet opgeschoond worden."""
        waarden = [
            rij.waarde_rauw
            for tabel in hulp.pagina("duitsland").tabellen
            for rij in tabel.rijen
        ]
        self.assertIn("€169,15", waarden)

        keniaanse = [
            rij.waarde_rauw
            for tabel in hulp.pagina("kenia").tabellen
            for rij in tabel.rijen
        ]
        self.assertIn("€169.15", keniaanse)

    def test_faalt_hard_bij_afwijkende_markup(self):
        """Stil een leeg resultaat opleveren is het ergst mogelijke faalgedrag."""
        with self.assertRaises(ExtractieFout):
            extraheer_main(hulp.lees_html("_fictief_twee_mains"))
        with self.assertRaises(ExtractieFout):
            extraheer_main("<div>geen main</div>")

    def test_tekst_gaat_mee_de_snapshot_in(self):
        """Nodig voor de terminologiedetector later, zonder opnieuw te crawlen."""
        self.assertIn("tarieflijst", hulp.pagina("duitsland").tekst)


if __name__ == "__main__":
    unittest.main()
