"""
Data source iterators for IPSC match data.

This package provides iterators for fetching and processing match data from various sources:
- SSI (Shoot'n Score It)  
- Practiscore
- IPSCResults.org
"""

from .base import MatchDataIterator, CombinedMatchDataIterator
from .ssi import SSIFileIterator, SSILiveIterator
from .practiscore import PractiscoreFileIterator, PractiscoreLiveIterator, PractiscoreRangeIterator
from .ipscresults import IPSCResultsFileIterator, IPSCResultsLiveIterator

__all__ = [
    'MatchDataIterator',
    'CombinedMatchDataIterator',
    'SSIFileIterator', 
    'SSILiveIterator',
    'PractiscoreFileIterator',
    'PractiscoreLiveIterator', 
    'PractiscoreRangeIterator',
    'IPSCResultsFileIterator',
    'IPSCResultsLiveIterator',
    'create_iterator'
]

def create_iterator(source_type: str, mode: str = 'file', **kwargs):
    """
    Factory function to create appropriate data iterators
    
    Args:
        source_type: Type of source ('ssi', 'practiscore', 'ipscresults', or 'all')
        mode: Iterator mode ('file' for stored data, 'live' for API calls)
        **kwargs: Additional arguments passed to iterator constructors
        
    Returns:
        Appropriate MatchDataIterator instance
    """
    if mode == 'file':
        return create_file_based_iterator(source_type, **kwargs)
    elif mode == 'live':
        return create_live_iterator(source_type, **kwargs)
    else:
        raise ValueError(f"Unknown mode: {mode}")

def create_file_based_iterator(source_type: str, match_data_dir: str = './data/matches/', **kwargs):
    """Create file-based iterators for existing data"""
    from typing import List, Optional
    
    filter_levels = kwargs.get('filter_levels')
    
    if source_type == 'ssi':
        return SSIFileIterator(match_data_dir, filter_levels)
    elif source_type == 'practiscore':
        return PractiscoreFileIterator(match_data_dir, filter_levels)
    elif source_type == 'ipscresults':
        return IPSCResultsFileIterator(match_data_dir, filter_levels)
    elif source_type == 'all':
        return CombinedMatchDataIterator([
            SSIFileIterator(match_data_dir, filter_levels),
            PractiscoreFileIterator(match_data_dir, filter_levels),
            IPSCResultsFileIterator(match_data_dir, filter_levels)
        ])
    else:
        raise ValueError(f"Unknown source type: {source_type}")

def create_live_iterator(source_type: str, **kwargs):
    """Create live data iterators"""
    if source_type == 'ssi':
        return SSILiveIterator(**kwargs)
    elif source_type == 'practiscore':
        return PractiscoreLiveIterator(**kwargs)
    elif source_type == 'ipscresults':
        return IPSCResultsLiveIterator(**kwargs)
    elif source_type == 'all':
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