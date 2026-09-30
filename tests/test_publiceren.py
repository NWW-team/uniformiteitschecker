import unittest

from checker import publiceren


class NepAntwoord:
    def raise_for_status(self):
        pass


class NepClient:
    def __init__(self):
        self.aanroepen = []

    def post(self, url, headers, json):
        self.aanroepen.append((url, headers, json))
        return NepAntwoord()


class TestPubliceren(unittest.TestCase):
    def test_schrijft_met_de_servicesleutel_en_werkt_bestaande_tabbladen_bij(self):
        client = NepClient()
        panelen = [{"familie": "a", "naam": "A", "datum": "2026-09-30", "volgorde": 0, "aantal": 1, "html": "<x>"}]
        n = publiceren.publiceer_panelen(
            panelen, url="https://x.supabase.co/", servicesleutel="geheim", client=client
        )
        self.assertEqual(n, 1)
        url, headers, body = client.aanroepen[0]
        self.assertEqual(url, "https://x.supabase.co/rest/v1/rapport_panelen?on_conflict=familie")
        self.assertEqual(headers["Authorization"], "Bearer geheim")
        self.assertIn("merge-duplicates", headers["Prefer"])
        self.assertEqual(body, panelen)

    def test_zonder_sleutel_stopt_het_met_uitleg(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as fout:
                publiceren.servicesleutel_uit_omgeving()
        self.assertIn("SUPABASE_SERVICE_KEY", str(fout.exception))


if __name__ == "__main__":
    unittest.main()
