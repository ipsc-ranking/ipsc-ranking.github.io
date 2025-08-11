#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Test fetch a few matches to validate the approach
"""

from practiscore import PractiScoreClient

def main():
    print("🧪 Test fetching a few PractiScore matches...")
    
    client = PractiScoreClient()
    
    # Test with a small range of recent matches
    test_ids = range(299990, 300000)  # Just 10 matches to test
    
    successful = 0
    
    for match_id in test_ids:
        print(f"\nTesting match {match_id}...")
        
        try:
            match_data = client.fetch_match_data(str(match_id))
            
            if match_data:
                title = match_data.get('match_title', 'Unknown')
                shooters = len(match_data.get('production_optics_results', []))
                
                if match_data.get('production_optics_results'):
                    print(f"  ✓ {match_id}: {title} ({shooters} shooters)")
                    
                    # Show some shooter info
                    for i, shooter in enumerate(match_data['production_optics_results'][:3]):
                        name = f"{shooter.get('first_name', '')} {shooter.get('last_name', '')}"
                        division = shooter.get('division', 'Unknown')
                        region = shooter.get('region', 'Unknown')
                        print(f"    {i+1}. {name} ({division}, {region})")
                    
                    # Save it
                    client.save_match_data(match_data)
                    successful += 1
                else:
                    print(f"  ✗ {match_id}: {title} (no handgun data or filtered out)")
            else:
                print(f"  ✗ {match_id}: No data")
                
        except Exception as e:
            print(f"  ✗ {match_id}: Error - {str(e)[:50]}...")
    
    print(f"\n✅ Test complete! Successfully fetched {successful} matches")

if __name__ == "__main__":
    main()