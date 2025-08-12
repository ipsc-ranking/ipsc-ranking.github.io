#!/usr/bin/env python3
"""
Comprehensive fix for ipscresults.org data issues:
1. Fix swapped first/last names in some files
2. Add missing players from individual divisions to combined_results
"""

import os
import json
from pathlib import Path

def normalize_name_format(first_name, last_name):
    """Fix swapped name formats like 'Gyllenberg,' -> 'Rasmus' vs 'Rasmus' -> 'Gyllenberg'"""
    # If first_name ends with comma, it's likely swapped
    if first_name and first_name.endswith(','):
        # Swap and clean
        actual_last = first_name.rstrip(',')
        actual_first = last_name
        return actual_first, actual_last
    
    return first_name, last_name

def fix_ipscresults_data():
    """Fix data issues in ipscresults files"""
    
    files_fixed = 0
    players_added = 0
    names_fixed = 0
    
    for file_path in Path('match_data').glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'divisions' not in data:
                continue
            
            file_modified = False
            
            # Step 1: Fix swapped names in all sections
            for div_name, div_data in data['divisions'].items():
                if 'shooters' in div_data:
                    for shooter in div_data['shooters']:
                        orig_first = shooter.get('first_name', '')
                        orig_last = shooter.get('last_name', '')
                        
                        fixed_first, fixed_last = normalize_name_format(orig_first, orig_last)
                        
                        if fixed_first != orig_first or fixed_last != orig_last:
                            shooter['first_name'] = fixed_first
                            shooter['last_name'] = fixed_last
                            file_modified = True
                            names_fixed += 1
            
            # Step 2: Fix combined_results if it exists
            if 'combined_results' in data:
                for result in data['combined_results']:
                    orig_first = result.get('first_name', '')
                    orig_last = result.get('last_name', '')
                    
                    fixed_first, fixed_last = normalize_name_format(orig_first, orig_last)
                    
                    if fixed_first != orig_first or fixed_last != orig_last:
                        result['first_name'] = fixed_first
                        result['last_name'] = fixed_last
                        file_modified = True
                        names_fixed += 1
            
            # Step 3: Add missing players from divisions to combined_results
            if 'combined_results' in data:
                # Get existing players in combined_results
                existing_players = set()
                for player in data['combined_results']:
                    key = f"{player.get('first_name', '')}|{player.get('last_name', '')}|{player.get('region', '')}|{player.get('division', '')}"
                    existing_players.add(key)
                
                # Check all divisions for missing players
                for div_name, div_data in data['divisions'].items():
                    if 'shooters' in div_data:
                        for shooter in div_data['shooters']:
                            key = f"{shooter.get('first_name', '')}|{shooter.get('last_name', '')}|{shooter.get('region', '')}|{shooter.get('division', '')}"
                            
                            if key not in existing_players:
                                # Add missing player to combined_results
                                data['combined_results'].append(shooter.copy())
                                existing_players.add(key)
                                file_modified = True
                                players_added += 1
                                
                                print(f"Added missing player: {shooter.get('first_name')} {shooter.get('last_name')} ({shooter.get('division')}) to {file_path}")
            
            # Save if modified
            if file_modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                files_fixed += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"\n=== Summary ===")
    print(f"Files fixed: {files_fixed}")
    print(f"Names normalized: {names_fixed}")
    print(f"Players added to combined_results: {players_added}")
    
    return files_fixed > 0

if __name__ == "__main__":
    print("=== Comprehensive ipscresults.org data fix ===")
    fix_ipscresults_data()