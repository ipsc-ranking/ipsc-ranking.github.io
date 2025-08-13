#!/usr/bin/env python3

import json
import os
import numpy as np
from collections import defaultdict
from datetime import datetime
from name_normalizer import normalize_name, get_normalized_player_id

def analyze_first_match_performance():
    """Analyze players' first match performance (across all divisions) to determine optimal START_MU"""
    print("Analyzing first match performance for new players (across all divisions)...")
    
    # Store all matches with dates for sorting
    all_matches = []
    
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
                        # Add match date for sorting
                        try:
                            match_date = datetime.fromisoformat(match_data['match_date'].replace('Z', '+00:00'))
                            match_data['parsed_date'] = match_date
                            all_matches.append(match_data)
                        except:
                            continue
                                    
            except Exception as e:
                continue
    
    # Sort matches by date
    all_matches.sort(key=lambda x: x['parsed_date'])
    
    print(f"Loaded {len(all_matches)} chronologically sorted matches")
    
    # Track each player's match history across ALL divisions
    # Use player name + region as identifier (no division in ID)
    player_matches = defaultdict(list)
    
    for match in all_matches:
        for result in match['combined_results']:
            if 'match_percentage' in result and result['match_percentage'] is not None:
                percentage = float(result['match_percentage'])
                if 0 <= percentage <= 100:  # Valid percentage
                    # Create player ID WITHOUT division - track across all divisions
                    first_name = normalize_name(result.get('first_name', ''))
                    last_name = normalize_name(result.get('last_name', ''))
                    region = result.get('region', 'Unknown')
                    
                    # Player ID format: firstname_lastname_region (NO division)
                    player_id = f"{first_name}_{last_name}_{region}".lower().strip('_')
                    
                    player_matches[player_id].append({
                        'date': match['parsed_date'],
                        'percentage': percentage,
                        'match_title': match.get('match_title', ''),
                        'first_name': result.get('first_name', ''),
                        'last_name': result.get('last_name', ''),
                        'division': result.get('division', 'Unknown'),
                        'region': region
                    })
    
    # Find first match performance for each player (across all divisions)
    first_match_performances = []
    player_count = 0
    division_analysis = defaultdict(list)
    
    for player_id, matches in player_matches.items():
        if len(matches) >= 2:  # Only include players with multiple matches
            # Sort by date to ensure we get the actual first match
            matches.sort(key=lambda x: x['date'])
            first_match = matches[0]
            first_match_performances.append(first_match['percentage'])
            
            # Track first match by division
            division_analysis[first_match['division']].append(first_match['percentage'])
            
            player_count += 1
    
    if not first_match_performances:
        print("No first match data found!")
        return
    
    first_match_performances = np.array(first_match_performances)
    
    print(f"\nFirst Match Performance Analysis (Across All Divisions):")
    print(f"Players analyzed: {player_count} (players with 2+ matches)")
    print(f"Average first match: {np.mean(first_match_performances):.1f}%")
    print(f"Median first match: {np.median(first_match_performances):.1f}%")
    print(f"Standard deviation: {np.std(first_match_performances):.1f}%")
    print(f"Min first match: {np.min(first_match_performances):.1f}%")
    print(f"Max first match: {np.max(first_match_performances):.1f}%")
    
    # Percentiles
    percentiles = [10, 25, 50, 75, 90, 95]
    print(f"\nFirst Match Percentiles:")
    for p in percentiles:
        value = np.percentile(first_match_performances, p)
        print(f"  {p:2d}th percentile: {value:.1f}%")
    
    # First match performance by division
    print(f"\nFirst Match Performance by Division:")
    for division, performances in division_analysis.items():
        if len(performances) >= 10:  # Only show divisions with enough data
            performances = np.array(performances)
            print(f"  {division}: {np.median(performances):.1f}% median ({len(performances)} players)")
    
    # Compare to overall performance
    print(f"\n" + "="*60)
    print("COMPARISON: FIRST MATCH vs OVERALL PERFORMANCE")
    print("="*60)
    
    # Get overall performance for comparison
    all_percentages = []
    for matches in player_matches.values():
        for match in matches:
            all_percentages.append(match['percentage'])
    
    all_percentages = np.array(all_percentages)
    
    print(f"Overall median: {np.median(all_percentages):.1f}%")
    print(f"First match median: {np.median(first_match_performances):.1f}%")
    print(f"Difference: {np.median(first_match_performances) - np.median(all_percentages):.1f}% (first match vs overall)")
    
    # Show learning curve
    print(f"\nLEARNING CURVE ANALYSIS:")
    improvement_data = []
    
    for matches in player_matches.values():
        if len(matches) >= 5:  # Need enough matches to see progression
            matches.sort(key=lambda x: x['date'])
            first_match_perf = matches[0]['percentage']
            # Average of matches 2-5 to reduce noise
            early_avg = np.mean([m['percentage'] for m in matches[1:5]])
            improvement = early_avg - first_match_perf
            improvement_data.append(improvement)
    
    if improvement_data:
        improvement_data = np.array(improvement_data)
        print(f"Average improvement from match 1 to matches 2-5: {np.mean(improvement_data):.1f}%")
        print(f"Median improvement: {np.median(improvement_data):.1f}%")
        
        # Players who improved vs declined
        improved = sum(1 for x in improvement_data if x > 0)
        declined = sum(1 for x in improvement_data if x < 0)
        unchanged = len(improvement_data) - improved - declined
        
        print(f"Players who improved: {improved} ({improved/len(improvement_data)*100:.1f}%)")
        print(f"Players who declined: {declined} ({declined/len(improvement_data)*100:.1f}%)")
    
    # Check cross-division progression
    print(f"\nCROSS-DIVISION ANALYSIS:")
    cross_division_players = 0
    same_division_first = 0
    
    for matches in player_matches.values():
        if len(matches) >= 2:
            matches.sort(key=lambda x: x['date'])
            divisions = [m['division'] for m in matches]
            unique_divisions = set(divisions)
            
            if len(unique_divisions) > 1:
                cross_division_players += 1
            
            if matches[0]['division'] == matches[1]['division']:
                same_division_first += 1
    
    print(f"Players who shot multiple divisions: {cross_division_players}")
    print(f"Players whose first 2 matches were same division: {same_division_first}")
    
    # Recommendations for START_MU
    print(f"\n" + "="*60)
    print("RECOMMENDATIONS FOR START_MU")
    print("="*60)
    
    median_first = np.median(first_match_performances)
    mean_first = np.mean(first_match_performances)
    q25_first = np.percentile(first_match_performances, 25)
    
    print(f"Current START_MU: 25 (arbitrary)")
    print(f"")
    print(f"Option 1 - Median first match: START_MU = {median_first:.0f}")
    print(f"  Rationale: Half of new players perform better/worse than this")
    print(f"")
    print(f"Option 2 - Mean first match: START_MU = {mean_first:.0f}")
    print(f"  Rationale: Average new player performance")
    print(f"")
    print(f"Option 3 - Conservative (25th percentile): START_MU = {q25_first:.0f}")
    print(f"  Rationale: Most new players (75%) perform better than this")
    
    print(f"\n✅ RECOMMENDED: START_MU = {median_first:.0f}")
    print(f"   This makes μ values directly correspond to expected match percentages")
    print(f"   New players start at realistic performance level (median first match)")
    print(f"   Player tracking is across ALL divisions for true first match")
    
    return {
        'median_first_match': median_first,
        'mean_first_match': mean_first,
        'std_first_match': np.std(first_match_performances),
        'q25_first_match': q25_first,
        'player_count': player_count
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
    analyze_first_match_performance()