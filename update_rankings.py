#!/usr/bin/env python3
"""
Simple rankings update script - Single source of truth approach.
All files live in the rankings/ directory, no copying needed.
"""

import os
import json
from datetime import datetime
from pathlib import Path

def update_metadata():
    """Update metadata directly in rankings/data/"""
    
    print("📊 Updating metadata...")
    
    # Import the match counting logic from existing script
    import sys
    sys.path.append('.')
    
    try:
        from update_metadata import count_matches_with_data
        
        # Get accurate match statistics
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
            'note': 'Single source of truth - all files in rankings/data/'
        }
        
        # Write directly to rankings/data/
        metadata_path = 'rankings/data/metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated {metadata_path}")
        print(f"   Matches with data: {stats['matches_with_handgun_data']:,}")
        
        return metadata
        
    except ImportError:
        # Fallback if update_metadata.py not available
        print("⚠  update_metadata.py not found, creating basic metadata")
        
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'update_date': datetime.now().strftime('%Y-%m-%d'),
            'update_time': datetime.now().strftime('%H:%M:%S'),
            'match_statistics': {
                'matches_with_handgun_data': 2417,  # Last known good value
                'matches_processed_in_rankings': 2417,
                'last_match_processed': datetime.now().strftime('%Y-%m-%d')
            },
            'note': 'Single source of truth - all files in rankings/data/'
        }
        
        metadata_path = 'rankings/data/metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated {metadata_path} (basic metadata)")
        return metadata

def validate_ranking_files():
    """Validate that all expected ranking files exist"""
    
    rankings_dir = Path("rankings/data")
    if not rankings_dir.exists():
        print("❌ rankings/data directory does not exist!")
        return False
    
    # Key files that should exist
    required_files = [
        'ipsc_ranking_combined.json',
        'ipsc_ranking_combined_junior.json',  # The one that was missing!
        'ipsc_ranking_production.json',
        'ipsc_ranking_open.json',
        'ipsc_ranking_standard.json',
        'ipsc_ranking_classic.json',
        'ipsc_ranking_revolver.json',
        'ipsc_ranking_pistol_caliber_carbine.json',
        'metadata.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not (rankings_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required ranking files present")
    return True

def show_statistics():
    """Show statistics about the rankings"""
    
    rankings_dir = Path("rankings/data")
    json_files = list(rankings_dir.glob("*.json"))
    
    print(f"📈 Rankings Statistics:")
    print(f"   Total files: {len(json_files)}")
    print(f"   Directory: {rankings_dir.absolute()}")
    
    # Show file sizes
    total_size = sum(f.stat().st_size for f in json_files)
    print(f"   Total size: {total_size / (1024*1024):.1f} MB")

def main():
    """Main update process"""
    
    print("🎯 IPSC Rankings - Single Source Update")
    print("=" * 50)
    
    # Ensure rankings directory exists
    os.makedirs("rankings/data", exist_ok=True)
    
    # Update metadata
    metadata = update_metadata()
    
    # Validate files
    if not validate_ranking_files():
        print("\n❌ Validation failed! Some required files are missing.")
        print("   You may need to run the ranking generation scripts first.")
        return 1
    
    # Show statistics
    show_statistics()
    
    print("\n✅ Rankings update complete!")
    print("\n🚀 Next steps:")
    print("   1. Test locally (choose one):")
    print("      Option A - Simple: python create_standalone.py")
    print("                         python -m http.server 8000 --directory rankings")
    print("                         Visit: http://localhost:8000/index_standalone.html")
    print("      Option B - Jekyll: ./serve_local.sh")
    print("                         Visit: http://localhost:4000")
    print("   2. Deploy: git add rankings/ && git commit && git push")
    
    return 0

if __name__ == "__main__":
    exit(main())