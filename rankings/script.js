// Main application JavaScript
console.log('IPSC script loaded!');

class IPSCRanking {
    constructor() {
        this.divisions = {
            'combined': 'Kombinerad ranking',
            'classic': 'Classic',
            'open': 'Open',
            'production': 'Production',
            'production_optics': 'Production Optics',
            'standard': 'Standard',
            'revolver': 'Revolver',
            'pistol_caliber_carbine': 'Pistol Caliber Carbine'
        };
        
        this.init();
    }

    async init() {
        await this.loadStats();
        this.setupEventListeners();
        this.updateLastUpdated();
    }

    async loadStats() {
        try {
            // Load player counts for each division
            for (const [divisionKey, divisionName] of Object.entries(this.divisions)) {
                try {
                    const response = await fetch(`data/ipsc_ranking_${divisionKey}.json`);
                    if (response.ok) {
                        const data = await response.json();
                        const count = data.length;
                        const countElement = document.getElementById(`count-${divisionKey.replace('_', '-')}`);
                        if (countElement) {
                            countElement.textContent = `${count} skyttar`;
                        }
                        
                        // Update total players count (use combined as reference)
                        if (divisionKey === 'combined') {
                            const totalElement = document.getElementById('total-players');
                            if (totalElement) {
                                totalElement.textContent = count.toLocaleString();
                            }
                        }
                    }
                } catch (error) {
                    console.warn(`Could not load stats for ${divisionKey}:`, error);
                }
            }

            // Load actual match count from metadata with cache busting
            try {
                const cacheBuster = Date.now();
                const metadataResponse = await fetch(`data/metadata.json?v=${cacheBuster}`);
                console.log('Metadata fetch response:', metadataResponse.status);
                
                if (metadataResponse.ok) {
                    const metadata = await metadataResponse.json();
                    console.log('Metadata loaded:', metadata);
                    
                    const totalMatchesElement = document.getElementById('total-matches');
                    if (totalMatchesElement && metadata.match_statistics) {
                        const matchCount = metadata.match_statistics.matches_processed_in_rankings || metadata.match_statistics.matches_with_handgun_data;
                        console.log('Setting match count to:', matchCount);
                        totalMatchesElement.textContent = matchCount.toLocaleString();
                    } else {
                        console.error('Missing element or statistics');
                        if (totalMatchesElement) {
                            totalMatchesElement.textContent = 'ELEMENT_MISSING';
                        }
                    }
                } else {
                    console.error('Metadata fetch failed:', metadataResponse.status);
                    const totalMatchesElement = document.getElementById('total-matches');
                    if (totalMatchesElement) {
                        totalMatchesElement.textContent = 'METADATA_FAILED';
                    }
                }
            } catch (metadataError) {
                console.error('Could not load metadata:', metadataError);
                const totalMatchesElement = document.getElementById('total-matches');
                if (totalMatchesElement) {
                    totalMatchesElement.textContent = 'JS_ERROR';
                }
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    setupEventListeners() {
        // Handle division card clicks
        document.querySelectorAll('.division-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const division = e.currentTarget.dataset.division;
                this.navigateToRanking(division);
            });
        });

        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    navigateToRanking(division) {
        window.location.href = `ranking.html?division=${division}`;
    }

    updateLastUpdated() {
        const lastUpdatedElement = document.getElementById('last-updated');
        if (lastUpdatedElement) {
            const now = new Date();
            lastUpdatedElement.textContent = now.toLocaleDateString('sv-SE');
        }
    }
}

// Ranking page functionality
class RankingPage {
    constructor() {
        this.currentDivision = null;
        this.currentCategory = null;
        this.allPlayers = [];
        this.filteredPlayers = [];
        this.init();
    }

    async init() {
        this.currentDivision = this.getDivisionFromURL();
        this.currentCategory = this.getCategoryFromURL();
        if (!this.currentDivision) {
            window.location.href = 'index.html';
            return;
        }

        this.updatePageTitle();
        await this.loadRankingData();
        this.setupEventListeners();
    }

    getDivisionFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('division');
    }

    getCategoryFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('category');
    }

    updatePageTitle() {
        const divisions = {
            'combined': 'Kombinerad ranking',
            'classic': 'Classic',
            'open': 'Open',
            'production': 'Production',
            'production_optics': 'Production Optics',
            'standard': 'Standard',
            'revolver': 'Revolver',
            'pistol_caliber_carbine': 'Pistol Caliber Carbine'
        };

        const categories = {
            'junior': 'Junior',
            'super_junior': 'Super Junior',
            'senior': 'Senior',
            'super_senior': 'Super Senior',
            'grand_senior': 'Grand Senior',
            'lady': 'Lady',
            'lady_junior': 'Lady Junior',
            'lady_senior': 'Lady Senior',
            'lady_super_senior': 'Lady Super Senior',
            'lady_grand_senior': 'Lady Grand Senior',
            'international': 'International'
        };

        const divisionName = divisions[this.currentDivision] || this.currentDivision;
        const categoryName = this.currentCategory ? categories[this.currentCategory] || this.currentCategory : null;
        
        let title = divisionName;
        if (categoryName) {
            title = `${divisionName} ${categoryName}`;
        }
        
        document.title = `${title} - Svenska IPSC Ranking`;
        
        const titleElement = document.querySelector('.ranking-title');
        if (titleElement) {
            titleElement.textContent = `${title} Ranking`;
        }
    }

    async loadRankingData() {
        try {
            // Construct filename based on division and category
            let filename = `data/ipsc_ranking_${this.currentDivision}`;
            if (this.currentCategory) {
                filename += `_${this.currentCategory}`;
            }
            filename += '.json';
            
            const response = await fetch(filename);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.allPlayers = await response.json();
            
            // Filter out non-Swedish shooters for Swedish IPSC Ranking
            this.allPlayers = this.allPlayers.filter(player => player.region === 'SWE');
            
            // Re-assign sequential Swedish ranks after filtering for all divisions
            this.allPlayers.forEach((player, index) => {
                if (this.currentDivision === 'combined') {
                    player.swedish_combined_rank = index + 1;
                } else {
                    player.swedish_rank = index + 1;
                }
            });
            
            console.log('RANKING FIX: Applied Swedish ranking to', this.allPlayers.length, 'players');
            
            this.filteredPlayers = [...this.allPlayers];
            this.renderRankingTable();
            this.updateRankingInfo();
        } catch (error) {
            console.error('Error loading ranking data:', error);
            this.showError('Kunde inte ladda rankingdata. Kontrollera att datafiler finns tillgängliga.');
        }
    }

    setupEventListeners() {
        const searchBox = document.getElementById('search-box');
        if (searchBox) {
            searchBox.addEventListener('input', (e) => {
                this.filterPlayers(e.target.value);
            });
        }
    }

    filterPlayers(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        if (!term) {
            this.filteredPlayers = [...this.allPlayers];
        } else {
            this.filteredPlayers = this.allPlayers.filter(player => 
                player.first_name.toLowerCase().includes(term) ||
                player.last_name.toLowerCase().includes(term) ||
                (player.alias && player.alias.toLowerCase().includes(term)) ||
                player.region.toLowerCase().includes(term)
            );
        }
        this.renderRankingTable();
        this.updateRankingInfo();
    }

    renderRankingTable() {
        const tbody = document.querySelector('#ranking-table tbody');
        const thead = document.querySelector('#ranking-table thead tr');
        if (!tbody) return;

        // Update table header for combined division
        if (thead && this.currentDivision === 'combined') {
            thead.innerHTML = `
                <th>Rank</th>
                <th>Skytt</th>
                <th>Division</th>
                <th>Rating</th>
                <th>% av bästa</th>
                <th>Matcher</th>
                <th>μ ± σ</th>
            `;
        } else if (thead && this.currentDivision !== 'combined') {
            // Reset to normal header for non-combined divisions
            thead.innerHTML = `
                <th>Rank</th>
                <th>Skytt</th>
                <th>Rating</th>
                <th>% av bästa</th>
                <th>Matcher</th>
                <th>μ ± σ</th>
            `;
        }

        tbody.innerHTML = '';

        this.filteredPlayers.forEach((player, index) => {
            const row = document.createElement('tr');
            
            // For category views, use sequential ranking (1, 2, 3...)
            // For division views, use appropriate rank field
            let playerRank;
            if (this.currentCategory) {
                // Category view: use sequential ranking starting from 1
                playerRank = index + 1;
            } else if (this.currentDivision === 'combined') {
                // Combined division: use swedish_combined_rank (assigned after filtering)
                playerRank = player.swedish_combined_rank || (index + 1);
            } else {
                // Regular division view: use swedish_rank (assigned after filtering)
                playerRank = player.swedish_rank || (index + 1);
            }
            
            // Determine rank class for top 3
            let rankClass = '';
            if (playerRank === 1) rankClass = 'rank-1';
            else if (playerRank === 2) rankClass = 'rank-2';
            else if (playerRank === 3) rankClass = 'rank-3';

            // Build row HTML conditionally based on division
            if (this.currentDivision === 'combined') {
                row.innerHTML = `
                    <td><span class="rank-number ${rankClass}">${playerRank}</span></td>
                    <td>
                        <div class="player-name">${player.first_name} ${player.last_name}</div>
                        ${player.alias ? `<div class="player-alias">(${player.alias})</div>` : ''}
                        <div class="player-region">${player.region}</div>
                    </td>
                    <td><span class="division-name">${player.division}</span></td>
                    <td><span class="rating-value">${player.conservative_rating.toFixed(1)}</span></td>
                    <td>
                        <div class="percentage-bar">
                            <div class="percentage-bg">
                                <div class="percentage-fill" style="width: ${player.percentage_of_best}%"></div>
                            </div>
                            <span>${player.percentage_of_best.toFixed(1)}%</span>
                        </div>
                    </td>
                    <td><span class="matches-count">${player.matches_played}</span></td>
                    <td><span class="rating-value">${player.mu.toFixed(1)} ± ${player.sigma.toFixed(1)}</span></td>
                `;
            } else {
                row.innerHTML = `
                    <td><span class="rank-number ${rankClass}">${playerRank}</span></td>
                    <td>
                        <div class="player-name">${player.first_name} ${player.last_name}</div>
                        ${player.alias ? `<div class="player-alias">(${player.alias})</div>` : ''}
                        <div class="player-region">${player.region}</div>
                    </td>
                    <td><span class="rating-value">${player.conservative_rating.toFixed(1)}</span></td>
                    <td>
                        <div class="percentage-bar">
                            <div class="percentage-bg">
                                <div class="percentage-fill" style="width: ${player.percentage_of_best}%"></div>
                            </div>
                            <span>${player.percentage_of_best.toFixed(1)}%</span>
                        </div>
                    </td>
                    <td><span class="matches-count">${player.matches_played}</span></td>
                    <td><span class="rating-value">${player.mu.toFixed(1)} ± ${player.sigma.toFixed(1)}</span></td>
                `;
            }
            
            tbody.appendChild(row);
        });
    }

    updateRankingInfo() {
        const infoElement = document.querySelector('.ranking-info');
        if (infoElement) {
            const total = this.allPlayers.length;
            const filtered = this.filteredPlayers.length;
            
            if (filtered === total) {
                infoElement.textContent = `Visar ${total} skyttar`;
            } else {
                infoElement.textContent = `Visar ${filtered} av ${total} skyttar`;
            }
        }
    }

    showError(message) {
        const container = document.querySelector('.ranking-content .container');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: #e53e3e;">
                    <h3>Fel vid laddning</h3>
                    <p>${message}</p>
                    <a href="index.html" class="back-button" style="margin-top: 1rem; display: inline-block;">
                        ← Tillbaka till startsidan
                    </a>
                </div>
            `;
        }
    }
}

// Initialize appropriate functionality based on current page
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, pathname:', window.location.pathname);
    if (window.location.pathname.includes('ranking.html')) {
        console.log('Creating RankingPage');
        new RankingPage();
    } else {
        console.log('Creating IPSCRanking');
        new IPSCRanking();
    }
});

// Utility functions
function formatNumber(num) {
    return num.toLocaleString('sv-SE');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('sv-SE');
}

// Export for potential use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { IPSCRanking, RankingPage };
}