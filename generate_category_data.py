#!/usr/bin/env python3
"""
Generate combined category ranking files from individual division category files.
This script creates combined rankings for each category (junior, senior, etc.) 
across all divisions and copies them to the data/ directory for web access.
"""

import json
import os
from pathlib import Path

def load_json_file(filepath):
    """Load JSON data from file, return empty list if file doesn't exist."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def combine_category_rankings(category):
    """Combine rankings for a specific category across all divisions (Swedish players only)."""
    divisions = ['classic', 'open', 'production', 'production_optics', 'standard', 'revolver', 'pistol_caliber_carbine']
    combined_players = []
    
    for division in divisions:
        filename = f"results/ipsc_ranking_{division}_{category}.json"
        players = load_json_file(filename)
        
        # Add division info to each player and filter for Swedish players only
        for player in players:
            if player.get('region') == 'SWE':
                player['division'] = division
                combined_players.append(player)
    
    # Sort by conservative_rating (descending)
    combined_players.sort(key=lambda x: x.get('conservative_rating', 0), reverse=True)
    
    # Add combined ranking and recalculate percentage_of_best
    if combined_players:
        best_rating = combined_players[0]['conservative_rating']
        for i, player in enumerate(combined_players, 1):
            player['combined_rank'] = i
            player['percentage_of_best'] = (player['conservative_rating'] / best_rating * 100) if best_rating > 0 else 0
    
    return combined_players

def main():
    """Generate category data files."""
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Categories to process
    categories = [
        'junior', 'senior', 'super_senior', 'grand_senior', 'super_junior',
        'lady', 'lady_senior'
    ]
    
    for category in categories:
        print(f"Processing category: {category}")
        combined_data = combine_category_rankings(category)
        
        if combined_data:
            output_file = f"data/ipsc_ranking_combined_{category}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=2)
            print(f"  → Created {output_file} with {len(combined_data)} players")
        else:
            print(f"  → No data found for {category}")
    
    print("Category data generation completed!")

if __name__ == "__main__":
    main()