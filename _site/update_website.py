#!/usr/bin/env python3
"""
Script to update the website data files from the results directory.
This script should be run after generating new ranking data.
"""

import os
import shutil
import json
from datetime import datetime
import argparse

def copy_ranking_files():
    """Copy JSON ranking files from results/ to docs/data/"""
    source_dir = "results"
    target_dir = "docs/data"
    
    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Copy all JSON files
    json_files = [f for f in os.listdir(source_dir) if f.endswith('.json')]
    
    copied_files = []
    for filename in json_files:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        try:
            shutil.copy2(source_path, target_path)
            copied_files.append(filename)
            print(f"✓ Copied {filename}")
        except Exception as e:
            print(f"✗ Failed to copy {filename}: {e}")
    
    return copied_files

def generate_stats():
    """Generate statistics about the ranking data"""
    data_dir = "docs/data"
    stats = {}
    
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    division = filename.replace('ipsc_ranking_', '').replace('.json', '')
                    stats[division] = {
                        'players': len(data),
                        'file_size': os.path.getsize(filepath)
                    }
            except Exception as e:
                print(f"Warning: Could not read {filename}: {e}")
    
    return stats

def update_last_modified():
    """Update the last modified timestamp in the website"""
    timestamp = datetime.now().isoformat()
    
    # Create a simple JSON file with metadata
    metadata = {
        'last_updated': timestamp,
        'update_date': datetime.now().strftime('%Y-%m-%d'),
        'update_time': datetime.now().strftime('%H:%M:%S')
    }
    
    with open('docs/data/metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Updated metadata with timestamp: {timestamp}")

def validate_data_files():
    """Validate that all expected data files exist and are valid JSON"""
    expected_files = [
        'ipsc_ranking_combined.json',
        'ipsc_ranking_classic.json',
        'ipsc_ranking_open.json',
        'ipsc_ranking_production.json',
        'ipsc_ranking_production_optics.json',
        'ipsc_ranking_standard.json',
        'ipsc_ranking_revolver.json',
        'ipsc_ranking_pistol_caliber_carbine.json'
    ]
    
    data_dir = "docs/data"
    missing_files = []
    invalid_files = []
    
    for filename in expected_files:
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            missing_files.append(filename)
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    invalid_files.append(f"{filename} (not a list)")
                elif len(data) == 0:
                    invalid_files.append(f"{filename} (empty)")
        except json.JSONDecodeError as e:
            invalid_files.append(f"{filename} (invalid JSON: {e})")
        except Exception as e:
            invalid_files.append(f"{filename} (error: {e})")
    
    if missing_files:
        print("✗ Missing files:")
        for filename in missing_files:
            print(f"  - {filename}")
    
    if invalid_files:
        print("✗ Invalid files:")
        for filename in invalid_files:
            print(f"  - {filename}")
    
    if not missing_files and not invalid_files:
        print("✓ All data files are valid")
        return True
    
    return False

def main():
    parser = argparse.ArgumentParser(description='Update website data files')
    parser.add_argument('--validate-only', action='store_true', 
                       help='Only validate existing files, do not copy')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics about the data files')
    
    args = parser.parse_args()
    
    print("Svenska IPSC Ranking - Website Update Tool")
    print("=" * 50)
    
    if args.validate_only:
        print("Validating data files...")
        if validate_data_files():
            print("✓ Validation passed")
            return 0
        else:
            print("✗ Validation failed")
            return 1
    
    # Copy files
    print("Copying ranking files...")
    copied_files = copy_ranking_files()
    
    if not copied_files:
        print("✗ No files were copied")
        return 1
    
    # Validate copied files
    print("\nValidating copied files...")
    if not validate_data_files():
        print("✗ Validation failed after copying")
        return 1
    
    # Update metadata
    print("\nUpdating metadata...")
    update_last_modified()
    
    # Show statistics if requested
    if args.stats:
        print("\nData statistics:")
        stats = generate_stats()
        for division, info in stats.items():
            size_mb = info['file_size'] / (1024 * 1024)
            print(f"  {division}: {info['players']} players, {size_mb:.1f} MB")
    
    print(f"\n✓ Successfully updated website data ({len(copied_files)} files)")
    print("\nNext steps:")
    print("1. Test the website locally: python -m http.server 8000 --directory docs")
    print("2. Commit and push changes to deploy to GitHub Pages")
    
    return 0

if __name__ == "__main__":
    exit(main())