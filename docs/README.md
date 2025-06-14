# Svenska IPSC Ranking - Website

Detta är den statiska webbplatsen för Svenska IPSC Ranking systemet.

## Översikt

Webbplatsen visar rankings för svenska IPSC-skyttar baserat på OpenSkill-algoritm. Systemet använder en konservativ rating (20:e percentilen) för att säkerställa rättvisa rankings.

## Funktioner

- **Responsiv design** - Fungerar på alla enheter
- **Divisionsspecifika rankings** - Separata rankings för varje IPSC-division
- **Sökfunktion** - Sök efter skyttar baserat på namn eller region
- **Realtidsdata** - Uppdateras dagligen med nya matchresultat
- **Transparent metodologi** - Tydlig förklaring av rankingsystemet

## Divisioner

- Alla divisioner (kombinerad ranking)
- Classic
- Open
- Production
- Production Optics
- Standard
- Revolver
- Pistol Caliber Carbine

## Teknisk implementation

### Frontend
- **HTML5** - Semantisk markup
- **CSS3** - Modern styling med flexbox och grid
- **Vanilla JavaScript** - Ingen externa beroenden
- **Responsiv design** - Mobile-first approach

### Data
- **JSON-format** - Strukturerad data för varje division
- **Statiska filer** - Snabb laddning och enkel hosting
- **GitHub Pages** - Automatisk deployment

### Datastruktur

Varje ranking-fil innehåller följande information för varje skytt:

```json
{
  "player_id": "unique_identifier",
  "first_name": "Förnamn",
  "last_name": "Efternamn",
  "alias": "Smeknamn",
  "region": "SWE",
  "division": "Classic",
  "mu": 38.99,
  "sigma": 10.67,
  "conservative_rating": 30.01,
  "ordinal": 6.98,
  "matches_played": 18,
  "rank": 1,
  "percentage_of_best": 100.0
}
```

## Deployment

### GitHub Pages

1. Aktivera GitHub Pages i repository-inställningar
2. Välj `docs` som källmapp
3. Webbplatsen blir tillgänglig på `https://username.github.io/repository-name`

### Lokal utveckling

```bash
# Starta en lokal server
python -m http.server 8000 --directory docs

# Eller med Node.js
npx serve docs
```

Besök sedan `http://localhost:8000` för att se webbplatsen.

## Uppdatering av data

För att uppdatera rankingdata:

1. Kör rankingalgoritmen för att generera nya JSON-filer
2. Kopiera de nya filerna till `docs/data/`
3. Commit och push till GitHub
4. GitHub Pages uppdateras automatiskt

```bash
# Exempel på uppdatering
cp results/*.json docs/data/
git add docs/data/
git commit -m "Uppdatera rankingdata"
git push
```

## Anpassning

### Styling
Redigera `docs/styles.css` för att ändra utseende och känsla.

### Funktionalitet
Redigera `docs/script.js` för att lägga till nya funktioner eller ändra beteende.

### Innehåll
Redigera HTML-filerna för att ändra struktur och innehåll.

## Browser-kompatibilitet

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Prestanda

- **Snabb laddning** - Optimerade bilder och minimal JavaScript
- **Caching** - Statiska filer cachas effektivt
- **Komprimering** - Gzip-komprimering för alla textfiler

## Säkerhet

- **HTTPS** - Säker överföring via GitHub Pages
- **Ingen backend** - Inga säkerhetshål från serverside kod
- **Statisk hosting** - Minimal attackyta

## Licens

Se huvudprojektets LICENCE.md för licensinformation.

## Bidrag

Bidrag välkomnas! Se huvudprojektets CONTRIBUTING.md för riktlinjer.

## Support

För frågor eller problem, skapa en issue i huvudrepository.