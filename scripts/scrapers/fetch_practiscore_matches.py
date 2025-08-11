#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Utility script to fetch match data from PractiScore and integrate with the ranking system.
"""

import os
import sys
import json
from typing import List
from practiscore import PractiScoreClient


def ensure_match_data_directory():
    """Ensure the match_data directory exists"""
    if not os.path.exists('match_data'):
        os.makedirs('match_data')
        print("Created match_data directory")


def fetch_matches(match_ids: List[str]) -> int:
    """
    Fetch multiple matches from PractiScore
    
    Args:
        match_ids: List of PractiScore match IDs to fetch
        
    Returns:
        Number of successfully fetched matches
    """
    client = PractiScoreClient()
    successful_fetches = 0
    
    ensure_match_data_directory()
    
    for match_id in match_ids:
        print(f"Fetching match {match_id}...")
        
        # Check if match already exists
        filename = f"match_data/match_{match_id}.json"
        if os.path.exists(filename):
            print(f"  Match {match_id} already exists, skipping")
            continue
        
        try:
            match_data = client.fetch_match_data(match_id)
            
            if match_data and match_data.get('production_optics_results'):
                client.save_match_data(match_data)
                successful_fetches += 1
                print(f"  Successfully fetched {len(match_data['production_optics_results'])} shooters")
            else:
                print(f"  Failed to fetch or parse match {match_id}")
                
        except Exception as e:
            print(f"  Error fetching match {match_id}: {e}")
    
    return successful_fetches


def update_match_with_division_data(match_id: str, division_results: dict):
    """
    Update an existing match file with division-specific results
    
    Args:
        match_id: Match ID to update
        division_results: Dictionary with division name as key and shooter list as value
    """
    filename = f"match_data/match_{match_id}.json"
    
    if not os.path.exists(filename):
        print(f"Match file {filename} does not exist")
        return
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            match_data = json.load(f)
        
        # Update with division results
        match_data.update(division_results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)
        
        print(f"Updated match {match_id} with division data")
        
    except Exception as e:
        print(f"Error updating match {match_id}: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_practiscore_matches.py <match_id1> [match_id2] [...]")
        print("  python fetch_practiscore_matches.py --list-file <file_with_match_ids>")
        print("")
        print("Examples:")
        print("  python fetch_practiscore_matches.py 287616")
        print("  python fetch_practiscore_matches.py 287616 287617 287618")
        sys.exit(1)
    
    match_ids = []
    
    if sys.argv[1] == '--list-file':
        if len(sys.argv) < 3:
            print("Error: --list-file requires a filename")
            sys.exit(1)
        
        try:
            with open(sys.argv[2], 'r') as f:
                match_ids = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[2]}' not found")
            sys.exit(1)
    else:
        match_ids = sys.argv[1:]
    
    if not match_ids:
        print("No match IDs provided")
        sys.exit(1)
    
    print(f"Fetching {len(match_ids)} matches from PractiScore...")
    successful = fetch_matches(match_ids)
    
    print(f"\nCompleted: {successful}/{len(match_ids)} matches fetched successfully")
    
    if successful > 0:
        print("\nTo process the fetched matches with the ranking system, run:")
        print("  python process_matches.py")


if __name__ == "__main__":
    main()