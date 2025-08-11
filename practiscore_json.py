#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

class PractiScoreJSONClient:
    """Enhanced PractiScore client that can parse JSON data from the page"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
    
    def fetch_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match data from PractiScore"""
        if not match_id or not match_id.strip():
            return None
        
        url = f'https://practiscore.com/results/new/{match_id.strip()}'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if not response.text or len(response.text) < 100:
                return None
            
            # Look for JSON data in the page
            match_json = self._extract_json_data(response.text)
            
            if match_json:
                # Parse the JSON data
                match_data = self._parse_json_match_data(match_json, match_id)
                
                # Validate it's an IPSC handgun match
                if self._is_ipsc_handgun_match(match_data):
                    return match_data
                else:
                    print(f"Skipping non-IPSC handgun match: {match_data.get('match_title', 'Unknown')}")
                    return None
            else:
                print(f"No JSON data found for match {match_id}")
                return None
                
        except Exception as e:
            print(f"Error fetching match {match_id}: {e}")
            return None
    
    def _extract_json_data(self, html_content: str) -> Optional[Dict]:
        """Extract JSON match data from HTML page"""
        
        # Look for common patterns where PractiScore embeds JSON data
        patterns = [
            r'matchDef\s*=\s*({.*?});',  # matchDef = {...};
            r'var\s+matchData\s*=\s*({.*?});',  # var matchData = {...};
            r'window\.matchData\s*=\s*({.*?});',  # window.matchData = {...};
            r'"match_data":\s*({.*?})',  # "match_data": {...}
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up the JSON string
                    json_str = self._clean_json_string(json_str)
                    match_json = json.loads(json_str)
                    
                    # Check if this looks like valid match data
                    if self._is_valid_match_json(match_json):
                        return match_json
                        
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean up JSON string extracted from HTML"""
        # Remove trailing commas, fix common issues
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas before }
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas before ]
        return json_str
    
    def _is_valid_match_json(self, data: Dict) -> bool:
        """Check if JSON data looks like valid match data"""
        required_fields = ['match_shooters', 'match_name']
        return all(field in data for field in required_fields)
    
    def _parse_json_match_data(self, match_json: Dict, match_id: str) -> Dict[str, Any]:
        """Parse JSON match data into our standard format"""
        
        # Extract basic match info
        match_title = match_json.get('match_name', f'Match {match_id}')
        match_date = self._parse_match_date(match_json.get('match_date', ''))
        match_level = self._determine_match_level(match_json)
        
        # Extract shooters
        shooters = []
        for shooter in match_json.get('match_shooters', []):
            if shooter.get('sh_del', False):  # Skip deleted shooters
                continue
                
            shooter_data = {
                'first_name': shooter.get('sh_fn', ''),
                'last_name': shooter.get('sh_ln', ''),
                'alias': '',
                'region': 'UNK',  # We'll need to determine region somehow
                'division': shooter.get('sh_dvp', 'Production Optics'),
                'match_percentage': 0.0,  # Will need to calculate from scores
                'placement': 0  # Will need to calculate
            }
            shooters.append(shooter_data)
        
        # Build match data in our expected format
        match_data = {
            'match_id': int(match_id),
            'match_title': match_title,
            'match_date': match_date,
            'match_level': match_level,
            'club_name': match_json.get('match_clubcode', 'Unknown'),
            'production_optics_results': shooters,
            'combined_results': shooters
        }
        
        return match_data
    
    def _parse_match_date(self, date_str: str) -> str:
        """Parse match date into ISO format"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%dT10:00:00')
        
        try:
            # Handle YYYY-MM-DD format
            if '-' in date_str and len(date_str) >= 10:
                date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%dT10:00:00')
        except ValueError:
            pass
        
        return datetime.now().strftime('%Y-%m-%dT10:00:00')
    
    def _determine_match_level(self, match_json: Dict) -> str:
        """Determine match level from JSON data"""
        # Default to Level II for most matches
        return 'Level II'
    
    def _is_ipsc_handgun_match(self, match_data: Dict[str, Any]) -> bool:
        """Check if this is an IPSC handgun match"""
        
        # Check divisions in the match
        shooters = match_data.get('production_optics_results', [])
        if not shooters:
            return False
        
        handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp'  # Common IPSC handgun divisions
        }
        
        # Check if any shooters have handgun divisions
        for shooter in shooters[:10]:  # Check first 10 shooters
            division = shooter.get('division', '').lower()
            if any(hg_div in division for hg_div in handgun_divisions):
                return True
        
        # Check match title
        title = match_data.get('match_title', '').lower()
        non_handgun_keywords = ['rifle', 'shotgun', '3-gun', 'multigun', 'pcc']
        
        if any(keyword in title for keyword in non_handgun_keywords):
            return False
        
        return True
    
    def save_match_data(self, match_data: Dict[str, Any], filename: Optional[str] = None):
        """Save match data to JSON file with timestamp and source prefix"""
        if not filename:
            # Create filename with timestamp prefix and source
            match_date = match_data.get('match_date', '')
            timestamp = self._extract_date_for_filename(match_date)
            match_id = match_data['match_id']
            filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            
            print(f"Match data saved to {filename}")
        except IOError as e:
            print(f"Error saving match data: {e}")
    
    def _extract_date_for_filename(self, match_date: str) -> str:
        """Extract date from match_date for filename prefix (YYYY-MM-DD format)"""
        try:
            if 'T' in match_date:
                # ISO format: 2024-07-08T10:00:00
                return match_date.split('T')[0]
            elif '-' in match_date and len(match_date) >= 10:
                # Already in YYYY-MM-DD format
                return match_date[:10]
        except:
            pass
        
        # Default to current date if parsing fails
        return datetime.now().strftime('%Y-%m-%d')

def main():
    """Test the JSON client"""
    client = PractiScoreJSONClient()
    
    # Test with a recent match ID
    test_id = '299999'
    print(f"Testing JSON extraction for match {test_id}")
    
    match_data = client.fetch_match_data(test_id)
    
    if match_data:
        print(f"Success! Found: {match_data['match_title']}")
        print(f"Shooters: {len(match_data['production_optics_results'])}")
        client.save_match_data(match_data)
    else:
        print("No data found")

if __name__ == "__main__":
    main()