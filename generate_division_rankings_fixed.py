#!/usr/bin/env python3
"""
Generate division-specific rankings using proper division-based rating calculations.
This script fixes the fundamental issue where overall ratings were being used for division rankings.
"""

import sys
import os
import json
from collections import defaultdict
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ranking.processor import IPSCRankingSystem
from division_normalizer import normalize_division_name, normalize_category_name, get_available_categories

def generate_division_specific_rankings():
    """Generate rankings for each division using division-specific rating calculations"""
    
    print("=== IPSC Division Rankings Generator (Division-Specific) ===")
    print("Loading handgun matches...")
    
    # Create a base ranking system to load matches
    base_ranking_system = IPSCRankingSystem()
    matches = base_ranking_system.load_matches()
    print(f"Found {len(matches)} handgun matches after filtering")
    
    # Separate matches by division
    division_matches = defaultdict(list)
    division_stats = defaultdict(int)
    
    for match in matches:
        if ('combined_results' in match and len(match['combined_results']) > 0) or ('shooters' in match and len(match['shooters']) > 0):
            results = match.get('combined_results', match.get('shooters', []))
            
            # Group match results by division
            division_results = defaultdict(list)
            for result in results:
                division = normalize_division_name(result.get('division', 'Unknown'))
                division_results[division].append(result)
                division_stats[division] += 1
            
            # Create separate match objects for each division
            for division, div_results in division_results.items():
                division_match = match.copy()
                division_match['combined_results'] = div_results
                division_matches[division].append(division_match)
    
    print(f"Division statistics:")
    for division, count in sorted(division_stats.items()):
        print(f"  {division}: {count} results")
    
    # Create separate ranking systems for each division
    division_rankings = {}
    
    print(f"\n=== Processing Each Division Separately ===")
    for division in division_matches:
        print(f"\nProcessing {division} division...")
        
        # Create a new ranking system for this division
        division_system = IPSCRankingSystem()
        
        # Process only matches from this division
        processed_matches = 0
        for match in division_matches[division]:
            division_system.process_match(match)
            processed_matches += 1
        
        print(f"  Processed {processed_matches} matches in {division}")
        
        # Generate ranking for this division only
        division_ranking = division_system.generate_ranking()
        print(f"  Generated ranking for {len(division_ranking)} players in {division}")
        
        # Add division-specific metadata to each player
        for i, player in enumerate(division_ranking):
            player['division'] = division
            player['division_rank'] = i + 1
            player['division_matches'] = player['matches_played']  # All matches are division matches now
            
            # Calculate percentage of best in this division
            if i == 0:
                best_rating = player['conservative_rating']
            player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
        
        division_rankings[division] = division_ranking
    
    # Save division-specific files
    os.makedirs('results', exist_ok=True)
    
    division_files = {
        'Open': 'ipsc_ranking_open.json',
        'Standard': 'ipsc_ranking_standard.json', 
        'Production': 'ipsc_ranking_production.json',
        'Production Optics': 'ipsc_ranking_production_optics.json',
        'Classic': 'ipsc_ranking_classic.json',
        'Revolver': 'ipsc_ranking_revolver.json',
        'Pistol Caliber Carbine': 'ipsc_ranking_pistol_caliber_carbine.json'
    }
    
    print(f"\n=== Saving Division Rankings ===")
    for division, filename in division_files.items():
        if division in division_rankings:
            # Filter for Swedish shooters only for website display
            all_players = division_rankings[division]
            swedish_players = [p for p in all_players if p.get('region') == 'SWE']
            
            # Recalculate Swedish-only division ranks and percentages
            if swedish_players:
                best_rating = swedish_players[0]['conservative_rating']
                for i, player in enumerate(swedish_players):
                    player['division_rank'] = i + 1
                    player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
            
            # Save to results/ directory only
            filepath = f'results/{filename}'
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(swedish_players, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved {filepath} ({len(swedish_players)} Swedish players, {len(all_players)} total calculated)")
        else:
            print(f"⚠ No players found for division: {division}")
    
    # Create a combined ranking (all divisions)
    combined_ranking = []
    for division, players in division_rankings.items():
        for player in players:
            combined_player = player.copy()
            combined_ranking.append(combined_player)
    
    # Sort combined ranking by conservative rating
    combined_ranking.sort(key=lambda x: x['conservative_rating'], reverse=True)
    
    # Add combined ranks
    best_rating = combined_ranking[0]['conservative_rating'] if combined_ranking else 0
    for i, player in enumerate(combined_ranking):
        player['combined_rank'] = i + 1
        player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
    
    # Save combined ranking
    with open('results/ipsc_ranking_combined.json', 'w', encoding='utf-8') as f:
        json.dump(combined_ranking, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved results/ipsc_ranking_combined.json ({len(combined_ranking)} total entries)")
    
    # Print verification
    print(f"\n=== Erik Stjernlöf Verification ===")
    for division, players in division_rankings.items():
        erik = next((p for p in players if 'erik_stjernlöf' in p.get('player_id', '').lower()), None)
        if erik:
            swedish_players = [p for p in players if p.get('region') == 'SWE']
            erik_swedish = next((p for p in swedish_players if 'erik_stjernlöf' in p.get('player_id', '').lower()), None)
            if erik_swedish:
                print(f"{division}: Swedish Rank #{erik_swedish['division_rank']}, {erik['division_matches']} matches, Rating: {erik['conservative_rating']:.1f}")

if __name__ == "__main__":
    generate_division_specific_rankings()