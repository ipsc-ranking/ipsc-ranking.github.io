#!/usr/bin/env python3
"""
Common interface and iterators for match data sources.

This module provides a common interface for iterating over match data from different sources
(SSI, Practiscore) and a unified iterator that combines all sources.
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
        if 'production_optics_results' in match_data:
            results = match_data['production_optics_results']
        elif 'combined_results' in match_data:
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


def create_file_based_iterator(source_type: str, match_data_dir: str = './match_data/', 
                             filter_levels: Optional[List[str]] = None) -> MatchDataIterator:
    """
    Factory function to create file-based iterators for existing data
    
    Args:
        source_type: Type of source ('ssi', 'practiscore', 'ipscresults', or 'all')
        match_data_dir: Directory containing match data files
        filter_levels: Optional list of match levels to include
        
    Returns:
        Appropriate MatchDataIterator instance
    """
    if source_type == 'ssi':
        from ssi_iterator import SSIFileIterator
        return SSIFileIterator(match_data_dir, filter_levels)
    elif source_type == 'practiscore':
        from practiscore_iterator import PractiscoreFileIterator
        return PractiscoreFileIterator(match_data_dir, filter_levels)
    elif source_type == 'ipscresults':
        from ipscresults_iterator import IPSCResultsFileIterator
        return IPSCResultsFileIterator(match_data_dir, filter_levels)
    elif source_type == 'all':
        from ssi_iterator import SSIFileIterator
        from practiscore_iterator import PractiscoreFileIterator
        from ipscresults_iterator import IPSCResultsFileIterator
        return CombinedMatchDataIterator([
            SSIFileIterator(match_data_dir, filter_levels),
            PractiscoreFileIterator(match_data_dir, filter_levels),
            IPSCResultsFileIterator(match_data_dir, filter_levels)
        ])
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def create_live_iterator(source_type: str, **kwargs) -> MatchDataIterator:
    """
    Factory function to create live data iterators
    
    Args:
        source_type: Type of source ('ssi', 'practiscore', 'ipscresults', or 'all')
        **kwargs: Arguments passed to specific iterator constructors
        
    Returns:
        Appropriate MatchDataIterator instance
    """
    if source_type == 'ssi':
        from ssi_iterator import SSILiveIterator
        return SSILiveIterator(**kwargs)
    elif source_type == 'practiscore':
        from practiscore_iterator import PractiscoreLiveIterator
        return PractiscoreLiveIterator(**kwargs)
    elif source_type == 'ipscresults':
        from ipscresults_iterator import IPSCResultsLiveIterator
        return IPSCResultsLiveIterator(**kwargs)
    elif source_type == 'all':
        from ssi_iterator import SSILiveIterator  
        from practiscore_iterator import PractiscoreLiveIterator
        from ipscresults_iterator import IPSCResultsLiveIterator
        
        # Split kwargs for different iterator types
        ssi_kwargs = {k: v for k, v in kwargs.items() if k in ['start_match_id', 'end_match_id', 'filter_levels']}
        practiscore_kwargs = {k: v for k, v in kwargs.items() if k in ['match_ids', 'client']}
        ipscresults_kwargs = {k: v for k, v in kwargs.items() if k in ['client', 'filter_levels', 'filter_regions', 'start_date', 'end_date']}
        
        iterators = []
        if ssi_kwargs:
            iterators.append(SSILiveIterator(**ssi_kwargs))
        if practiscore_kwargs:
            iterators.append(PractiscoreLiveIterator(**practiscore_kwargs))
        if ipscresults_kwargs:
            iterators.append(IPSCResultsLiveIterator(**ipscresults_kwargs))
            
        return CombinedMatchDataIterator(iterators)
    else:
        raise ValueError(f"Unknown source type: {source_type}")