#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3
"""
Create sample Norwegian IPSC matches for testing the ranking system
"""

import json
import os
from datetime import datetime, timedelta
import random

def create_sample_match(match_id, title, date, level="Level II", shooters_count=30):
    """Create a sample match with realistic Norwegian shooter data"""
    
    # Norwegian names and regions
    norwegian_names = [
        ("Lars", "Hansen"), ("Erik", "Johansen"), ("Ole", "Olsen"), ("Nils", "Nielsen"),
        ("Bjørn", "Andersen"), ("Kari", "Larsen"), ("Anna", "Pedersen"), ("Per", "Kristensen"),
        ("Tor", "Berg"), ("Gunnar", "Dahl"), ("Magnus", "Haugen"), ("Stein", "Bakken"),
        ("Rune", "Eriksen"), ("Geir", "Svendsen"), ("Trond", "Moen"), ("Øyvind", "Lund"),
        ("Jonas", "Solberg"), ("Andreas", "Fossum"), ("Martin", "Strand"), ("Thomas", "Røed"),
        ("Fredrik", "Holm"), ("Kristian", "Lie"), ("Morten", "Kval"), ("Sindre", "Vik"),
        ("Håkon", "Dale"), ("Espen", "Mo"), ("Audun", "Bø"), ("Frode", "Nes"),
        ("Line", "Sæther"), ("Ingrid", "Rød"), ("Maria", "Knudsen"), ("Hilde", "Aas"),
        ("Silje", "Eide"), ("Cathrine", "Skjøt"), ("Ida", "Myhre"), ("Julie", "Gilje"),
        ("Astrid", "Nygård"), ("Tone", "Grimm"), ("Liv", "Borg"), ("Ruth", "Sand")
    ]
    
    # Select random shooters
    selected_shooters = random.sample(norwegian_names, min(shooters_count, len(norwegian_names)))
    
    # Generate realistic match percentages (top shooter = 100%, others distributed)
    base_scores = sorted([random.uniform(75, 99.5) for _ in range(len(selected_shooters))], reverse=True)
    # Normalize so best score is 100%
    max_score = base_scores[0]
    match_percentages = [(score / max_score) * 100 for score in base_scores]
    
    shooters = []
    for i, ((first_name, last_name), percentage) in enumerate(zip(selected_shooters, match_percentages)):
        shooters.append({
            "first_name": first_name,
            "last_name": last_name,
            "alias": "",
            "region": "NOR",
            "division": "Production Optics",
            "match_percentage": round(percentage, 2),
            "placement": i + 1
        })
    
    match_data = {
        "match_id": match_id,
        "match_title": title,
        "match_date": date,
        "match_level": level,
        "club_name": "Norwegian Shooting Club",
        "production_optics_results": shooters,
        "combined_results": shooters  # For compatibility
    }
    
    return match_data

def main():
    """Create several sample matches"""
    
    # Ensure match_data directory exists
    os.makedirs('match_data', exist_ok=True)
    
    # Create sample matches over the past year
    base_date = datetime.now() - timedelta(days=365)
    
    sample_matches = [
        (100001, "Oslo IPSC Open 2024", "Level III"),
        (100002, "Bergen Shooting Championship", "Level II"), 
        (100003, "Trondheim Winter Match", "Level II"),
        (100004, "Stavanger IPSC Cup", "Level II"),
        (100005, "Northern Norway Championships", "Level III"),
        (100006, "Oslo Indoor Series #1", "Level II"),
        (100007, "Bergen Spring Match", "Level II"),
        (100008, "Trondheim Summer Cup", "Level II"),
        (100009, "Stavanger Autumn Classic", "Level II"),
        (100010, "Norwegian IPSC Nationals", "Level IV"),
        (100011, "Oslo Indoor Series #2", "Level II"),
        (100012, "Bergen Winter Challenge", "Level II"),
        (100013, "Trondheim New Year Match", "Level II"),
        (100014, "Stavanger Spring Open", "Level II"),
        (100015, "Northern Lights IPSC", "Level II"),
    ]
    
    created_matches = 0
    
    for i, (match_id, title, level) in enumerate(sample_matches):
        # Calculate match date (spread over the year)
        match_date = base_date + timedelta(days=i * 25)
        date_str = match_date.strftime('%Y-%m-%dT10:00:00')
        
        # Vary shooter count (20-40 shooters per match)
        shooter_count = random.randint(20, 40)
        
        # Create match data
        match_data = create_sample_match(match_id, title, date_str, level, shooter_count)
        
        # Save to file
        filename = f'match_data/match_{match_id}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created {filename}: {title} ({len(match_data['production_optics_results'])} shooters)")
        created_matches += 1
    
    print(f"\nSuccessfully created {created_matches} sample matches!")
    print("Run 'python process_matches.py' to generate rankings from these matches.")

if __name__ == "__main__":
    main()