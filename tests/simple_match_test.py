#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Simple test of known working matches
"""

import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

def test_known_matches():
    """Test the matches we know exist"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    })
    
    # Test the matches we know work
    known_matches = ['100000', '200000', '250000']
    
    print("🧪 Testing known working matches...")
    
    successful = 0
    
    for match_id in known_matches:
        print(f"\n📄 Testing match {match_id}:")
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            response = session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                continue
            
            if len(response.text) < 2000:
                print(f"  ❌ Content too short ({len(response.text)} chars)")
                continue
            
            if 'Scores Search' in response.text:
                print(f"  ❌ Redirected to search")
                continue
            
            # Extract title
            soup = BeautifulSoup(response.text, 'html.parser')
            title_meta = soup.find('meta', {'property': 'og:title'})
            
            if title_meta and title_meta.get('content'):
                title = title_meta['content'].strip()
                print(f"  ✅ Title: {title}")
                
                # Look for shooter data
                shooters_found = False
                
                # Check for table data
                tables = soup.find_all('table')
                table_rows = 0
                for table in tables:
                    rows = table.find_all('tr')
                    if len(rows) > 5:  # Substantial table
                        table_rows += len(rows)
                        shooters_found = True
                
                if table_rows > 0:
                    print(f"  📊 Found {table_rows} table rows")
                
                # Check for JavaScript data
                if 'shooters' in response.text.lower():
                    print(f"  📋 Contains 'shooters' data")
                    shooters_found = True
                
                if 'results' in response.text.lower():
                    print(f"  📋 Contains 'results' data")
                    shooters_found = True
                
                # Check for IPSC/USPSA indicators
                content_lower = response.text.lower()
                if 'production' in content_lower:
                    print(f"  🎯 Contains 'production' division")
                if 'optics' in content_lower:
                    print(f"  🎯 Contains 'optics' division")
                if 'uspsa' in content_lower or 'ipsc' in content_lower:
                    print(f"  🎯 USPSA/IPSC match")
                
                if shooters_found:
                    print(f"  ✅ Match {match_id} looks promising for scraping!")
                    successful += 1
                    
                    # Save a sample
                    sample_data = {
                        'match_id': int(match_id),
                        'match_title': title,
                        'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                        'match_level': 'Level II',
                        'club_name': 'Unknown',
                        'test_scraped': True,
                        'content_length': len(response.text),
                        'has_tables': table_rows > 0,
                        'source': 'practiscore'
                    }
                    
                    filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_test_{match_id}.json"
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(sample_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"  💾 Saved test data to {filename}")
                else:
                    print(f"  ⚠️  No shooter data found")
            else:
                print(f"  ❌ No valid title found")
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}...")
    
    print(f"\n🏁 Test complete: {successful}/{len(known_matches)} matches were scrapable")
    
    if successful > 0:
        print(f"✅ Success! We can scrape PractiScore matches")
        print(f"The approach works - now we just need to find more match IDs")
        print(f"\n📋 Next steps:")
        print(f"1. Use focused scraper on proven ranges")
        print(f"2. Look for patterns in working match IDs")
        print(f"3. Gradually expand the search ranges")
    else:
        print(f"❌ No matches were scrapable")
        print(f"This suggests the data format may be different")

if __name__ == "__main__":
    test_known_matches()