"""
Division name normalization for IPSC ranking system.
Maps various division name variations to standard IPSC divisions.
"""

def normalize_division_name(division_name):
    """
    Normalize division names to standard IPSC divisions.
    
    Standard divisions:
    - 'Open'
    - 'Standard' 
    - 'Production'
    - 'Revolver'
    - 'Classic'
    - 'Pistol Caliber Carbine'
    - 'Production Optics'
    
    Args:
        division_name (str): Original division name from match data
        
    Returns:
        str: Normalized division name
    """
    if not division_name:
        return 'Unknown'
    
    # Convert to lowercase and strip whitespace for comparison
    normalized = division_name.lower().strip()
    
    # Remove common suffixes like +, -, etc.
    # Keep the base division name
    base_division = normalized
    for suffix in ['+', '-', 'plus', 'minus']:
        if base_division.endswith(suffix):
            base_division = base_division[:-len(suffix)].strip()
    
    # Mapping dictionary for various division name variations
    division_mapping = {
        # Open variations
        'open': 'Open',
        'semi-auto open': 'Open',
        'semiminusauto_open': 'Open',
        'semi_auto_open': 'Open',
        
        # Standard variations  
        'standard': 'Standard',
        'semi-auto standard': 'Standard',
        'semiminusauto_standard': 'Standard',
        'semi_auto_standard': 'Standard',
        'standard_manual': 'Standard',
        
        # Production variations
        'production': 'Production',
        
        # Revolver variations
        'revolver': 'Revolver',
        
        # Classic variations
        'classic': 'Classic',
        
        # Pistol Caliber Carbine variations
        'pistol caliber carbine': 'Pistol Caliber Carbine',
        'pistol_caliber_carbine': 'Pistol Caliber Carbine',
        'pistol caliber carbine optics': 'Pistol Caliber Carbine',
        'pistol_caliber_carbine_optics': 'Pistol Caliber Carbine',
        'pistol caliber carbine iron': 'Pistol Caliber Carbine',
        'pistol_caliber_carbine_iron': 'Pistol Caliber Carbine',
        
        # Production Optics variations
        'production optics': 'Production Optics',
        'production_optics': 'Production Optics',
        'production optics light': 'Production Optics',
        'production_optics_light': 'Production Optics',
        
        # Handle other variations that might appear
        'modified': 'Open',  # Modified is typically similar to Open
        'custom': 'Open',    # Custom is typically similar to Open
        'semi-auto limited': 'Standard',  # Limited is typically similar to Standard
        'semiminusauto_limited': 'Standard',
    }
    
    # Try to find exact match first
    if base_division in division_mapping:
        return division_mapping[base_division]
    
    # Try partial matching for compound names
    for key, value in division_mapping.items():
        if key in base_division or base_division in key:
            return value
    
    # If no match found, try to make a reasonable guess based on keywords
    if 'open' in base_division:
        return 'Open'
    elif 'standard' in base_division:
        return 'Standard'
    elif 'production' in base_division and 'optics' in base_division:
        return 'Production Optics'
    elif 'production' in base_division:
        return 'Production'
    elif 'revolver' in base_division:
        return 'Revolver'
    elif 'classic' in base_division:
        return 'Classic'
    elif 'pistol' in base_division and 'carbine' in base_division:
        return 'Pistol Caliber Carbine'
    elif 'carbine' in base_division:
        return 'Pistol Caliber Carbine'
    
    # If still no match, return the original name cleaned up
    return division_name.strip()


def get_division_statistics(matches_data):
    """
    Analyze division names in match data to understand the variations present.
    
    Args:
        matches_data (list): List of match data dictionaries
        
    Returns:
        dict: Statistics about division name variations
    """
    division_counts = {}
    normalized_counts = {}
    
    for match in matches_data:
        if 'combined_results' in match:
            for result in match['combined_results']:
                original_division = result.get('division', 'Unknown')
                normalized_division = normalize_division_name(original_division)
                
                # Count original divisions
                division_counts[original_division] = division_counts.get(original_division, 0) + 1
                
                # Count normalized divisions
                normalized_counts[normalized_division] = normalized_counts.get(normalized_division, 0) + 1
    
    return {
        'original_divisions': division_counts,
        'normalized_divisions': normalized_counts,
        'total_original_variations': len(division_counts),
        'total_normalized_divisions': len(normalized_counts)
    }


if __name__ == "__main__":
    # Test the normalization function
    test_divisions = [
        "Open+", "Open-", "Open",
        "Standard+", "Standard-", "Standard",
        "Production+", "Production-", "Production",
        "Production Optics+", "Production Optics-", "Production Optics",
        "Revolver+", "Revolver-", "Revolver",
        "Classic+", "Classic-", "Classic",
        "Pistol Caliber Carbine+", "Pistol Caliber Carbine-",
        "Pistol Caliber Carbine Optics+", "Pistol Caliber Carbine Optics-",
        "Semi-Auto Open", "Semi-Auto Standard",
        "Modified", "Custom"
    ]
    
    print("Division Normalization Test:")
    print("=" * 50)
    for division in test_divisions:
        normalized = normalize_division_name(division)
        print(f"{division:<30} -> {normalized}")