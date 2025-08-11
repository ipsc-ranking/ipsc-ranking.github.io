#!/usr/bin/env python3
"""
Test and example usage for IPSCResults.org iterator.
"""

from datetime import datetime, timedelta
from ipscresults_iterator import (
    IPSCResultsClient, 
    IPSCResultsLiveIterator, 
    IPSCResultsMatchFetcher
)
from match_data_iterator import create_live_iterator


def test_ipscresults_client():
    """Test basic IPSCResults client functionality"""
    print("=== Testing IPSCResults Client ===")
    
    client = IPSCResultsClient()
    
    # Test getting match list
    print("1. Fetching match list...")
    matches = client.get_match_list()
    print(f"   Found {len(matches)} matches")
    
    if matches:
        # Show first few matches
        print("   First 3 matches:")
        for i, match in enumerate(matches[:3]):
            print(f"   {i+1}. {match['Name']} - {match['Date']} (Level {match['Level']})")
        
        # Test getting match detail for first match
        first_match = matches[0]
        match_id = first_match['ID']
        print(f"\n2. Testing match detail for: {first_match['Name']}")
        
        detail = client.get_match_detail(match_id)
        if detail:
            print(f"   Location: {detail.get('Location', 'Unknown')}")
            print(f"   Match Director: {detail.get('MatchDirector', 'Unknown')}")
            print(f"   Region: {detail.get('Region', 'Unknown')}")
        
        # Test getting divisions
        print(f"\n3. Testing divisions for match {match_id}")
        divisions = client.get_match_divisions(match_id)
        if divisions:
            print(f"   Available divisions: {len(divisions)}")
            for div in divisions:
                print(f"   - {div['Division']} (Code: {div['DivisionCode']}, Total: {div['Total']})")
            
            # Find Production Optics
            prod_optics_code = client.get_production_optics_division_code(divisions)
            if prod_optics_code:
                print(f"   Production Optics division code: {prod_optics_code}")
                
                # Test getting results
                print(f"\n4. Testing results for Production Optics division")
                results = client.get_match_results(match_id, prod_optics_code)
                if results:
                    print(f"   Found {len(results)} competitors")
                    # Show top 3
                    for i, result in enumerate(results[:3]):
                        name = result.get('CompetitorName', 'Unknown')
                        region = result.get('Region', 'Unknown')
                        percentage = result.get('MatchPercent', 0)
                        print(f"   {i+1}. {name} ({region}): {percentage:.1f}%")
                else:
                    print("   No results found")
            else:
                print("   Production Optics division not found")
        else:
            print("   No divisions found")


def test_ipscresults_live_iterator():
    """Test IPSCResults live iterator"""
    print("\n\n=== Testing IPSCResults Live Iterator ===")
    
    # Test with filters to limit results for demo
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)  # Last 60 days
    
    iterator = IPSCResultsLiveIterator(
        filter_levels=[3, 4, 5],  # Level III and above
        filter_regions=['Sweden', 'Denmark', 'Norway'],
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Testing iterator with filters:")
    print(f"  - Levels: [3, 4, 5]")
    print(f"  - Regions: ['Sweden', 'Denmark', 'Norway']")
    print(f"  - Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    count = 0
    for match in iterator:
        if count < 3:  # Show first 3 matches
            print(f"\n{count+1}. {match['match_title']}")
            print(f"   Source: {match['source']}")
            print(f"   Date: {match['match_date']}")
            print(f"   Level: {match['match_level']}")
            print(f"   Region: {match.get('region', 'Unknown')}")
            print(f"   Shooters: {len(match['results'])}")
            
            # Show top 3 shooters
            for i, result in enumerate(match['results'][:3]):
                shooter = result['raw_result']
                name = f"{shooter['first_name']} {shooter['last_name']}"
                region = shooter['region']
                percentage = shooter['match_percentage']
                print(f"     {i+1}. {name} ({region}): {percentage:.1f}%")
        
        count += 1
        
        # Limit for demo to avoid too many API calls
        if count >= 5:
            break
    
    print(f"\nTotal matches found with filters: {count}")


def test_factory_function():
    """Test the factory function for IPSCResults"""
    print("\n\n=== Testing Factory Function ===")
    
    try:
        # Test IPSCResults specific iterator
        print("1. Testing IPSCResults-specific iterator:")
        iterator = create_live_iterator('ipscresults', 
                                      filter_levels=[4, 5],
                                      filter_regions=['Sweden'])
        
        count = 0
        for match in iterator:
            if count == 0:  # Just show first match
                print(f"   Found: {match['match_title']} ({match['match_date']})")
            count += 1
            if count >= 2:  # Limit for demo
                break
        
        print(f"   Total matches: {count}")
        
    except Exception as e:
        print(f"   Error: {e}")


def test_match_fetcher():
    """Test the match fetcher utility"""
    print("\n\n=== Testing Match Fetcher ===")
    
    # First get a match ID from the match list
    client = IPSCResultsClient()
    matches = client.get_match_list()
    
    if matches:
        # Find a match with Production Optics
        for match_info in matches[:5]:  # Check first 5 matches
            match_id = match_info['ID']
            divisions = client.get_match_divisions(match_id)
            prod_optics_code = client.get_production_optics_division_code(divisions)
            
            if prod_optics_code:
                print(f"Testing fetcher with match: {match_info['Name']}")
                
                fetcher = IPSCResultsMatchFetcher()
                match_data = fetcher.fetch_match(match_id)
                
                if match_data:
                    print(f"  Successfully fetched match data")
                    print(f"  Title: {match_data['match_title']}")
                    print(f"  Date: {match_data['match_date']}")
                    print(f"  Shooters: {len(match_data['production_optics_results'])}")
                    
                    # Test saving to file
                    try:
                        fetcher.save_match_data(match_data)
                        print(f"  Successfully saved match data to file")
                    except Exception as e:
                        print(f"  Error saving: {e}")
                else:
                    print(f"  Failed to fetch match data")
                
                break
        else:
            print("No matches with Production Optics found in first 5 matches")
    else:
        print("No matches found")


def main():
    """Run all tests"""
    print("IPSCResults Iterator Test Suite")
    print("=" * 50)
    
    try:
        test_ipscresults_client()
        
        # Uncomment to test live iterator (makes many API calls)
        # test_ipscresults_live_iterator()
        
        test_factory_function()
        test_match_fetcher()
        
        print("\n" + "=" * 50)
        print("Tests completed!")
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()