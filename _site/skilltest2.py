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



class IPSCRankingSystem:
    def __init__(self, daily_sigma_increase=0.05):
        # Initialize OpenSkill model with custom parameters for IPSC
        self.model = OPENSKILL_MODEL(
            mu=25.0,  # Default skill level
            sigma=25/3,  # Default uncertainty
            beta=25/6,  # Default for L3 matches, will be adjusted per match level
            tau=25/300,  # Skill decay rate per day
            #draw_probability=0.00001  # Very low draw probability for IPSC
        )
        
        # Store all players with their current ratings
        self.players = {}
        
        # Track match history for inactivity adjustment
        self.player_last_match = {}
        
        # Beta values for different match levels
        self.beta_values = {
            'Level II': 25/12,
            'Level III': 25/6,
            'Level IV': 25/3,
            'Level V': 25/1.5
        }
        
        # Daily sigma increase for inactive players
        self.daily_sigma_increase = daily_sigma_increase
        
        # Track the current date for processing
        self.current_processing_date = None
    
    def load_matches(self):
        """Load all match files from the match_data directory"""
        matches = []
        
        for filename in os.listdir(MATCH_FILES_LOCATION):
            if filename.endswith('.json'):
                filepath = os.path.join(MATCH_FILES_LOCATION, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        match_data = json.load(f)
                        if 'production_optics_results' in match_data and len(match_data['production_optics_results']) > 0:
                            matches.append(match_data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort matches by date
        matches.sort(key=lambda x: datetime.fromisoformat(x['match_date'].replace('Z', '+00:00')))
        return matches
    
    def get_player_id(self, first_name, last_name, region, alias=None):
        """Create a unique player identifier"""
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
                'matches_played': 0,
                'last_decay_date': None  # Track when we last applied decay
            }
        
        return player_id
    
    def apply_time_decay_to_player(self, player_id, current_date):
        """Apply time decay to a specific player"""
        if player_id not in self.player_last_match:
            return
            
        player_data = self.players[player_id]
        last_match_date = self.player_last_match[player_id]
        last_decay_date = player_data.get('last_decay_date', last_match_date)
        
        # Calculate days since last decay application
        days_since_decay = (current_date - last_decay_date).days
        
        if days_since_decay <= 0:
            return
            
        current_rating = player_data['rating']
        
        # Apply decay: increase sigma based on days of inactivity
        additional_sigma = self.daily_sigma_increase * days_since_decay
        new_sigma = min(
            current_rating.sigma + additional_sigma,
            self.model.sigma  # Cap at model's maximum sigma
        )
        
        # Create new rating with increased uncertainty
        try:
            player_data['rating'] = self.model.rating(
                mu=current_rating.mu,
                sigma=new_sigma,
                name=current_rating.name
            )
            player_data['last_decay_date'] = current_date
            
            # Debug output for significant decay
            if additional_sigma > 0.5:
                print(f"Applied {additional_sigma:.2f} sigma decay to {player_data['first_name']} {player_data['last_name']} ({days_since_decay} days)")
                
        except Exception as e:
            print(f"Could not apply decay to {player_id}: {e}")
    
    def apply_time_decay_all_players(self, current_date):
        """Apply time decay to all players based on their inactivity"""
        for player_id in self.players.keys():
            self.apply_time_decay_to_player(player_id, current_date)
    
    def process_match(self, match_data):
        """Process a single match and update player ratings"""
        if 'production_optics_results' not in match_data:
            return
        
        match_date = datetime.fromisoformat(match_data['match_date'].replace('Z', '+00:00'))
        match_level = match_data.get('match_level', 'Level II')
        
        # Apply time decay before processing the match
        self.apply_time_decay_all_players(match_date)
        
        # Adjust the model's beta for match level
        original_beta = self.model.beta
        self.model.beta = self.beta_values.get(match_level, self.model.beta)
        
        # Prepare teams using existing ratings directly
        teams = []
        player_ids = []
        
        for result in match_data['production_optics_results']:
            player_id = self.get_or_create_player(
                result['first_name'],
                result['last_name'],
                result.get('region', 'UNK'),
                result.get('alias'),
            )
            player_ids.append(player_id)
            teams.append([self.players[player_id]['rating']])
            
            # Update last match date and reset decay date
            self.player_last_match[player_id] = match_date
            self.players[player_id]['matches_played'] += 1
            self.players[player_id]['last_decay_date'] = match_date
        
        scores = [result['match_points'] for result in match_data['production_optics_results']]
        
        try:
            updated_teams = self.model.rate(teams, scores=scores)
            
            # Update player ratings
            for i, player_id in enumerate(player_ids):
                self.players[player_id]['rating'] = updated_teams[i][0]
                
        except Exception as e:
            print(f"Error processing match {match_data.get('match_id', 'unknown')}: {e}")
        finally:
            # Restore original beta
            self.model.beta = original_beta
    
    def calculate_conservative_rating(self, rating, percentile=80.0):
        """Calculate conservative rating using specified percentile"""
        try:
            from scipy.stats import norm
            # For 20th percentile, we want the z-score where 20% is below
            z = abs(norm.ppf(percentile / 100.0))
            return rating.mu - z * rating.sigma
        except ImportError:
            # Fallback if scipy is not available
            # Use simple approximation: mu - sigma gives roughly 16th percentile
            z_approx = 0.84  # Approximate z-score for 20th percentile
            return rating.mu - z_approx * rating.sigma
    
    def apply_final_decay(self, reference_date=None):
        """Apply final time decay before generating rankings"""
        if reference_date is None:
            reference_date = datetime.now()
            
        print(f"Applying final time decay as of {reference_date.strftime('%Y-%m-%d')}")
        self.apply_time_decay_all_players(reference_date)
    
    def print_ranking(self, top_n=None):
        """Print the ranking in a readable format"""
        rankings = self.generate_ranking()
        
        if top_n:
            rankings = rankings[:top_n]
        
        print("=" * 120)
        print("IPSC PRODUCTION OPTICS RANKING - SWEDEN")
        print("=" * 120)
        print(f"{'Rank':<5} {'Name':<25} {'Rating':<8} {'Matches':<8} {'μ':<8} {'σ':<8} {'Last Match':<12}")
        print("-" * 120)
        
        for player in rankings:
            name = f"{player['first_name']} {player['last_name']}"
            last_match = player.get('last_match_date', 'Unknown')
            if isinstance(last_match, datetime):
                last_match = last_match.strftime('%Y-%m-%d')
            
            print(f"{player['rank']:<5} {name:<25} "
                  f"{player['conservative_rating']:<8.1f} "
                  f"{player['matches_played']:<8} {player['mu']:<8.1f} {player['sigma']:<8.1f} "
                  f"{last_match:<12}")
    
    def generate_ranking(self, sweden_only=True):
        """Generate the final ranking of all players"""
        rankings = []
        
        for player_id, player_data in self.players.items():
            # Skip non-Swedish players if sweden_only is True
            if sweden_only and ('region' not in player_data or player_data['region'] != 'SWE'):
                continue
                
            rating = player_data['rating']
            conservative_rating = self.calculate_conservative_rating(rating)
            
            # Get last match date
            last_match_date = self.player_last_match.get(player_id, None)
            
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
                'matches_played': player_data['matches_played'],
                'last_match_date': last_match_date
            })
        
        # Sort by conservative rating (descending)
        rankings.sort(key=lambda x: x['conservative_rating'], reverse=True)
        
        # Add ranking positions
        for i, player in enumerate(rankings):
            player['rank'] = i + 1
        
        return rankings

def main():
    # Create ranking system with daily sigma increase of 0.1
    ranking_system = IPSCRankingSystem(daily_sigma_increase=0.1)
    
    # Load and process all matches
    print("Loading matches...")
    matches = ranking_system.load_matches()
    print(f"Found {len(matches)} matches")
    
    print("Processing matches...")
    for i, match in enumerate(matches):
        if i % 50 == 0:  # Progress indicator
            print(f"Processing match {i+1}/{len(matches)}")
        
        if 'production_optics_results' in match and len(match['production_optics_results']) > 0:
            ranking_system.process_match(match)
    
    # Apply final decay adjustment (to current date)
    ranking_system.apply_final_decay()
    
    # Print the ranking
    print(f"\nGenerated ranking for {len(ranking_system.players)} players in {len(matches)} matches")
    ranking_system.print_ranking(top_n=50)  # Show top 50 players
    
    # Save full ranking to file
    rankings = ranking_system.generate_ranking()
    
    # Convert datetime objects to strings for JSON serialization
    for player in rankings:
        if isinstance(player.get('last_match_date'), datetime):
            player['last_match_date'] = player['last_match_date'].isoformat()

    with open('ipsc_production_optics_ranking.json', 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull ranking saved to 'ipsc_production_optics_ranking.json'")
    print(f"Total players ranked: {len(rankings)}")

if __name__ == "__main__":
    main()