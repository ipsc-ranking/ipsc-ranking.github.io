#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Test fetching a few recent PractiScore matches to validate the new system
"""

from practiscore_json import PractiScoreJSONClient
import time

def main():
    print("🧪 Testing recent PractiScore match fetching...")
    
    client = PractiScoreJSONClient()
    
    # Test with a few recent match IDs
    test_ids = [299995, 299996, 299997, 299998, 299999]
    
    successful = 0
    
    for match_id in test_ids:
        print(f"\n--- Testing match {match_id} ---")
        
        try:
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data and match_data.get('production_optics_results'):
                title = match_data.get('match_title', 'Unknown')
                shooters = len(match_data.get('production_optics_results', []))
                date = match_data.get('match_date', 'Unknown')
                
                print(f"  ✓ SUCCESS: {title}")
                print(f"    Date: {date}")
                print(f"    Shooters: {shooters}")
                
                # Show first few shooters
                for i, shooter in enumerate(match_data['production_optics_results'][:3]):
                    name = f"{shooter.get('first_name', '')} {shooter.get('last_name', '')}"
                    division = shooter.get('division', 'Unknown')
                    region = shooter.get('region', 'Unknown')
                    print(f"    {i+1}. {name} ({division}, {region})")
                
                # Save it with new timestamp naming
                client.save_match_data(match_data)
                successful += 1
                
            else:
                print(f"  ✗ No valid IPSC handgun data found")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}...")
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n✅ Test complete!")
    print(f"Successfully fetched {successful}/{len(test_ids)} matches")
    
    if successful > 0:
        print("\nNew files should be named like: YYYY-MM-DD_practiscore_ID.json")
        print("Run 'python process_matches.py' to include them in rankings")

if __name__ == "__main__":
    main()