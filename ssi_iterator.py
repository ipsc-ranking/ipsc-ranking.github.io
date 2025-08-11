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
from match_data_iterator import MatchDataIterator
from ssi import get_match_info, parse_results, parse_date_string


class SSILiveIterator(MatchDataIterator):
    """Iterator for fetching live SSI match data"""
    
    def __init__(self, start_match_id: int = 1, end_match_id: int = 23000, filter_levels: Optional[List[str]] = None):
        """
        Initialize SSI live data iterator
        
        Args:
            start_match_id: Starting match ID to fetch
            end_match_id: Ending match ID to fetch
            filter_levels: List of match levels to include (e.g., ['Level III', 'Level IV', 'Level V'])
        """
        self.start_match_id = start_match_id
        self.end_match_id = end_match_id
        self.filter_levels = filter_levels or ['Level III', 'Level IV', 'Level V']
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over SSI matches by fetching live data"""
        for match_id in range(self.start_match_id, self.end_match_id + 1):
            try:
                match_data = get_match_info(match_id)
                
                if not match_data:
                    continue
                
                # Filter by match level if specified
                match_level = match_data.get('match_level')
                if self.filter_levels and match_level not in self.filter_levels:
                    continue
                
                # Check if match has production optics results
                if 'production_optics_results' not in match_data or not match_data['production_optics_results']:
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
    
    def __init__(self, match_data_dir: str = './match_data/', filter_levels: Optional[List[str]] = None):
        """
        Initialize SSI file iterator
        
        Args:
            match_data_dir: Directory containing SSI match JSON files
            filter_levels: List of match levels to include
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
                
                # Skip if no production optics results
                if 'production_optics_results' not in match_data or not match_data['production_optics_results']:
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
            if match_data and 'production_optics_results' in match_data:
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