#!/usr/bin/env python3
"""
Fix missing players in combined_results by checking individual divisions.
"""

import os
import json
from pathlib import Path

def fix_combined_results():
    """Fix combined_results by adding missing players from individual divisions"""
    
    matches_fixed = 0
    
    for file_path in Path('match_data').glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'divisions' not in data or 'combined_results' not in data:
                continue
            
            # Get existing combined_results player IDs
            existing_players = set()
            for player in data['combined_results']:
                player_key = f"{player.get('first_name', '')}_{player.get('last_name', '')}_{player.get('region', '')}_{player.get('division', '')}"
                existing_players.add(player_key)
            
            # Check all division sections for missing players
            missing_players = []
            for div_name, div_data in data['divisions'].items():
                if 'shooters' in div_data:
                    for shooter in div_data['shooters']:
                        player_key = f"{shooter.get('first_name', '')}_{shooter.get('last_name', '')}_{shooter.get('region', '')}_{shooter.get('division', '')}"
                        
                        if player_key not in existing_players:
                            missing_players.append(shooter)
                            existing_players.add(player_key)
            
            if missing_players:
                print(f"Found {len(missing_players)} missing players in {file_path}")
                for player in missing_players:
                    print(f"  - {player.get('first_name')} {player.get('last_name')} ({player.get('division')})")
                    data['combined_results'].append(player)
                
                # Save the fixed file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                matches_fixed += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"\nFixed {matches_fixed} match files")
    return matches_fixed

if __name__ == "__main__":
    print("=== Fixing missing combined_results entries ===")
    fix_combined_results()