"""Van corpus naar rapport, met een vast verwacht aantal signalen.

Dit is het vangnet: verandert de termenlijst of de matcher, dan valt hier op wat dat
met de uitkomst doet.
"""

import json

from uniformiteitschecker.cli import main
from uniformiteitschecker.crawler import lees_corpus
from uniformiteitschecker.rapport import samenvatting, schrijf_html, schrijf_json
from uniformiteitschecker.regels import controleer_alles, laad_regels

VERWACHT_PER_REGEL = {
    "reisdocument-vs-paspoort": 2,        # 2x 'paspoort', niet 'paspoortfoto'
    "identiteitskaart-vs-id-kaart": 1,    # 'ID-kaart'
    "travel-document-vs-passport": 1,     # 'passport'
    "legalisation-spelling": 1,           # 'Legalization'
    "authorisation-spelling": 1,          # 'authorization'
}


def test_bevindingen_over_mini_corpus(fixtures):
    paginas = lees_corpus(fixtures / "corpus")
    regels = laad_regels("config/termen.yaml")
    bevindingen = controleer_alles(paginas, regels)

    gevonden = {regel_id: aantal for regel_id, aantal, _ in samenvatting(bevindingen)}
    assert gevonden == VERWACHT_PER_REGEL


def test_engelse_regels_raken_geen_nederlandse_paginas(fixtures):
    paginas = lees_corpus(fixtures / "corpus")
    bevindingen = controleer_alles(paginas, laad_regels("config/termen.yaml"))
    for bevinding in bevindingen:
        assert bevinding.taal == ("en" if bevinding.regel_id.endswith(("spelling", "passport")) else "nl")


def test_rapport_bevat_url_fragment_en_voorkeursterm(fixtures, tmp_path):
    paginas = lees_corpus(fixtures / "corpus")
    bevindingen = controleer_alles(paginas, laad_regels("config/termen.yaml"))

    html_pad = tmp_path / "rapport.html"
    schrijf_html(bevindingen, paginas, html_pad, {"nww-nl": ["/onderwerpen/paspoort"]})
    html = html_pad.read_text(encoding="utf-8")

    assert "https://www.nederlandwereldwijd.nl/onderwerpen/paspoort/aanvragen" in html
    assert "<mark>paspoort</mark>" in html
    assert "reisdocument" in html
    assert "/onderwerpen/paspoort" in html          # afbakening staat in het rapport
    assert "<script" not in html                     # zelfstandig bestand, geen scripts


def test_json_is_geldig_en_gesorteerd(fixtures, tmp_path):
    paginas = lees_corpus(fixtures / "corpus")
    bevindingen = controleer_alles(paginas, laad_regels("config/termen.yaml"))

    json_pad = tmp_path / "bevindingen.json"
    schrijf_json(bevindingen, json_pad)
    gegevens = json.loads(json_pad.read_text(encoding="utf-8"))

    assert len(gegevens) == sum(VERWACHT_PER_REGEL.values())
    sleutels = [(r["regel_id"], r["url"], r["positie"]) for r in gegevens]
    assert sleutels == sorted(sleutels)


def test_leeg_rapport_meldt_dat_netjes(tmp_path):
    pad = tmp_path / "rapport.html"
    schrijf_html([], [], pad)
    assert "Geen afwijkingen gevonden" in pad.read_text(encoding="utf-8")


def test_cli_check_draait_over_fixtures(fixtures, tmp_path, capsys):
    code = main([
        "check",
        "--corpus", str(fixtures / "corpus"),
        "--regels", "config/termen.yaml",
        "--sites", "config/sites.yaml",
        "--uit", str(tmp_path),
    ])
    uitvoer = capsys.readouterr().out

    assert code == 0
    assert "3 pagina's gecontroleerd" in uitvoer
    assert (tmp_path / "rapport.html").exists()
    assert (tmp_path / "bevindingen.json").exists()


def test_cli_check_strict_geeft_exitcode_1(fixtures, tmp_path):
    code = main([
        "check", "--corpus", str(fixtures / "corpus"), "--regels", "config/termen.yaml",
        "--uit", str(tmp_path), "--strict",
    ])
    assert code == 1


def test_cli_check_zonder_corpus_meldt_dat(tmp_path):
    code = main(["check", "--corpus", str(tmp_path / "leeg"), "--uit", str(tmp_path)])
    assert code == 1
