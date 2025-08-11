#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Focused PractiScore scraper working in proven ranges
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

class FocusedPractiScoreScraper:
    """Scraper focused on proven match ID ranges"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
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
        self.stats = {
            'checked': 0,
            'valid': 0,
            'ipsc': 0,
            'saved': 0,
            'redirects': 0,
            'errors': 0
        }
    
    def is_valid_match(self, response: requests.Response) -> tuple[bool, str]:
        """Check if response is a valid match page"""
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        if len(response.text) < 2000:
            return False, "Too short"
        
        if 'Scores Search' in response.text:
            return False, "Redirected to search"
        
        # Look for match title
        soup = BeautifulSoup(response.text, 'html.parser')
        title_meta = soup.find('meta', {'property': 'og:title'})
        
        if title_meta and title_meta.get('content'):
            title = title_meta['content'].strip()
            if title and title != "Scores Search":
                return True, title
        
        return False, "No valid title"
    
    def extract_match_data(self, html_content: str, match_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Extract match data from HTML"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for shooters in various formats
            shooters = []
            
            # Method 1: JavaScript data
            js_shooters = self._extract_js_shooters(html_content)
            if js_shooters:
                shooters.extend(js_shooters)
                print(f"    Found {len(js_shooters)} shooters from JavaScript")
            
            # Method 2: HTML tables  
            if not shooters:
                table_shooters = self._extract_table_shooters(soup)
                if table_shooters:
                    shooters.extend(table_shooters)
                    print(f"    Found {len(table_shooters)} shooters from tables")
            
            if not shooters:
                print(f"    No shooters found")
                return None
            
            # Filter for IPSC handgun shooters
            handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
            
            if not handgun_shooters:
                print(f"    No IPSC handgun shooters (found {len(shooters)} total)")
                return None
            
            print(f"    ✅ {len(handgun_shooters)} IPSC handgun shooters")
            
            return {
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
            
        except Exception as e:
            print(f"    Parse error: {str(e)[:50]}...")
            return None
    
    def _extract_js_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from JavaScript"""
        
        shooters = []
        
        # Look for various JavaScript patterns
        patterns = [
            r'var\s+shooters\s*=\s*(\[.*?\]);',
            r'shooters\s*:\s*(\[.*?\])',
            r'match_shooters\s*:\s*(\[.*?\])',
            r'results\s*:\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JSON
                    json_str = re.sub(r',\s*]', ']', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    
                    data = json.loads(json_str)
                    
                    for shooter in data:
                        if isinstance(shooter, dict) and not shooter.get('sh_del', False):
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
            
            # Parse data rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                shooter = self._parse_table_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_table_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse table row into shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name (text with space and reasonable length)
        name = None
        for text in cell_texts:
            if (re.match(r'^[A-Za-zÅÄÖåäö\s\-\.\']{3,50}$', text) and 
                ' ' in text and 
                len(text.split()) <= 4):
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
        
        # Find division
        division = 'Production Optics'  # Default
        for text in cell_texts:
            text_lower = text.lower()
            for div in self.handgun_divisions:
                if div in text_lower:
                    division = text
                    break
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': 'UNK',
            'division': division,
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
        
        # Check for handgun divisions
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        # Exclude non-handgun disciplines
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', '3-gun', 'multigun', 'precision'}
        if any(excl in division for excl in excluded):
            return False
        
        # For USPSA/IPSC matches, default to include
        return True
    
    def scrape_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match"""
        
        self.stats['checked'] += 1
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            return None
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            response = self.session.get(url, timeout=10)
            
            is_valid, info = self.is_valid_match(response)
            
            if not is_valid:
                if info.startswith('HTTP'):
                    self.stats['errors'] += 1
                else:
                    self.stats['redirects'] += 1
                return None
            
            self.stats['valid'] += 1
            title = info  # info contains the title
            
            print(f"  📄 {match_id}: {title[:50]}...")
            
            # Extract match data
            match_data = self.extract_match_data(response.text, match_id, title)
            
            if match_data:
                self.stats['ipsc'] += 1
                self.save_match_data(match_data)
                self.stats['saved'] += 1
                return match_data
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"    Error: {str(e)[:30]}...")
        
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
            
            shooters = len(match_data.get('combined_results', []))
            print(f"    💾 Saved with {shooters} shooters")
            
        except IOError as e:
            print(f"    Save error: {e}")
    
    def scan_range(self, start_id: int, end_id: int, max_matches: int = 50) -> int:
        """Scan a range of match IDs"""
        
        print(f"🔍 Scanning matches {start_id}-{end_id} (max {max_matches} IPSC matches)")
        
        successful = 0
        
        for match_id in range(start_id, end_id + 1):
            
            if self.stats['checked'] % 50 == 0 and self.stats['checked'] > 0:
                self.print_progress()
            
            match_data = self.scrape_match(str(match_id))
            
            if match_data:
                successful += 1
                
                if successful >= max_matches:
                    print(f"  🏁 Found {max_matches} IPSC matches, stopping range")
                    break
            
            # Rate limiting
            time.sleep(random.uniform(1, 2))
        
        return successful
    
    def print_progress(self):
        """Print current progress"""
        s = self.stats
        print(f"  📊 Progress: {s['checked']} checked, {s['valid']} valid, {s['ipsc']} IPSC, {s['saved']} saved")

def main():
    """Main scraping function"""
    
    print("🎯 Focused PractiScore Scraper")
    print("=" * 50)
    
    scraper = FocusedPractiScoreScraper()
    
    # Focus on proven ranges where we know matches exist
    ranges_to_scan = [
        (99000, 101000, 30),    # Around 100000 (proven working)
        (249000, 251000, 30),   # Around 250000 (proven working) 
        (200000, 202000, 20),   # Around 200000 (proven working)
        (150000, 152000, 20),   # Test around 150000
    ]
    
    total_found = 0
    
    for start, end, max_matches in ranges_to_scan:
        print(f"\n--- Scanning range {start}-{end} ---")
        
        found = scraper.scan_range(start, end, max_matches)
        total_found += found
        
        print(f"Range {start}-{end} complete: {found} IPSC matches found")
        
        # Pause between ranges
        if found > 0:
            print("✅ Found matches - pausing 10s before next range...")
            time.sleep(10)
        else:
            print("No matches - pausing 5s...")
            time.sleep(5)
        
        # Stop if we've found enough
        if total_found >= 50:
            print(f"Found {total_found} total matches - stopping")
            break
    
    print(f"\n🏁 Scanning complete!")
    print(f"📊 Final Statistics:")
    s = scraper.stats
    print(f"  Total checked: {s['checked']}")
    print(f"  Valid matches: {s['valid']}")
    print(f"  IPSC matches: {s['ipsc']}")
    print(f"  Saved matches: {s['saved']}")
    print(f"  Redirects: {s['redirects']}")
    print(f"  Errors: {s['errors']}")
    
    if total_found > 0:
        print(f"\n📋 Next steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Check new files in match_data/ directory")
        print(f"3. Expand to adjacent ranges if successful")

if __name__ == "__main__":
    main()