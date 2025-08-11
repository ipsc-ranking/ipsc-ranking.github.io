#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Simple test to understand PractiScore's current structure
"""

import requests
import time
from bs4 import BeautifulSoup

def test_practiscore_access():
    """Test basic PractiScore access"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    print("🌐 Testing PractiScore access...")
    
    # Test 1: Main results page
    try:
        response = session.get('https://practiscore.com/results', timeout=10)
        print(f"✅ Main results page: {response.status_code}")
        
        if 'cloudflare' in response.text.lower() and 'blocked' in response.text.lower():
            print("❌ Blocked by Cloudflare")
            return False
        
    except Exception as e:
        print(f"❌ Failed to access main page: {e}")
        return False
    
    # Test 2: Try some common match URL patterns
    test_patterns = [
        'https://practiscore.com/results/new/300000',
        'https://practiscore.com/results/new/299999',
        'https://practiscore.com/results/new/299998',
        'https://practiscore.com/results/200000',  # Different format
        'https://practiscore.com/results/100000',  # Even older format
    ]
    
    print("\n🔍 Testing different match URL patterns...")
    
    for url in test_patterns:
        try:
            response = session.get(url, timeout=10, allow_redirects=False)
            
            if response.status_code == 200:
                print(f"✅ {url}: 200 OK - Match exists!")
                # Check if it has actual match content
                if len(response.text) > 5000 and 'Scores Search' not in response.text:
                    print(f"   📊 Has substantial content ({len(response.text)} chars)")
                    return True
                else:
                    print(f"   ⚠️  Redirected to search page")
                    
            elif response.status_code == 302:
                print(f"⚠️  {url}: 302 Redirect - No match found")
                
            elif response.status_code == 403:
                print(f"❌ {url}: 403 Forbidden - Blocked")
                
            else:
                print(f"⚠️  {url}: {response.status_code}")
                
            time.sleep(1)  # Be respectful
            
        except Exception as e:
            print(f"❌ {url}: Error - {str(e)[:30]}...")
    
    # Test 3: Try to find any recent matches through search
    print("\n🔍 Searching for recent matches...")
    
    try:
        search_response = session.get('https://practiscore.com/search/matches', timeout=10)
        
        if search_response.status_code == 200:
            soup = BeautifulSoup(search_response.text, 'html.parser')
            
            # Look for any result links
            links = soup.find_all('a', href=True)
            match_links = [link['href'] for link in links 
                          if 'results' in link['href'] and any(c.isdigit() for c in link['href'])]
            
            if match_links:
                print(f"✅ Found {len(match_links)} potential match links:")
                for link in match_links[:5]:  # Show first 5
                    print(f"   {link}")
                return True
            else:
                print("❌ No match links found in search")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    return False

def main():
    print("🧪 Simple PractiScore Access Test")
    print("=" * 40)
    
    if test_practiscore_access():
        print("\n✅ Success! PractiScore is accessible and we found working URLs")
        print("This means the scraping approach should work with the right match IDs")
    else:
        print("\n❌ No working match URLs found")
        print("This suggests:")
        print("1. Match IDs we tested don't exist")
        print("2. URL structure might be different")
        print("3. Authentication might be required")
        print("\nSince you can access PractiScore normally in your browser,")
        print("could you share a working match URL to help understand the structure?")

if __name__ == "__main__":
    main()