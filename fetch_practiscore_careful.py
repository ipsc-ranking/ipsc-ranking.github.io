#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Carefully fetch recent IPSC handgun matches from PractiScore with proper rate limiting
"""

import time
import os
from practiscore import PractiScoreClient

def main():
    print("🎯 Carefully fetching recent IPSC handgun matches from PractiScore...")
    
    client = PractiScoreClient()
    
    # Start with a smaller, more recent range to avoid overwhelming their servers
    recent_ranges = [
        (299000, 300000),  # Very recent (smaller range)
    ]
    
    total_fetched = 0
    
    for start, end in recent_ranges:
        print(f"\n=== Fetching range {start}-{end} with careful rate limiting ===")
        
        range_fetched = 0
        checked = 0
        errors_429 = 0
        consecutive_429 = 0
        
        for match_id in range(start, end + 1):
            checked += 1
            
            # Progress
            if checked % 50 == 0:
                print(f"  Progress: {checked}/{end-start+1}, fetched: {range_fetched}, 429 errors: {errors_429}")
            
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
                    consecutive_429 = 0  # Reset 429 counter on success
                    
                    title = match_data.get('match_title', 'Unknown')[:50]
                    shooters = len(match_data.get('production_optics_results', []))
                    print(f"    ✓ {match_id}: {title}... ({shooters} shooters)")
                    
            except Exception as e:
                if "429" in str(e):
                    errors_429 += 1
                    consecutive_429 += 1
                    print(f"    Rate limited on {match_id}, waiting longer...")
                    
                    # Progressive backoff for 429 errors
                    if consecutive_429 < 5:
                        time.sleep(10)  # 10 seconds
                    elif consecutive_429 < 10:
                        time.sleep(30)  # 30 seconds
                    else:
                        time.sleep(60)  # 1 minute
                        
                    # If we get too many consecutive 429s, give up on this range
                    if consecutive_429 > 20:
                        print(f"    Too many consecutive rate limits, skipping rest of range")
                        break
                else:
                    consecutive_429 = 0  # Reset on non-429 errors
                    # Most IDs don't exist, that's normal
                    pass
            
            # Conservative rate limiting - 2 seconds between requests
            time.sleep(2.0)
        
        print(f"Range {start}-{end} complete: {range_fetched} matches fetched, {errors_429} rate limit errors")
    
    print(f"\n✅ Careful fetch complete!")
    print(f"Total IPSC handgun matches fetched: {total_fetched}")
    print("Run 'python process_matches.py' to update rankings")

if __name__ == "__main__":
    main()