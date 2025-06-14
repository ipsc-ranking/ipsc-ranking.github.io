import openskill
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

import openskill.models


from pprint import pprint

MATCH_FILES_LOCATION = './match_data/'


OPENSKILL_MODEL = openskill.models.BradleyTerryPart

START_MU = 25

PERCENTILE = 80

from scipy.stats import norm
z_score = abs(norm.ppf(PERCENTILE / 100.0))

START_SIGMA = START_MU/z_score



class IPSCRankingSystem:
    def __init__(self):
        # Initialize OpenSkill model with custom parameters for IPSC
        self.model = OPENSKILL_MODEL(
            mu=START_MU,  # Default skill level
            sigma=START_SIGMA,  # Default uncertainty
            beta=START_MU/12,  # Default for L2 matches, will be adjusted per match level
            tau=START_MU/300,  # Skill decay rate per day
            #draw_probability=0.00001  # Very low draw probability for IPSC
        )
        
        # Store all players with their current ratings
        self.players = {}
        
        # Track match history for inactivity adjustment
        self.player_last_match = {}
        
        # Beta values for different match levels
        self.beta_values = {
            'Level II': START_MU/12,
            'Level III': START_MU/6,
            'Level IV': START_MU/3,
            'Level V': START_MU/1.5
        }
    
    def load_matches(self):
        """Load all match files from the match_data directory"""
        matches = []
        
        for filename in os.listdir(MATCH_FILES_LOCATION):
            if filename.endswith('.json'):
                filepath = os.path.join(MATCH_FILES_LOCATION, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        match_data = json.load(f)
                        if 'production_optics_results' in match_data and len(match_data['production_optics_results']) > 0 :
                            if match_data['match_level'] in ['Level III', 'Level IV', 'Level V'] or True:
                                matches.append(match_data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort matches by date
        matches.sort(key=lambda x: datetime.fromisoformat(x['match_date'].replace('Z', '+00:00')))
        return matches
    
    def get_player_id(self, first_name, last_name, region, alias=None):
        """Create a unique player identifier"""
        #if alias and alias.strip():
        #    return f"{first_name}_{last_name}_{alias}".lower().replace(' ', '_')
        return f"{first_name}_{last_name}_{region}".lower().replace(' ', '_')
    
    def get_or_create_player(self, first_name, last_name, region, alias=None):
        """Get existing player or create new one"""
        player_id = self.get_player_id(first_name, last_name, region)
        
        if player_id not in self.players:
            self.players[player_id] = {
                'rating': self.model.rating(name=player_id),
                'first_name': first_name,
                'last_name': last_name,
                'alias': alias,
                'region': region,
                'matches_played': 0
            }
        
        return player_id
    
    def adjust_for_inactivity(self, current_date):
        """Adjust ratings for player inactivity"""
        for player_id, player_data in self.players.items():
            if player_id in self.player_last_match:
                days_since_last_match = (current_date - self.player_last_match[player_id]).days
                if days_since_last_match > 0:
                    current_rating = player_data['rating']
                    
                    # Apply tau (skill decay) for each day of inactivity
                    # tau = 25/300 per day, so multiply by days inactive
                    additional_sigma = self.model.tau * days_since_last_match
                    
                    # Use the player's current sigma as base, add daily decay
                    new_sigma = min(
                        current_rating.sigma + additional_sigma, 
                        self.model.sigma  # Cap at model's maximum sigma
                    )
                    
                    # Create a new rating with updated sigma
                    try:
                        player_data['rating'] = self.model.rating(
                            mu=current_rating.mu,
                            sigma=new_sigma
                        )
                    except Exception as e:
                        print(f"Could not adjust inactivity for {player_id}: {e}")

    def process_match(self, match_data):
        """Process a single match and update player ratings"""
        if 'production_optics_results' not in match_data:
            return
        
        match_date = datetime.fromisoformat(match_data['match_date'].replace('Z', '+00:00'))

        #print(match_date)
        match_level = match_data.get('match_level', 'Level II')
        
        #self.adjust_for_inactivity(match_date)
        
        # Temporarily adjust the main model's beta
        #original_beta = self.model.beta
        self.model.beta = self.beta_values.get(match_level)
        
        # Prepare teams using existing ratings directly
        teams = []
        player_ids = []
        
        for result in match_data['production_optics_results']:
            player_id = self.get_or_create_player(
                result['first_name'],
                result['last_name'],
                result.get('region'),
                result.get('alias'),
            )
            player_ids.append(player_id)
            teams.append([self.players[player_id]['rating']])
            
            self.player_last_match[player_id] = match_date
            self.players[player_id]['matches_played'] += 1
        
        scores = [result['match_percentage'] for result in match_data['production_optics_results']]

        
        try:
            updated_teams = self.model.rate(teams, scores=scores)

            #pprint(updated_teams)
            
            # Update player ratings directly
            for i, player_id in enumerate(player_ids):
                self.players[player_id]['rating'] = updated_teams[i][0]
                
        except Exception as e:
            print(f"Error processing match {match_data.get('match_id', 'unknown')}: {e}")
        finally:
            pass
            # Restore original beta
            #self.model.beta = original_beta
    
    def calculate_conservative_rating(self, rating, percentile=80.0):
        """Calculate conservative rating using specified percentile"""
        from scipy.stats import norm
        alpha = 1
        target = 0
        z = abs(norm.ppf(percentile / 100.0))
        return rating.ordinal(z=z, alpha=alpha, target=target)

    def print_ranking(self, top_n=None):
        """Print the ranking in a readable format"""
        rankings = self.generate_ranking()
        
        if top_n:
            rankings = rankings[:top_n]
        
        print("=" * 120)
        print("IPSC PRODUCTION OPTICS RANKING - SWEDEN")
        print("=" * 120)
        print(f"{'Rank':<5} {'Name':<25} {'Alias':<15} {'Rating':<8} {'Matches':<8} {'μ':<8} {'σ':<8}")
        print("-" * 120)
        
        for player in rankings:
            name = f"{player['first_name']} {player['last_name']}"
            alias = player['alias'] or ""
            
            print(f"{player['rank']:<5} {name:<25} {alias:<15} "
                    f"{player['conservative_rating']:<8.1f}"
                    f"{player['matches_played']:<8} {player['mu']:<8.1f} {player['sigma']:<8.1f}")
        
    def generate_ranking(self, sweden_only=True):
        """Generate the final ranking of all players"""
        rankings = []
        
        for player_id, player_data in self.players.items():
            # Skip non-Swedish players if sweden_only is True
            #print(player_data)
            if sweden_only and ('region' not in player_data or player_data['region'] != 'SWE'):
                continue
            #print(player_data['region'])
                
            rating = player_data['rating']
            conservative_rating = self.calculate_conservative_rating(rating)
            
            rankings.append({
                'player_id': player_id,
                'first_name': player_data['first_name'],
                'last_name': player_data['last_name'],
                'alias': player_data['alias'],
                'region': player_data.get('region', 'Unknown'),
                'mu': rating.mu,
                'sigma': rating.sigma,
                'conservative_rating': conservative_rating,
                'ordinal': rating.ordinal(),
                'matches_played': player_data['matches_played']
            })
        
        # Sort by conservative rating (descending)
        rankings.sort(key=lambda x: x['conservative_rating'], reverse=True)
        
        # Add ranking positions and percentages
        if rankings:
            best_rating = rankings[0]['conservative_rating']
            for i, player in enumerate(rankings):
                player['rank'] = i + 1
                player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
        
        
        #print(rankings)
        return rankings
    


def main():
    # Create ranking system
    ranking_system = IPSCRankingSystem()
    
    # Load and process all matches
    print("Loading matches...")
    matches = ranking_system.load_matches()
    print(f"Found {len(matches)} matches")
    
    print("Processing matches...")
    for i, match in enumerate(matches):
        print(f"Processing match {i+1}/{len(matches)}: {match.get('match_title', 'Unknown')}")
        if 'production_optics_results' in match and len(match['production_optics_results']) > 0:
            ranking_system.process_match(match)
    
    # Adjust for inactivity (using current date)
    #print("Adjusting for inactivity...")
    #ranking_system.adjust_for_inactivity(datetime.now())
    
    # Print the ranking
    print(f"\nGenerated ranking for {len(ranking_system.players)} players in {len(matches)} matches")
    ranking_system.print_ranking(top_n=500)  # Show top 50 players
    
    # Save full ranking to file
    rankings = ranking_system.generate_ranking()

    with open('ipsc_production_optics_ranking.json', 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull ranking saved to 'ipsc_production_optics_ranking.json'")
    print(f"Total players ranked: {len(rankings)}")

if __name__ == "__main__":
    main()