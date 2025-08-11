#!/usr/bin/env python3
"""
Demo script to fetch and save some IPSCResults matches.
"""

from datetime import datetime, timedelta
from ipscresults_iterator import IPSCResultsMatchFetcher, IPSCResultsClient


def fetch_recent_matches_with_production_optics():
    """Fetch recent matches that have Production Optics division"""
    print("Fetching recent matches with Production Optics...")
    
    client = IPSCResultsClient()
    fetcher = IPSCResultsMatchFetcher(client)
    
    # Get match list
    matches = client.get_match_list()
    
    # Filter for recent matches (last year)
    recent_date = datetime.now() - timedelta(days=365)
    recent_matches = []
    
    for match_info in matches:
        try:
            match_date = datetime.fromisoformat(match_info['Date'])
            if match_date >= recent_date:
                recent_matches.append(match_info)
        except:
            continue
    
    print(f"Found {len(recent_matches)} matches from the last year")
    
    # Look for matches with Production Optics
    production_optics_matches = []
    
    for i, match_info in enumerate(recent_matches[:20]):  # Check first 20 recent matches
        match_id = match_info['ID']
        print(f"Checking match {i+1}/20: {match_info['Name']}")
        
        divisions = client.get_match_divisions(match_id)
        prod_optics_code = client.get_production_optics_division_code(divisions)
        
        if prod_optics_code:
            print(f"  ✓ Has Production Optics division")
            production_optics_matches.append(match_info)
            
            # Fetch and save this match
            match_data = fetcher.fetch_match(match_id)
            if match_data:
                try:
                    fetcher.save_match_data(match_data)
                    print(f"  ✓ Saved match data")
                except Exception as e:
                    print(f"  ✗ Error saving: {e}")
            else:
                print(f"  ✗ Failed to fetch match data")
            
            # Limit to 3 matches for demo
            if len(production_optics_matches) >= 3:
                break
        else:
            print(f"  - No Production Optics division")
    
    print(f"\nFound and saved {len(production_optics_matches)} matches with Production Optics")
    for match in production_optics_matches:
        print(f"  - {match['Name']} ({match['Date']})")


def demo_specific_match():
    """Demo fetching a specific match by ID"""
    print("\n" + "="*50)
    print("Demo: Fetching specific match")
    
    # Use the match ID from our earlier test
    match_id = "217f9972-02f5-4425-ab0f-3992e66ff137"  # Rooster Mountain 2025
    
    fetcher = IPSCResultsMatchFetcher()
    
    print(f"Fetching match: {match_id}")
    match_data = fetcher.fetch_match(match_id)
    
    if match_data:
        print(f"Successfully fetched: {match_data['match_title']}")
        print(f"Date: {match_data['match_date']}")
        print(f"Level: {match_data['match_level']}")
        print(f"Region: {match_data.get('region', 'Unknown')}")
        print(f"Shooters: {len(match_data['production_optics_results'])}")
        
        # Show top 5 shooters
        print("\nTop 5 shooters:")
        for i, shooter in enumerate(match_data['production_optics_results'][:5]):
            name = f"{shooter['first_name']} {shooter['last_name']}"
            region = shooter['region']
            percentage = shooter['match_percentage']
            print(f"  {i+1}. {name} ({region}): {percentage:.1f}%")
        
        # Save the match
        try:
            fetcher.save_match_data(match_data)
            print("\n✓ Match data saved successfully")
        except Exception as e:
            print(f"\n✗ Error saving match: {e}")
    else:
        print("Failed to fetch match data")


def main():
    """Main demo function"""
    print("IPSCResults Match Fetcher Demo")
    print("=" * 50)
    
    try:
        # Demo 1: Fetch recent matches with Production Optics
        # fetch_recent_matches_with_production_optics()
        
        # Demo 2: Fetch specific match (less API calls)
        demo_specific_match()
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()