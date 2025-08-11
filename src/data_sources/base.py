#!/usr/bin/env python3
"""
Base classes and common functionality for match data iterators.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
import os


class MatchDataIterator(ABC):
    """Abstract base class for match data iterators"""
    
    @abstractmethod
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterator yielding normalized match data dictionaries"""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the data source"""
        pass
    
    def normalize_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize match data to a common format.
        This ensures all match data follows the same structure regardless of source.
        """
        normalized = {
            'match_id': match_data.get('match_id'),
            'match_title': match_data.get('match_title'),
            'match_date': match_data.get('match_date'),
            'match_level': match_data.get('match_level'),
            'club_name': match_data.get('club_name'),
            'source': match_data.get('source', self.get_source_name()),
            'raw_data': match_data  # Keep original data for debugging
        }
        
        # Normalize results - handle different field names from different sources
        results = []
        
        # Check for different result field names
        if 'combined_results' in match_data:
            results = match_data['combined_results']
        elif 'shooters' in match_data:
            results = match_data['shooters']
        
        # Normalize each shooter's data
        normalized_results = []
        for result in results:
            normalized_result = {
                'first_name': result.get('first_name'),
                'last_name': result.get('last_name'),
                'alias': result.get('alias', ''),
                'region': result.get('region'),
                'division': result.get('division'),
                'category': result.get('category', []),
                'classification': result.get('classification'),
                'club': result.get('club'),
                'match_percentage': result.get('match_percentage'),
                'placement': result.get('placement', result.get('position')),
                'match_points': result.get('match_points'),
                'raw_result': result  # Keep original result data
            }
            normalized_results.append(normalized_result)
        
        normalized['results'] = normalized_results
        return normalized


class CombinedMatchDataIterator(MatchDataIterator):
    """Iterator that combines multiple match data sources"""
    
    def __init__(self, iterators: List[MatchDataIterator]):
        """
        Initialize with a list of match data iterators
        
        Args:
            iterators: List of MatchDataIterator instances to combine
        """
        self.iterators = iterators
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over all matches from all sources, sorted by date"""
        all_matches = []
        
        # Collect all matches from all sources
        for iterator in self.iterators:
            for match_data in iterator:
                all_matches.append(match_data)
        
        # Sort by match date (chronological order)
        all_matches.sort(key=lambda x: self._parse_date(x.get('match_date', '')))
        
        # Yield each match
        for match in all_matches:
            yield match
    
    def get_source_name(self) -> str:
        """Return combined source name"""
        source_names = [iterator.get_source_name() for iterator in self.iterators]
        return f"combined({', '.join(source_names)})"
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime for sorting"""
        if not date_str:
            return datetime.min
        
        try:
            # Handle ISO format with timezone
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Handle other formats as needed
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return datetime.min