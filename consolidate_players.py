#!/usr/bin/env python3
"""
Consolidate duplicate players in existing ranking data.
This will merge players with different name variations into single entries.
"""

import json
import os
from collections import defaultdict
from name_normalizer import normalize_name, get_normalized_player_id

def consolidate_ranking_file(filepath):
    """Consolidate duplicate players in a single ranking file"""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    # Group players by normalized ID
    consolidated = defaultdict(list)
    
    for player in players:
        # Extract info from player data
        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        region = player.get('region', 'UNK')
        division = player.get('division', '')
        
        # Fix division field if it contains region prefix (e.g., "Swe Standard" -> "Standard")
        if division.lower().startswith(region.lower() + ' '):
            division = division[len(region)+1:]
        
        # Generate normalized ID
        normalized_id = get_normalized_player_id(first_name, last_name, region, division)
        consolidated[normalized_id].append(player)
    
    # Merge duplicate players
    merged_players = []
    duplicates_found = 0
    
    for normalized_id, player_list in consolidated.items():
        if len(player_list) > 1:
            duplicates_found += len(player_list) - 1
            print(f"  Found {len(player_list)} duplicates for {normalized_id}:")
            for p in player_list:
                print(f"    - {p.get('first_name', '')} {p.get('last_name', '')} (ID: {p.get('player_id', 'N/A')})")
            
            # Merge logic: take the player with most matches, or best rating if tied
            best_player = max(player_list, key=lambda p: (p.get('matches_played', 0), p.get('conservative_rating', 0)))
            
            # Update with normalized names and fixed division
            best_player['first_name'] = normalize_name(best_player.get('first_name', ''))
            best_player['last_name'] = normalize_name(best_player.get('last_name', ''))
            best_player['player_id'] = normalized_id
            
            # Fix division field if needed
            original_division = best_player.get('division', '')
            region = best_player.get('region', 'UNK')
            if original_division.lower().startswith(region.lower() + ' '):
                best_player['division'] = original_division[len(region)+1:]
            
            merged_players.append(best_player)
        else:
            # Single player, just normalize names and fix division
            player = player_list[0]
            player['first_name'] = normalize_name(player.get('first_name', ''))
            player['last_name'] = normalize_name(player.get('last_name', ''))
            player['player_id'] = normalized_id
            
            # Fix division field if needed
            original_division = player.get('division', '')
            region = player.get('region', 'UNK')
            if original_division.lower().startswith(region.lower() + ' '):
                player['division'] = original_division[len(region)+1:]
            
            merged_players.append(player)
    
    # Sort by conservative rating (descending)
    merged_players.sort(key=lambda x: x.get('conservative_rating', 0), reverse=True)
    
    # Update ranks and percentages
    if merged_players:
        best_rating = merged_players[0].get('conservative_rating', 1)
        for i, player in enumerate(merged_players):
            player['rank'] = i + 1
            rating = player.get('conservative_rating', 0)
            player['percentage_of_best'] = (rating / best_rating * 100) if best_rating > 0 else 0
    
    # Save consolidated file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(merged_players, f, indent=2, ensure_ascii=False)
    
    print(f"  Consolidated {len(players)} -> {len(merged_players)} players (removed {duplicates_found} duplicates)")
    return duplicates_found

def main():
    """Consolidate all ranking files"""
    print("🔄 Consolidating duplicate players in ranking files...")
    
    rankings_dir = 'rankings/data'
    if not os.path.exists(rankings_dir):
        print(f"❌ Directory {rankings_dir} not found!")
        return
    
    total_duplicates = 0
    files_processed = 0
    
    # Process all ranking JSON files
    for filename in os.listdir(rankings_dir):
        if filename.startswith('ipsc_ranking_') and filename.endswith('.json'):
            filepath = os.path.join(rankings_dir, filename)
            duplicates = consolidate_ranking_file(filepath)
            total_duplicates += duplicates
            files_processed += 1
    
    print(f"\n✅ Consolidation complete!")
    print(f"   Files processed: {files_processed}")
    print(f"   Total duplicates removed: {total_duplicates}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the changes: git diff rankings/data/")
    print(f"   2. Test the website: jekyll serve")
    print(f"   3. If satisfied: git add rankings/data/ && git commit")

if __name__ == "__main__":
    main()