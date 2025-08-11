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
from match_data_iterator import MatchDataIterator
from practiscore import PractiScoreClient


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
    
    def __init__(self, match_data_dir: str = './match_data/', filter_levels: Optional[List[str]] = None):
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
                print(f"Error loading Practiscore file {filename}: {e}")
                continue
    
    def get_source_name(self) -> str:
        """Return the Practiscore source name"""
        return 'practiscore'


class PractiscoreRangeIterator(MatchDataIterator):
    """Iterator for fetching Practiscore matches in a range"""
    
    def __init__(self, start_match_id: int, end_match_id: int, 
                 client: Optional[PractiScoreClient] = None,
                 filter_levels: Optional[List[str]] = None):
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