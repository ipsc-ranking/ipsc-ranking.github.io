#!/usr/bin/env python3
"""
Example usage of the new match data iterator system.

This script demonstrates how to use the refactored iterator modules
for both file-based and live data sources.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_sources import create_iterator
from data_sources.ssi import SSIFileIterator, SSILiveIterator  
from data_sources.practiscore import PractiscoreFileIterator, PractiscoreLiveIterator
from data_sources.ipscresults import IPSCResultsFileIterator, IPSCResultsLiveIterator


def demo_file_based_iterators():
    """Demonstrate file-based iterators"""
    print("=== File-Based Iterator Demo ===")
    
    # Example 1: SSI files only
    print("\n1. SSI files only:")
    ssi_iterator = create_iterator('ssi', 'file', match_data_dir='../data/matches/', 
                                  filter_levels=['Level III', 'Level IV', 'Level V'])
    
    count = 0
    for match in ssi_iterator:
        if count < 3:  # Show first 3 matches
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
            print(f"    Shooters: {len(match['results'])}")
        count += 1
    print(f"  Total SSI matches: {count}")
    
    # Example 2: Practiscore files only  
    print("\n2. Practiscore files only:")
    practiscore_iterator = create_file_based_iterator('practiscore', './match_data/')
    
    count = 0
    for match in practiscore_iterator:
        if count < 3:  # Show first 3 matches
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
            print(f"    Shooters: {len(match['results'])}")
        count += 1
    print(f"  Total Practiscore matches: {count}")
    
    # Example 2.5: IPSCResults files only
    print("\n2.5. IPSCResults files only:")
    ipscresults_iterator = create_file_based_iterator('ipscresults', './match_data/')
    
    count = 0
    for match in ipscresults_iterator:
        if count < 3:  # Show first 3 matches
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
            print(f"    Shooters: {len(match['results'])}")
        count += 1
    print(f"  Total IPSCResults matches: {count}")
    
    # Example 3: Combined (all sources)
    print("\n3. Combined all sources:")
    combined_iterator = create_file_based_iterator('all', './match_data/')
    
    source_counts = {}
    total_matches = 0
    for match in combined_iterator:
        source = match['source']
        source_counts[source] = source_counts.get(source, 0) + 1
        total_matches += 1
        
        if total_matches <= 5:  # Show first 5 matches
            print(f"  - {source}: {match['match_title']} ({match['match_date']})")
    
    print(f"  Total matches: {total_matches}")
    for source, count in source_counts.items():
        print(f"    {source}: {count}")
        
    # Example 4: Test individual IPSCResults iterator
    print("\n4. Direct IPSCResults file iterator:")
    ipscresults_direct = IPSCResultsFileIterator('./match_data/')
    
    count = 0
    for match in ipscresults_direct:
        if count < 2:  # Show first 2 matches
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
        count += 1
    print(f"  Total direct IPSCResults matches: {count}")


def demo_live_iterators():
    """Demonstrate live data iterators"""
    print("\n\n=== Live Iterator Demo ===")
    
    # Note: These examples fetch live data, so use small ranges for demo
    
    # Example 1: SSI live data
    print("\n1. SSI live data (small range for demo):")
    try:
        ssi_live = create_live_iterator('ssi', start_match_id=22740, end_match_id=22742,
                                      filter_levels=['Level III', 'Level IV', 'Level V'])
        
        for match in ssi_live:
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
            print(f"    Level: {match.get('match_level', 'Unknown')}")
            print(f"    Shooters: {len(match['results'])}")
            break  # Just show one for demo
            
    except Exception as e:
        print(f"  Error fetching SSI live data: {e}")
    
    # Example 2: Practiscore live data
    print("\n2. Practiscore live data (specific match IDs):")
    try:
        # Use known Practiscore match IDs
        practiscore_live = create_live_iterator('practiscore', match_ids=['287616'])
        
        for match in practiscore_live:
            print(f"  - {match['source']}: {match['match_title']} ({match['match_date']})")
            print(f"    Level: {match.get('match_level', 'Unknown')}")
            print(f"    Shooters: {len(match['results'])}")
            
    except Exception as e:
        print(f"  Error fetching Practiscore live data: {e}")


def demo_direct_iterator_usage():
    """Demonstrate direct usage of iterator classes"""
    print("\n\n=== Direct Iterator Usage Demo ===")
    
    # Example 1: Direct SSI file iterator
    print("\n1. Direct SSI file iterator:")
    ssi_iterator = SSIFileIterator('./match_data/')
    
    count = 0
    for match in ssi_iterator:
        if count < 2:  # Show first 2 matches
            print(f"  - Match {match['match_id']}: {match['match_title']}")
            print(f"    Date: {match['match_date']}, Level: {match['match_level']}")
            
            # Show first few shooters
            for i, result in enumerate(match['results'][:3]):
                shooter = result['raw_result']
                print(f"    {i+1}. {shooter['first_name']} {shooter['last_name']}: {shooter['match_percentage']:.1f}%")
        count += 1
    
    print(f"  Total SSI matches found: {count}")


def main():
    """Main demo function"""
    print("Match Data Iterator System Demo")
    print("=" * 50)
    
    try:
        demo_file_based_iterators()
        demo_direct_iterator_usage()
        
        # Uncomment to test live data (will make network requests)
        # demo_live_iterators()
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()