#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Comprehensive script to fetch ALL IPSC handgun matches from PractiScore
using improved JSON parsing
"""

import time
import os
from practiscore_json import PractiScoreJSONClient

def fetch_range_comprehensive(client, start_id, end_id, max_matches=1000):
    """Fetch matches in a range with comprehensive logging"""
    
    print(f"🎯 Fetching IPSC handgun matches {start_id} to {end_id}")
    print(f"   Will stop after {max_matches} successful matches to avoid overload")
    
    total_checked = 0
    total_found = 0
    total_ipsc_handgun = 0
    total_saved = 0
    
    for match_id in range(start_id, end_id + 1):
        total_checked += 1
        
        # Progress indicator
        if total_checked % 100 == 0:
            print(f"  Progress: {total_checked}/{end_id-start_id+1} checked")
            print(f"  Results: {total_found} found, {total_ipsc_handgun} IPSC HG, {total_saved} saved")
        
        # Stop if we've saved enough matches
        if total_saved >= max_matches:
            print(f"  Reached maximum of {max_matches} matches, stopping")
            break
        
        # Skip if already exists
        filename = f"match_data/match_{match_id}.json"
        if os.path.exists(filename):
            continue
        
        try:
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data:
                total_found += 1
                
                # Check if it's IPSC handgun
                if match_data.get('production_optics_results'):
                    total_ipsc_handgun += 1
                    
                    # Save it
                    client.save_match_data(match_data)
                    total_saved += 1
                    
                    # Show successful saves
                    title = match_data.get('match_title', 'Unknown')[:50]
                    shooters = len(match_data.get('production_optics_results', []))
                    print(f"    ✓ {match_id}: {title}... ({shooters} shooters)")
                    
        except Exception as e:
            # Most match IDs don't exist
            if total_checked % 1000 == 0:  # Only show errors occasionally
                print(f"    Range error at {match_id}: {str(e)[:30]}...")
        
        # Rate limiting
        time.sleep(0.1)
    
    print(f"\nRange {start_id}-{end_id} results:")
    print(f"  Total checked: {total_checked}")
    print(f"  Matches found: {total_found}")
    print(f"  IPSC handgun: {total_ipsc_handgun}")
    print(f"  Successfully saved: {total_saved}")
    
    return total_saved

def main():
    print("🌍 Comprehensive IPSC Handgun Match Fetcher")
    print("=" * 50)
    
    client = PractiScoreJSONClient()
    
    # Define ranges to scan (most recent first)
    ranges = [
        (299000, 300000, 200),  # Very recent, get 200 matches
        (295000, 299000, 300),  # Recent, get 300 matches  
        (290000, 295000, 500),  # 2023-2024, get 500 matches
        (280000, 290000, 1000), # 2022-2023, get 1000 matches
        (270000, 280000, 1000), # 2021-2022, get 1000 matches
        (250000, 270000, 2000), # 2020-2021, get 2000 matches
        (200000, 250000, 3000), # 2018-2020, get 3000 matches
        (150000, 200000, 2000), # 2016-2018, get 2000 matches
        (100000, 150000, 1000), # 2014-2016, get 1000 matches
        (50000, 100000, 500),   # 2012-2014, get 500 matches
        (1, 50000, 200),        # Very old, get 200 matches
    ]
    
    total_fetched = 0
    
    for start, end, max_matches in ranges:
        print(f"\n{'='*60}")
        print(f"Range {start}-{end} (max {max_matches} matches)")
        print(f"{'='*60}")
        
        range_fetched = fetch_range_comprehensive(client, start, end, max_matches)
        total_fetched += range_fetched
        
        print(f"Range complete: {range_fetched} matches saved")
        print(f"Total matches fetched so far: {total_fetched}")
        
        # Pause between ranges
        print("Pausing 10 seconds before next range...")
        time.sleep(10)
        
        # Optional: Stop after getting a good amount of data
        if total_fetched >= 5000:
            print(f"\nReached {total_fetched} matches - stopping to avoid overload")
            break
    
    print(f"\n🎉 Comprehensive fetch complete!")
    print(f"Total IPSC handgun matches fetched: {total_fetched}")
    print(f"Matches saved to: match_data/")
    print("\nNext steps:")
    print("1. Run 'python process_matches.py' to update rankings")
    print("2. Rankings will include all players but show only Swedish players")

if __name__ == "__main__":
    main()