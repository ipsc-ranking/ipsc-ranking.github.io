#!/usr/bin/env python3
"""
Practiscore data iterator module.

This module provides iterators for Practiscore match data, both for live data fetching
and for iterating over existing JSON files.
"""

import json
import os
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
from .base import MatchDataIterator
import requests
from bs4 import BeautifulSoup
import re


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
            'combined_results': shooters
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
        
        required_fields = ['match_id', 'match_title', 'match_date', 'combined_results']
        
        for field in required_fields:
            if field not in match_data:
                print(f"Missing required field: {field}")
                return False
        
        # Validate shooters data
        shooters = match_data.get('combined_results', [])
        if not isinstance(shooters, list):
            print("combined_results must be a list")
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
        shooters = match_data.get('combined_results', [])
        if shooters:
            for shooter in shooters[:5]:  # Check first few shooters
                division = shooter.get('division', '').lower()
                
                # IPSC handgun divisions (including PCC which uses handgun calibers)
                handgun_divisions = [
                    'production', 'production optics', 'carry optics',
                    'classic', 'standard', 'open', 'revolver', 'limited',
                    'ipsc handgun', 'handgun', 'pcc', 'pistol caliber carbine'
                ]
                
                if any(hg_div in division for hg_div in handgun_divisions):
                    return True
                
                # Non-handgun divisions to exclude
                non_handgun_divisions = [
                    'rifle', 'shotgun', 'precision',
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


class PractiscoreLiveIterator(MatchDataIterator):
    """Iterator for fetching live Practiscore match data"""
    
    def __init__(self, match_ids: List[str], client: Optional[PractiScoreClient] = None):
        """
        Initialize Practiscore live data iterator
        
        Args:
            match_ids: List of Practiscore match IDs to fetch
            client: Optional PractiScoreClient instance (will create one if not provided)
        """
        self.match_ids = match_ids
        self.client = client or PractiScoreClient()
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Practiscore matches by fetching live data"""
        for match_id in self.match_ids:
            try:
                match_data = self.client.fetch_match_data(str(match_id))
                
                if not match_data:
                    continue
                
                # Add source information
                match_data['source'] = self.get_source_name()
                
                # Normalize and yield the match data
                yield self.normalize_match_data(match_data)
                
            except Exception as e:
                print(f"Error fetching Practiscore match {match_id}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the Practiscore source name"""
        return 'practiscore'


class PractiscoreFileIterator(MatchDataIterator):
    """Iterator for Practiscore match data stored in JSON files"""
    
    def __init__(self, match_data_dir: str = './match_data/', filter_levels: Optional[List[int]] = None):
        """
        Initialize Practiscore file iterator
        
        Args:
            match_data_dir: Directory containing Practiscore match JSON files
            filter_levels: List of match levels to include
        """
        self.match_data_dir = match_data_dir
        self.filter_levels = filter_levels
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Practiscore match files"""
        if not os.path.exists(self.match_data_dir):
            return
        
        # Get all Practiscore match files (files with '_practiscore_' in name)
        practiscore_files = []
        for filename in os.listdir(self.match_data_dir):
            if filename.endswith('.json') and '_practiscore_' in filename:
                practiscore_files.append(filename)
        
        # Process each file
        for filename in practiscore_files:
            filepath = os.path.join(self.match_data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                
                # Skip if no combined results
                if 'combined_results' not in match_data or not match_data['combined_results']:
                    continue
                
                # Filter by match level if specified
                match_level = match_data.get('match_level')
                if self.filter_levels and match_level not in self.filter_levels:
                    continue
                
                # Add source information if not present
                if 'source' not in match_data:
                    match_data['source'] = self.get_source_name()
                
                # Normalize and yield the match data
                yield self.normalize_match_data(match_data)
                
            except Exception as e:
                print(f"Error loading Practiscore file {filename}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the Practiscore source name"""
        return 'practiscore'


class PractiscoreRangeIterator(MatchDataIterator):
    """Iterator for fetching Practiscore matches in a range"""
    
    def __init__(self, start_match_id: int, end_match_id: int, 
                 client: Optional[PractiScoreClient] = None,
                 filter_levels: Optional[List[int]] = None):
        """
        Initialize Practiscore range iterator
        
        Args:
            start_match_id: Starting Practiscore match ID
            end_match_id: Ending Practiscore match ID
            client: Optional PractiScoreClient instance
            filter_levels: List of match levels to include
        """
        self.start_match_id = start_match_id
        self.end_match_id = end_match_id
        self.client = client or PractiScoreClient()
        self.filter_levels = filter_levels
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Practiscore match ID range"""
        for match_id in range(self.start_match_id, self.end_match_id + 1):
            try:
                match_data = self.client.fetch_match_data(str(match_id))
                
                if not match_data:
                    continue
                
                # Filter by match level if specified
                match_level = match_data.get('match_level')
                if self.filter_levels and match_level not in self.filter_levels:
                    continue
                
                # Add source information
                match_data['source'] = self.get_source_name()
                
                # Normalize and yield the match data
                yield self.normalize_match_data(match_data)
                
            except Exception as e:
                print(f"Error fetching Practiscore match {match_id}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the Practiscore source name"""
        return 'practiscore'


class PractiscoreMatchFetcher:
    """Utility class for fetching individual Practiscore matches"""
    
    def __init__(self, client: Optional[PractiScoreClient] = None):
        """Initialize with optional client"""
        self.client = client or PractiScoreClient()
    
    def fetch_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single Practiscore match by ID
        
        Args:
            match_id: Practiscore match ID to fetch
            
        Returns:
            Match data dictionary or None if not found/error
        """
        try:
            match_data = self.client.fetch_match_data(match_id)
            if match_data:
                match_data['source'] = 'practiscore'
                return match_data
            return None
        except Exception as e:
            print(f"Error fetching Practiscore match {match_id}: {e}")
            return None
    
    def fetch_multiple_matches(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple Practiscore matches by IDs
        
        Args:
            match_ids: List of Practiscore match IDs to fetch
            
        Returns:
            List of match data dictionaries (excludes failed fetches)
        """
        matches = []
        for match_id in match_ids:
            match_data = self.fetch_match(match_id)
            if match_data:
                matches.append(match_data)
        return matches
    
    def search_matches_by_date_range(self, start_date: datetime, end_date: datetime,
                                   match_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Practiscore matches within a date range
        
        Args:
            start_date: Start date for search
            end_date: End date for search
            match_ids: List of match IDs to search within
            
        Returns:
            List of matching match data dictionaries
        """
        matches = []
        
        for match_id in match_ids:
            try:
                match_data = self.fetch_match(match_id)
                if not match_data:
                    continue
                
                match_date_str = match_data.get('match_date')
                if not match_date_str:
                    continue
                
                try:
                    match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    if start_date <= match_date <= end_date:
                        matches.append(match_data)
                except (ValueError, TypeError):
                    continue
                    
            except Exception as e:
                print(f"Error searching Practiscore match {match_id}: {e}")
                continue
        
        return matches


def create_practiscore_iterator_from_known_ids(known_ids_file: str = 'known_practiscore_ids.txt') -> PractiscoreLiveIterator:
    """
    Create a Practiscore iterator from a file containing known match IDs
    
    Args:
        known_ids_file: Path to file containing Practiscore match IDs (one per line)
        
    Returns:
        PractiscoreLiveIterator instance
    """
    match_ids = []
    
    if os.path.exists(known_ids_file):
        try:
            with open(known_ids_file, 'r') as f:
                for line in f:
                    match_id = line.strip()
                    if match_id and match_id.isdigit():
                        match_ids.append(match_id)
        except Exception as e:
            print(f"Error reading known IDs file {known_ids_file}: {e}")
    
    return PractiscoreLiveIterator(match_ids)