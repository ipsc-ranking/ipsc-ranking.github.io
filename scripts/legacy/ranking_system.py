#!/usr/bin/env python3
"""
Main entry point for the IPSC ranking system.

This script processes match data from multiple sources and generates skill-based rankings.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ranking import IPSCRankingSystem


def main():
    """Main entry point for the ranking system"""
    # Create ranking system
    ranking_system = IPSCRankingSystem()
    
    # Load and process all matches
    print("Loading matches...")
    matches = ranking_system.load_matches()
    print(f"Found {len(matches)} matches")
    
    print("Processing matches...")
    for i, match in enumerate(matches):
        print(f"Processing match {i+1}/{len(matches)}: {match.get('match_title', 'Unknown')}")
        if ('production_optics_results' in match and len(match['production_optics_results']) > 0) or \
           ('combined_results' in match and len(match['combined_results']) > 0) or \
           ('shooters' in match and len(match['shooters']) > 0):
            ranking_system.process_match(match)
    
    # Print the ranking
    print(f"\nGenerated ranking for {len(ranking_system.players)} players in {len(matches)} matches")
    ranking_system.print_ranking(top_n=50)  # Show top 50 players
    
    # Save full ranking to file
    os.makedirs('results', exist_ok=True)
    rankings = ranking_system.generate_ranking()

    with open('results/ipsc_ranking_production_optics.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(rankings, f, indent=2, ensure_ascii=False)
    
    # Save detailed match data
    match_count = ranking_system.save_match_details('results/match_details.json')
    
    print(f"\nFull ranking saved to 'results/ipsc_ranking_production_optics.json'")
    print(f"Total players ranked: {len(rankings)}")
    print(f"Detailed data for {match_count} matches saved to 'results/match_details.json'")


if __name__ == "__main__":
    main()