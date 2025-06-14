#!/usr/bin/env python3
"""
Test script to verify division normalization is working correctly.
"""

import json
import os
from collections import defaultdict
from division_normalizer import normalize_division_name, get_division_statistics

def test_normalization():
    """Test the division normalization on actual match data"""
    
    # Load a few match files to test
    match_files_location = './match_data/'
    matches = []
    
    # Load first 10 match files for testing
    count = 0
    for filename in sorted(os.listdir(match_files_location)):
        if filename.endswith('.json') and count < 10:
            filepath = os.path.join(match_files_location, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                    if 'combined_results' in match_data and len(match_data['combined_results']) > 0:
                        matches.append(match_data)
                        count += 1
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    print(f"Loaded {len(matches)} matches for testing")
    
    # Analyze division variations
    stats = get_division_statistics(matches)
    
    print("\n" + "="*60)
    print("DIVISION NORMALIZATION TEST RESULTS")
    print("="*60)
    print(f"Original division variations: {stats['total_original_variations']}")
    print(f"Normalized divisions: {stats['total_normalized_divisions']}")
    
    print(f"\nOriginal -> Normalized mappings:")
    print("-" * 50)
    sorted_original = sorted(stats['original_divisions'].items(), key=lambda x: x[1], reverse=True)
    for division, count in sorted_original:
        normalized = normalize_division_name(division)
        print(f"{division:<30} ({count:>3}) -> {normalized}")
    
    print(f"\nNormalized division counts:")
    print("-" * 30)
    for division, count in sorted(stats['normalized_divisions'].items()):
        print(f"{division:<25}: {count:>4} players")
    
    # Test specific cases
    print(f"\nTesting specific normalization cases:")
    print("-" * 40)
    test_cases = [
        "Production Optics-",
        "Standard+", 
        "Open-",
        "Pistol Caliber Carbine Optics-",
        "Semi-Auto Open",
        "Production-"
    ]
    
    for case in test_cases:
        normalized = normalize_division_name(case)
        print(f"{case:<30} -> {normalized}")

if __name__ == "__main__":
    test_normalization()