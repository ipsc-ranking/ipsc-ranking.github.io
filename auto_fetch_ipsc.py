#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Automatically fetch recent IPSC handgun matches from PractiScore
"""

import time
import os
from practiscore import PractiScoreClient

def main():
    print("🎯 Auto-fetching recent IPSC handgun matches...")
    
    client = PractiScoreClient()
    
    # Start with recent ranges (last 2 years approximately)
    recent_ranges = [
        (295000, 300000),  # Very recent
        (290000, 295000),  # Recent
        (285000, 290000),  # 2023-2024
    ]
    
    total_fetched = 0
    
    for start, end in recent_ranges:
        print(f"\n=== Fetching range {start}-{end} ===")
        
        range_fetched = 0
        checked = 0
        
        for match_id in range(start, end + 1):
            checked += 1
            
            # Progress
            if checked % 100 == 0:
                print(f"  Progress: {checked}/{end-start+1}, fetched: {range_fetched}")
            
            # Skip existing
            filename = f"match_data/match_{match_id}.json"
            if os.path.exists(filename):
                continue
            
            try:
                match_data = client.fetch_match_data(str(match_id))
                
                if match_data and match_data.get('production_optics_results'):
                    client.save_match_data(match_data)
                    range_fetched += 1
                    total_fetched += 1
                    
                    title = match_data.get('match_title', 'Unknown')[:50]
                    shooters = len(match_data.get('production_optics_results', []))
                    print(f"    ✓ {match_id}: {title}... ({shooters} shooters)")
                    
            except Exception:
                # Most IDs don't exist, that's normal
                pass
            
            # Rate limiting
            time.sleep(0.2)
        
        print(f"Range {start}-{end} complete: {range_fetched} matches fetched")
    
    print(f"\n✅ Auto-fetch complete!")
    print(f"Total IPSC handgun matches fetched: {total_fetched}")
    print("Run 'python process_matches.py' to update rankings")

if __name__ == "__main__":
    main()