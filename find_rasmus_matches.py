#!/usr/bin/env python3
"""
Find all matches for Rasmus Gyllenberg in Production Optics division.
"""

import os
import json
from pathlib import Path

def search_rasmus_matches():
    """Search for all Rasmus Gyllenberg matches in Production Optics"""
    production_optics_matches = []
    all_matches = []
    
    # Search in both directories
    search_dirs = [
        'data/matches',
        'match_data'
    ]
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        print(f"\nSearching in {search_dir}...")
        
        for file_path in Path(search_dir).glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                
                # Check combined_results if available
                if 'combined_results' in match_data:
                    for result in match_data['combined_results']:
                        if ('gyllenberg' in result.get('last_name', '').lower() and 
                            'rasmus' in result.get('first_name', '').lower()):
                            
                            division = result.get('division', '')
                            match_info = {
                                'file': str(file_path),
                                'match_title': match_data.get('match_title', 'Unknown'),
                                'match_date': match_data.get('match_date', 'Unknown'),
                                'division': division,
                                'match_points': result.get('match_points', 0),
                                'placement': result.get('placement', 0)
                            }
                            
                            all_matches.append(match_info)
                            
                            if 'production optics' in division.lower():
                                production_optics_matches.append(match_info)
                
                # Also check individual division sections (for ipscresults format)
                if 'divisions' in match_data:
                    for div_name, div_data in match_data['divisions'].items():
                        if 'production optics' in div_name.lower() and 'shooters' in div_data:
                            for shooter in div_data['shooters']:
                                if ('gyllenberg' in shooter.get('last_name', '').lower() and 
                                    'rasmus' in shooter.get('first_name', '').lower()):
                                    
                                    match_info = {
                                        'file': str(file_path),
                                        'match_title': match_data.get('match_title', 'Unknown'),
                                        'match_date': match_data.get('match_date', 'Unknown'),
                                        'division': 'Production Optics',
                                        'match_points': shooter.get('match_points', 0),
                                        'placement': shooter.get('placement', 0)
                                    }
                                    
                                    # Check if already found in combined_results
                                    if not any(m['file'] == match_info['file'] and 
                                             'production optics' in m['division'].lower() 
                                             for m in production_optics_matches):
                                        production_optics_matches.append(match_info)
                                        all_matches.append(match_info)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
    
    return production_optics_matches, all_matches

if __name__ == "__main__":
    print("=== Searching for Rasmus Gyllenberg matches ===")
    
    prod_optics, all_matches = search_rasmus_matches()
    
    print(f"\n=== PRODUCTION OPTICS MATCHES ({len(prod_optics)}) ===")
    for i, match in enumerate(sorted(prod_optics, key=lambda x: x['match_date']), 1):
        print(f"{i:2d}. {match['match_date'][:10]} - {match['match_title']}")
        print(f"    Division: {match['division']}")
        print(f"    Points: {match['match_points']}, Placement: {match['placement']}")
        print(f"    File: {match['file']}")
        print()
    
    print(f"\n=== ALL DIVISIONS SUMMARY ===")
    division_counts = {}
    for match in all_matches:
        div = match['division']
        division_counts[div] = division_counts.get(div, 0) + 1
    
    print("Division breakdown:")
    for div, count in sorted(division_counts.items()):
        print(f"  {div}: {count} matches")
    
    print(f"\nTotal matches found: {len(all_matches)}")
    print(f"Production Optics matches: {len(prod_optics)}")