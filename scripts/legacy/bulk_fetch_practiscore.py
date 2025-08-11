#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Bulk fetch PractiScore matches using known patterns and ranges
"""

import time
import os
from practiscore import PractiScoreClient

def fetch_match_batch(client, match_ids):
    """Fetch a batch of matches"""
    successful = 0
    
    for match_id in match_ids:
        try:
            # Check if already exists
            filename = f"match_data/match_{match_id}.json"
            if os.path.exists(filename):
                print(f"  {match_id}: Already exists")
                continue
                
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data and match_data.get('production_optics_results'):
                client.save_match_data(match_data)
                successful += 1
                print(f"  ✓ {match_id}: {match_data.get('match_title', 'Unknown')[:60]}...")
            else:
                print(f"  ✗ {match_id}: No data or no production optics")
                
        except Exception as e:
            print(f"  ✗ {match_id}: Error - {str(e)[:50]}...")
        
        # Rate limiting
        time.sleep(0.5)
    
    return successful

def main():
    print("🎯 Bulk fetching PractiScore matches...")
    
    client = PractiScoreClient()
    
    # Start with recent match ranges that are most likely to exist
    recent_ranges = [
        range(290000, 300000),  # Very recent
        range(285000, 290000),  # Recent
        range(280000, 285000),  # 2024
        range(275000, 280000),  # Late 2023
        range(270000, 275000),  # 2023
    ]
    
    total_fetched = 0
    
    for match_range in recent_ranges:
        range_start = match_range.start
        range_end = match_range.stop - 1
        
        print(f"\n=== Fetching matches {range_start} to {range_end} ===")
        
        # Convert range to list
        match_ids = list(match_range)
        
        # Fetch in smaller batches
        batch_size = 100
        for i in range(0, len(match_ids), batch_size):
            batch = match_ids[i:i+batch_size]
            print(f"Batch {i//batch_size + 1}: matches {batch[0]} to {batch[-1]}")
            
            batch_fetched = fetch_match_batch(client, batch)
            total_fetched += batch_fetched
            
            print(f"  Batch result: {batch_fetched}/{len(batch)} successful")
            print(f"  Total fetched so far: {total_fetched}")
            
            # Pause between batches
            time.sleep(2)
    
    print(f"\n✅ Bulk fetch complete!")
    print(f"Total matches fetched: {total_fetched}")
    print("\nRun 'python process_matches.py' to update rankings with new data")

if __name__ == "__main__":
    main()