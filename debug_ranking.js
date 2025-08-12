// Debug script to test ranking logic
const fs = require('fs');

// Load the production optics data
const data = JSON.parse(fs.readFileSync('rankings/data/ipsc_ranking_production_optics.json', 'utf8'));

console.log('Original data - first few entries:');
data.slice(0, 5).forEach((player, i) => {
    console.log(`${i+1}. ${player.first_name} ${player.last_name} (${player.region}) - Global rank: ${player.rank}, Rating: ${player.conservative_rating.toFixed(1)}`);
});

// Filter Swedish shooters (same logic as website)
const swedishShooters = data.filter(player => player.region === 'SWE');

// Assign Swedish ranks (same logic as website)
swedishShooters.forEach((player, index) => {
    player.swedish_rank = index + 1;
});

console.log('\nSwedish shooters after filtering and ranking:');
swedishShooters.slice(0, 5).forEach((player) => {
    console.log(`${player.swedish_rank}. ${player.first_name} ${player.last_name} - Global rank: ${player.rank}, Swedish rank: ${player.swedish_rank}, Rating: ${player.conservative_rating.toFixed(1)}`);
});

// Find Ted specifically
const ted = swedishShooters.find(p => p.first_name === 'Ted' && p.last_name === 'Åhlenius');
if (ted) {
    console.log(`\nTed Åhlenius specifically:`);
    console.log(`- Global rank: ${ted.rank}`);
    console.log(`- Swedish rank: ${ted.swedish_rank}`);
    console.log(`- Rating: ${ted.conservative_rating.toFixed(1)}`);
    console.log(`- Should show rank ${ted.swedish_rank} on website`);
} else {
    console.log('\nTed Åhlenius not found!');
}