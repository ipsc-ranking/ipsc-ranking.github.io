#!/usr/bin/env python3
"""
IPSCResults.org data iterator module.

This module provides iterators for IPSCResults.org match data using their OData API.
"""

import json
import os
import requests
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
from match_data_iterator import MatchDataIterator


class IPSCResultsClient:
    """Client for fetching data from IPSCResults.org OData API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.base_url = 'https://ipscresults.org/odata'
    
    def get_match_list(self) -> List[Dict[str, Any]]:
        """Fetch the complete match list from IPSCResults.org"""
        url = f"{self.base_url}/StatsMatchList?$format=json&$count=true"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            print(f"Error fetching match list: {e}")
            return []
    
    def get_match_detail(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific match"""
        url = f"{self.base_url}/StatsMatchDetail({match_id})?$format=json&$count=true"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching match detail {match_id}: {e}")
            return None
    
    def get_match_divisions(self, match_id: str) -> List[Dict[str, Any]]:
        """Fetch available divisions for a match"""
        url = f"{self.base_url}/StatsMatchDetail/Stats.DivisionList(id={match_id})?$format=json&$count=true"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            print(f"Error fetching divisions for match {match_id}: {e}")
            return []
    
    def get_match_results(self, match_id: str, division_code: int) -> List[Dict[str, Any]]:
        """Fetch results for a specific match and division"""
        url = f"{self.base_url}/StatsMatchDetail/Stats.MatchResult(id={match_id},div={division_code})?$format=json&$count=true"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except Exception as e:
            print(f"Error fetching results for match {match_id}, division {division_code}: {e}")
            return []
    
    def get_production_optics_division_code(self, divisions: List[Dict[str, Any]]) -> Optional[int]:
        """Find the Production Optics division code from divisions list"""
        for division in divisions:
            if division.get('Division', '').lower() == 'production optics':
                return division.get('DivisionCode')
        return None


class IPSCResultsLiveIterator(MatchDataIterator):
    """Iterator for fetching live IPSCResults.org match data"""
    
    def __init__(self, client: Optional[IPSCResultsClient] = None, 
                 filter_levels: Optional[List[int]] = None,
                 filter_regions: Optional[List[str]] = None,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None):
        """
        Initialize IPSCResults live data iterator
        
        Args:
            client: Optional IPSCResultsClient instance
            filter_levels: List of match levels to include (e.g., [3, 4, 5])
            filter_regions: List of regions to include (e.g., ['Sweden', 'Denmark'])
            start_date: Only include matches from this date onwards
            end_date: Only include matches up to this date
        """
        self.client = client or IPSCResultsClient()
        self.filter_levels = filter_levels
        self.filter_regions = filter_regions
        self.start_date = start_date
        self.end_date = end_date
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over IPSCResults matches by fetching live data"""
        try:
            matches = self.client.get_match_list()
            
            for match_info in matches:
                # Apply filters
                if not self._match_passes_filters(match_info):
                    continue
                
                match_id = match_info['ID']
                
                # Get detailed match information
                match_detail = self.client.get_match_detail(match_id)
                if not match_detail:
                    continue
                
                # Get divisions
                divisions = self.client.get_match_divisions(match_id)
                production_optics_code = self.client.get_production_optics_division_code(divisions)
                
                if production_optics_code is None:
                    continue  # Skip matches without Production Optics division
                
                # Get Production Optics results
                results = self.client.get_match_results(match_id, production_optics_code)
                if not results:
                    continue
                
                # Build normalized match data
                match_data = self._build_match_data(match_info, match_detail, results)
                if match_data:
                    yield self.normalize_match_data(match_data)
                    
        except Exception as e:
            print(f"Error in IPSCResults iterator: {e}")
    
    def _match_passes_filters(self, match_info: Dict[str, Any]) -> bool:
        """Check if match passes the configured filters"""
        # Filter by level
        if self.filter_levels is not None:
            match_level = match_info.get('Level')
            if match_level not in self.filter_levels:
                return False
        
        # Filter by region
        if self.filter_regions is not None:
            region = match_info.get('RegionName', '')
            if region not in self.filter_regions:
                return False
        
        # Filter by date range
        match_date_str = match_info.get('Date', '')
        if match_date_str and (self.start_date or self.end_date):
            try:
                match_date = datetime.fromisoformat(match_date_str)
                if self.start_date and match_date < self.start_date:
                    return False
                if self.end_date and match_date > self.end_date:
                    return False
            except (ValueError, TypeError):
                return False
        
        return True
    
    def _build_match_data(self, match_info: Dict[str, Any], 
                         match_detail: Dict[str, Any], 
                         results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build normalized match data from API responses"""
        try:
            # Extract match information
            match_id = match_info['ID']
            match_title = match_info['Name']
            match_date = match_info['Date']
            match_level = f"Level {match_info['Level']}" if match_info.get('Level') else 'Level II'
            region = match_info.get('RegionName', 'Unknown')
            
            # Process shooters
            shooters = []
            for i, result in enumerate(results):
                # Parse competitor name
                full_name = result.get('CompetitorName', '').strip()
                name_parts = full_name.split() if full_name else ['Unknown', 'Shooter']
                
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                else:
                    first_name = name_parts[0] if name_parts else 'Unknown'
                    last_name = 'Shooter'
                
                shooter = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'alias': '',
                    'region': self._normalize_region(result.get('Region', region)),
                    'division': 'Production Optics',
                    'category': result.get('Category', []) if result.get('Category') else [],
                    'classification': result.get('Recognition', ''),
                    'club': '',  # Not available in IPSCResults.org
                    'match_percentage': float(result.get('MatchPercent', 0)),
                    'placement': int(result.get('Rank', i + 1)),
                    'match_points': float(result.get('Points', 0)),
                    'competitor_number': result.get('CompetitorNumber', ''),
                }
                shooters.append(shooter)
            
            # Build complete match data
            match_data = {
                'match_id': match_id,
                'match_title': match_title,
                'match_date': f"{match_date}T10:00:00" if match_date else datetime.now().isoformat(),
                'match_level': match_level,
                'club_name': match_detail.get('Location', region),
                'region': region,
                'source': self.get_source_name(),
                'production_optics_results': shooters,
                'combined_results': shooters,  # For compatibility
                'api_data': {
                    'match_info': match_info,
                    'match_detail': match_detail,
                    'results': results
                }
            }
            
            return match_data
            
        except Exception as e:
            print(f"Error building match data for {match_info.get('ID', 'unknown')}: {e}")
            return None
    
    def _normalize_region(self, region_code: str) -> str:
        """Normalize region codes to standard format"""
        region_mapping = {
            'SWE': 'SWE',
            'DEN': 'DEN', 
            'NOR': 'NOR',
            'FIN': 'FIN',
            'GER': 'GER',
            'DEU': 'GER',  # Alternative German code
            # Add more mappings as needed
        }
        return region_mapping.get(region_code, region_code)
    
    def get_source_name(self) -> str:
        """Return the IPSCResults source name"""
        return 'ipscresults'


class IPSCResultsFileIterator(MatchDataIterator):
    """Iterator for IPSCResults match data stored in JSON files"""
    
    def __init__(self, match_data_dir: str = './match_data/', filter_levels: Optional[List[str]] = None):
        """
        Initialize IPSCResults file iterator
        
        Args:
            match_data_dir: Directory containing IPSCResults match JSON files
            filter_levels: List of match levels to include
        """
        self.match_data_dir = match_data_dir
        self.filter_levels = filter_levels
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over IPSCResults match files"""
        if not os.path.exists(self.match_data_dir):
            return
        
        # Get all IPSCResults match files (files with '_ipscresults_' in name)
        ipscresults_files = []
        for filename in os.listdir(self.match_data_dir):
            if filename.endswith('.json') and '_ipscresults_' in filename:
                ipscresults_files.append(filename)
        
        # Process each file
        for filename in ipscresults_files:
            filepath = os.path.join(self.match_data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                
                # Skip if no production optics results or combined results
                has_results = (
                    ('production_optics_results' in match_data and match_data['production_optics_results']) or
                    ('combined_results' in match_data and match_data['combined_results'])
                )
                if not has_results:
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
                print(f"Error loading IPSCResults file {filename}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the IPSCResults source name"""
        return 'ipscresults'


class IPSCResultsMatchFetcher:
    """Utility class for fetching individual IPSCResults matches"""
    
    def __init__(self, client: Optional[IPSCResultsClient] = None):
        """Initialize with optional client"""
        self.client = client or IPSCResultsClient()
    
    def fetch_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single IPSCResults match by ID
        
        Args:
            match_id: IPSCResults match ID (UUID format)
            
        Returns:
            Match data dictionary or None if not found/error
        """
        try:
            # Get match detail
            match_detail = self.client.get_match_detail(match_id)
            if not match_detail:
                return None
            
            # Get divisions
            divisions = self.client.get_match_divisions(match_id)
            production_optics_code = self.client.get_production_optics_division_code(divisions)
            
            if production_optics_code is None:
                return None
            
            # Get results
            results = self.client.get_match_results(match_id, production_optics_code)
            if not results:
                return None
            
            # Build match info from detail (approximate)
            match_info = {
                'ID': match_id,  # Use the ID we passed in
                'Name': match_detail.get('Name', 'Unknown Match'),
                'Date': match_detail.get('Date', '')[:10] if match_detail.get('Date') else datetime.now().strftime('%Y-%m-%d'),
                'Level': match_detail.get('Level', 2),
                'RegionName': match_detail.get('Region', 'Unknown')
            }
            
            # Build and return match data
            iterator = IPSCResultsLiveIterator(self.client)
            match_data = iterator._build_match_data(match_info, match_detail, results)
            return match_data
            
        except Exception as e:
            print(f"Error fetching IPSCResults match {match_id}: {e}")
            return None
    
    def save_match_data(self, match_data: Dict[str, Any], filename: Optional[str] = None):
        """Save IPSCResults match data to JSON file"""
        if not filename:
            match_date = match_data.get('match_date', '')
            timestamp = self._extract_date_for_filename(match_date)
            match_id = str(match_data['match_id'])[:8]  # Use first 8 chars of UUID
            filename = f"match_data/{timestamp}_ipscresults_{match_id}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            print(f"IPSCResults match data saved to {filename}")
        except IOError as e:
            print(f"Error saving IPSCResults match data to {filename}: {e}")
            raise
    
    def _extract_date_for_filename(self, match_date: str) -> str:
        """Extract date from match_date for filename prefix (YYYY-MM-DD format)"""
        try:
            if 'T' in match_date:
                return match_date.split('T')[0]
            elif '-' in match_date and len(match_date) >= 10:
                return match_date[:10]
        except:
            pass
        
        return datetime.now().strftime('%Y-%m-%d')