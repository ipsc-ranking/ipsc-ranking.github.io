#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Bulk PractiScore scraper with multiple strategies
"""

import requests
import time
import random
import os
from datetime import datetime
from enhanced_practiscore import EnhancedPractiScoreClient

def test_individual_matches():
    """Test individual match fetching"""
    print("🎯 Testing individual match fetching...")
    
    client = EnhancedPractiScoreClient()
    
    # Try a range of recent match IDs
    test_ranges = [
        range(299950, 299960),  # Very recent
        range(299900, 299910),  # Recent
        range(299800, 299810),  # A bit older
    ]
    
    successful = 0
    total_tested = 0
    
    for test_range in test_ranges:
        print(f"\nTesting range {test_range.start}-{test_range.stop-1}")
        
        for match_id in test_range:
            total_tested += 1
            print(f"  Testing {match_id}...", end=" ")
            
            try:
                match_data = client.fetch_match_data(str(match_id))
                
                if match_data and match_data.get('production_optics_results'):
                    successful += 1
                    shooters = len(match_data['production_optics_results'])
                    title = match_data.get('match_title', 'Unknown')[:30]
                    print(f"✓ {title}... ({shooters} shooters)")
                    
                    # Save it
                    client.save_match_data(match_data)
                else:
                    print("✗ No data")
                    
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}...")
            
            # Rate limiting
            time.sleep(random.uniform(1, 3))
            
            # Stop if we find some successful matches
            if successful >= 5:
                print(f"\nFound {successful} matches, stopping early")
                break
        
        if successful >= 5:
            break
    
    print(f"\n📊 Results: {successful}/{total_tested} matches successfully fetched")
    return successful

def bulk_scan_range(start_id: int, end_id: int, max_success: int = 50):
    """Bulk scan a range of match IDs"""
    print(f"🚀 Bulk scanning range {start_id}-{end_id} (max {max_success} matches)")
    
    client = EnhancedPractiScoreClient()
    
    successful = 0
    checked = 0
    
    for match_id in range(start_id, end_id + 1):
        checked += 1
        
        if checked % 20 == 0:
            print(f"  Progress: {checked}/{end_id-start_id+1}, found: {successful}")
        
        # Skip if already exists
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            continue
        
        try:
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data and match_data.get('production_optics_results'):
                successful += 1
                shooters = len(match_data['production_optics_results'])
                title = match_data.get('match_title', 'Unknown')[:40]
                print(f"    ✓ {match_id}: {title}... ({shooters} shooters)")
                
                client.save_match_data(match_data)
                
                # Stop if we've found enough
                if successful >= max_success:
                    print(f"    Reached {max_success} matches, stopping")
                    break
            
        except Exception as e:
            if checked % 50 == 0:  # Only show errors occasionally
                print(f"    Error at {match_id}: {str(e)[:30]}...")
        
        # Rate limiting with randomization
        time.sleep(random.uniform(0.5, 2.0))
    
    print(f"Range {start_id}-{end_id} complete: {successful} matches found")
    return successful

def main():
    """Main bulk scraping function"""
    print("🌐 Starting bulk PractiScore scraping...")
    print("=" * 60)
    
    total_fetched = 0
    
    # Strategy 1: Test individual matches first
    individual_success = test_individual_matches()
    total_fetched += individual_success
    
    if individual_success > 0:
        print(f"✅ Individual testing successful! Found {individual_success} matches")
        
        # Strategy 2: Bulk scan recent ranges
        print(f"\n🔄 Starting bulk scanning...")
        
        ranges_to_scan = [
            (299900, 300000, 100),  # Very recent
            (299500, 299900, 200),  # Recent
            (299000, 299500, 300),  # Moderately recent
            (298000, 299000, 500),  # Older but still recent
        ]
        
        for start, end, max_matches in ranges_to_scan:
            print(f"\n--- Scanning range {start}-{end} (max {max_matches}) ---")
            
            range_success = bulk_scan_range(start, end, max_matches)
            total_fetched += range_success
            
            print(f"Range complete: {range_success} matches")
            print(f"Total fetched so far: {total_fetched}")
            
            # Pause between ranges
            if range_success > 0:
                print("Pausing 30 seconds before next range...")
                time.sleep(30)
            
            # Stop if we've got a good amount
            if total_fetched >= 1000:
                print(f"Reached {total_fetched} matches - stopping")
                break
    
    else:
        print("❌ Individual testing failed - PractiScore may be blocking all requests")
        print("Consider alternative approaches:")
        print("1. Manual data entry for key matches")
        print("2. Browser automation with Selenium")
        print("3. API access if available")
        print("4. Data sharing with other organizations")
    
    print(f"\n🏁 Scraping complete!")
    print(f"Total matches fetched: {total_fetched}")
    
    if total_fetched > 0:
        print(f"\nNext steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Check new files in match_data/ directory")

if __name__ == "__main__":
    main()