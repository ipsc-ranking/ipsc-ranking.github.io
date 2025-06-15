# Rankingsystem för svenska IPSC-skyttar

## Bakgrund

Det finns idag inget rankingsystem för IPSC-skyttar i Sverige vilket gör det svårt för en enskild skytt att se sin egen utveckling, men även svårt att hålla transparenta och rättvisa kvalificeringar till mästerskap.

Nedan är ett förslag på hur ett rankingsystem kan se ut och hur det kan implementeras.

## Val av grundläggande rankingsystem

Det finns ett gäng olika grundläggande rankingsystem som används för ranking i olika sporter och spel. De vanligaste är:

- Elo
- Glicko
- TrueSkill
- Glicko-2
- OpenSkill

Av dessa är TrueSkill och OpenSkill de som är bäst anpassade för tävlingar med flera deltagare i varje match.

Elo är det mest kända rankingsystemet och används bland annat för schack och är ett bra system för tävlingar med två deltagare i varje match. Det är dock inte lämpligt för tävlingar med flera deltagare i varje match. Det är också med sitt poängbaserade system sämre på att vara förutsägbart än de andra systemen, som reagerar snabbare på förändringar i spelarnas prestationer.

Glicko och Glicko-2 är båda baserade på Elo och är bättre på att vara förutsägbara än Elo, men är fortfarande inte lämpliga för tävlingar med flera deltagare i varje match.

TrueSkill är inte helt fritt att använda, men OpenSkill är relativt likt TrueSkill och är fritt att använda.

Mot bakgrund av detta föreslås att man använder OpenSkill som grund för rankingsystemet.

## Justering för osäkerhet/antalet matcher

Openskill fungerar genom att ge varje spelare en förväntad medelpoäng och en osäkerhet.

Inom statistiken kallas medelpoängen/väntevärdet ofta för my(μ) och osäkerheten/standardavvikelsen för sigma(σ).

En naiv implementation av ett rankingsystem skulle kunna använda sig av enbart medelpoängen, men då skulle systemet kunna ge en fördel till vissa spelare med endast ett fåtal matcher, som råkat ha bra resultat på dessa matcher. För att undvika detta behöver man ta hänsyn till osäkerheten.

Ett förslag på hur man kan göra detta är att använda sig av percentiler, exempelvis den 20e percentilen.

Detta innebär att man använder den poäng för rankingen som systemet tycker man i 20% av fallen har sämre resultat än, men 80 % av fallen har bättre resultat än.

Detta innebär att man tar hänsyn till osäkerheten, och att man inte kan få en hög ranking genom att ha ett fåtal bra resultat.

## Justering för inaktivitet
En inaktiv skytt bör inte ha samma ranking som en aktiv skytt.

Ett förslag på hur man kan justera för detta är att addera en konstant till osäkerheten för varje dag som går sedan den senaste matchen.

Storleken på konstanten är något bör optimeras baserat på data för att få ett så bra resultat som möjligt.

## Justering för nivå av match
En skytt är mer sannolik att göra sitt yttersta i en match på hög nivå än i en match på låg nivå.

En match på hög nivå bör därför vara mer värd än en match på låg nivå.

I OpenSkill finns en parameter som heter beta, som är en skala för osäkerheten. Från början är beta satt till 25/6. Om beta ökas kommer matchen att bli mer värd, och om beta minskas kommer matchen att bli mindre värd.

Förslagsvis sätter vi beta till 25/12 för L2 matcher, 25/6 för L3 matcher, 25/3 för L4 matcher och 25/1.5 för L5 matcher.

## Urval av matcher

För den enskilde skytten är det kul att kunna se sin egen utveckling över tid med så hög upplösning som möjligt. För att kunna göra detta behöver man ta hänsyn till så många matcher som möjligt.

Det är endast L3+ matcher som rapporteras till IROA, vilket gör att det kan vara svårt att veta vilka matcher på lägre nivå som ägt rum utanför sverige.

Förslaget är därför att vi använder L2+ matcher som ägt rum i Sverige, och L3+ matcher som ägt rum i hela världen.

## Tillgång till matchresultat
En förutsättning för att kunna göra detta är att ha tillgång till matchresultat från de utvalda matcherna.

Det bästa vore om man kunde få ta del av alla matchresultat som rapporterats till IROA, alternativt kan man samköra data från NROI, IROA/IPSC.org, PractiScore, ESS(i alla regioner man kommer åt), SSI och ipscresults.org. Samt eventuellt andra källor.

## Presentation av resultat

I rankingen bör skyttens ordningsnummer visas, men även % av poängen jämfört med den bästa skytten i rankingen, detta så att informationen presenteras på ett sätt skytten är van vid.

Rankingen bör uppdateras dagligen, så att skytten kan se hur de ligger till i rankingen efter varje match.

Rankingen bör presenteras per division, så att skytten kan se hur de ligger till i sin division.

Rankingen bör presenteras per kategori, så att skytten kan se hur de ligger till i sin kategori.

Vi bör även presentera hur rankingen förändras över tid, så att skytten kan se hur de förändras i rankingen över tid.
