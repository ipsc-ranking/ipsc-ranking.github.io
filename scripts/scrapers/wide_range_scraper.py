#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Wide-range PractiScore scraper that skips non-existent matches
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

class WideRangePractiScoreScraper:
    """Scrape PractiScore across wide ID ranges, skipping non-existent matches"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # IPSC Handgun divisions
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        # Statistics
        self.checked = 0
        self.found = 0
        self.redirects = 0
        self.errors = 0
        self.ipsc_matches = 0
    
    def is_valid_match_page(self, response: requests.Response) -> bool:
        """Check if response contains a valid match page"""
        
        # Check for redirects to search page
        if response.history or 'Scores Search' in response.text:
            return False
        
        # Must have substantial content
        if len(response.text) < 2000:
            return False
        
        # Should not be a general results page
        if 'search-result-list' in response.text:
            return False
        
        return True
    
    def extract_match_data(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Extract match data from HTML"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1') or soup.find('title')
            match_title = "Unknown Match"
            
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and 'scores search' not in title_text.lower():
                    match_title = title_text.replace(' | PractiScore', '').strip()
            
            # Look for shooters in various ways
            shooters = []
            
            # Method 1: JavaScript data
            js_shooters = self._extract_js_shooters(html_content)
            if js_shooters:
                shooters.extend(js_shooters)
            
            # Method 2: HTML tables
            if not shooters:
                table_shooters = self._extract_table_shooters(soup)
                if table_shooters:
                    shooters.extend(table_shooters)
            
            if not shooters:
                return None
            
            # Filter for IPSC handgun
            handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
            
            if not handgun_shooters:
                return None
            
            return {
                'match_id': int(match_id),
                'match_title': match_title,
                'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                'match_level': 'Level II',
                'club_name': 'Unknown',
                'combined_results': handgun_shooters,
                'production_optics_results': [s for s in handgun_shooters 
                                             if 'production optics' in s.get('division', '').lower()],
                'source': 'practiscore'
            }
            
        except Exception as e:
            print(f"    Parse error: {str(e)[:30]}...")
            return None
    
    def _extract_js_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from JavaScript"""
        
        shooters = []
        
        # Common PractiScore patterns
        patterns = [
            r'var\s+shooters\s*=\s*(\[.*?\]);',
            r'matchData\s*=\s*\{.*?shooters\s*:\s*(\[.*?\])',
            r'match_shooters\s*:\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    
                    data = json.loads(json_str)
                    
                    for shooter in data:
                        if isinstance(shooter, dict):
                            formatted = self._format_shooter(shooter)
                            if formatted:
                                shooters.append(formatted)
                                
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return shooters
    
    def _extract_table_shooters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shooters from HTML tables"""
        
        shooters = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Parse table rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                shooter = self._parse_table_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_table_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse table row to shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name
        name = None
        for text in cell_texts:
            if re.match(r'^[A-Za-zÅÄÖåäö\s\-\.\']{3,50}$', text) and ' ' in text:
                name = text
                break
        
        if not name:
            return None
        
        name_parts = name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Find percentage
        percentage = 0.0
        for text in cell_texts:
            if '%' in text:
                try:
                    percentage = float(text.replace('%', '').replace(',', '.'))
                    break
                except ValueError:
                    continue
            elif re.match(r'^\d+[\.,]?\d*$', text):
                try:
                    num = float(text.replace(',', '.'))
                    if 0 <= num <= 150:
                        percentage = num
                        break
                except ValueError:
                    continue
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': 'UNK',
            'division': 'Production Optics',
            'match_percentage': percentage,
            'placement': 999
        }
    
    def _format_shooter(self, raw_shooter: Dict) -> Optional[Dict[str, Any]]:
        """Format raw shooter data"""
        
        first_name = raw_shooter.get('sh_fn', raw_shooter.get('first_name', ''))
        last_name = raw_shooter.get('sh_ln', raw_shooter.get('last_name', ''))
        
        if not first_name and not last_name:
            return None
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': raw_shooter.get('alias', ''),
            'region': raw_shooter.get('region', 'UNK'),
            'division': raw_shooter.get('sh_dvp', raw_shooter.get('division', 'Production Optics')),
            'match_percentage': float(raw_shooter.get('percentage', raw_shooter.get('match_percentage', 0.0))),
            'placement': raw_shooter.get('placement', 999)
        }
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if shooter is in handgun division"""
        
        division = shooter.get('division', '').lower()
        
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', '3-gun', 'multigun'}
        if any(excl in division for excl in excluded):
            return False
        
        return True
    
    def scrape_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match, return None if doesn't exist"""
        
        self.checked += 1
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            return None
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            response = self.session.get(url, timeout=10)
            
            if not self.is_valid_match_page(response):
                self.redirects += 1
                return None  # Skip non-existent matches
            
            self.found += 1
            
            # Extract match data
            match_data = self.extract_match_data(response.text, match_id)
            
            if match_data:
                self.ipsc_matches += 1
                self.save_match_data(match_data)
                
                title = match_data.get('match_title', 'Unknown')[:40]
                shooters = len(match_data.get('combined_results', []))
                print(f"  ✅ {match_id}: {title}... ({shooters} shooters)")
                
                return match_data
            
        except Exception as e:
            self.errors += 1
            if self.errors % 10 == 0:  # Only show occasional errors
                print(f"    Error {match_id}: {str(e)[:30]}...")
        
        return None
    
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
            print(f"    Save error: {e}")
    
    def scan_range(self, start_id: int, end_id: int, max_matches: int = 100) -> int:
        """Scan a range of match IDs"""
        
        print(f"🔍 Scanning matches {start_id}-{end_id} (max {max_matches} IPSC matches)")
        
        successful = 0
        
        for match_id in range(start_id, end_id + 1):
            
            if self.checked % 100 == 0:
                print(f"  📊 Progress: {self.checked} checked, {self.found} exist, {self.ipsc_matches} IPSC, {self.redirects} missing")
            
            match_data = self.scrape_match(str(match_id))
            
            if match_data:
                successful += 1
                
                if successful >= max_matches:
                    print(f"  🏁 Found {max_matches} IPSC matches, stopping")
                    break
            
            # Rate limiting
            time.sleep(random.uniform(0.5, 1.5))
        
        return successful
    
    def print_stats(self):
        """Print scanning statistics"""
        print(f"\n📊 Scanning Statistics:")
        print(f"  Total checked: {self.checked}")
        print(f"  Matches found: {self.found}")
        print(f"  IPSC matches: {self.ipsc_matches}")
        print(f"  Redirects (missing): {self.redirects}")
        print(f"  Errors: {self.errors}")
        
        if self.found > 0:
            print(f"  Success rate: {(self.found/self.checked)*100:.1f}%")
            print(f"  IPSC rate: {(self.ipsc_matches/self.found)*100:.1f}%")

def main():
    """Main scanning function"""
    
    print("🌐 Wide-Range PractiScore Scanner")
    print("=" * 50)
    
    scraper = WideRangePractiScoreScraper()
    
    # Scan multiple ranges to find where matches actually exist
    ranges_to_scan = [
        (1, 1000, 10),           # Very old matches
        (10000, 11000, 10),      # Old matches  
        (50000, 51000, 20),      # Medium old
        (100000, 101000, 20),    # More recent
        (200000, 201000, 30),    # Recent
        (250000, 251000, 30),    # Very recent
        (299000, 300000, 50),    # Latest
    ]
    
    total_found = 0
    
    for start, end, max_matches in ranges_to_scan:
        print(f"\n--- Scanning range {start}-{end} ---")
        
        found = scraper.scan_range(start, end, max_matches)
        total_found += found
        
        scraper.print_stats()
        
        if found > 0:
            print(f"✅ Found {found} IPSC matches in range {start}-{end}")
            
            # If we found matches, scan more in this area
            if found >= max_matches // 2:
                print(f"Good hit rate - this range looks promising!")
        
        print("Pausing 5 seconds before next range...")
        time.sleep(5)
        
        # Stop if we've found enough
        if total_found >= 100:
            print(f"Found {total_found} total matches - stopping")
            break
    
    print(f"\n🏁 Scanning complete!")
    print(f"Total IPSC matches found: {total_found}")
    
    scraper.print_stats()
    
    if total_found > 0:
        print("\n📋 Next steps:")
        print("1. Run 'python process_matches.py' to update rankings")
        print("2. Check new files in match_data/ directory")
    else:
        print("\nℹ️  No IPSC matches found. This could mean:")
        print("1. Different URL structure than expected")
        print("2. Matches in different ID ranges")
        print("3. Authentication required")

if __name__ == "__main__":
    main()