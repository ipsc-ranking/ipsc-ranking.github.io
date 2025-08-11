#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4 curl

"""
Curl-based PractiScore scraper using subprocess to leverage working curl
"""

import subprocess
import json
import time
import random
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class CurlPractiScoreScraper:
    """Use curl subprocess to scrape PractiScore"""
    
    def __init__(self):
        # IPSC Handgun divisions
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        # Browser headers for curl
        self.headers = [
            '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.5',
            '-H', 'Accept-Encoding: gzip, deflate, br',
            '-H', 'Connection: keep-alive',
            '-H', 'Upgrade-Insecure-Requests: 1',
            '-H', 'Cache-Control: max-age=0'
        ]
    
    def curl_get(self, url: str, follow_redirects: bool = True, timeout: int = 30) -> Optional[str]:
        """Use curl to fetch URL"""
        
        cmd = ['curl', '-s', '--compressed', '--max-time', str(timeout)]
        
        if follow_redirects:
            cmd.append('-L')
        
        cmd.extend(self.headers)
        cmd.append(url)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"    Curl error (code {result.returncode}): {result.stderr[:50]}...")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"    Curl timeout after {timeout}s")
            return None
        except Exception as e:
            print(f"    Curl exception: {str(e)[:50]}...")
            return None
    
    def fetch_match_page(self, match_id: str) -> Optional[str]:
        """Fetch match page content"""
        
        url = f'https://practiscore.com/results/new/{match_id}'
        print(f"  🌐 Fetching {url}")
        
        content = self.curl_get(url)
        
        if not content:
            return None
        
        # Check if we got redirected to search page (no match found)
        if 'Scores Search' in content and '/results' in content:
            print(f"    ⏭️  Match {match_id} not found (redirected to search)")
            return None
        
        # Check for Cloudflare blocks
        if 'cloudflare' in content.lower() and 'blocked' in content.lower():
            print(f"    ❌ Cloudflare blocked")
            return None
        
        # Check for actual match content
        if len(content) < 1000:
            print(f"    ❌ Content too short ({len(content)} chars)")
            return None
        
        print(f"    ✅ Got content ({len(content)} chars)")
        return content
    
    def parse_match_html(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Parse HTML content to extract match data"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract match title
            title_elem = soup.find('h1') or soup.find('title')
            match_title = "Unknown Match"
            
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and 'scores search' not in title_text.lower():
                    match_title = title_text.replace(' | PractiScore', '')
            
            # Look for shooters data in various formats
            shooters = []
            
            # Method 1: Look for JavaScript data
            js_shooters = self._extract_js_shooters(html_content)
            if js_shooters:
                shooters.extend(js_shooters)
            
            # Method 2: Parse HTML tables
            if not shooters:
                table_shooters = self._parse_results_tables(soup)
                if table_shooters:
                    shooters.extend(table_shooters)
            
            # Method 3: Look for JSON in script tags
            if not shooters:
                json_shooters = self._extract_json_shooters(soup)
                if json_shooters:
                    shooters.extend(json_shooters)
            
            if not shooters:
                print(f"    ❌ No shooters found")
                return None
            
            # Filter for IPSC handgun shooters
            handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
            
            if not handgun_shooters:
                print(f"    ⏭️  No IPSC handgun shooters found")
                return None
            
            match_data = {
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
            
            print(f"    ✅ Found {len(handgun_shooters)} IPSC handgun shooters")
            return match_data
            
        except Exception as e:
            print(f"    ❌ Parse error: {str(e)[:50]}...")
            return None
    
    def _extract_js_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from JavaScript variables"""
        
        shooters = []
        
        # Look for common PractiScore JS patterns
        patterns = [
            r'var\s+matchData\s*=\s*(\{.*?\});',
            r'window\.matchData\s*=\s*(\{.*?\});',
            r'match_shooters\s*:\s*(\[.*?\])',
            r'shooters\s*:\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JSON
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    
                    data = json.loads(json_str)
                    
                    if isinstance(data, dict):
                        # Extract shooters from dict
                        shooter_data = data.get('shooters', data.get('match_shooters', []))
                    elif isinstance(data, list):
                        # Direct list of shooters
                        shooter_data = data
                    else:
                        continue
                    
                    for shooter in shooter_data:
                        if isinstance(shooter, dict) and not shooter.get('sh_del', False):
                            formatted = self._format_shooter_data(shooter)
                            if formatted:
                                shooters.append(formatted)
                                
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        
        return shooters
    
    def _parse_results_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse HTML tables for shooter results"""
        
        shooters = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Analyze header row to understand table structure
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            # Look for shooter result tables
            if not any(h in ['name', 'shooter', 'first', 'last', 'place'] for h in headers):
                continue
            
            # Parse data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                shooter = self._parse_table_row(cells, headers)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_table_row(self, cells, headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a table row into shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name (look for text with spaces and letters)
        name = None
        for text in cell_texts:
            if re.match(r'^[A-Za-zÅÄÖåäö\s\-\.\']{3,50}$', text) and ' ' in text and len(text.split()) <= 4:
                name = text
                break
        
        if not name:
            return None
        
        name_parts = name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Find percentage/score
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
                    if 0 <= num <= 150:  # Reasonable percentage range
                        percentage = num
                        break
                except ValueError:
                    continue
        
        # Find division (look for known handgun divisions)
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
    
    def _extract_json_shooters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shooters from JSON in script tags"""
        
        shooters = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            # Look for JSON-like shooter data
            try:
                # Simple heuristic: look for objects with shooter-like fields
                json_matches = re.finditer(r'\{[^{}]*(?:"sh_fn"|"first_name"|"shooters")[^{}]*\}', script.string)
                for match in json_matches:
                    try:
                        data = json.loads(match.group())
                        formatted = self._format_shooter_data(data)
                        if formatted:
                            shooters.append(formatted)
                    except json.JSONDecodeError:
                        continue
                        
            except Exception:
                continue
        
        return shooters
    
    def _format_shooter_data(self, raw_shooter: Dict) -> Optional[Dict[str, Any]]:
        """Format raw shooter data into standard format"""
        
        if not isinstance(raw_shooter, dict):
            return None
        
        # Extract name
        first_name = raw_shooter.get('sh_fn', raw_shooter.get('first_name', ''))
        last_name = raw_shooter.get('sh_ln', raw_shooter.get('last_name', ''))
        
        if not first_name and not last_name:
            return None
        
        # Extract other fields
        division = raw_shooter.get('sh_dvp', raw_shooter.get('division', 'Production Optics'))
        percentage = raw_shooter.get('percentage', raw_shooter.get('match_percentage', 0.0))
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': raw_shooter.get('alias', ''),
            'region': raw_shooter.get('region', 'UNK'),
            'division': division,
            'match_percentage': float(percentage) if percentage else 0.0,
            'placement': raw_shooter.get('placement', 999)
        }
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if shooter is in a handgun division"""
        
        division = shooter.get('division', '').lower()
        
        # Check if it's a handgun division
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        # Exclude non-handgun disciplines
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', '3-gun', 'multigun'}
        if any(excl in division for excl in excluded):
            return False
        
        return True  # Default to include if unclear
    
    def scrape_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match"""
        
        print(f"🎯 Scraping match {match_id}")
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            print(f"  ⏭️  Already exists")
            return None
        
        # Fetch page
        html_content = self.fetch_match_page(match_id)
        if not html_content:
            return None
        
        # Parse data
        match_data = self.parse_match_html(html_content, match_id)
        if not match_data:
            return None
        
        # Save data
        self.save_match_data(match_data)
        return match_data
    
    def save_match_data(self, match_data: Dict[str, Any]):
        """Save match data with timestamp naming"""
        
        match_date = match_data.get('match_date', '')
        timestamp = match_date.split('T')[0] if 'T' in match_date else datetime.now().strftime('%Y-%m-%d')
        match_id = match_data['match_id']
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            
            shooters = len(match_data.get('combined_results', []))
            title = match_data.get('match_title', 'Unknown')[:40]
            print(f"  💾 Saved: {title}... ({shooters} shooters)")
            
        except IOError as e:
            print(f"  ❌ Save error: {e}")
    
    def test_match_range(self, start_id: int, end_id: int) -> int:
        """Test a range of match IDs to find working ones"""
        
        print(f"🧪 Testing match range {start_id}-{end_id}")
        
        successful = 0
        
        for match_id in range(start_id, end_id + 1):
            try:
                match_data = self.scrape_match(str(match_id))
                
                if match_data:
                    successful += 1
                
                # Rate limiting - be respectful
                time.sleep(random.uniform(2, 4))
                
            except KeyboardInterrupt:
                print(f"\n⚠️ Interrupted by user")
                break
            except Exception as e:
                print(f"  ❌ Error with match {match_id}: {str(e)[:30]}...")
                time.sleep(1)
        
        print(f"🏁 Test complete: {successful}/{end_id-start_id+1} matches found")
        return successful

def main():
    """Main scraper function"""
    
    print("🌐 Curl-based PractiScore Scraper")
    print("=" * 50)
    
    scraper = CurlPractiScoreScraper()
    
    # Test recent match IDs to find valid ones
    print("\n🧪 Testing recent matches...")
    
    test_ranges = [
        (299990, 299999),  # Very recent
        (299980, 299989),  # Recent
        (299900, 299909),  # A bit older
    ]
    
    total_found = 0
    
    for start, end in test_ranges:
        print(f"\n--- Testing range {start}-{end} ---")
        found = scraper.test_match_range(start, end)
        total_found += found
        
        if found > 0:
            print(f"✅ Found {found} matches in this range")
        
        # If we found some matches, continue testing
        if total_found >= 10:
            print(f"Found {total_found} matches total, stopping")
            break
        
        print("Pausing 10 seconds before next range...")
        time.sleep(10)
    
    print(f"\n🏁 Scraping complete!")
    print(f"Total matches found: {total_found}")
    
    if total_found > 0:
        print("\n📋 Next steps:")
        print("1. Run 'python process_matches.py' to update rankings")
        print("2. Check new files in match_data/ directory")
    else:
        print("\n❌ No matches found. Try:")
        print("1. Testing different match ID ranges")
        print("2. Manual data entry for key matches")
        print("3. Browser automation approach")

if __name__ == "__main__":
    main()