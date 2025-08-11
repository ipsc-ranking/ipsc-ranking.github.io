#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Working PractiScore scraper focused on proven ranges with actual data extraction
"""

import requests
import json
import time
import random
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class WorkingPractiScoreScraper:
    """Proven working scraper for PractiScore"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
        })
        
        # IPSC Handgun divisions
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        # Statistics
        self.stats = {
            'checked': 0,
            'valid': 0,
            'ipsc': 0,
            'saved': 0,
            'skipped': 0
        }
    
    def is_valid_match(self, response: requests.Response) -> tuple[bool, str]:
        """Check if response is a valid match"""
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        if len(response.text) < 2000:
            return False, "Content too short"
        
        if 'Scores Search' in response.text:
            return False, "Redirected to search"
        
        # Extract title
        soup = BeautifulSoup(response.text, 'html.parser')
        title_meta = soup.find('meta', {'property': 'og:title'})
        
        if title_meta and title_meta.get('content'):
            title = title_meta['content'].strip()
            if title and title != "Scores Search":
                return True, title
        
        return False, "No valid title"
    
    def extract_shooters_from_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shooters from HTML tables"""
        
        shooters = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 5:  # Skip small tables
                continue
            
            # Analyze table structure
            header_row = rows[0] if rows else None
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
                
                # Look for shooter result tables
                if not any(h in headers for h in ['name', 'place', 'first', 'last', 'division']):
                    continue
            
            # Parse shooter rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:  # Need enough columns
                    continue
                
                shooter = self._parse_shooter_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_shooter_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse table row to extract shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find placement (usually first column)
        placement = 999
        for i, text in enumerate(cell_texts[:3]):  # Check first 3 columns
            if text.isdigit() and 1 <= int(text) <= 500:
                placement = int(text)
                break
        
        # Find name (text with space, reasonable length)
        name = None
        first_name = ""
        last_name = ""
        
        for text in cell_texts:
            if (re.match(r'^[A-Za-zÅÄÖåäö\s\-\.\']{3,50}$', text) and 
                ' ' in text and 
                len(text.split()) <= 4 and
                not text.lower() in ['production optics', 'open division', 'standard division']):
                name = text
                name_parts = name.split()
                first_name = name_parts[0] if name_parts else ''
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                break
        
        if not first_name and not last_name:
            return None
        
        # Find percentage
        percentage = 0.0
        for text in cell_texts:
            if '%' in text:
                try:
                    percentage = float(text.replace('%', '').replace(',', '.'))
                    break
                except ValueError:
                    continue
            elif re.match(r'^\d+[\.,]\d+$', text):  # Decimal number
                try:
                    num = float(text.replace(',', '.'))
                    if 50 <= num <= 120:  # Reasonable percentage range
                        percentage = num
                        break
                except ValueError:
                    continue
        
        # Find division
        division = 'Production Optics'  # Default
        for text in cell_texts:
            text_lower = text.lower()
            for div in self.handgun_divisions:
                if div in text_lower or text_lower in div:
                    division = text
                    break
        
        # Find region (usually 2-3 letter codes)
        region = 'UNK'
        for text in cell_texts:
            if re.match(r'^[A-Z]{2,3}$', text) and text not in ['DNS', 'DNF', 'DQ']:
                region = text
                break
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': region,
            'division': division,
            'match_percentage': percentage,
            'placement': placement
        }
    
    def _is_ipsc_handgun_match(self, shooters: List[Dict], title: str) -> bool:
        """Check if this is an IPSC handgun match"""
        
        # Check title for obvious IPSC/USPSA indicators
        title_lower = title.lower()
        if any(indicator in title_lower for indicator in ['uspsa', 'ipsc', 'steel challenge']):
            return True
        
        # Check if shooters have handgun divisions
        handgun_count = 0
        for shooter in shooters[:10]:  # Check first 10
            division = shooter.get('division', '').lower()
            if any(hg_div in division for hg_div in self.handgun_divisions):
                handgun_count += 1
        
        # Must have reasonable number of handgun shooters
        return handgun_count >= len(shooters) * 0.3  # At least 30% handgun
    
    def scrape_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match"""
        
        self.stats['checked'] += 1
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            self.stats['skipped'] += 1
            return None
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            response = self.session.get(url, timeout=10)
            
            is_valid, info = self.is_valid_match(response)
            if not is_valid:
                return None
            
            self.stats['valid'] += 1
            title = info
            
            print(f"  📄 {match_id}: {title[:50]}...")
            
            # Extract shooters
            soup = BeautifulSoup(response.text, 'html.parser')
            shooters = self.extract_shooters_from_tables(soup)
            
            if not shooters:
                print(f"    ❌ No shooters found")
                return None
            
            # Check if IPSC handgun match
            if not self._is_ipsc_handgun_match(shooters, title):
                print(f"    ⏭️  Not IPSC handgun ({len(shooters)} shooters)")
                return None
            
            self.stats['ipsc'] += 1
            
            # Filter handgun shooters
            handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
            
            match_data = {
                'match_id': int(match_id),
                'match_title': title,
                'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                'match_level': 'Level II',
                'club_name': 'Unknown',
                'combined_results': handgun_shooters,
                'production_optics_results': [s for s in handgun_shooters 
                                             if 'production optics' in s.get('division', '').lower()],
                'source': 'practiscore'
            }
            
            self.save_match_data(match_data)
            self.stats['saved'] += 1
            
            print(f"    ✅ Saved {len(handgun_shooters)} IPSC handgun shooters")
            return match_data
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:30]}...")
            return None
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if shooter is in handgun division"""
        
        division = shooter.get('division', '').lower()
        
        # Check for handgun divisions
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        # Exclude non-handgun
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', 'precision'}
        if any(excl in division for excl in excluded):
            return False
        
        return True  # Default include for USPSA/IPSC
    
    def save_match_data(self, match_data: Dict[str, Any]):
        """Save match data"""
        
        match_date = match_data.get('match_date', '')
        timestamp = match_date.split('T')[0] if 'T' in match_date else datetime.now().strftime('%Y-%m-%d')
        match_id = match_data['match_id']
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"    💾 Save error: {e}")
    
    def scan_range(self, start_id: int, end_id: int, max_matches: int = 30) -> int:
        """Scan range of match IDs"""
        
        print(f"🔍 Scanning matches {start_id}-{end_id} (max {max_matches} IPSC matches)")
        
        successful = 0
        
        for match_id in range(start_id, end_id + 1):
            
            if self.stats['checked'] % 25 == 0 and self.stats['checked'] > 0:
                self.print_progress()
            
            match_data = self.scrape_match(str(match_id))
            
            if match_data:
                successful += 1
                
                if successful >= max_matches:
                    print(f"  🏁 Found {max_matches} IPSC matches, stopping")
                    break
            
            # Rate limiting
            time.sleep(random.uniform(0.8, 1.5))
        
        return successful
    
    def print_progress(self):
        """Print progress"""
        s = self.stats
        print(f"    📊 Progress: {s['checked']} checked, {s['valid']} valid, {s['ipsc']} IPSC, {s['saved']} saved, {s['skipped']} skipped")

def main():
    """Main scraping function"""
    
    print("🎯 Working PractiScore Scraper")
    print("=" * 50)
    
    scraper = WorkingPractiScoreScraper()
    
    # Focus on proven working ranges
    ranges = [
        (99900, 100100, 20),   # Around proven 100000
        (249900, 250100, 20),  # Around proven 250000
        (99500, 99900, 15),    # Expand around 100000
        (250100, 250500, 15),  # Expand around 250000
        (199900, 200100, 15),  # Around 200000
    ]
    
    total_found = 0
    
    for start, end, max_matches in ranges:
        print(f"\n--- Scanning range {start}-{end} ---")
        
        found = scraper.scan_range(start, end, max_matches)
        total_found += found
        
        print(f"Range complete: {found} IPSC matches found")
        scraper.print_progress()
        
        if found > 0:
            print("✅ Found matches - continuing to next range...")
        
        # Stop early if we found enough
        if total_found >= 50:
            print(f"Found {total_found} total matches - stopping")
            break
        
        time.sleep(3)  # Pause between ranges
    
    print(f"\n🏁 Scraping complete!")
    print(f"📊 Final Statistics:")
    s = scraper.stats
    print(f"  Total checked: {s['checked']}")
    print(f"  Valid matches: {s['valid']}")
    print(f"  IPSC matches: {s['ipsc']}")
    print(f"  Saved matches: {s['saved']}")
    print(f"  Skipped existing: {s['skipped']}")
    
    if total_found > 0:
        print(f"\n✅ Success! Found {total_found} IPSC matches")
        print(f"📋 Next steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Check new files in match_data/ directory")
        print(f"3. Expand to more ranges based on successful patterns")

if __name__ == "__main__":
    main()