#!/usr/bin/env python3
"""
Quick test of the reorganized structure.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        from data_sources import create_iterator, MatchDataIterator
        print("✓ Data sources import successful")
    except ImportError as e:
        print(f"✗ Data sources import failed: {e}")
        return False
    
    try:
        from ranking import IPSCRankingSystem
        print("✓ Ranking system import successful")
    except ImportError as e:
        print(f"✗ Ranking system import failed: {e}")
        return False
    
    try:
        from utils import normalize_division_name
        print("✓ Utils import successful")
    except ImportError as e:
        print(f"✗ Utils import failed: {e}")
        return False
    
    return True


def test_iterator_creation():
    """Test that iterators can be created"""
    print("\nTesting iterator creation...")
    
    try:
        from data_sources import create_iterator
        
        # Test file-based iterator
        iterator = create_iterator('all', 'file', match_data_dir='./data/matches/')
        print("✓ File-based iterator created successfully")
        
        # Test that it has the expected methods
        assert hasattr(iterator, '__iter__')
        assert hasattr(iterator, 'get_source_name')
        print("✓ Iterator has required methods")
        
        return True
    except Exception as e:
        print(f"✗ Iterator creation failed: {e}")
        return False


def test_ranking_system():
    """Test that ranking system can be created"""
    print("\nTesting ranking system...")
    
    try:
        from ranking import IPSCRankingSystem
        
        system = IPSCRankingSystem()
        print("✓ Ranking system created successfully")
        
        # Test that it has expected methods
        assert hasattr(system, 'load_matches')
        assert hasattr(system, 'process_match')
        assert hasattr(system, 'generate_ranking')
        print("✓ Ranking system has required methods")
        
        return True
    except Exception as e:
        print(f"✗ Ranking system creation failed: {e}")
        return False


def test_data_loading():
    """Test basic data loading"""
    print("\nTesting data loading...")
    
    try:
        from data_sources import create_iterator
        
        iterator = create_iterator('all', 'file', match_data_dir='./data/matches/')
        
        # Get matches to check for proper discipline filtering
        matches = []
        for i, match in enumerate(iterator):
            matches.append(match)
            if i >= 10:  # Get first 11 to check
                break
        
        print(f"✓ Successfully loaded {len(matches)} matches")
        
        if matches:
            for i, match in enumerate(matches):
                print(f"✓ Match {i+1}: {match.get('match_title', 'Unknown')} from {match.get('source', 'unknown source')} (Level: {match.get('match_level', 'N/A')})")
                # Check if it's a shotgun match
                title_lower = match.get('match_title', '').lower()
                if any(keyword in title_lower for keyword in ['shotgun', 'hagel', 'skeet', 'trap']):
                    print(f"  ⚠️  WARNING: This appears to be a shotgun match!")
        
        return True
    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Testing reorganized IPSC ranking system structure")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_iterator_creation,
        test_ranking_system,
        test_data_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The reorganized structure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the reorganized structure.")
        return 1


if __name__ == "__main__":
    sys.exit(main())