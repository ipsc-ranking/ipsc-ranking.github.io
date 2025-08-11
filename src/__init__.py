"""
IPSC Ranking System

A comprehensive system for processing and ranking IPSC match data from multiple sources.
"""

__version__ = "1.0.0"
__author__ = "IPSC Ranking System"

from .data_sources import create_iterator, MatchDataIterator
from .ranking import IPSCRankingSystem

__all__ = [
    'create_iterator',
    'MatchDataIterator', 
    'IPSCRankingSystem'
]