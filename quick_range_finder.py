#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests

"""
Quick range finder to locate where PractiScore matches actually exist
"""

import requests
import time
import random

def quick_test_ranges():
    """Quickly test different ranges to find where matches exist"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    
    # Test ranges - sampling across different ranges
    test_ranges = [
        (1, 100, 10),           # Very old
        (1000, 2000, 10),       # Old  
        (10000, 11000, 10),     # Medium old
        (50000, 51000, 10),     # Recent-ish
        (100000, 110000, 20),   # More recent
        (150000, 160000, 20),   # Recent
        (200000, 210000, 20),   # Very recent
        (250000, 260000, 20),   # Latest
        (280000, 290000, 20),   # Current
        (295000, 300000, 20),   # Most recent
    ]
    
    print("🔍 Quick Range Finder")
    print("=" * 40)
    
    for start, end, sample_size in test_ranges:
        print(f"\n--- Testing range {start}-{end} ({sample_size} samples) ---")
        
        # Sample random IDs from this range
        test_ids = random.sample(range(start, end + 1), min(sample_size, end - start + 1))
        
        valid_matches = []
        redirects = 0
        errors = 0
        
        for match_id in test_ids:
            url = f'https://practiscore.com/results/new/{match_id}'
            
            try:
                response = session.get(url, timeout=5, allow_redirects=False)
                
                if response.status_code == 200:
                    # Check if it's a real match page
                    if len(response.text) > 5000 and 'Scores Search' not in response.text:
                        valid_matches.append(match_id)
                        print(f"  ✅ {match_id}: Valid match found!")
                    else:
                        print(f"  ⚠️  {match_id}: 200 but redirected to search")
                        redirects += 1
                elif response.status_code == 302:
                    redirects += 1
                else:
                    errors += 1
                    
            except Exception:
                errors += 1
            
            time.sleep(0.5)  # Quick but respectful
        
        print(f"  Results: {len(valid_matches)} valid, {redirects} redirects, {errors} errors")
        
        if valid_matches:
            print(f"  🎯 FOUND VALID RANGE! Valid IDs: {valid_matches}")
            print(f"  This range ({start}-{end}) has working matches!")
            
            # Test a few more in this promising range
            print(f"  Testing 10 more in this range...")
            additional_tests = random.sample(range(start, end + 1), 10)
            additional_valid = []
            
            for match_id in additional_tests:
                if match_id in test_ids:  # Skip already tested
                    continue
                    
                url = f'https://practiscore.com/results/new/{match_id}'
                try:
                    response = session.get(url, timeout=5, allow_redirects=False)
                    if (response.status_code == 200 and 
                        len(response.text) > 5000 and 
                        'Scores Search' not in response.text):
                        additional_valid.append(match_id)
                        print(f"    ✅ {match_id}: Additional valid match!")
                except Exception:
                    pass
                time.sleep(0.5)
            
            if additional_valid:
                print(f"  🚀 Range {start}-{end} looks very promising!")
                print(f"  Total valid matches found: {len(valid_matches + additional_valid)}")
                return start, end, valid_matches + additional_valid
        
        # Small pause between ranges
        time.sleep(2)
    
    print("\n❌ No valid match ranges found")
    return None, None, []

def main():
    promising_range = quick_test_ranges()
    
    if promising_range[0]:
        start, end, valid_ids = promising_range
        print(f"\n🎯 RECOMMENDED SCRAPING RANGE: {start}-{end}")
        print(f"Found {len(valid_ids)} working matches in this range")
        print(f"Working match IDs: {sorted(valid_ids)}")
        
        print(f"\n📋 Next steps:")
        print(f"1. Focus scraping on range {start}-{end}")
        print(f"2. Try adjacent ranges: {start-10000}-{start} and {end}-{end+10000}")
        print(f"3. Use these working IDs to understand the data format")
        
        # Test one working match to see data format
        if valid_ids:
            test_id = valid_ids[0]
            print(f"\n🔍 Testing data format for match {test_id}...")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            })
            
            try:
                response = session.get(f'https://practiscore.com/results/new/{test_id}', timeout=10)
                if response.status_code == 200:
                    print(f"  Content length: {len(response.text)} chars")
                    
                    # Look for key indicators
                    content = response.text.lower()
                    
                    if 'production' in content:
                        print("  ✅ Contains 'production' - likely has IPSC divisions")
                    if 'optics' in content:
                        print("  ✅ Contains 'optics' - likely has Production Optics")
                    if 'percentage' in content or '%' in content:
                        print("  ✅ Contains percentage data")
                    if 'shooters' in content:
                        print("  ✅ Contains shooter data")
                    
                    # Show a sample of the content structure
                    if '<table' in content:
                        print("  ✅ Contains HTML tables")
                    if 'json' in content or '{' in response.text:
                        print("  ✅ Likely contains JSON data")
                        
            except Exception as e:
                print(f"  ❌ Error testing format: {e}")
    
    else:
        print(f"\n💡 Suggestions:")
        print(f"1. Try different URL patterns (maybe not /results/new/)")
        print(f"2. Check if authentication is required")
        print(f"3. Verify the current PractiScore URL structure")

if __name__ == "__main__":
    main()