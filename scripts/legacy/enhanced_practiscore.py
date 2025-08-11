#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Enhanced PractiScore client with improved anti-blocking measures
"""

import requests
import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import urllib3

# Disable SSL warnings for now
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EnhancedPractiScoreClient:
    """Enhanced PractiScore client with anti-blocking measures"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Rotate through different user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        ]
        
        self.setup_session()
    
    def setup_session(self):
        """Setup session with anti-blocking headers"""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        
        # Add some randomization
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    def get_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Get URL with retry logic and anti-blocking measures"""
        
        for attempt in range(max_retries):
            try:
                # Random delay between requests
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    print(f"    Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                
                # Rotate user agent
                self.session.headers['User-Agent'] = random.choice(self.user_agents)
                
                # Make request
                response = self.session.get(url, timeout=30, verify=False)
                
                # Check if we got blocked
                if response.status_code == 403:
                    print(f"    403 Forbidden (attempt {attempt + 1})")
                    continue
                elif response.status_code == 503:
                    print(f"    503 Service Unavailable (attempt {attempt + 1})")
                    continue
                elif 'cloudflare' in response.text.lower() and 'blocked' in response.text.lower():
                    print(f"    Cloudflare block detected (attempt {attempt + 1})")
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                print(f"    Request error (attempt {attempt + 1}): {str(e)[:50]}...")
                continue
        
        return None
    
    def fetch_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match data from PractiScore with enhanced anti-blocking"""
        if not match_id or not match_id.strip().isdigit():
            return None
        
        url = f'https://practiscore.com/results/new/{match_id.strip()}'
        
        response = self.get_with_retry(url)
        if not response:
            return None
        
        # Try multiple parsing approaches
        match_data = None
        
        # Approach 1: Look for embedded JSON data
        match_data = self._extract_json_from_html(response.text, match_id)
        
        # Approach 2: Try API-style endpoints
        if not match_data:
            match_data = self._try_api_endpoints(match_id)
        
        # Approach 3: Parse HTML tables as fallback
        if not match_data:
            match_data = self._parse_html_tables(response.text, match_id)
        
        if match_data and self._is_ipsc_handgun_match(match_data):
            return match_data
        
        return None
    
    def _extract_json_from_html(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from HTML content"""
        
        # Look for various JavaScript patterns
        patterns = [
            r'matchDef\s*=\s*({.*?});',
            r'var\s+matchData\s*=\s*({.*?});',
            r'window\.matchData\s*=\s*({.*?});',
            r'window\.match\s*=\s*({.*?});',
            r'"match_data":\s*({.*?})',
            r'match_info\s*=\s*({.*?});',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up the JSON
                    json_str = self._clean_json_string(json_str)
                    match_json = json.loads(json_str)
                    
                    if self._is_valid_match_json(match_json):
                        return self._parse_json_match_data(match_json, match_id)
                        
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _try_api_endpoints(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Try different API-style endpoints"""
        
        api_urls = [
            f'https://practiscore.com/api/matches/{match_id}',
            f'https://practiscore.com/api/results/{match_id}',
            f'https://practiscore.com/results/{match_id}.json',
            f'https://practiscore.com/results/data/{match_id}',
        ]
        
        for url in api_urls:
            try:
                response = self.get_with_retry(url)
                if response and response.headers.get('content-type', '').startswith('application/json'):
                    match_json = response.json()
                    if self._is_valid_match_json(match_json):
                        return self._parse_json_match_data(match_json, match_id)
            except:
                continue
        
        return None
    
    def _parse_html_tables(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Parse HTML tables as fallback method"""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic match info
            title_elem = soup.find('h1') or soup.find('title')
            match_title = title_elem.get_text(strip=True) if title_elem else f"Match {match_id}"
            
            # Look for results tables
            tables = soup.find_all('table')
            shooters = []
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # Parse table data
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue
                    
                    # Try to extract shooter data
                    shooter = self._parse_table_row(cells)
                    if shooter:
                        shooters.append(shooter)
            
            if shooters:
                return {
                    'match_id': int(match_id),
                    'match_title': match_title,
                    'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                    'match_level': 'Level II',
                    'club_name': 'Unknown',
                    'production_optics_results': shooters,
                    'combined_results': shooters
                }
        
        except Exception:
            pass
        
        return None
    
    def _parse_table_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse a table row into shooter data"""
        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for name (usually contains spaces and letters)
            name = None
            for text in cell_texts:
                if re.match(r'^[A-Za-z\s\-\.]{3,}$', text) and ' ' in text:
                    name = text
                    break
            
            if not name:
                return None
            
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            # Look for percentage or score
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
                        if 0 <= num <= 100:
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
            
        except Exception:
            return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean up JSON string"""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json_str
    
    def _is_valid_match_json(self, data: Dict) -> bool:
        """Check if JSON data looks like valid match data"""
        return isinstance(data, dict) and (
            'match_shooters' in data or 
            'shooters' in data or 
            'results' in data
        )
    
    def _parse_json_match_data(self, match_json: Dict, match_id: str) -> Dict[str, Any]:
        """Parse JSON match data into standard format"""
        
        # Extract basic info
        match_title = match_json.get('match_name', f'Match {match_id}')
        match_date = self._parse_match_date(match_json.get('match_date', ''))
        
        # Extract shooters from various possible fields
        shooters = []
        shooter_data = (match_json.get('match_shooters', []) or 
                       match_json.get('shooters', []) or 
                       match_json.get('results', []))
        
        for shooter in shooter_data:
            if isinstance(shooter, dict) and not shooter.get('sh_del', False):
                shooter_data = {
                    'first_name': shooter.get('sh_fn', shooter.get('first_name', '')),
                    'last_name': shooter.get('sh_ln', shooter.get('last_name', '')),
                    'alias': shooter.get('alias', ''),
                    'region': shooter.get('region', 'UNK'),
                    'division': shooter.get('sh_dvp', shooter.get('division', 'Production Optics')),
                    'match_percentage': shooter.get('percentage', 0.0),
                    'placement': shooter.get('placement', 999)
                }
                shooters.append(shooter_data)
        
        return {
            'match_id': int(match_id),
            'match_title': match_title,
            'match_date': match_date,
            'match_level': 'Level II',
            'club_name': match_json.get('club_name', 'Unknown'),
            'production_optics_results': shooters,
            'combined_results': shooters
        }
    
    def _parse_match_date(self, date_str: str) -> str:
        """Parse match date"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%dT10:00:00')
        
        try:
            if '-' in date_str and len(date_str) >= 10:
                date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%dT10:00:00')
        except ValueError:
            pass
        
        return datetime.now().strftime('%Y-%m-%dT10:00:00')
    
    def _is_ipsc_handgun_match(self, match_data: Dict[str, Any]) -> bool:
        """Check if this is an IPSC handgun match"""
        
        # Check divisions
        shooters = match_data.get('production_optics_results', [])
        if not shooters:
            return False
        
        handgun_divisions = {
            'production', 'production optics', 'carry optics',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp'
        }
        
        for shooter in shooters[:5]:
            division = shooter.get('division', '').lower()
            if any(hg_div in division for hg_div in handgun_divisions):
                return True
        
        return len(shooters) > 0  # If we have shooters, assume it's handgun
    
    def save_match_data(self, match_data: Dict[str, Any], filename: Optional[str] = None):
        """Save match data with timestamp naming"""
        if not filename:
            match_date = match_data.get('match_date', '')
            timestamp = self._extract_date_for_filename(match_date)
            match_id = match_data['match_id']
            filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved: {filename}")
        except IOError as e:
            print(f"✗ Save error: {e}")
    
    def _extract_date_for_filename(self, match_date: str) -> str:
        """Extract date for filename"""
        try:
            if 'T' in match_date:
                return match_date.split('T')[0]
            elif '-' in match_date and len(match_date) >= 10:
                return match_date[:10]
        except:
            pass
        
        return datetime.now().strftime('%Y-%m-%d')

def main():
    """Test the enhanced client"""
    client = EnhancedPractiScoreClient()
    
    # Test with a few match IDs
    test_ids = ['299990', '299995', '299999']
    
    for match_id in test_ids:
        print(f"\n🔍 Testing match {match_id}...")
        
        match_data = client.fetch_match_data(match_id)
        
        if match_data:
            print(f"  ✓ Success: {match_data['match_title']}")
            print(f"    Shooters: {len(match_data['production_optics_results'])}")
            client.save_match_data(match_data)
        else:
            print(f"  ✗ Failed to fetch match {match_id}")
        
        time.sleep(2)  # Rate limiting

if __name__ == "__main__":
    main()