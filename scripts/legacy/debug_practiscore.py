#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def debug_practiscore_page(match_id='287616'):
    """Debug the structure of a PractiScore page"""
    url = f'https://practiscore.com/results/new/{match_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        print(f"Page length: {len(response.text)} characters")
        
        # Check for common elements
        print(f"\nElements found:")
        print(f"  Tables: {len(soup.find_all('table'))}")
        print(f"  Divs: {len(soup.find_all('div'))}")
        print(f"  Scripts: {len(soup.find_all('script'))}")
        
        # Look for any JavaScript that might load data
        scripts = soup.find_all('script')
        for i, script in enumerate(scripts):
            if script.string and ('result' in script.string.lower() or 'data' in script.string.lower()):
                print(f"  Script {i} contains result/data references")
        
        # Check if this might be a single-page application
        if 'angular' in response.text.lower() or 'react' in response.text.lower() or 'vue' in response.text.lower():
            print("\n  This appears to be a SPA that loads data via JavaScript")
        
        # Save the HTML for manual inspection
        with open('debug_practiscore.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\nSaved HTML to debug_practiscore.html for manual inspection")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_practiscore_page()