#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


class PractiScoreClient:
    """Client for fetching and parsing PractiScore match data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
    
    def fetch_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match data from PractiScore by match ID"""
        if not match_id or not match_id.strip():
            print("Error: Match ID cannot be empty")
            return None
        
        # Validate match ID format (should be numeric)
        if not match_id.strip().isdigit():
            print(f"Error: Invalid match ID format '{match_id}'. Expected numeric ID.")
            return None
        
        url = f'https://practiscore.com/results/new/{match_id.strip()}'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if response contains actual content
            if not response.text or len(response.text) < 100:
                print(f"Error: Empty or too short response for match {match_id}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for common error pages
            if self._is_error_page(soup):
                print(f"Error: Match {match_id} not found or access denied")
                return None
            
            match_data = self._parse_match_data(soup, match_id)
            
            # Validate parsed data
            if not self._validate_match_data(match_data):
                print(f"Error: Invalid match data structure for match {match_id}")
                return None
            
            return match_data
            
        except requests.Timeout:
            print(f"Error: Timeout fetching match {match_id}")
            return None
        except requests.RequestException as e:
            print(f"Error fetching match {match_id}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing match {match_id}: {e}")
            return None
    
    def _parse_match_data(self, soup: BeautifulSoup, match_id: str) -> Dict[str, Any]:
        """Parse match data from BeautifulSoup object"""
        
        # Extract match title
        title_element = soup.find('h1') or soup.find('title')
        match_title = title_element.get_text(strip=True) if title_element else f"Match {match_id}"
        
        # Extract match date - look for date in various formats
        match_date = self._extract_match_date(soup)
        
        # Extract match level - look for level indicators
        match_level = self._extract_match_level(soup)
        
        # Extract club name
        club_name = self._extract_club_name(soup)
        
        # Extract shooter results
        shooters = self._extract_shooter_results(soup)
        
        # Build match data in expected format
        match_data = {
            'match_id': int(match_id),
            'match_title': match_title,
            'match_date': match_date,
            'match_level': match_level,
            'club_name': club_name,
            'production_optics_results': shooters,
            'combined_results': shooters  # For compatibility
        }
        
        return match_data
    
    def _extract_match_date(self, soup: BeautifulSoup) -> str:
        """Extract match date from HTML"""
        # Look for date patterns in text
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}.\d{2}.\d{4}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group()
                try:
                    # Try to parse and standardize the date
                    if '-' in date_str:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    elif '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    elif '.' in date_str:
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    else:
                        date_obj = datetime.strptime(date_str, '%B %d, %Y')
                    
                    return date_obj.strftime('%Y-%m-%dT10:00:00')
                except ValueError:
                    continue
        
        # Default to current date if no date found
        return datetime.now().strftime('%Y-%m-%dT10:00:00')
    
    def _extract_match_level(self, soup: BeautifulSoup) -> str:
        """Extract match level from HTML"""
        text = soup.get_text().lower()
        
        if 'level v' in text or 'level 5' in text:
            return 'Level V'
        elif 'level iv' in text or 'level 4' in text:
            return 'Level IV'
        elif 'level iii' in text or 'level 3' in text:
            return 'Level III'
        elif 'level ii' in text or 'level 2' in text:
            return 'Level II'
        else:
            return 'Level II'  # Default
    
    def _extract_club_name(self, soup: BeautifulSoup) -> str:
        """Extract club name from HTML"""
        # Look for common club name patterns
        club_patterns = [
            r'(\w+\s+\w+\s+Gun\s+Club)',
            r'(\w+\s+Shooting\s+Club)',
            r'(\w+\s+Pistol\s+Club)',
            r'(\w+\s+HG)',
            r'(\w+\s+PK)'
        ]
        
        text = soup.get_text()
        for pattern in club_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return 'Unknown'
    
    def _extract_shooter_results(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shooter results from HTML"""
        shooters = []
        
        # Look for tables containing results
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            # Skip if too few rows
            if len(rows) < 2:
                continue
                
            # Try to identify header row
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            # Look for shooter data indicators
            if not any(keyword in ' '.join(headers) for keyword in ['name', 'shooter', 'competitor', 'place', 'rank']):
                continue
            
            # Parse data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # Need at least name and some data
                    continue
                
                shooter_data = self._parse_shooter_row(cells, headers)
                if shooter_data:
                    shooters.append(shooter_data)
        
        # If no shooters found in tables, try alternative parsing
        if not shooters:
            shooters = self._extract_shooters_from_text(soup)
        
        # Calculate match percentages if not already present
        if shooters:
            self._calculate_match_percentages(shooters)
        
        return shooters
    
    def _parse_shooter_row(self, cells: List, headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single shooter row"""
        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Extract name (usually first or second column)
            name = self._extract_name_from_cells(cell_texts)
            if not name:
                return None
            
            first_name, last_name = self._split_name(name)
            
            # Extract score/percentage
            score = self._extract_score_from_cells(cell_texts)
            
            # Extract placement
            placement = self._extract_placement_from_cells(cell_texts)
            
            return {
                'first_name': first_name,
                'last_name': last_name,
                'alias': '',
                'region': 'NOR',  # Default region
                'division': 'Production Optics',
                'match_percentage': score,
                'placement': placement
            }
            
        except Exception as e:
            print(f"Error parsing shooter row: {e}")
            return None
    
    def _extract_name_from_cells(self, cells: List[str]) -> Optional[str]:
        """Extract name from cell data"""
        for cell in cells:
            # Skip numeric cells and short cells
            if cell.isdigit() or len(cell) < 3:
                continue
            
            # Look for name patterns (contains letters and possibly spaces)
            if re.match(r'^[A-Za-z\s\-\.]+$', cell) and ' ' in cell:
                return cell
        
        return None
    
    def _extract_score_from_cells(self, cells: List[str]) -> float:
        """Extract score/percentage from cell data"""
        for cell in cells:
            # Look for percentage patterns
            if '%' in cell:
                try:
                    return float(cell.replace('%', '').strip())
                except ValueError:
                    continue
            
            # Look for decimal numbers that could be scores
            try:
                num = float(cell)
                if 0 <= num <= 100:
                    return num
            except ValueError:
                continue
        
        return 0.0
    
    def _extract_placement_from_cells(self, cells: List[str]) -> int:
        """Extract placement from cell data"""
        for cell in cells:
            try:
                num = int(cell)
                if 1 <= num <= 1000:  # Reasonable placement range
                    return num
            except ValueError:
                continue
        
        return 999  # Default placement
    
    def _split_name(self, full_name: str) -> tuple[str, str]:
        """Split full name into first and last name"""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], ' '.join(parts[1:])
        else:
            return parts[0], 'Unknown'
    
    def _extract_shooters_from_text(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Fallback method to extract shooters from plain text"""
        # This is a simplified fallback - in practice, you'd need more sophisticated parsing
        # Could be implemented to parse text-based results if needed
        _ = soup  # Acknowledge parameter
        return []
    
    def _calculate_match_percentages(self, shooters: List[Dict[str, Any]]):
        """Calculate match percentages based on scores"""
        if not shooters:
            return
        
        # Find the highest score to calculate percentages
        scores = [s.get('match_percentage', 0) for s in shooters]
        max_score = max(scores) if scores else 100
        
        # If scores are already percentages (0-100), use them as-is
        if max_score <= 100:
            return
        
        # Otherwise, calculate percentages
        for shooter in shooters:
            if max_score > 0:
                shooter['match_percentage'] = (shooter.get('match_percentage', 0) / max_score) * 100
    
    def _is_error_page(self, soup: BeautifulSoup) -> bool:
        """Check if the page indicates an error or missing match"""
        text = soup.get_text().lower()
        
        error_indicators = [
            'not found',
            '404',
            'error',
            'access denied',
            'no results',
            'match not available'
        ]
        
        return any(indicator in text for indicator in error_indicators)
    
    def _validate_match_data(self, match_data: Optional[Dict[str, Any]]) -> bool:
        """Validate that match data has required structure and is IPSC handgun"""
        if not match_data:
            return False
        
        # Check if this is an IPSC handgun match
        if not self._is_ipsc_handgun_match(match_data):
            print(f"Skipping non-IPSC handgun match: {match_data.get('match_title', 'Unknown')}")
            return False
        
        required_fields = ['match_id', 'match_title', 'match_date', 'production_optics_results']
        
        for field in required_fields:
            if field not in match_data:
                print(f"Missing required field: {field}")
                return False
        
        # Validate shooters data
        shooters = match_data.get('production_optics_results', [])
        if not isinstance(shooters, list):
            print("production_optics_results must be a list")
            return False
        
        if len(shooters) == 0:
            print("No shooters found in match data")
            return False
        
        # Validate each shooter has required fields
        required_shooter_fields = ['first_name', 'last_name', 'match_percentage']
        for i, shooter in enumerate(shooters):
            if not isinstance(shooter, dict):
                print(f"Shooter {i} is not a dictionary")
                return False
            
            for field in required_shooter_fields:
                if field not in shooter:
                    print(f"Shooter {i} missing required field: {field}")
                    return False
        
        return True
    
    def _is_ipsc_handgun_match(self, match_data: Dict[str, Any]) -> bool:
        """Check if this is an IPSC handgun match (not rifle, shotgun, etc.)"""
        title = match_data.get('match_title', '').lower()
        
        # Check if any shooters have handgun divisions
        shooters = match_data.get('production_optics_results', [])
        if shooters:
            for shooter in shooters[:5]:  # Check first few shooters
                division = shooter.get('division', '').lower()
                
                # IPSC handgun divisions
                handgun_divisions = [
                    'production', 'production optics', 'carry optics',
                    'classic', 'standard', 'open', 'revolver', 'limited',
                    'ipsc handgun', 'handgun'
                ]
                
                if any(hg_div in division for hg_div in handgun_divisions):
                    return True
                
                # Non-handgun divisions to exclude
                non_handgun_divisions = [
                    'rifle', 'shotgun', 'pcc', 'carbine', 'precision',
                    'long range', '3-gun', 'multigun'
                ]
                
                if any(nh_div in division for nh_div in non_handgun_divisions):
                    return False
        
        # Fall back to title analysis
        # Keywords that indicate non-handgun disciplines
        non_handgun_keywords = [
            'rifle', 'gevär', 'gewehr', 'fucile', 'fusil',
            'shotgun', 'hagel', 'schrot', 'fucile a canna liscia',
            'pcc', 'pistol caliber carbine', 'carbine',
            '3-gun', 'three gun', 'multigun', 'multi-gun',
            'two gun', '2-gun', 'twogun',
            'precision rifle', 'long range', 'sniper'
        ]
        
        # If match contains non-handgun keywords, skip it
        if any(keyword in title for keyword in non_handgun_keywords):
            return False
        
        # Keywords that indicate IPSC handgun matches
        handgun_keywords = [
            'ipsc', 'handgun', 'pistol', 'production', 'classic', 
            'standard', 'open', 'revolver', 'limited',
            'production optics', 'carry optics'
        ]
        
        # If match contains handgun keywords, it's likely a handgun match
        if any(keyword in title for keyword in handgun_keywords):
            return True
        
        # Default to true if unclear (many matches don't specify discipline in title)
        return True
    
    def save_match_data(self, match_data: Dict[str, Any], filename: Optional[str] = None):
        """Save match data to JSON file with timestamp and source prefix"""
        if not self._validate_match_data(match_data):
            raise ValueError("Invalid match data structure")
        
        if not filename:
            # Create filename with timestamp prefix and source
            match_date = match_data.get('match_date', '')
            timestamp = self._extract_date_for_filename(match_date)
            match_id = match_data['match_id']
            filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            
            print(f"Match data saved to {filename}")
        except IOError as e:
            print(f"Error saving match data to {filename}: {e}")
            raise
    
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
    """Main function for testing the PractiScore client"""
    client = PractiScoreClient()
    
    # Example usage
    match_id = '287616'
    print(f"Fetching match data for match ID: {match_id}")
    
    match_data = client.fetch_match_data(match_id)
    
    if match_data:
        print(f"Successfully fetched match: {match_data['match_title']}")
        print(f"Date: {match_data['match_date']}")
        print(f"Level: {match_data['match_level']}")
        print(f"Shooters: {len(match_data['production_optics_results'])}")
        
        # Save the data
        client.save_match_data(match_data)
        
        # Print first few shooters
        for i, shooter in enumerate(match_data['production_optics_results'][:5]):
            print(f"{i+1}. {shooter['first_name']} {shooter['last_name']}: {shooter['match_percentage']:.1f}%")
    else:
        print("Failed to fetch match data")


if __name__ == "__main__":
    main()