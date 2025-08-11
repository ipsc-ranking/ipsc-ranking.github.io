#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.selenium python3Packages.beautifulsoup4 firefox geckodriver

"""
Selenium-based PractiScore scraper to bypass Cloudflare protection
"""

import json
import time
import random
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import re

class SeleniumPractiScoreScraper:
    """Selenium-based scraper to bypass Cloudflare protection"""
    
    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        
        # IPSC Handgun divisions
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Firefox driver with realistic browser profile"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Make browser look more realistic
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0')
        
        # Set realistic viewport
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Firefox(options=options)
            
            # Execute script to hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Firefox driver initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Firefox driver: {e}")
            print("Make sure Firefox and geckodriver are installed:")
            print("  - Firefox: included in most Linux distributions")
            print("  - geckodriver: should be available via nix-shell")
            return False
    
    def wait_for_cloudflare(self, timeout: int = 30) -> bool:
        """Wait for Cloudflare challenge to complete"""
        print("🔄 Waiting for Cloudflare challenge...")
        
        try:
            # Wait for either success or failure
            WebDriverWait(self.driver, timeout).until(
                lambda driver: (
                    "cloudflare" not in driver.page_source.lower() or
                    "blocked" not in driver.page_source.lower() or
                    "practiscore" in driver.title.lower()
                )
            )
            
            # Check if we successfully bypassed
            if "sorry, you have been blocked" in self.driver.page_source.lower():
                print("❌ Still blocked by Cloudflare")
                return False
            elif "practiscore" in self.driver.page_source.lower():
                print("✅ Successfully bypassed Cloudflare")
                return True
            
            return True
            
        except TimeoutException:
            print("⏰ Cloudflare challenge timeout")
            return False
    
    def fetch_match_page(self, match_id: str, max_retries: int = 3) -> Optional[str]:
        """Fetch match page using Selenium"""
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        for attempt in range(max_retries):
            try:
                print(f"🌐 Loading {url} (attempt {attempt + 1}/{max_retries})")
                
                # Navigate to page
                self.driver.get(url)
                
                # Random delay to appear more human
                time.sleep(random.uniform(2, 4))
                
                # Check for Cloudflare challenge
                if "cloudflare" in self.driver.page_source.lower():
                    if not self.wait_for_cloudflare():
                        if attempt < max_retries - 1:
                            print(f"Retrying in {(attempt + 1) * 5} seconds...")
                            time.sleep((attempt + 1) * 5)
                            continue
                        else:
                            return None
                
                # Wait for page to load completely
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                # Additional wait for dynamic content
                time.sleep(2)
                
                return self.driver.page_source
                
            except Exception as e:
                print(f"❌ Error loading page (attempt {attempt + 1}): {str(e)[:50]}...")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
        
        return None
    
    def parse_match_html(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Parse match HTML content to extract data"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract match title
            title_elem = soup.find('h1') or soup.find('title') or soup.find('h2')
            match_title = "Unknown Match"
            
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and "cloudflare" not in title_text.lower():
                    match_title = title_text
            
            # Look for results data in various formats
            match_data = None
            
            # Method 1: Look for JavaScript data
            match_data = self._extract_js_data(html_content, match_id)
            
            # Method 2: Parse HTML tables
            if not match_data:
                match_data = self._parse_results_tables(soup, match_id)
            
            # Method 3: Look for JSON data in script tags
            if not match_data:
                match_data = self._extract_json_from_scripts(soup, match_id)
            
            if match_data:
                match_data['match_title'] = match_title
                return match_data
            
        except Exception as e:
            print(f"❌ Error parsing HTML: {str(e)[:50]}...")
        
        return None
    
    def _extract_js_data(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Extract data from JavaScript variables"""
        
        # Look for common PractiScore JavaScript patterns
        patterns = [
            r'var\s+matchData\s*=\s*(\{.*?\});',
            r'window\.matchData\s*=\s*(\{.*?\});',
            r'matchDef\s*=\s*(\{.*?\});',
            r'match_data\s*:\s*(\{.*?\})',
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
                    if self._validate_match_data(data):
                        return self._format_match_data(data, match_id)
                        
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return None
    
    def _parse_results_tables(self, soup: BeautifulSoup, match_id: str) -> Optional[Dict[str, Any]]:
        """Parse HTML tables for results"""
        
        tables = soup.find_all('table')
        shooters = []
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Try to identify results table
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            # Look for shooter-like columns
            if not any(header in ['name', 'shooter', 'first', 'last'] for header in headers):
                continue
            
            # Parse data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                shooter = self._parse_shooter_row(cells, headers)
                if shooter:
                    shooters.append(shooter)
        
        if shooters:
            return {
                'match_id': int(match_id),
                'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                'match_level': 'Level II',
                'club_name': 'Unknown',
                'combined_results': shooters,
                'production_optics_results': [s for s in shooters if 'production optics' in s.get('division', '').lower()]
            }
        
        return None
    
    def _parse_shooter_row(self, cells, headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a table row into shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name
        name = None
        for text in cell_texts:
            if re.match(r'^[A-Za-zÅÄÖåäö\s\-\.]{3,}$', text) and ' ' in text:
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
                    percentage = float(text.replace('%', ''))
                    break
                except ValueError:
                    continue
            elif re.match(r'^\d+\.?\d*$', text):
                try:
                    num = float(text)
                    if 0 <= num <= 150:  # Reasonable percentage range
                        percentage = num
                        break
                except ValueError:
                    continue
        
        # Find division
        division = 'Production Optics'
        for text in cell_texts:
            text_lower = text.lower()
            if any(div in text_lower for div in self.handgun_divisions):
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
    
    def _extract_json_from_scripts(self, soup: BeautifulSoup, match_id: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from script tags"""
        
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            # Look for JSON-like data
            try:
                # Simple heuristic: look for objects with shooter data
                if 'shooters' in script.string or 'results' in script.string:
                    # Try to extract JSON objects
                    json_matches = re.finditer(r'\{[^{}]*(?:"shooters"|"results")[^{}]*\}', script.string)
                    for match in json_matches:
                        try:
                            data = json.loads(match.group())
                            if self._validate_match_data(data):
                                return self._format_match_data(data, match_id)
                        except json.JSONDecodeError:
                            continue
                            
            except Exception:
                continue
        
        return None
    
    def _validate_match_data(self, data: Dict) -> bool:
        """Validate that data looks like match data"""
        
        return (isinstance(data, dict) and 
                ('shooters' in data or 'results' in data or 'match_shooters' in data) and
                len(str(data)) > 100)  # Must have substantial content
    
    def _format_match_data(self, raw_data: Dict, match_id: str) -> Dict[str, Any]:
        """Format raw data into standard match format"""
        
        shooters = []
        
        # Extract shooters from various possible keys
        shooter_data = (raw_data.get('shooters', []) or 
                       raw_data.get('results', []) or 
                       raw_data.get('match_shooters', []))
        
        for shooter in shooter_data:
            if isinstance(shooter, dict):
                formatted_shooter = {
                    'first_name': shooter.get('first_name', shooter.get('sh_fn', '')),
                    'last_name': shooter.get('last_name', shooter.get('sh_ln', '')),
                    'alias': shooter.get('alias', ''),
                    'region': shooter.get('region', 'UNK'),
                    'division': shooter.get('division', shooter.get('sh_dvp', 'Production Optics')),
                    'match_percentage': shooter.get('percentage', shooter.get('match_percentage', 0.0)),
                    'placement': shooter.get('placement', 999)
                }
                shooters.append(formatted_shooter)
        
        return {
            'match_id': int(match_id),
            'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
            'match_level': raw_data.get('match_level', 'Level II'),
            'club_name': raw_data.get('club_name', 'Unknown'),
            'combined_results': shooters,
            'production_optics_results': [s for s in shooters if 'production optics' in s.get('division', '').lower()]
        }
    
    def scrape_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match"""
        
        print(f"🎯 Scraping match {match_id}...")
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            print(f"  ⏭️  Already exists: {filename}")
            return None
        
        # Fetch page
        html_content = self.fetch_match_page(match_id)
        if not html_content:
            print(f"  ❌ Failed to fetch page")
            return None
        
        # Parse data
        match_data = self.parse_match_html(html_content, match_id)
        if not match_data:
            print(f"  ❌ No valid data found")
            return None
        
        # Check if IPSC handgun match
        if not self._is_ipsc_handgun_match(match_data):
            print(f"  ⏭️  Not an IPSC handgun match")
            return None
        
        # Save data
        self.save_match_data(match_data)
        
        shooters = len(match_data.get('combined_results', []))
        title = match_data.get('match_title', 'Unknown')[:40]
        print(f"  ✅ Success: {title}... ({shooters} shooters)")
        
        return match_data
    
    def _is_ipsc_handgun_match(self, match_data: Dict[str, Any]) -> bool:
        """Check if this is an IPSC handgun match"""
        
        shooters = match_data.get('combined_results', [])
        if not shooters:
            return False
        
        # Check first few shooters for handgun divisions
        for shooter in shooters[:5]:
            division = shooter.get('division', '').lower()
            if any(hg_div in division for hg_div in self.handgun_divisions):
                return True
        
        return len(shooters) > 0  # If we have shooters, assume handgun
    
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
            print(f"    💾 Saved: {filename}")
        except IOError as e:
            print(f"    ❌ Save error: {e}")
    
    def scrape_range(self, start_id: int, end_id: int, max_matches: int = 50) -> int:
        """Scrape a range of matches"""
        
        print(f"🚀 Scraping matches {start_id}-{end_id} (max {max_matches})")
        
        successful = 0
        total_checked = 0
        
        for match_id in range(start_id, end_id + 1):
            total_checked += 1
            
            if total_checked % 10 == 0:
                print(f"  📊 Progress: {total_checked}/{end_id-start_id+1}, found: {successful}")
            
            try:
                match_data = self.scrape_match(str(match_id))
                
                if match_data:
                    successful += 1
                    
                    if successful >= max_matches:
                        print(f"  🏁 Reached {max_matches} matches, stopping")
                        break
                
                # Rate limiting - be respectful
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"  ❌ Error with match {match_id}: {str(e)[:30]}...")
                time.sleep(2)
        
        print(f"🏁 Range complete: {successful}/{total_checked} matches found")
        return successful
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser closed")

def main():
    """Main scraping function"""
    
    print("🤖 Selenium PractiScore Scraper")
    print("=" * 50)
    
    scraper = None
    
    try:
        # Initialize scraper (headless=False for debugging)
        scraper = SeleniumPractiScoreScraper(headless=True)
        
        if not scraper.driver:
            print("❌ Failed to initialize browser driver")
            return
        
        # Test with a few matches first
        print("\n🧪 Testing individual matches...")
        test_matches = ['299990', '299995', '299999']
        
        test_successful = 0
        for match_id in test_matches:
            match_data = scraper.scrape_match(match_id)
            if match_data:
                test_successful += 1
            time.sleep(5)  # Be extra respectful during testing
        
        if test_successful > 0:
            print(f"\n✅ Testing successful! Found {test_successful} matches")
            print("🚀 Starting bulk scraping...")
            
            # Scrape recent ranges
            total_found = scraper.scrape_range(299950, 299999, max_matches=20)
            
            print(f"\n🏁 Scraping complete!")
            print(f"Total matches found: {total_found}")
            
            if total_found > 0:
                print("\n📋 Next steps:")
                print("1. Run 'python process_matches.py' to update rankings")
                print("2. Check new files in match_data/ directory")
            
        else:
            print(f"\n❌ Testing failed - all matches blocked or inaccessible")
            print("Consider:")
            print("1. Running with headless=False to see what's happening")
            print("2. Manual data entry for key matches")
            print("3. Requesting API access from PractiScore")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()