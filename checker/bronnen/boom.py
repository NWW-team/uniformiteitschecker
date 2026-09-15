"""Lichte HTML-boom op stdlib `html.parser`.

Er is geen bs4 of lxml in de omgeving, en dat is geen probleem: de pagina's zijn
server-rendered met schone semantische markup, dus een minimale boom volstaat. Voordeel
is dat de app zonder installatiestap in elke verse container draait.
"""

from __future__ import annotations

from html.parser import HTMLParser

# Tags die zichzelf sluiten en dus nooit een kind krijgen.
LEGE_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Inhoud hiervan is geen zichtbare tekst.
NEGEER_INHOUD = {"script", "style", "noscript", "template"}


class Node:
    """Eén element in de boom. `tag` is None voor het wortelelement."""

    __slots__ = ("tag", "attrs", "kinderen", "ouder")

    def __init__(self, tag: str | None, attrs: dict[str, str] | None = None,
                 ouder: "Node | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        # Kinderen zijn Node-objecten of tekstfragmenten (str).
        self.kinderen: list["Node | str"] = []
        self.ouder = ouder

    def vind_alle(self, tag: str) -> list["Node"]:
        """Alle afstammelingen met deze tag, in documentvolgorde."""
        gevonden: list[Node] = []
        for kind in self.kinderen:
            if isinstance(kind, Node):
                if kind.tag == tag:
                    gevonden.append(kind)
                gevonden.extend(kind.vind_alle(tag))
        return gevonden

    def directe_kinderen(self, tag: str) -> list["Node"]:
        return [k for k in self.kinderen if isinstance(k, Node) and k.tag == tag]

    def tekst(self) -> str:
        """Alle zichtbare tekst, met witruimte samengevouwen.

        Labels bevatten geneste tags (bv. `<span lang="fr">Laissez-passer</span> of
        noodpaspoort`), dus platslaan is precies wat we willen.
        """
        delen: list[str] = []
        self._verzamel_tekst(delen)
        return " ".join("".join(delen).split())

    def _verzamel_tekst(self, uit: list[str]) -> None:
        for kind in self.kinderen:
            if isinstance(kind, str):
                uit.append(kind)
            elif kind.tag not in NEGEER_INHOUD:
                # Blokovergangen mogen woorden niet aan elkaar plakken.
                uit.append(" ")
                kind._verzamel_tekst(uit)
                uit.append(" ")


class _Bouwer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.wortel = Node(None)
        self._stapel = [self.wortel]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: (v or "") for k, v in attrs}, self._stapel[-1])
        self._stapel[-1].kinderen.append(node)
        if tag not in LEGE_TAGS:
            self._stapel.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: (v or "") for k, v in attrs}, self._stapel[-1])
        self._stapel[-1].kinderen.append(node)

    def handle_endtag(self, tag: str) -> None:
        # Zoek terug naar de bijbehorende open tag; ongebalanceerde markup mag de
        # boom niet laten ontsporen.
        for i in range(len(self._stapel) - 1, 0, -1):
            if self._stapel[i].tag == tag:
                del self._stapel[i:]
                return

    def handle_data(self, data: str) -> None:
        self._stapel[-1].kinderen.append(data)


def ontleed(html: str) -> Node:
    """Ontleed HTML tot een boom en geef het wortelelement terug."""
    bouwer = _Bouwer()
    bouwer.feed(html)
    bouwer.close()
    return bouwer.wortel
