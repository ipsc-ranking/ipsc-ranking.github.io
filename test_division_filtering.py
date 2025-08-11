#!/usr/bin/env python3
"""
Test division filtering capabilities of the refactored system.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_ipscresults_division_filtering():
    """Test IPSCResults division filtering"""
    print("\n=== Testing IPSCResults Division Filtering ===")
    
    try:
        from data_sources.ipscresults import IPSCResultsClient
        
        client = IPSCResultsClient()
        print("✓ IPSCResultsClient created successfully")
        
        # Test handgun division detection
        sample_divisions = [
            {'Division': 'Production Optics', 'DivisionCode': 1},
            {'Division': 'Standard', 'DivisionCode': 2}, 
            {'Division': 'Open', 'DivisionCode': 3},
            {'Division': 'PCC', 'DivisionCode': 4},  # Should be included (handgun)
            {'Division': 'Pistol Caliber Carbine', 'DivisionCode': 5},  # Should be included (handgun)
            {'Division': 'Shotgun Open', 'DivisionCode': 6},  # Should be excluded
            {'Division': 'Rifle Standard', 'DivisionCode': 7}  # Should be excluded
        ]
        
        handgun_divisions = client.get_handgun_division_codes(sample_divisions)
        print(f"✓ Found {len(handgun_divisions)} handgun divisions from {len(sample_divisions)} total divisions")
        
        # Verify only handgun divisions are included
        handgun_names = [div['name'] for div in handgun_divisions]
        print(f"  Handgun divisions: {handgun_names}")
        
        expected_handgun = ['Production Optics', 'Standard', 'Open', 'PCC', 'Pistol Caliber Carbine']
        excluded_non_handgun = ['Shotgun Open', 'Rifle Standard']
        
        for name in expected_handgun:
            if name not in handgun_names:
                print(f"  ❌ Missing expected handgun division: {name}")
                return False
        
        for name in excluded_non_handgun:
            if name in handgun_names:
                print(f"  ❌ Incorrectly included non-handgun division: {name}")
                return False
        
        print("✓ Division filtering working correctly")
        return True
        
    except Exception as e:
        print(f"❌ IPSCResults division filtering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ssi_handgun_filtering():
    """Test SSI handgun match filtering"""
    print("\n=== Testing SSI Handgun Filtering ===")
    
    try:
        from data_sources.ssi import is_handgun_match
        
        # Test cases
        test_cases = [
            # Handgun matches (should return True)
            ([{'url': '/ipsc/results/match/123/div/hg1/', 'name': 'Open'}], True, 'Handgun Open'),
            ([{'url': '/ipsc/results/match/123/div/hg18/', 'name': 'Production Optics'}], True, 'Handgun Production Optics'),
            ([{'url': '/ipsc/results/match/123/div/hg17/', 'name': 'Pistol Caliber Carbine'}], True, 'Handgun PCC'),
            ([{'url': '/ipsc/results/match/123/div/iop/', 'name': 'Production Optics'}], True, 'IPSC Production Optics'),
            ([{'url': '/ipsc/results/match/123/div/ist/', 'name': 'Standard'}], True, 'IPSC Standard'),
            ([{'url': '/ipsc/results/match/123/div/unknown/', 'name': 'PCC'}], True, 'PCC by name'),
            ([{'url': '/ipsc/results/match/123/div/unknown/', 'name': 'Pistol Caliber Carbine'}], True, 'PCC by full name'),
            
            # Non-handgun matches (should return False)  
            ([{'url': '/ipsc/results/match/123/div/sg1/', 'name': 'Open'}], False, 'Shotgun Open'),
            ([{'url': '/ipsc/results/match/123/div/sg3/', 'name': 'Standard'}], False, 'Shotgun Standard'),
            ([{'url': '/ipsc/results/match/123/div/rf1/', 'name': 'Open'}], False, 'Rifle Open'),
            ([{'url': '/ipsc/results/match/123/div/rf2/', 'name': 'Standard'}], False, 'Rifle Standard'),
        ]
        
        all_passed = True
        for divisions, expected, description in test_cases:
            result = is_handgun_match(divisions)
            if result == expected:
                print(f"  ✓ {description}: {result} (correct)")
            else:
                print(f"  ❌ {description}: {result} (expected {expected})")
                all_passed = False
        
        if all_passed:
            print("✓ SSI handgun filtering working correctly")
        return all_passed
        
    except Exception as e:
        print(f"❌ SSI handgun filtering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_combined_results_consistency():
    """Test that all data sources consistently use combined_results"""
    print("\n=== Testing Combined Results Consistency ===")
    
    try:
        from data_sources import create_iterator
        
        iterator = create_iterator('all', 'file', match_data_dir='./data/matches/')
        
        matches_found = 0
        inconsistent_matches = 0
        
        for match in iterator:
            matches_found += 1
            
            # Check that combined_results is present
            if 'combined_results' not in match.get('raw_data', {}):
                print(f"  ❌ Match missing combined_results: {match.get('match_title', 'Unknown')}")
                inconsistent_matches += 1
                continue
                
            # Check that production_optics_results is not present (except in legacy data)
            raw_data = match.get('raw_data', {})
            if 'production_optics_results' in raw_data:
                print(f"  ⚠️  Match still has production_optics_results: {match.get('match_title', 'Unknown')}")
            
            # Verify combined_results has data
            combined_results = raw_data.get('combined_results', [])
            if not combined_results:
                print(f"  ❌ Match has empty combined_results: {match.get('match_title', 'Unknown')}")
                inconsistent_matches += 1
            
            if matches_found >= 10:  # Test first 10 matches
                break
        
        print(f"  Tested {matches_found} matches")
        if inconsistent_matches == 0:
            print("✓ All matches consistently use combined_results")
            return True
        else:
            print(f"❌ {inconsistent_matches} matches have inconsistent results format")
            return False
        
    except Exception as e:
        print(f"❌ Combined results consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all division filtering tests"""
    print("Testing Division Filtering and Data Consistency")
    print("=" * 60)
    
    tests = [
        test_ipscresults_division_filtering,
        test_ssi_handgun_filtering, 
        test_combined_results_consistency
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All division filtering tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())