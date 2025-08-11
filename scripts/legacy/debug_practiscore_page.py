#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Debug PractiScore page structure to understand how to extract data
"""

import requests
import re

def main():
    print("🔍 Debugging PractiScore page structure...")
    
    # Test with a known match ID
    match_id = '299999'
    url = f'https://practiscore.com/results/new/{match_id}'
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        
        # Look for JavaScript patterns
        js_patterns = [
            r'matchDef\s*=\s*{',
            r'var\s+\w+\s*=\s*{',
            r'window\.\w+\s*=\s*{',
            r'match_\w+',
            r'shooters',
            r'results'
        ]
        
        content = response.text
        print(f"\nSearching for data patterns...")
        
        for pattern in js_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                print(f"  Found pattern '{pattern}': {len(matches)} times")
        
        # Look for JSON-like structures
        json_like = re.findall(r'{[^{}]*"[^"]*":[^{}]*}', content)
        print(f"\nFound {len(json_like)} JSON-like structures")
        
        # Show some context around matchDef if it exists
        matchdef_match = re.search(r'matchDef\s*=\s*({.*?});', content, re.DOTALL)
        if matchdef_match:
            print(f"\nFound matchDef! Length: {len(matchdef_match.group(1))}")
            print(f"First 200 chars: {matchdef_match.group(1)[:200]}...")
        else:
            print(f"\nNo matchDef found")
        
        # Check if it's an error page
        if 'not found' in content.lower() or 'error' in content.lower():
            print(f"\nPage appears to be an error page")
        
        # Save a sample of the page for manual inspection
        with open('debug_practiscore_page.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nSaved page content to debug_practiscore_page.html for inspection")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()