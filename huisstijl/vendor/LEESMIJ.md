# vendor — Rijkshuisstijl Community, onveranderd overgenomen

Officiële uitvoerbestanden van
[nl-design-system/rijkshuisstijl-community](https://github.com/nl-design-system/rijkshuisstijl-community),
overgenomen uit `NWW-team/social-media-postmaker` (die ze onveranderd uit npm haalde).
Niet met de hand bewerken.

| Bestand | Uit welk pakket | Versie |
| --- | --- | --- |
| `rhc-components.css` | `@rijkshuisstijl-community/components-css` → `dist/index.css` | 18.0.2 |
| `rhc-tokens-hemelblauw.css` | `@rijkshuisstijl-community/design-tokens` → `dist/hemelblauw/index.css` | 18.0.1 |
| `fonts/RijksSansWeb-Regular.woff2` | Rijksoverheid, RijksSans Web (variabel) | 2023-11 |
| `fonts/fira-sans-latin-{400,600,700}-normal.woff2` | `@rijkshuisstijl-community/font` → `dist/files/` | 1.1.6 |

Opnieuw ophalen: `npm pack @rijkshuisstijl-community/components-css @rijkshuisstijl-community/design-tokens @rijkshuisstijl-community/font`.

## Licenties

- `components-css` en `font`: EUPL-1.2.
- `design-tokens`: **niet** open source; gebruik is voorbehouden aan de Rijksoverheid en
  partijen die voor de Rijksoverheid werken. In orde voor deze interne tool, niet voor hergebruik daarbuiten.
- Het huisstijllettertype RijksSansVF (`fonts/RijksSansWeb-Regular.woff2`, variabel, door de
  opdrachtgever aangeleverd) is licentieplichtig. Gebruik is beperkt tot medewerkers van de
  Rijksoverheid; deze app wordt alleen door hen gebruikt. Het lettertype wordt in de rapporten
  ingesloten, dus verspreid rapporten niet buiten de Rijksoverheid. Fira Sans is de terugval.
