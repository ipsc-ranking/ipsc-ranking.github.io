#!/usr/bin/env python3
"""
Generate division-specific rankings using handgun-filtered data.
This script ensures only legitimate handgun matches are used for rankings.
"""

import sys
import os
import json
from collections import defaultdict
from datetime import datetime, timedelta

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from process_matches import IPSCRankingSystem
from division_normalizer import normalize_division_name

def normalize_category_name(category):
    """Normalize category names"""
    if isinstance(category, list):
        return category[0] if category else 'Open'
    return category or 'Open'

def get_available_categories(matches):
    """Get available categories from matches"""
    categories = defaultdict(set)
    for match in matches:
        results = match.get('combined_results', match.get('shooters', []))
        for result in results:
            division = normalize_division_name(result.get('division', 'Unknown'))
            category = normalize_category_name(result.get('category', 'Open'))
            categories[division].add(category)
    return dict(categories)

def generate_all_division_rankings():
    """Generate rankings for each division using handgun-filtered data with optimized indexing"""
    
    print("=== IPSC Division Rankings Generator (Handgun Only) ===")
    print("Loading and processing handgun matches...")
    
    # Create ranking system with handgun filtering
    ranking_system = IPSCRankingSystem()
    
    # Load handgun-only matches (this includes our filtering)
    matches = ranking_system.load_matches()
    print(f"Found {len(matches)} handgun matches after filtering")
    
    print("Building player-division index...")
    # Build optimized index during match processing
    processed_matches = 0
    division_stats = defaultdict(int)
    player_division_index = defaultdict(lambda: defaultdict(lambda: {'matches': 0, 'categories': set()}))
    result_cache = {}  # Cache for player_id lookups
    
    for i, match in enumerate(matches):
        if i % 100 == 0:
            print(f"Processing match {i+1}/{len(matches)}")
        
        if ('combined_results' in match and len(match['combined_results']) > 0) or ('shooters' in match and len(match['shooters']) > 0):
            ranking_system.process_match(match)
            processed_matches += 1
            
            # Build index while processing - single pass through results
            results = match.get('combined_results', match.get('shooters', []))
            for result in results:
                division = normalize_division_name(result.get('division', 'Unknown'))
                category = normalize_category_name(result.get('category', ['-']))
                division_stats[division] += 1
                
                # Create cache key for player_id lookup
                cache_key = (result['first_name'], result['last_name'], result.get('region'), result.get('alias'))
                if cache_key not in result_cache:
                    result_cache[cache_key] = ranking_system.get_player_id(
                        result['first_name'],
                        result['last_name'], 
                        result.get('region'),
                        result.get('alias')
                    )
                
                player_id = result_cache[cache_key]
                player_division_index[player_id][division]['matches'] += 1
                player_division_index[player_id][division]['categories'].add(category)
    
    print(f"\nProcessed {processed_matches} handgun matches")
    print(f"Total unique players: {len(ranking_system.players)}")
    print(f"Built index for {len(player_division_index)} players across divisions")
    
    print("\nDivision participation stats:")
    for division, count in sorted(division_stats.items()):
        print(f"  {division}: {count} results")
    
    # Generate overall ranking first
    overall_ranking = ranking_system.generate_ranking(sweden_only=False)
    
    # Get available categories for analysis (using existing function)
    available_categories = get_available_categories(matches)
    print("\nAvailable categories by division:")
    for division, categories in available_categories.items():
        print(f"  {division}: {', '.join(categories)}")
    
    print("Generating division-specific rankings using index...")
    # Use index for fast lookup - O(1) instead of O(n²)
    division_rankings = defaultdict(list)
    division_category_rankings = defaultdict(lambda: defaultdict(list))
    combined_ranking = []
    
    for player in overall_ranking:
        player_id = player['player_id']
        
        # Fast lookup using index
        if player_id in player_division_index:
            player_divisions = player_division_index[player_id]
            
            # Create division-specific entries
            for division, division_data in player_divisions.items():
                division_player = player.copy()
                division_player['division'] = division
                division_player['division_matches'] = division_data['matches']
                division_player['categories'] = list(division_data['categories'])
                
                # Update player_id to include division (first_name, last_name, region, division)
                division_normalized = division.lower().replace(' ', '_').replace('-', '_')
                first_name = player.get('first_name', '').lower().replace(' ', '_')
                last_name = player.get('last_name', '').lower().replace(' ', '_')
                region = player.get('region', 'unknown').upper()
                division_player['player_id'] = f"{first_name}_{last_name}_{region}_{division_normalized}"
                
                division_rankings[division].append(division_player)
                
                # Add to category-specific rankings for each category the player competed in
                for category in division_data['categories']:
                    category_player = division_player.copy()
                    category_player['category'] = category
                    division_category_rankings[division][category].append(category_player)
                
                # Also add to combined ranking
                combined_player = division_player.copy()
                combined_ranking.append(combined_player)
    
    # Sort each division ranking and add division ranks
    final_rankings = {}
    
    for division, players in division_rankings.items():
        # Sort by conservative rating (same as overall ranking)
        players.sort(key=lambda x: x['conservative_rating'], reverse=True)
        
        # Add division-specific ranking
        if players:
            best_rating = players[0]['conservative_rating']
            for i, player in enumerate(players):
                player['division_rank'] = i + 1
                player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
        
        final_rankings[division] = players
        print(f"\n{division}: {len(players)} players")
    
    # Sort combined ranking by conservative rating and add combined ranks
    combined_ranking.sort(key=lambda x: x['conservative_rating'], reverse=True)
    if combined_ranking:
        best_rating = combined_ranking[0]['conservative_rating']
        for i, player in enumerate(combined_ranking):
            player['combined_rank'] = i + 1
            player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
    
    # Save division-specific files (Sweden-only for website display)  
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
    
    # Define cutoff date for activity filtering (4 years ago)
    cutoff_date = datetime.now() - timedelta(days=4*365)
    
    # Save main division rankings (all categories combined)
    for division, filename in division_files.items():
        if division in division_rankings:
            # Filter for Swedish shooters who are active within 4 years
            swedish_players = []
            for p in division_rankings[division]:
                if p.get('region') == 'SWE':
                    # Check if player has been active within 4 years
                    player_id = p['player_id']
                    if player_id in ranking_system.player_last_match:
                        last_match_date = ranking_system.player_last_match[player_id]
                        if last_match_date >= cutoff_date:
                            swedish_players.append(p)
                    # If no last match date recorded, include them (fallback for data issues)
                    else:
                        swedish_players.append(p)
            
            # Sort Swedish players by conservative rating and recalculate ranks
            if swedish_players:
                swedish_players.sort(key=lambda x: x['conservative_rating'], reverse=True)
                best_rating = swedish_players[0]['conservative_rating']
                for i, player in enumerate(swedish_players):
                    player['division_rank'] = i + 1
                    player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
            
            # Save to results/ directory only
            filepath = f'results/{filename}'
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(swedish_players, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved {filepath} ({len(swedish_players)} Swedish players, {len(division_rankings[division])} total calculated)")
        else:
            print(f"⚠ No players found for division: {division}")
    
    # Save category-specific rankings for each division
    print("\n=== Generating Category-Specific Rankings ===")
    for division in division_files.keys():
        if division in division_category_rankings:
            for category in division_category_rankings[division]:
                if category == 'Open':  # Skip Open category as it's the same as main division
                    continue
                    
                # Sort category players by rating
                category_players = division_category_rankings[division][category]
                category_players.sort(key=lambda x: x['conservative_rating'], reverse=True)
                
                # Add category-specific ranking
                if category_players:
                    best_rating = category_players[0]['conservative_rating']
                    for i, player in enumerate(category_players):
                        player['category_rank'] = i + 1
                        player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
                
                # Filter for Swedish shooters who are active within 4 years
                swedish_category_players = []
                for p in category_players:
                    if p.get('region') == 'SWE':
                        # Check if player has been active within 4 years
                        player_id = p['player_id']
                        if player_id in ranking_system.player_last_match:
                            last_match_date = ranking_system.player_last_match[player_id]
                            if last_match_date >= cutoff_date:
                                swedish_category_players.append(p)
                        # If no last match date recorded, include them (fallback for data issues)
                        else:
                            swedish_category_players.append(p)
                
                # Sort Swedish category players by conservative rating and recalculate ranks
                if swedish_category_players:
                    swedish_category_players.sort(key=lambda x: x['conservative_rating'], reverse=True)
                    best_rating = swedish_category_players[0]['conservative_rating']
                    for i, player in enumerate(swedish_category_players):
                        player['category_rank'] = i + 1
                        player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
                
                if swedish_category_players:  # Only save if there are Swedish players in this category
                    # Create filenames for category rankings
                    division_slug = division.lower().replace(' ', '_')
                    category_slug = category.lower().replace(' ', '_')
                    category_filename = f'ipsc_ranking_{division_slug}_{category_slug}.json'
                    
                    # Save to results/ directory only
                    filepath = f'results/{category_filename}'
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(swedish_category_players, f, indent=2, ensure_ascii=False)
                    
                    print(f"✓ Saved {division} - {category}: {filepath} ({len(swedish_category_players)} Swedish players)")
    
    # Also save full international rankings for reference
    for division, filename in division_files.items():
        if division in final_rankings:
            full_filename = filename.replace('.json', '_international.json')
            filepath = f'results/{full_filename}'
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(final_rankings[division], f, indent=2, ensure_ascii=False)
            print(f"✓ Saved {filepath} ({len(final_rankings[division])} international players)")
        else:
            print(f"⚠ No players found for division: {division}")
    
    # Save combined ranking (Swedish players only, active within 4 years)
    
    swedish_combined_ranking = []
    for p in overall_ranking:
        if p.get('region') == 'SWE':
            # Check if player has been active within 4 years
            player_id = p['player_id']
            if player_id in ranking_system.player_last_match:
                last_match_date = ranking_system.player_last_match[player_id]
                if last_match_date >= cutoff_date:
                    swedish_combined_ranking.append(p)
            # If no last match date recorded, include them (fallback for data issues)
            else:
                swedish_combined_ranking.append(p)
    
    # Sort Swedish combined ranking by conservative rating and recalculate ranks
    if swedish_combined_ranking:
        swedish_combined_ranking.sort(key=lambda x: x['conservative_rating'], reverse=True)
        best_rating = swedish_combined_ranking[0]['conservative_rating']
        for i, player in enumerate(swedish_combined_ranking):
            player['rank'] = i + 1
            player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
    
    with open('results/ipsc_ranking_combined.json', 'w', encoding='utf-8') as f:
        json.dump(swedish_combined_ranking, f, indent=2, ensure_ascii=False)
    
    total_swedish = len([p for p in overall_ranking if p.get('region') == 'SWE'])
    filtered_count = total_swedish - len(swedish_combined_ranking)
    print(f"✓ Saved results/ipsc_ranking_combined.json ({len(swedish_combined_ranking)} active Swedish players)")
    print(f"  Filtered out {filtered_count} inactive Swedish players (no matches in 4+ years)")
    print(f"  Total calculated: {len(overall_ranking)} international players")
    
    # Save all divisions ranking
    with open('results/ipsc_ranking_all_divisions.json', 'w', encoding='utf-8') as f:
        json.dump(combined_ranking, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved results/ipsc_ranking_all_divisions.json ({len(combined_ranking)} total entries)")
    
    print("\n✅ Successfully generated handgun-only division rankings!")
    
    # Update metadata with actual processed match count
    update_metadata_with_processed_count(processed_matches)
    
    return final_rankings

def update_metadata_with_processed_count(processed_match_count):
    """Update metadata.json with the actual number of matches processed by rankings"""
    import json
    import os
    from datetime import datetime
    
    print(f"\n📊 Updating metadata with processed match count: {processed_match_count}")
    
    metadata = {
        'last_updated': datetime.now().isoformat(),
        'update_date': datetime.now().strftime('%Y-%m-%d'),
        'update_time': datetime.now().strftime('%H:%M:%S'),
        'match_statistics': {
            'matches_processed_in_rankings': processed_match_count,
            'note': 'This count reflects matches actually used in ranking calculations (filtered for handgun divisions, minimum participants, etc.)'
        }
    }
    
    # Update all metadata files
    metadata_files = [
        'docs/data/metadata.json',
        'data/metadata.json'
    ]
    
    for filepath in metadata_files:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated {filepath} with processed match count: {processed_match_count}")

if __name__ == "__main__":
    generate_all_division_rankings()