#!/usr/bin/env python3
"""
Simple search for Rasmus Gyllenberg Production Optics matches.
"""

import os
import json
from pathlib import Path

def find_rasmus_production_optics():
    """Find Rasmus Production Optics matches"""
    matches = []
    
    # Search match_data directory (ipscresults files)
    if os.path.exists('match_data'):
        print("Searching match_data directory...")
        for file_path in Path('match_data').glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check combined_results
                if 'combined_results' in data:
                    for result in data['combined_results']:
                        if ('gyllenberg' in result.get('last_name', '').lower() and 
                            'rasmus' in result.get('first_name', '').lower() and
                            'production optics' in result.get('division', '').lower()):
                            
                            matches.append({
                                'file': str(file_path),
                                'date': data.get('match_date', 'Unknown')[:10],
                                'title': data.get('match_title', 'Unknown'),
                                'division': result.get('division'),
                                'points': result.get('match_points', 0),
                                'placement': result.get('placement', 0)
                            })
                
                # Check divisions section
                if 'divisions' in data and 'Production Optics' in data['divisions']:
                    div_data = data['divisions']['Production Optics']
                    if 'shooters' in div_data:
                        for shooter in div_data['shooters']:
                            if ('gyllenberg' in shooter.get('last_name', '').lower() and 
                                'rasmus' in shooter.get('first_name', '').lower()):
                                
                                matches.append({
                                    'file': str(file_path),
                                    'date': data.get('match_date', 'Unknown')[:10],
                                    'title': data.get('match_title', 'Unknown'),
                                    'division': 'Production Optics',
                                    'points': shooter.get('match_points', 0),
                                    'placement': shooter.get('placement', 0)
                                })
                                
            except Exception as e:
                continue
    
    return matches

if __name__ == "__main__":
    matches = find_rasmus_production_optics()
    
    print(f"\n=== RASMUS GYLLENBERG PRODUCTION OPTICS MATCHES ({len(matches)}) ===")
    
    for i, match in enumerate(sorted(matches, key=lambda x: x['date']), 1):
        print(f"{i:2d}. {match['date']} - {match['title']}")
        print(f"    Points: {match['points']}, Placement: {match['placement']}")
        print(f"    File: {match['file']}")
        print()