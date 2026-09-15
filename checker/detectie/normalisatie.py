"""Waarden vergelijkbaar maken vóór ze te vergelijken.

Dit is de belangrijkste les uit de verkenning. Een ruwe stringvergelijking over 12
tariefpagina's gaf ~90 "tegenstrijdigheden" waarvan er één echt was, en een eerste run
over alle 218 pagina's gaf er nog ~20 doordat Kenia en Irak bedragen in Engelse notatie
schrijven (`€167.80`, `€1,139.00`) in plaats van Nederlandse (`€ 167,80`).

Beide gevallen zijn opmaakverschillen, geen inhoudelijke verschillen. Dus: vergelijk op
de genormaliseerde numerieke waarde, en meld de notatie apart als afwijking van de
schrijfrichtlijnen — zodat dat signaal niet verdwijnt maar ook niet als twintig
tegenstrijdigheden langskomt.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

NOTATIE_NL = "nl"
NOTATIE_EN = "en"

# Een bedrag: optioneel euroteken, cijfers met punten en/of komma's als scheidingsteken.
_BEDRAG = re.compile(r"^\s*(?:€\s*)?(\d[\d.,]*)\s*$")
_LAATSTE_SCHEIDING = re.compile(r"[.,](\d+)$")


def _geldig_heel_getal(heel: str, duizendteken: str) -> bool:
    """Is dit een geldig geheel deel — zonder scheidingstekens, of in groepen van drie?

    Voorkomt dat onzin als `12.34.56` als bedrag wordt gelezen; die waarde valt dan
    terug op een tekstvergelijking in plaats van stilzwijgend een getal te worden.
    """
    if heel.isdigit():
        return True
    return re.fullmatch(rf"\d{{1,3}}(?:{re.escape(duizendteken)}\d{{3}})+", heel) is not None


def _ontleed(rauw: str) -> tuple[Decimal, str] | None:
    """Ontleed een bedrag tot (waarde, notatie), of None als het geen bedrag is.

    De notatie leiden we af uit het laatste scheidingsteken: gevolgd door twee cijfers
    is het een decimaalteken, gevolgd door drie cijfers een duizendscheidingsteken. Zo
    worden `1.139,00` en `1,139.00` allebei correct 1139.00.
    """
    m = _BEDRAG.match(rauw)
    if not m:
        return None
    cijfers = m.group(1)

    laatste = _LAATSTE_SCHEIDING.search(cijfers)
    if laatste is None:
        # Geen scheidingsteken: een heel bedrag zonder centen.
        return (Decimal(cijfers), NOTATIE_NL) if cijfers.isdigit() else None

    scheidingsteken = cijfers[laatste.start()]
    staart = laatste.group(1)

    if len(staart) == 2:
        # Decimaalteken. Komma is Nederlands, punt is Engels.
        notatie = NOTATIE_NL if scheidingsteken == "," else NOTATIE_EN
        heel = cijfers[: laatste.start()]
        decimalen = staart
    elif len(staart) == 3:
        # Duizendscheidingsteken. Punt is Nederlands, komma is Engels.
        notatie = NOTATIE_NL if scheidingsteken == "." else NOTATIE_EN
        heel = cijfers
        decimalen = "00"
    else:
        return None

    duizendteken = "." if notatie == NOTATIE_NL else ","
    if not _geldig_heel_getal(heel, duizendteken):
        return None

    try:
        return Decimal(f"{heel.replace('.', '').replace(',', '')}.{decimalen}"), notatie
    except InvalidOperation:
        return None


def normaliseer_bedrag(rauw: str) -> Decimal | None:
    """Zet een bedrag om naar een `Decimal`, of geef None als het geen bedrag is.

    Negeert euroteken, witruimte, scheidingstekens en notatieverschillen — precies de
    dingen die anders valse inhoudelijke afwijkingen opleveren.
    """
    ontleed = _ontleed(rauw)
    return ontleed[0] if ontleed else None


def notatie(rauw: str) -> str | None:
    """Welke cijfernotatie dit bedrag gebruikt, of None als het geen bedrag is."""
    ontleed = _ontleed(rauw)
    return ontleed[1] if ontleed else None


def normaliseer_waarde(rauw: str) -> str:
    """Genormaliseerde tekstvorm van een celwaarde, voor vergelijking.

    Bedragen worden hun numerieke waarde; andere waarden worden witruimte-genormaliseerd
    en kleingeletterd, zodat alleen betekenisvolle verschillen overblijven.
    """
    bedrag = normaliseer_bedrag(rauw)
    if bedrag is not None:
        return str(bedrag)
    return " ".join(rauw.split()).casefold()


def normaliseer_label(rauw: str) -> str:
    """Sleutel waarop rijen van zusterpagina's aan elkaar gekoppeld worden.

    Witruimte, interpunctie en hoofdletters mogen de koppeling niet breken; een
    voetnootmarkering (`Schengenvisum laag tarief**`) verwijst naar tekst onder de
    tabel en hoort niet bij de identiteit van de rij.
    """
    zonder_voetnoot = rauw.rstrip("*").strip()
    samengevouwen = " ".join(zonder_voetnoot.split())
    return re.sub(r"[^\w\s]", "", samengevouwen, flags=re.UNICODE).casefold().strip()


def bevat_euroteken(rauw: str) -> bool:
    return "€" in rauw


# "6 t/m 11", "6-11", "6 - 11" en "6 tot en met 11" duiden hetzelfde bereik aan.
_BEREIK = re.compile(r"(\d+)\s*(?:t/m|tot en met|-|–)\s*(\d+)")

# Een toelichting tussen haakjes, bijvoorbeeld "(dubbel aantal visapagina's)".
_HAAKJES = re.compile(r"\s*\([^)]*\)")


def normaliseer_bereik(rauw: str) -> str:
    """Schrijf getalbereiken in één vorm.

    Veilig omdat de getallen zelf gelijk moeten blijven: `6 t/m 11` en `6-11` worden
    dezelfde sleutel, maar `tot 6 jaar` en `6 t/m 11 jaar` blijven verschillend.
    """
    return _BEREIK.sub(r"\1-\2", rauw)


def heeft_haakjes(rauw: str) -> bool:
    return _HAAKJES.search(rauw) is not None


def zonder_haakjes(rauw: str) -> str:
    """Verwijder toelichtingen tussen haakjes.

    Uitsluitend te gebruiken wanneer één van de vergeleken labels géén haakjes heeft.
    Anders voegt deze functie `Inburgeringsexamen (voor naturalisatie)` en
    `Inburgeringsexamen (MVV)` samen, en dat zijn verschillende examens.
    """
    return _HAAKJES.sub(" ", rauw)


def labelsleutel_bereik(rauw: str) -> str:
    """Labelsleutel waarin getalbereiken genormaliseerd zijn."""
    return normaliseer_label(normaliseer_bereik(rauw))


def labelsleutel_kaal(rauw: str) -> str:
    """Labelsleutel zonder haakjes en met genormaliseerd bereik."""
    return normaliseer_label(zonder_haakjes(normaliseer_bereik(rauw)))
