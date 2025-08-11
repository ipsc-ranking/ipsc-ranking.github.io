#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Comprehensive script to discover and fetch all Swedish IPSC matches from PractiScore
"""

import os
import time
import json
from datetime import datetime, timedelta
from practiscore import PractiScoreClient
from typing import List, Set

class PractiScoreDiscovery:
    def __init__(self):
        self.client = PractiScoreClient()
        self.swedish_keywords = [
            'sweden', 'svenska', 'stockholm', 'gothenburg', 'göteborg', 
            'malmö', 'uppsala', 'västerås', 'örebro', 'linköping',
            'helsingborg', 'jönköping', 'norrköping', 'lund', 'umeå',
            'gävle', 'borås', 'södertälje', 'eskilstuna', 'karlstad',
            'täby', 'sundsvall', 'växjö', 'halmstad', 'sundbyberg',
            'swe', 'swedish', 'nordic'
        ]
    
    def discover_match_range(self, start_id: int = 280000, end_id: int = 300000, batch_size: int = 100):
        """
        Discover Swedish matches by trying match ID ranges
        """
        print(f"Discovering matches in range {start_id} to {end_id}")
        potential_matches = []
        
        for match_id in range(start_id, end_id + 1):
            if match_id % batch_size == 0:
                print(f"  Checking match {match_id}...")
                
            # Rate limiting - be respectful to PractiScore
            time.sleep(0.1)
            
            try:
                # Quick check if match exists by trying to fetch basic info
                match_data = self.client.fetch_match_data(str(match_id))
                
                if match_data and self.is_swedish_match(match_data):
                    potential_matches.append(match_id)
                    print(f"  Found Swedish match: {match_id} - {match_data.get('match_title', 'Unknown')}")
                    
            except Exception as e:
                # Most IDs won't exist, that's normal
                continue
                
        return potential_matches
    
    def is_swedish_match(self, match_data: dict) -> bool:
        """
        Determine if a match is Swedish based on title, club, or location
        """
        searchable_text = ' '.join([
            match_data.get('match_title', '').lower(),
            match_data.get('club_name', '').lower(),
        ])
        
        # Check for Swedish keywords
        return any(keyword in searchable_text for keyword in self.swedish_keywords)
    
    def discover_recent_matches(self, days_back: int = 365):
        """
        Try to discover recent matches by checking common Swedish match ID patterns
        """
        print(f"Looking for recent matches from last {days_back} days")
        
        # Common PractiScore ID ranges for recent matches
        recent_ranges = [
            (280000, 290000),  # Recent range 1
            (290000, 300000),  # Recent range 2
            (270000, 280000),  # Slightly older
        ]
        
        all_matches = []
        
        for start, end in recent_ranges:
            print(f"Checking range {start}-{end}")
            matches = self.discover_match_range(start, end)
            all_matches.extend(matches)
            
            # Rate limiting between ranges
            time.sleep(2)
            
        return all_matches
    
    def fetch_known_swedish_matches(self):
        """
        Fetch matches from known Swedish match IDs or patterns
        """
        # These are example IDs - you might have specific Swedish match IDs
        known_ids = [
            '287616',  # Example from the practiscore.py file
            # Add more known Swedish match IDs here
        ]
        
        print(f"Fetching {len(known_ids)} known Swedish matches")
        
        successful = 0
        for match_id in known_ids:
            try:
                match_data = self.client.fetch_match_data(match_id)
                if match_data:
                    self.client.save_match_data(match_data)
                    successful += 1
                    print(f"  Fetched match {match_id}: {match_data.get('match_title', 'Unknown')}")
            except Exception as e:
                print(f"  Failed to fetch {match_id}: {e}")
                
        return successful

def main():
    """Main discovery and fetching process"""
    print("🇸🇪 Starting comprehensive PractiScore Swedish match discovery...")
    
    discovery = PractiScoreDiscovery()
    
    # Strategy 1: Fetch known Swedish matches first
    print("\n=== Step 1: Fetching known Swedish matches ===")
    known_fetched = discovery.fetch_known_swedish_matches()
    print(f"Fetched {known_fetched} known matches")
    
    # Strategy 2: Discover recent matches by scanning ID ranges
    print("\n=== Step 2: Discovering recent Swedish matches ===")
    discovered_matches = discovery.discover_recent_matches(days_back=730)  # 2 years
    
    if discovered_matches:
        print(f"\n=== Step 3: Fetching {len(discovered_matches)} discovered matches ===")
        
        successful = 0
        for match_id in discovered_matches:
            try:
                match_data = discovery.client.fetch_match_data(str(match_id))
                if match_data:
                    discovery.client.save_match_data(match_data)
                    successful += 1
                    print(f"  Fetched: {match_id} - {match_data.get('match_title', 'Unknown')}")
                    
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"  Failed {match_id}: {e}")
        
        print(f"\nSuccessfully fetched {successful} discovered matches")
    else:
        print("No additional Swedish matches discovered in recent ranges")
    
    # Strategy 3: Try systematic scanning of older ranges (optional)
    print("\n=== Step 4: Scanning older match ranges (optional) ===")
    user_input = input("Scan older matches (2020-2023)? This may take a while [y/N]: ")
    
    if user_input.lower().startswith('y'):
        older_matches = discovery.discover_match_range(200000, 280000, batch_size=1000)
        
        if older_matches:
            print(f"Found {len(older_matches)} older Swedish matches")
            # Fetch them too
            for match_id in older_matches:
                try:
                    match_data = discovery.client.fetch_match_data(str(match_id))
                    if match_data:
                        discovery.client.save_match_data(match_data)
                        print(f"  Fetched older: {match_id}")
                    time.sleep(1)
                except Exception as e:
                    print(f"  Failed older {match_id}: {e}")
    
    print("\n✅ PractiScore discovery and fetching complete!")
    print("Run 'python process_matches.py' to update rankings with new data")

if __name__ == "__main__":
    main()