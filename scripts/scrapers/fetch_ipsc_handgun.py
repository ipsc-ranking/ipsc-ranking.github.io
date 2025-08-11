#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Fetch all IPSC handgun matches from PractiScore
"""

import time
import os
from practiscore import PractiScoreClient

def fetch_range(client, start_id, end_id, batch_size=50):
    """Fetch matches in a range"""
    print(f"Fetching IPSC handgun matches {start_id} to {end_id}")
    
    total_checked = 0
    total_fetched = 0
    handgun_matches = 0
    
    for match_id in range(start_id, end_id + 1):
        total_checked += 1
        
        # Progress indicator
        if total_checked % batch_size == 0:
            print(f"  Progress: {total_checked}/{end_id-start_id+1} checked, {handgun_matches} handgun matches found, {total_fetched} fetched")
        
        # Skip if already exists
        filename = f"match_data/match_{match_id}.json"
        if os.path.exists(filename):
            continue
        
        try:
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data:
                handgun_matches += 1
                
                # The client now validates that it's IPSC handgun
                if match_data.get('production_optics_results'):
                    client.save_match_data(match_data)
                    total_fetched += 1
                    
                    # Show successful fetches
                    title = match_data.get('match_title', 'Unknown')[:50]
                    shooters = len(match_data.get('production_optics_results', []))
                    print(f"    ✓ {match_id}: {title}... ({shooters} shooters)")
                    
        except Exception as e:
            # Most match IDs don't exist, that's normal
            if "not found" not in str(e).lower():
                print(f"    ✗ {match_id}: {str(e)[:30]}...")
        
        # Rate limiting - be respectful to PractiScore
        time.sleep(0.3)
    
    print(f"Range {start_id}-{end_id} complete:")
    print(f"  Total checked: {total_checked}")
    print(f"  Handgun matches found: {handgun_matches}")
    print(f"  Successfully fetched: {total_fetched}")
    
    return total_fetched

def main():
    print("🎯 Fetching ALL IPSC handgun matches from PractiScore...")
    print("This will focus on handgun matches only (no rifle, shotgun, etc.)")
    
    client = PractiScoreClient()
    
    # Define ranges to scan - start with most recent
    ranges = [
        (295000, 300000),  # Very recent (2024+)
        (290000, 295000),  # Recent (2024)
        (285000, 290000),  # Late 2023
        (280000, 285000),  # 2023
        (275000, 280000),  # 2022-2023
        (270000, 275000),  # 2022
        (260000, 270000),  # 2021-2022
        (250000, 260000),  # 2021
        (240000, 250000),  # 2020-2021
        (230000, 240000),  # 2020
        (220000, 230000),  # 2019-2020
        (200000, 220000),  # 2018-2019
        (180000, 200000),  # 2017-2018
        (160000, 180000),  # 2016-2017
        (140000, 160000),  # 2015-2016
        (120000, 140000),  # 2014-2015
        (100000, 120000),  # 2013-2014
        (80000, 100000),   # 2012-2013
        (60000, 80000),    # 2011-2012
        (40000, 60000),    # 2010-2011
        (20000, 40000),    # 2009-2010
        (1, 20000),        # Very old
    ]
    
    total_fetched = 0
    
    for start, end in ranges:
        print(f"\n=== Range {start}-{end} ({end-start+1} IDs) ===")
        
        # Ask user for each range
        user_input = input(f"Fetch IPSC handgun matches from {start} to {end}? [y/N/q]: ")
        
        if user_input.lower() == 'q':
            print("Quitting...")
            break
        elif user_input.lower().startswith('y'):
            range_fetched = fetch_range(client, start, end)
            total_fetched += range_fetched
            
            print(f"Range complete. Total IPSC handgun matches fetched: {total_fetched}")
            
            # Pause between ranges
            time.sleep(5)
        else:
            print(f"Skipping range {start}-{end}")
    
    print(f"\n✅ IPSC handgun fetching complete!")
    print(f"Total matches fetched: {total_fetched}")
    print(f"Matches saved to: match_data/")
    print("\nNext steps:")
    print("1. Run 'python process_matches.py' to update rankings")
    print("2. The ranking will include all players but filter to show only Swedish players")

if __name__ == "__main__":
    main()