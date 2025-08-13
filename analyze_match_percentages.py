#!/usr/bin/env python3

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

def analyze_match_percentages():
    """Analyze the distribution of match percentages in our data"""
    print("Analyzing match percentage distribution...")
    
    all_percentages = []
    match_count = 0
    
    # Load all match files
    match_files_location = './data/matches/'
    for filename in os.listdir(match_files_location):
        if filename.endswith('.json'):
            filepath = os.path.join(match_files_location, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                    
                    # Create combined_results from divisions if missing
                    if 'combined_results' not in match_data and 'divisions' in match_data:
                        combined_results = []
                        divisions = match_data.get('divisions', {})
                        
                        if isinstance(divisions, dict):
                            # IPSCResults format: divisions is a dict
                            for div_name, div_data in divisions.items():
                                if isinstance(div_data, dict) and 'shooters' in div_data:
                                    combined_results.extend(div_data['shooters'])
                        elif isinstance(divisions, list):
                            # SSI format: divisions is a list
                            for division in divisions:
                                if isinstance(division, dict) and 'shooters' in division:
                                    combined_results.extend(division['shooters'])
                        
                        match_data['combined_results'] = combined_results
                    
                    # Filter for handgun matches only
                    if not is_handgun_match(match_data):
                        continue
                    
                    if 'combined_results' in match_data and len(match_data['combined_results']) > 1:
                        match_count += 1
                        for result in match_data['combined_results']:
                            if 'match_percentage' in result and result['match_percentage'] is not None:
                                percentage = float(result['match_percentage'])
                                if 0 <= percentage <= 100:  # Valid percentage
                                    all_percentages.append(percentage)
                                    
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    if not all_percentages:
        print("No match percentages found!")
        return
    
    all_percentages = np.array(all_percentages)
    
    print(f"\nMatch Percentage Analysis:")
    print(f"Total matches analyzed: {match_count}")
    print(f"Total percentage data points: {len(all_percentages)}")
    print(f"Average match percentage: {np.mean(all_percentages):.1f}%")
    print(f"Median match percentage: {np.median(all_percentages):.1f}%")
    print(f"Standard deviation: {np.std(all_percentages):.1f}%")
    print(f"Min: {np.min(all_percentages):.1f}%")
    print(f"Max: {np.max(all_percentages):.1f}%")
    
    # Percentiles
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    print(f"\nPercentiles:")
    for p in percentiles:
        value = np.percentile(all_percentages, p)
        print(f"  {p:2d}th percentile: {value:.1f}%")
    
    # Analyze top performers (those who typically shoot high percentages)
    # Group by player and find their average percentage
    player_percentages = defaultdict(list)
    
    for filename in os.listdir(match_files_location):
        if filename.endswith('.json'):
            filepath = os.path.join(match_files_location, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                    
                    if 'combined_results' not in match_data and 'divisions' in match_data:
                        combined_results = []
                        divisions = match_data.get('divisions', {})
                        
                        if isinstance(divisions, dict):
                            for div_name, div_data in divisions.items():
                                if isinstance(div_data, dict) and 'shooters' in div_data:
                                    combined_results.extend(div_data['shooters'])
                        elif isinstance(divisions, list):
                            for division in divisions:
                                if isinstance(division, dict) and 'shooters' in division:
                                    combined_results.extend(division['shooters'])
                        
                        match_data['combined_results'] = combined_results
                    
                    if not is_handgun_match(match_data):
                        continue
                    
                    if 'combined_results' in match_data and len(match_data['combined_results']) > 1:
                        for result in match_data['combined_results']:
                            if 'match_percentage' in result and result['match_percentage'] is not None:
                                percentage = float(result['match_percentage'])
                                if 0 <= percentage <= 100:
                                    # Create player ID
                                    player_name = f"{result.get('first_name', '')} {result.get('last_name', '')}"
                                    if player_name.strip():
                                        player_percentages[player_name].append(percentage)
                                        
            except Exception as e:
                continue
    
    # Calculate average percentages for players with multiple matches
    player_averages = []
    for player, percentages in player_percentages.items():
        if len(percentages) >= 3:  # At least 3 matches
            avg_percentage = np.mean(percentages)
            player_averages.append(avg_percentage)
    
    if player_averages:
        player_averages = np.array(player_averages)
        print(f"\nPlayer Average Analysis ({len(player_averages)} players with 3+ matches):")
        print(f"Average of player averages: {np.mean(player_averages):.1f}%")
        print(f"Median of player averages: {np.median(player_averages):.1f}%")
        print(f"Std dev of player averages: {np.std(player_averages):.1f}%")
        
        # Top performers
        top_percentiles = [90, 95, 99]
        print(f"\nTop performers (player averages):")
        for p in top_percentiles:
            value = np.percentile(player_averages, p)
            print(f"  Top {100-p}% of players average: {value:.1f}%+")
    
    # Recommendations for START_MU
    print(f"\n" + "="*60)
    print("RECOMMENDATIONS FOR START_MU")
    print("="*60)
    
    # Current system uses START_MU = 25, which doesn't relate to percentages
    current_start_mu = 25
    
    # Option 1: Use median percentage as START_MU
    median_percentage = np.median(all_percentages)
    print(f"Option 1 - Median-based: START_MU = {median_percentage:.0f}")
    print(f"  Rationale: Average player starts at median performance level")
    
    # Option 2: Use a value that makes top players reach ~90-95%
    if player_averages is not None and len(player_averages) > 0:
        top_5_percent = np.percentile(player_averages, 95)
        # If we want top players to reach ~95% mu, and they're currently at top_5_percent
        # Then START_MU should be scaled accordingly
        suggested_start_mu = median_percentage
        print(f"Option 2 - Scaled system: START_MU = {suggested_start_mu:.0f}")
        print(f"  This would make mu values roughly correspond to match percentages")
        print(f"  Top 5% of players average {top_5_percent:.1f}%, they could reach ~{top_5_percent:.0f} mu")
    
    # Option 3: Conservative approach
    conservative_start = np.percentile(all_percentages, 25)  # 25th percentile
    print(f"Option 3 - Conservative: START_MU = {conservative_start:.0f}")
    print(f"  Rationale: New players start below average, room to grow")
    
    return {
        'median_percentage': median_percentage,
        'mean_percentage': np.mean(all_percentages),
        'std_percentage': np.std(all_percentages),
        'player_averages': player_averages if player_averages is not None else [],
        'current_start_mu': current_start_mu
    }

def is_handgun_match(match_data):
    """Check if a match is a handgun match"""
    source = match_data.get('source', '')
    
    # Handle IPSCResults.org files
    if source == 'ipscresults':
        divisions = match_data.get('divisions', {})
        if isinstance(divisions, dict):
            handgun_divisions = [
                'open', 'standard', 'production', 'production optics', 
                'classic', 'revolver', 'limited', 'carry optics', 
                'pcc', 'pistol caliber carbine'
            ]
            
            for div_name in divisions.keys():
                if div_name.lower() in handgun_divisions:
                    return True
    
    # Handle SSI files
    elif isinstance(match_data.get('divisions', []), list):
        divisions = match_data.get('divisions', [])
        handgun_patterns = ['/hg1/', '/hg2/', '/hg3/', '/hg4/', '/hg5/', '/hg12/', '/hg18/', '/hg19/']
        
        for division in divisions:
            division_url = division.get('url', '')
            if any(pattern in division_url for pattern in handgun_patterns):
                return True
    
    # Check match title
    match_title = match_data.get('match_title', '')
    if match_title and isinstance(match_title, str):
        match_title_lower = match_title.lower()
        if 'handgun' in match_title_lower and 'shotgun' not in match_title_lower and 'rifle' not in match_title_lower:
            return True
        
    return False

if __name__ == "__main__":
    analyze_match_percentages()