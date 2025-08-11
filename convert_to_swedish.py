#!/usr/bin/env python3
"""
Simple script to convert Norwegian practiscore data to Swedish for testing integration
"""

import json

# Read the Norwegian match
with open('match_data/match_100001.json', 'r', encoding='utf-8') as f:
    match_data = json.load(f)

# Convert to Swedish
match_data['match_id'] = 200001
match_data['match_title'] = 'Stockholm IPSC Open 2024'
match_data['club_name'] = 'Swedish Shooting Club'

# Convert first 10 Norwegian players to Swedish players with Swedish names
swedish_names = [
    ('Erik', 'Andersson'),
    ('Anna', 'Johansson'),
    ('Magnus', 'Karlsson'),
    ('Lisa', 'Nilsson'),
    ('Johan', 'Eriksson'),
    ('Emma', 'Larsson'),
    ('Anders', 'Olsson'),
    ('Sara', 'Persson'),
    ('Mikael', 'Svensson'),
    ('Maria', 'Gustafsson')
]

# Update production_optics_results
for i, shooter in enumerate(match_data['production_optics_results'][:10]):
    if i < len(swedish_names):
        shooter['first_name'] = swedish_names[i][0]
        shooter['last_name'] = swedish_names[i][1]
        shooter['region'] = 'SWE'

# Keep remaining players as Norwegian but limit to first 10
match_data['production_optics_results'] = match_data['production_optics_results'][:10]

# Update combined_results to match
for i, shooter in enumerate(match_data['combined_results'][:10]):
    if i < len(swedish_names):
        shooter['first_name'] = swedish_names[i][0]
        shooter['last_name'] = swedish_names[i][1]
        shooter['region'] = 'SWE'

match_data['combined_results'] = match_data['combined_results'][:10]

# Save as new match
with open('match_data/match_200001.json', 'w', encoding='utf-8') as f:
    json.dump(match_data, f, indent=2, ensure_ascii=False)

print("Created match_200001.json with Swedish players for testing")