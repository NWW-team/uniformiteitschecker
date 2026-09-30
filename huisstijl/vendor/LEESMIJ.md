# vendor — Rijkshuisstijl Community, onveranderd overgenomen

Officiële uitvoerbestanden van
[nl-design-system/rijkshuisstijl-community](https://github.com/nl-design-system/rijkshuisstijl-community),
overgenomen uit `NWW-team/social-media-postmaker` (die ze onveranderd uit npm haalde).
Niet met de hand bewerken.

| Bestand | Uit welk pakket | Versie |
| --- | --- | --- |
| `rhc-components.css` | `@rijkshuisstijl-community/components-css` → `dist/index.css` | 18.0.2 |
| `rhc-tokens-hemelblauw.css` | `@rijkshuisstijl-community/design-tokens` → `dist/hemelblauw/index.css` | 18.0.1 |
| `fonts/fira-sans-latin-{400,600,700}-normal.woff2` | `@rijkshuisstijl-community/font` → `dist/files/` | 1.1.6 |

Opnieuw ophalen: `npm pack @rijkshuisstijl-community/components-css @rijkshuisstijl-community/design-tokens @rijkshuisstijl-community/font`.

## Licenties

- `components-css` en `font`: EUPL-1.2.
- `design-tokens`: **niet** open source; gebruik is voorbehouden aan de Rijksoverheid en
  partijen die voor de Rijksoverheid werken. In orde voor deze interne tool, niet voor hergebruik daarbuiten.
- Het huisstijllettertype RijksSansVF zit hier bewust niet in (licentieplichtig). De tokens noemen
  hem als eerste keuze: staat hij op de werklaptop, dan gebruikt de browser hem vanzelf. Anders Fira Sans.
