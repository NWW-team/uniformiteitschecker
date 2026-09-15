"""Register van detectoren.

Een detector is een functie die pagina's inleest en bevindingen teruggeeft. Ze
registreren zich onder een naam, zodat `regels/families.yaml` per familie kan kiezen
welke detectoren draaien zonder dat de pijplijn verandert.
"""

from __future__ import annotations

from typing import Callable, Iterable

from ..model import Bevinding, Pagina
from . import labeldrift, opmaak, terminologie, zustertabellen

Detector = Callable[..., list[Bevinding]]

_REGISTER: dict[str, Detector] = {
    zustertabellen.REGEL_ID: zustertabellen.detecteer,
    opmaak.REGEL_ID: opmaak.detecteer,
    labeldrift.REGEL_ID: labeldrift.detecteer,
    terminologie.REGEL_ID: terminologie.detecteer,
}

# Bovengrens per detector per run. Slaat een detector hierdoorheen, dan is er vrijwel
# zeker iets structureels gewijzigd in de template -- geen honderden losse fouten. Het
# rapport zegt dat dan expliciet, in plaats van de redactie te bedelven.
MAX_BEVINDINGEN_PER_DETECTOR = 50


def namen() -> list[str]:
    return sorted(_REGISTER)


def draai(
    detector_namen: Iterable[str],
    paginas: list[Pagina],
    **opties: object,
) -> tuple[list[Bevinding], list[str]]:
    """Draai de genoemde detectoren. Geeft bevindingen plus waarschuwingen terug."""
    bevindingen: list[Bevinding] = []
    waarschuwingen: list[str] = []

    for naam in detector_namen:
        detector = _REGISTER.get(naam)
        if detector is None:
            raise KeyError(f"onbekende detector {naam!r}; beschikbaar: {namen()}")

        gevonden = detector(paginas, **opties)
        if len(gevonden) > MAX_BEVINDINGEN_PER_DETECTOR:
            waarschuwingen.append(
                f"Regel {naam} gaf {len(gevonden)} signalen, "
                f"{MAX_BEVINDINGEN_PER_DETECTOR} getoond. Dit duidt eerder op een "
                "gewijzigde template dan op honderden losse fouten -- controleer dat "
                "eerst voordat je de lijst afgaat."
            )
            gevonden = gevonden[:MAX_BEVINDINGEN_PER_DETECTOR]
        bevindingen.extend(gevonden)

    return bevindingen, waarschuwingen
