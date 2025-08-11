#!/usr/bin/env python3
"""
Rename existing match files to use timestamp_source_id.json format
"""

import os
import json
import glob
from datetime import datetime

def extract_match_date(filepath):
    """Extract match date from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        match_date = data.get('match_date', '')
        if 'T' in match_date:
            return match_date.split('T')[0]
        elif '-' in match_date and len(match_date) >= 10:
            return match_date[:10]
        else:
            # Default to a very old date for unknown dates
            return '1900-01-01'
    except:
        return '1900-01-01'

def determine_source(filepath, data):
    """Determine source based on file content"""
    filename = os.path.basename(filepath)
    
    # Check if it's already in new format
    if '_' in filename and not filename.startswith('match_'):
        return None  # Already renamed
    
    # Check for practiscore indicators
    if any(key in data for key in ['production_optics_results', 'combined_results']):
        if data.get('match_id', 0) >= 100000:  # High ID suggests practiscore
            return 'practiscore'
    
    # Check for SSI/Swedish indicators
    if 'shooters' in data:
        return 'ssi'
    
    # Default to ssi for older matches
    return 'ssi'

def main():
    print("🔄 Renaming match files to new timestamp_source_id.json format...")
    
    # Find all match files
    match_files = glob.glob('match_data/match_*.json')
    
    renamed = 0
    skipped = 0
    
    for filepath in match_files:
        try:
            # Load the match data
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract info for new filename
            match_date = extract_match_date(filepath)
            source = determine_source(filepath, data)
            match_id = data.get('match_id', 'unknown')
            
            if source is None:
                skipped += 1
                continue
            
            # Create new filename
            new_filename = f"match_data/{match_date}_{source}_{match_id}.json"
            
            # Check if new file already exists
            if os.path.exists(new_filename):
                print(f"  Skip {os.path.basename(filepath)} -> already exists as {os.path.basename(new_filename)}")
                skipped += 1
                continue
            
            # Rename the file
            os.rename(filepath, new_filename)
            print(f"  ✓ {os.path.basename(filepath)} -> {os.path.basename(new_filename)}")
            renamed += 1
            
        except Exception as e:
            print(f"  ✗ Error renaming {filepath}: {e}")
            skipped += 1
    
    print(f"\n✅ Renaming complete!")
    print(f"  Renamed: {renamed} files")
    print(f"  Skipped: {skipped} files")
    
    # Show the new file structure
    print(f"\n📁 New file structure preview:")
    new_files = sorted(glob.glob('match_data/*_*_*.json'))[:10]
    for f in new_files:
        print(f"  {os.path.basename(f)}")
    
    if len(new_files) > 10:
        print(f"  ... and {len(glob.glob('match_data/*_*_*.json')) - 10} more files")

if __name__ == "__main__":
    main()