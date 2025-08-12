#!/usr/bin/env python3
"""
SSI (Shoot'n Score It) data iterator module.

This module provides iterators for SSI match data, both for live data fetching
and for iterating over existing JSON files.
"""

import json
import os
import requests
from bs4 import BeautifulSoup
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
import re
from dateutil import parser
from .base import MatchDataIterator


def parse_date_string(date_text):
    """Parse date string with special handling for noon/midnight"""
    if not date_text:
        return None
        
    try:
        # Handle special cases
        date_text_clean = date_text.strip()
        
        # Replace noon and midnight with times
        if ', noon' in date_text_clean:
            date_text_clean = date_text_clean.replace(', noon', ' 12:00 PM')
        elif ', midnight' in date_text_clean:
            date_text_clean = date_text_clean.replace(', midnight', ' 12:00 AM')
        
        # Parse the cleaned date string
        parsed_date = parser.parse(date_text_clean)
        return parsed_date.isoformat()
    except Exception as e:
        print(f"Error parsing date '{date_text}': {e}")
        return None


def parse_results(soup):
    """Parse the Production Optics results from the HTML"""
    results = []
    
    # Find the results table
    table = soup.find('table', id='sortTable')
    if not table:
        return results
    
    # Find all result rows (skip header)
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 11:  # Ensure we have all expected columns
            # Parse category abbreviation
            category =  cells[6].get_text(strip=True)
            if category == 'None':
                category = []
            else:
                category = [c.strip() for c in category.split(' ')]
            
            result = {
                'position': int(cells[0].get_text(strip=True)),
                'match_percentage': float(cells[1].get_text(strip=True)),
                'match_points': float(cells[2].get_text(strip=True)),
                'first_name': cells[3].get_text(strip=True),
                'last_name': cells[4].get_text(strip=True),
                'division': cells[5].get_text(strip=True),
                'category': category,
                'region': cells[7].get_text(strip=True),
                'classification': cells[8].get_text(strip=True),
                'alias': cells[9].get_text(strip=True),
                'club': cells[10].get_text(strip=True)
            }
            results.append(result)
    
    return results


def is_handgun_match(divisions):
    """Check if match contains handgun divisions (not shotgun/rifle)"""
    for division in divisions:
        url = division.get('url', '')
        # Check if URL contains handgun division indicators (including PCC)
        if '/div/hg' in url or '/div/iop' in url or '/div/ist' in url:
            return True
        # Check division name for PCC indicators
        name = division.get('name', '').lower()
        if 'pistol caliber carbine' in name or 'pcc' in name:
            return True
        # Exclude shotgun (sg) and rifle (rf) divisions
        if '/div/sg' in url or '/div/rf' in url:
            continue
    return False


def get_match_info(match_id):
    """Get match information from SSI"""
    url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/selection/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    match_info = {
        'match_id': match_id,
        'divisions': [],
        'match_url': None,
        'match_title': None,
        'match_level': None
    }

    has_production_optics = False
    
    # Find the first ssi-table that contains the divisions and return URL
    first_table = soup.find('div', class_='ssi-table')
    if first_table:
        # Get the match title from the title row
        title_row = first_table.find('div', class_='ssi-title-row')
        if title_row:
            # Extract title text (excluding the "return" button text)
            title_text = title_row.get_text(strip=True)
            if title_text.endswith('return'):
                title_text = title_text[:-6].strip()  # Remove "return" from the end
            match_info['match_title'] = title_text
            
            # Find the return URL button
            return_btn = title_row.find('a', class_='btn btn-primary')
            if return_btn:
                match_info['match_url'] = return_btn.get('href')
        
        # Find all division links in the items-spaced-8px div
        items_div = first_table.find('div', class_='items-spaced-8px')
        if items_div:
            # Get all links that contain '/div/' in their href (excluding category links)
            division_links = items_div.find_all('a', href=lambda x: x and '/div/' in x and '/cat/' not in x)
            
            for link in division_links:
                # Skip the "Combined" link
                if 'combined' not in link.get('href', '') and False:
                    name = link.text.strip()
                    if name == 'Production Optics':
                        has_production_optics = True
                    match_info['divisions'].append({
                        'url': link.get('href'),
                        'name': name
                    })

    
    LEVELS = {'Level II', 'Level III', ' Level IV', 'Level V'}
    
    # Fetch match level from the match URL
    if match_info['match_url']:
        match_response = requests.get('https://shootnscoreit.com' + match_info['match_url'])
        match_soup = BeautifulSoup(match_response.text, 'html.parser')
        
        level_match = re.search(r'Level\s+(I{1,3}|IV|V)', match_response.text, re.IGNORECASE)
        if level_match:
            match_info['match_level'] = level_match.group(0)

        # Extract match date from the ssi-card-title
        date_title = match_soup.find('div', class_='ssi-card-title title-2')
        if date_title:
            date_text = date_title.get_text(strip=True)
            match_info['match_date'] = parse_date_string(date_text)

    # Check if this is a handgun match before processing
    if not is_handgun_match(match_info['divisions']):
        return None

    if has_production_optics and match_info['match_level'] in LEVELS:
        url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/div/hg18/'
        result_response = requests.get(url)
        result_soup = BeautifulSoup(result_response.text, 'html.parser')
        production_optics_results = parse_results(result_soup)

        match_info['combined_results'] = production_optics_results

    
    return match_info


class SSILiveIterator(MatchDataIterator):
    """Iterator for fetching live SSI match data"""
    
    def __init__(self, start_match_id: int = 1, end_match_id: int = 23000, filter_levels: Optional[List[int]] = None):
        """
        Initialize SSI live data iterator
        
        Args:
            start_match_id: Starting match ID to fetch
            end_match_id: Ending match ID to fetch
            filter_levels: List of match levels to include (e.g., [3, 4, 5])
        """
        self.start_match_id = start_match_id
        self.end_match_id = end_match_id
        self.filter_levels = filter_levels or [3, 4, 5]
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over SSI matches by fetching live data"""
        for match_id in range(self.start_match_id, self.end_match_id + 1):
            try:
                match_data = get_match_info(match_id)
                
                if not match_data:
                    continue
                
                # Filter by match level if specified
                match_level = match_data.get('match_level')
                
                # Normalize string levels to integers
                if isinstance(match_level, str):
                    level_map = {'Level I': 1, 'Level II': 2, 'Level III': 3, 'Level IV': 4, 'Level V': 5}
                    match_level = level_map.get(match_level, 1)  # Default to Level I if unknown
                    match_data['match_level'] = match_level
                
                if self.filter_levels and match_level not in self.filter_levels:
                    continue
                
                # Check if match has results
                if 'combined_results' not in match_data or not match_data['combined_results']:
                    continue
                
                # Add source information
                match_data['source'] = self.get_source_name()
                
                # Normalize and yield the match data
                yield self.normalize_match_data(match_data)
                
            except Exception as e:
                print(f"Error fetching SSI match {match_id}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the SSI source name"""
        return 'ssi'


class SSIFileIterator(MatchDataIterator):
    """Iterator for SSI match data stored in JSON files"""
    
    def __init__(self, match_data_dir: str = './match_data/', filter_levels: Optional[List[int]] = None):
        """
        Initialize SSI file iterator
        
        Args:
            match_data_dir: Directory containing SSI match JSON files
            filter_levels: List of match levels to include (e.g., [3, 4, 5])
        """
        self.match_data_dir = match_data_dir
        self.filter_levels = filter_levels
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over SSI match files"""
        if not os.path.exists(self.match_data_dir):
            return
        
        # Get all SSI match files (files without '_practiscore_' in name)
        ssi_files = []
        for filename in os.listdir(self.match_data_dir):
            if filename.endswith('.json') and '_practiscore_' not in filename:
                ssi_files.append(filename)
        
        # Process each file
        for filename in ssi_files:
            filepath = os.path.join(self.match_data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                
                # Skip if no results
                if 'combined_results' not in match_data or not match_data['combined_results']:
                    continue
                
                # Filter by match level if specified
                match_level = match_data.get('match_level')
                
                # Normalize string levels to integers
                if isinstance(match_level, str):
                    level_map = {'Level I': 1, 'Level II': 2, 'Level III': 3, 'Level IV': 4, 'Level V': 5}
                    match_level = level_map.get(match_level, 1)  # Default to Level I if unknown
                    match_data['match_level'] = match_level
                
                if self.filter_levels and match_level not in self.filter_levels:
                    continue
                
                # Add source information if not present
                if 'source' not in match_data:
                    match_data['source'] = self.get_source_name()
                
                # Normalize and yield the match data
                yield self.normalize_match_data(match_data)
                
            except Exception as e:
                print(f"Error loading SSI file {filename}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the SSI source name"""
        return 'ssi'


class SSIMatchFetcher:
    """Utility class for fetching individual SSI matches"""
    
    @staticmethod
    def fetch_match(match_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single SSI match by ID
        
        Args:
            match_id: SSI match ID to fetch
            
        Returns:
            Match data dictionary or None if not found/error
        """
        try:
            match_data = get_match_info(match_id)
            if match_data and 'combined_results' in match_data:
                match_data['source'] = 'ssi'
                return match_data
            return None
        except Exception as e:
            print(f"Error fetching SSI match {match_id}: {e}")
            return None
    
    @staticmethod
    def search_matches_by_date_range(start_date: datetime, end_date: datetime, 
                                   search_range: tuple = (1, 23000)) -> List[Dict[str, Any]]:
        """
        Search for SSI matches within a date range
        
        Args:
            start_date: Start date for search
            end_date: End date for search  
            search_range: Tuple of (start_match_id, end_match_id) to search within
            
        Returns:
            List of matching match data dictionaries
        """
        matches = []
        start_id, end_id = search_range
        
        for match_id in range(start_id, end_id + 1):
            try:
                match_data = SSIMatchFetcher.fetch_match(match_id)
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
                print(f"Error searching SSI match {match_id}: {e}")
                continue
        
        return matches