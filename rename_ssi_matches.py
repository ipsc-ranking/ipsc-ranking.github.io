#!/usr/bin/env python3
"""
Rename SSI match files to include dates and titles for better identification
"""

import json
import os
import re
from datetime import datetime

def create_safe_filename(name, date, match_id):
    """Create a safe filename from match name and date"""
    if not name or name == 'null':
        name = 'Unknown_Match'
    
    # Clean the name for filename use
    safe_name = re.sub(r'[^\w\s-]', '', str(name))
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    safe_name = safe_name.strip('_')[:30]
    
    # Extract date part
    if date and date != 'null':
        try:
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            date_part = dt.strftime('%Y-%m-%d')
        except:
            date_part = 'unknown_date'
    else:
        date_part = 'unknown_date'
    
    return f'{date_part}_ssi_{safe_name}_{match_id}.json'

def main():
    print('🎯 Renaming SSI match files to include dates...')

    # Count current SSI files
    match_files = [f for f in os.listdir('data/matches') if f.startswith('match_') and f.endswith('.json')]
    print(f'Found {len(match_files)} SSI match files to process')

    renamed = 0
    skipped = 0

    for filename in match_files:
        filepath = f'data/matches/{filename}'
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            match_id = data.get('match_id')
            match_title = data.get('match_title')
            match_date = data.get('match_date')
            
            # Skip empty matches
            if not match_title or match_title == 'null':
                skipped += 1
                continue
            
            # Create new filename
            new_filename = create_safe_filename(match_title, match_date, match_id)
            new_filepath = f'data/matches/{new_filename}'
            
            # Skip if new file already exists
            if os.path.exists(new_filepath):
                skipped += 1
                continue
            
            # Rename the file
            os.rename(filepath, new_filepath)
            renamed += 1
            
            if renamed % 50 == 0:
                title = str(match_title)[:30]
                date = match_date[:10] if match_date else 'unknown'
                print(f'  ✓ Renamed {renamed}: {title}... ({date})')
                
        except Exception as e:
            print(f'  ❌ Error processing {filename}: {e}')
            continue

    print(f'\n✅ Renamed {renamed} SSI matches, skipped {skipped}')
    
    # Show sample of new filenames
    print('Sample of new SSI filenames:')
    ssi_files = [f for f in os.listdir('data/matches') if '_ssi_' in f][:5]
    for f in ssi_files:
        print(f'  {f}')

if __name__ == "__main__":
    main()