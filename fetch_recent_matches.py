#!/usr/bin/env python3
"""
Fetch recent matches from available data sources to expand our dataset.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def fetch_recent_ssi_matches():
    """Try to fetch recent SSI matches"""
    print("=== Fetching Recent SSI Matches ===")
    
    try:
        from data_sources.ssi import SSILiveIterator, SSIMatchFetcher
        
        # Try to fetch matches from recent range (last few match IDs we have data for)
        print("Checking recent SSI match ID range...")
        
        # Get the highest match ID we currently have
        import glob
        ssi_files = glob.glob('./data/matches/*ssi*.json')
        max_match_id = 0
        
        for file in ssi_files:
            try:
                parts = os.path.basename(file).split('_')
                if len(parts) >= 3:
                    match_id = int(parts[2].replace('.json', ''))
                    max_match_id = max(max_match_id, match_id)
            except (ValueError, IndexError):
                continue
        
        print(f"Highest existing SSI match ID: {max_match_id}")
        
        # Try to fetch a few matches after our highest ID
        start_id = max_match_id + 1
        end_id = max_match_id + 50  # Try next 50 matches
        
        print(f"Attempting to fetch SSI matches {start_id}-{end_id}")
        
        fetcher = SSIMatchFetcher()
        new_matches = 0
        
        for match_id in range(start_id, end_id + 1):
            try:
                match_data = fetcher.fetch_match(match_id)
                if match_data and 'combined_results' in match_data:
                    # Save the match
                    date_str = match_data.get('match_date', '')[:10] if match_data.get('match_date') else 'unknown'
                    filename = f"./data/matches/{date_str}_ssi_{match_id}.json"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(match_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"  ✓ Saved match {match_id}: {match_data.get('match_title', 'Unknown')}")
                    new_matches += 1
                else:
                    print(f"  - No data for match {match_id}")
                    
            except Exception as e:
                print(f"  × Error fetching match {match_id}: {e}")
                continue
        
        print(f"Fetched {new_matches} new SSI matches")
        return new_matches
        
    except Exception as e:
        print(f"Error in SSI fetching: {e}")
        return 0

def fetch_recent_practiscore_matches():
    """Try to fetch recent Practiscore matches"""
    print("\n=== Fetching Recent Practiscore Matches ===")
    
    try:
        from data_sources.practiscore import PractiscoreRangeIterator, PractiscoreMatchFetcher
        
        # Try a range of recent match IDs
        # Practiscore IDs are often in the 200000+ range for recent matches
        print("Attempting to fetch recent Practiscore matches...")
        
        fetcher = PractiscoreMatchFetcher()
        new_matches = 0
        
        # Try some recent-looking match IDs
        recent_ids = range(290000, 290050)  # Try 50 IDs in a recent range
        
        for match_id in recent_ids:
            try:
                match_data = fetcher.fetch_match(str(match_id))
                if match_data and 'combined_results' in match_data:
                    # Save the match
                    date_str = match_data.get('match_date', '')[:10] if match_data.get('match_date') else 'unknown'
                    filename = f"./data/matches/{date_str}_practiscore_{match_id}.json"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(match_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"  ✓ Saved match {match_id}: {match_data.get('match_title', 'Unknown')}")
                    new_matches += 1
                    
                    # Don't fetch too many at once
                    if new_matches >= 10:
                        break
                        
            except Exception as e:
                # Expected for many IDs that don't exist
                continue
        
        print(f"Fetched {new_matches} new Practiscore matches")
        return new_matches
        
    except Exception as e:
        print(f"Error in Practiscore fetching: {e}")
        return 0

def main():
    """Main fetching function"""
    print("Fetching Recent Match Data")
    print("=" * 40)
    
    total_new = 0
    
    # Fetch from different sources
    total_new += fetch_recent_ssi_matches()
    total_new += fetch_recent_practiscore_matches()
    
    print(f"\n=" * 40)
    print(f"Total new matches fetched: {total_new}")
    
    if total_new > 0:
        print("\nRun 'python3 ranking_system.py' to process the new matches!")
    else:
        print("\nNo new matches found. The dataset is up to date.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())