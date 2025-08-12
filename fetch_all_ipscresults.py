#!/usr/bin/env python3
"""
Comprehensive script to fetch ALL matches from ipscresults.org.
This will significantly expand our dataset from ~21 matches to ~1,229 matches.
"""

import os
import json
import time
from datetime import datetime
from src.data_sources.ipscresults import IPSCResultsClient, IPSCResultsMatchFetcher

def load_existing_match_ids():
    """Load existing IPSCResults match IDs to avoid duplicates"""
    existing_ids = set()
    
    if not os.path.exists('./match_data/'):
        return existing_ids
    
    for filename in os.listdir('./match_data/'):
        if '_ipscresults_' in filename and filename.endswith('.json'):
            try:
                with open(f'./match_data/{filename}', 'r') as f:
                    data = json.load(f)
                    
                # Extract match ID from the data
                match_id = data.get('match_id')
                if match_id:
                    existing_ids.add(match_id)
                    
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}")
                continue
    
    print(f"📊 Found {len(existing_ids)} existing IPSCResults matches")
    return existing_ids

def fetch_all_matches():
    """Fetch ALL matches from ipscresults.org"""
    print("🌍 Fetching ALL ipscresults.org matches...")
    print("=" * 60)
    
    client = IPSCResultsClient()
    fetcher = IPSCResultsMatchFetcher(client)
    
    # Load existing match IDs
    existing_ids = load_existing_match_ids()
    
    # Get complete match list
    print("📡 Fetching complete match list from ipscresults.org...")
    matches = client.get_match_list()
    
    if not matches:
        print("❌ Failed to fetch match list")
        return 0
    
    print(f"✅ Retrieved {len(matches)} total matches from API")
    
    # Analyze the dataset
    dates = [m.get('Date', '') for m in matches if m.get('Date')]
    dates = [d for d in dates if d]
    if dates:
        dates.sort()
        print(f"📅 Date range: {dates[0]} to {dates[-1]}")
    
    # Level distribution
    levels = {}
    for m in matches:
        level = m.get('Level', 'Unknown')
        levels[level] = levels.get(level, 0) + 1
    print(f"🎯 Level distribution: {dict(sorted(levels.items()))}")
    
    # Filter out already processed matches
    new_matches = [m for m in matches if m['ID'] not in existing_ids]
    print(f"📥 New matches to process: {len(new_matches)}")
    
    if not new_matches:
        print("✅ All matches already processed!")
        return 0
    
    # Process all new matches
    total_saved = 0
    total_divisions = 0
    skipped = 0
    errors = 0
    
    for i, match_info in enumerate(new_matches):
        match_id = match_info['ID']
        match_name = match_info.get('Name', 'Unknown Match')
        match_date = match_info.get('Date', 'Unknown')
        match_level = match_info.get('Level', 'Unknown')
        
        print(f"\\n[{i+1}/{len(new_matches)}] Processing: {match_name}")
        print(f"  📅 {match_date} | 🎯 Level {match_level} | 🆔 {match_id[:8]}...")
        
        try:
            # Fetch all handgun divisions for this match
            match_divisions = fetcher.fetch_match(match_id)
            
            if not match_divisions:
                print(f"  ⚠️  No handgun divisions found")
                skipped += 1
                continue
            
            match_data = match_divisions[0]  # Combined match with all divisions
            divisions_info = match_data.get('divisions', {})
            
            print(f"  ✅ Found {len(divisions_info)} handgun divisions:")
            for div_name, div_data in divisions_info.items():
                shooter_count = div_data.get('shooter_count', 0)
                print(f"     📊 {div_name}: {shooter_count} shooters")
                total_divisions += 1
            
            # Save the combined match data
            try:
                fetcher.save_match_data(match_data)
                total_saved += 1
                print(f"  💾 Saved successfully")
                
            except Exception as e:
                print(f"  ❌ Error saving: {e}")
                errors += 1
            
            # Add small delay to be respectful to the API
            time.sleep(0.2)
            
        except Exception as e:
            print(f"  ❌ Error processing match: {e}")
            errors += 1
            continue
        
        # Progress checkpoint every 50 matches
        if (i + 1) % 50 == 0:
            print(f"\\n📊 Progress checkpoint:")
            print(f"   Processed: {i+1}/{len(new_matches)}")
            print(f"   Saved: {total_saved}")
            print(f"   Skipped: {skipped}")
            print(f"   Errors: {errors}")
            print(f"   Total divisions: {total_divisions}")
    
    print(f"\\n🎯 Complete Fetch Summary:")
    print(f"   Total matches in database: {len(matches)}")
    print(f"   Previously processed: {len(existing_ids)}")
    print(f"   New matches processed: {len(new_matches)}")
    print(f"   Successfully saved: {total_saved}")
    print(f"   Skipped (no handgun data): {skipped}")
    print(f"   Errors: {errors}")
    print(f"   Total divisions processed: {total_divisions}")
    
    return total_saved

def main():
    """Main function"""
    print("🚀 IPSCResults.org COMPLETE Database Fetcher")
    print("=" * 60)
    print("This will fetch ALL matches from ipscresults.org (2004-2025)")
    print("Expected: ~1,229 matches with thousands of divisions")
    print("=" * 60)
    
    # Ensure directories exist
    os.makedirs('./match_data/', exist_ok=True)
    
    start_time = datetime.now()
    
    # Fetch all matches
    new_matches = fetch_all_matches()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    if new_matches > 0:
        print(f"\\n✅ Successfully fetched {new_matches} new match files!")
        print(f"⏱️  Total time: {duration}")
        print(f"\\n🔧 Next steps:")
        print("   1. Run ranking generation: python process_matches.py")
        print("   2. Update website: python update_rankings.py")
        print("\\n📈 This will SIGNIFICANTLY improve ranking accuracy!")
        print("   - Much larger dataset (20x more matches)")
        print("   - Historical data back to 2004")
        print("   - More accurate skill ratings")
    else:
        print(f"\\n📍 No new matches to process")
        print("   All ipscresults.org matches are already in the database")
    
    return 0

if __name__ == "__main__":
    exit(main())