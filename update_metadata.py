#!/usr/bin/env python3
"""
Update metadata.json with accurate match counts and statistics
"""

import json
import os
from datetime import datetime
from collections import defaultdict

def has_handgun_results(match_data):
    """Check if match has any handgun results"""
    
    # Check for combined_results (main field)
    if match_data.get('combined_results'):
        return len(match_data['combined_results']) > 0
    
    # Check for shooters field (alternative)
    if match_data.get('shooters'):
        return len(match_data['shooters']) > 0
    
    # Check for production_optics_results (SSI format)
    if match_data.get('production_optics_results'):
        return len(match_data['production_optics_results']) > 0
    
    # Check for any division-specific results
    handgun_divisions = [
        'production_results', 'open_results', 'standard_results',
        'classic_results', 'revolver_results', 'production_optics_results'
    ]
    
    for division in handgun_divisions:
        if match_data.get(division) and len(match_data[division]) > 0:
            return True
    
    return False

def get_match_source(filename):
    """Determine match source from filename"""
    if '_ssi_' in filename:
        return 'SSI'
    elif '_ipscresults_' in filename:
        return 'IPSC Results'
    elif '_practiscore_' in filename:
        return 'PractiScore'
    elif filename.startswith('match_'):
        return 'SSI'  # Legacy SSI files
    else:
        return 'Unknown'

def count_matches_with_data():
    """Count matches that actually have handgun result data"""
    print("🔍 Counting matches with actual handgun result data...")
    
    match_files = [f for f in os.listdir('data/matches') if f.endswith('.json')]
    
    total_files = len(match_files)
    matches_with_data = 0
    matches_without_data = 0
    source_counts = defaultdict(int)
    source_with_data = defaultdict(int)
    
    for i, filename in enumerate(match_files):
        if i % 1000 == 0:
            print(f"  Progress: {i}/{total_files} files checked")
        
        filepath = f'data/matches/{filename}'
        source = get_match_source(filename)
        source_counts[source] += 1
        
        try:
            with open(filepath, 'r') as f:
                match_data = json.load(f)
            
            if has_handgun_results(match_data):
                matches_with_data += 1
                source_with_data[source] += 1
            else:
                matches_without_data += 1
                
        except Exception as e:
            print(f"  Error reading {filename}: {e}")
            matches_without_data += 1
    
    print(f"\n📊 Match Data Summary:")
    print(f"  Total match files: {total_files}")
    print(f"  Matches with handgun data: {matches_with_data}")
    print(f"  Matches without data: {matches_without_data}")
    print(f"  Data coverage: {matches_with_data/total_files*100:.1f}%")
    
    print(f"\n📂 By Source:")
    for source in sorted(source_counts.keys()):
        total = source_counts[source]
        with_data = source_with_data[source]
        coverage = with_data/total*100 if total > 0 else 0
        print(f"  {source}: {with_data}/{total} matches ({coverage:.1f}%)")
    
    return {
        'total_match_files': total_files,
        'matches_with_handgun_data': matches_with_data,
        'matches_without_data': matches_without_data,
        'data_coverage_percent': round(matches_with_data/total_files*100, 1),
        'source_breakdown': {
            source: {
                'total_files': source_counts[source],
                'matches_with_data': source_with_data[source],
                'coverage_percent': round(source_with_data[source]/source_counts[source]*100, 1) if source_counts[source] > 0 else 0
            }
            for source in sorted(source_counts.keys())
        }
    }

def update_metadata():
    """Update metadata.json with current statistics"""
    
    stats = count_matches_with_data()
    
    metadata = {
        'last_updated': datetime.now().isoformat(),
        'update_date': datetime.now().strftime('%Y-%m-%d'),
        'update_time': datetime.now().strftime('%H:%M:%S'),
        'match_statistics': {
            'total_match_files': stats['total_match_files'],
            'matches_with_handgun_data': stats['matches_with_handgun_data'],
            'matches_without_data': stats['matches_without_data'],
            'data_coverage_percent': stats['data_coverage_percent']
        },
        'data_sources': stats['source_breakdown'],
        'note': 'Website displays only matches with actual handgun result data'
    }
    
    # Update all metadata files
    metadata_files = [
        'docs/data/metadata.json',
        'data/metadata.json'
    ]
    
    for filepath in metadata_files:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated {filepath}")
    
    return metadata

if __name__ == "__main__":
    print("🎯 Updating metadata with accurate match counts...")
    metadata = update_metadata()
    
    print(f"\n🏆 Final Statistics for Website:")
    print(f"  Matches with handgun data: {metadata['match_statistics']['matches_with_handgun_data']:,}")
    print(f"  Data coverage: {metadata['match_statistics']['data_coverage_percent']}%")
    print(f"  Last updated: {metadata['update_date']} at {metadata['update_time']}")