#!/usr/bin/env python3
"""
Name normalization utilities for IPSC ranking system.
Handles special characters, aliases, and capitalization.
"""

import re
import unicodedata

def normalize_name(name):
    """
    Normalize a person's name for consistent matching.
    
    Rules:
    - Remove quotes and aliases in quotes
    - Convert to proper case (Title Case)
    - Replace special characters: ö->o, ä->a, å->a, ü->u, etc.
    - Replace ae->a, oe->o
    - Remove middle initials and dots
    - Normalize whitespace and hyphens
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Remove quotes and content within quotes (aliases)
    # "Mats \"Dalmas\" Bäckström" -> "Mats Bäckström"
    name = re.sub(r'"[^"]*"', '', name)
    
    # Remove single quotes and apostrophes
    name = name.replace("'", "").replace("`", "")
    
    # Normalize unicode to decomposed form and remove accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    
    # Additional character replacements
    replacements = {
        'ö': 'o', 'Ö': 'O',
        'ä': 'a', 'Ä': 'A', 
        'å': 'a', 'Å': 'A',
        'ü': 'u', 'Ü': 'U',
        'ø': 'o', 'Ø': 'O',
        'æ': 'a', 'Æ': 'A',
        'ß': 'ss',
        'ç': 'c', 'Ç': 'C',
        'ñ': 'n', 'Ñ': 'N'
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # Replace double-letter combinations within words
    name = re.sub(r'ae', 'a', name, flags=re.IGNORECASE)
    name = re.sub(r'oe', 'o', name, flags=re.IGNORECASE)
    
    # Remove middle initials and dots
    # "Mats O. Bäckström" -> "Mats Bäckström"
    name = re.sub(r'\b[A-Z]\.\s*', '', name)
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Convert to title case while preserving hyphens
    parts = name.split('-')
    parts = [part.strip().title() for part in parts if part.strip()]
    name = '-'.join(parts)
    
    return name

def normalize_player_id_component(text):
    """
    Normalize text for use in player IDs (lowercase, underscores).
    """
    if not text:
        return ""
    
    # First normalize the name
    text = normalize_name(text)
    
    # Convert to lowercase and replace spaces/special chars with underscores
    text = text.lower()
    text = re.sub(r'[^a-z0-9\-]', '_', text)
    text = re.sub(r'_+', '_', text)  # Collapse multiple underscores
    text = text.strip('_')  # Remove leading/trailing underscores
    
    return text

def get_normalized_player_id(first_name, last_name, region, division=None):
    """
    Generate a normalized player ID from name components.
    """
    first_norm = normalize_player_id_component(first_name)
    last_norm = normalize_player_id_component(last_name)
    region_norm = region.upper() if region else 'UNK'
    
    base_id = f"{first_norm}_{last_norm}_{region_norm}".lower()
    
    if division:
        # Normalize division for ID
        div_norm = division.lower().replace(' ', '_').replace('-', '_')
        return f"{base_id}_{div_norm}"
    
    return base_id

# Test cases
if __name__ == "__main__":
    test_cases = [
        'Mats "Dalmas" Bäckström',
        'lars-tony skoog', 
        'Mats O. Bäckström',
        'Åke Öström',
        'Jean-Marie Müller',
        'Peter ae Larsson',
        'erik oe hansen'
    ]
    
    print("Name normalization test:")
    for name in test_cases:
        normalized = normalize_name(name)
        player_id = normalize_player_id_component(name)
        print(f"{name:25} -> {normalized:20} -> {player_id}")