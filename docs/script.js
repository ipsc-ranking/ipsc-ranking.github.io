// Main application JavaScript
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

            // Estimate total matches (this would need to be calculated from match data)
            const totalMatchesElement = document.getElementById('total-matches');
            if (totalMatchesElement) {
                totalMatchesElement.textContent = '1000+';
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
        this.allPlayers = [];
        this.filteredPlayers = [];
        this.init();
    }

    async init() {
        this.currentDivision = this.getDivisionFromURL();
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

        const divisionName = divisions[this.currentDivision] || this.currentDivision;
        document.title = `${divisionName} - Svenska IPSC Ranking`;
        
        const titleElement = document.querySelector('.ranking-title');
        if (titleElement) {
            titleElement.textContent = `${divisionName} Ranking`;
        }
    }

    async loadRankingData() {
        try {
            const response = await fetch(`data/ipsc_ranking_${this.currentDivision}.json`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.allPlayers = await response.json();
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
        if (!tbody) return;

        tbody.innerHTML = '';

        this.filteredPlayers.forEach((player, index) => {
            const row = document.createElement('tr');
            
            // Determine rank class for top 3
            let rankClass = '';
            if (player.rank === 1) rankClass = 'rank-1';
            else if (player.rank === 2) rankClass = 'rank-2';
            else if (player.rank === 3) rankClass = 'rank-3';

            row.innerHTML = `
                <td><span class="rank-number ${rankClass}">${player.rank}</span></td>
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
    if (window.location.pathname.includes('ranking.html')) {
        new RankingPage();
    } else {
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