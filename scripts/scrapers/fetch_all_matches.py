#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Script to fetch ALL PractiScore matches systematically
"""

import time
from practiscore import PractiScoreClient

class PractiScoreScanner:
    def __init__(self):
        self.client = PractiScoreClient()
    
    def scan_range(self, start_id: int, end_id: int, batch_size: int = 100):
        """
        Scan a range of match IDs and fetch all valid matches
        """
        print(f"Scanning match IDs {start_id} to {end_id}")
        
        successful = 0
        failed = 0
        
        for match_id in range(start_id, end_id + 1):
            if match_id % batch_size == 0:
                print(f"  Progress: {match_id}/{end_id} (Success: {successful}, Failed: {failed})")
            
            try:
                match_data = self.client.fetch_match_data(str(match_id))
                
                if match_data and match_data.get('production_optics_results'):
                    self.client.save_match_data(match_data)
                    successful += 1
                    
                    if match_id % 10 == 0:  # Show some successful fetches
                        print(f"    ✓ {match_id}: {match_data.get('match_title', 'Unknown')[:50]}...")
                else:
                    failed += 1
                    
            except Exception:
                failed += 1
            
            # Rate limiting - be respectful
            time.sleep(0.2)
        
        print(f"Range {start_id}-{end_id} complete: {successful} successful, {failed} failed")
        return successful

def main():
    print("🌍 Fetching ALL PractiScore matches...")
    print("Note: This will take a long time and fetch thousands of matches")
    
    scanner = PractiScoreScanner()
    
    # Define ranges to scan - adjust based on known PractiScore ID patterns
    ranges = [
        (280000, 290000),  # Recent matches
        (270000, 280000),  # 2023-2024
        (250000, 270000),  # 2022-2023  
        (200000, 250000),  # 2020-2022
        (150000, 200000),  # 2018-2020
        (100000, 150000),  # 2016-2018
        (50000, 100000),   # 2014-2016
        (1, 50000),        # Very old matches
    ]
    
    total_fetched = 0
    
    for start, end in ranges:
        print(f"\n=== Scanning range {start}-{end} ===")
        
        # Ask user if they want to continue with this range
        user_input = input(f"Scan {end-start+1} match IDs from {start} to {end}? [y/N/q]: ")
        
        if user_input.lower() == 'q':
            print("Quitting...")
            break
        elif user_input.lower().startswith('y'):
            fetched = scanner.scan_range(start, end)
            total_fetched += fetched
            print(f"Range complete. Total matches fetched so far: {total_fetched}")
        else:
            print(f"Skipping range {start}-{end}")
    
    print(f"\n✅ Fetching complete! Total matches fetched: {total_fetched}")
    print("Run 'python process_matches.py' to update rankings")

if __name__ == "__main__":
    main()