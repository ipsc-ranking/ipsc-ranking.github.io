import requests
from bs4 import BeautifulSoup
import re
from dateutil import parser

import json
import os

import openskill


LEVELS = {'Level II', 'Level III', ' Level IV', 'Level V'}

DIVISIONS = {
    'Open', 'Standard', 'Production', 'Revolver', 'Classic',
    'Pistol Caliber Carbine', 'Production Optics'
}

def parse_date_string(date_text):
    """Parse date string with special handling for noon/midnight"""
    if not date_text:
        return None
        
    try:
        # Handle special cases
        date_text_clean = date_text.strip()
        
        # Replace noon and midnight with times
        if ', noon' in date_text_clean:
            date_text_clean = date_text_clean.replace(', noon', ' 12:00 PM')
        elif ', midnight' in date_text_clean:
            date_text_clean = date_text_clean.replace(', midnight', ' 12:00 AM')
        
        # Parse the cleaned date string
        parsed_date = parser.parse(date_text_clean)
        return parsed_date.isoformat()
    except Exception as e:
        print(f"Error parsing date '{date_text}': {e}")
        return None

def parse_results(soup):
    """Parse the Production Optics results from the HTML"""
    results = []
    
    # Find the results table
    table = soup.find('table', id='sortTable')
    if not table:
        return results
    
    # Find all result rows (skip header)
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 11:  # Ensure we have all expected columns
            # Parse category abbreviation
            #cat_cell = cells[6].find('abbr')
            category =  cells[6].get_text(strip=True)
            if category == 'None':
                category = []
            else:
                category = [c.strip() for c in category.split(' ')]
            
            result = {
                'position': int(cells[0].get_text(strip=True)),
                'match_percentage': float(cells[1].get_text(strip=True)),
                'match_points': float(cells[2].get_text(strip=True)),
                'first_name': cells[3].get_text(strip=True),
                'last_name': cells[4].get_text(strip=True),
                'division': cells[5].get_text(strip=True),
                'category': category,
                'region': cells[7].get_text(strip=True),
                'classification': cells[8].get_text(strip=True),
                'alias': cells[9].get_text(strip=True),
                'club': cells[10].get_text(strip=True)
            }
            results.append(result)
    
    return results

def get_match_info(match_id):
    url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/selection/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    match_info = {
        'match_id': match_id,
        'divisions': [],
        'match_url': None,
        'match_title': None,
        'match_level': None
    }

    has_production_optics = False
    
    # Find the first ssi-table that contains the divisions and return URL
    first_table = soup.find('div', class_='ssi-table')
    if first_table:
        # Get the match title from the title row
        title_row = first_table.find('div', class_='ssi-title-row')
        if title_row:
            # Extract title text (excluding the "return" button text)
            title_text = title_row.get_text(strip=True)
            if title_text.endswith('return'):
                title_text = title_text[:-6].strip()  # Remove "return" from the end
            match_info['match_title'] = title_text
            
            # Find the return URL button
            return_btn = title_row.find('a', class_='btn btn-primary')
            if return_btn:
                match_info['match_url'] = return_btn.get('href')
        
        # Find all division links in the items-spaced-8px div
        items_div = first_table.find('div', class_='items-spaced-8px')
        if items_div:
            # Get all links that contain '/div/' in their href (excluding category links)
            division_links = items_div.find_all('a', href=lambda x: x and '/div/' in x and '/cat/' not in x)
            
            for link in division_links:
                # Skip the "Combined" link
                if 'combined' not in link.get('href', '') and False:
                    name = link.text.strip()
                    if name == 'Production Optics':
                        has_production_optics = True
                    match_info['divisions'].append({
                        'url': link.get('href'),
                        'name': name
                    })

    
    
    # Fetch match level from the match URL
    if match_info['match_url']:
        match_response = requests.get('https://shootnscoreit.com' + match_info['match_url'])
        #print(match_response.text)
        match_soup = BeautifulSoup(match_response.text, 'html.parser')
        
        level_match = re.search(r'Level\s+(I{1,3}|IV|V)', match_response.text, re.IGNORECASE)
        if level_match:
            match_info['match_level'] = level_match.group(0)

        # Extract match date from the ssi-card-title
        date_title = match_soup.find('div', class_='ssi-card-title title-2')
        if date_title:
            date_text = date_title.get_text(strip=True)
            match_info['match_date'] = parse_date_string(date_text)

    if has_production_optics and match_info['match_level'] in LEVELS:
        url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/div/hg18/'
        result_response = requests.get(url)
        result_soup = BeautifulSoup(result_response.text, 'html.parser')
        production_optics_results = parse_results(result_soup)

        match_info['production_optics_results'] = production_optics_results

    
    return match_info


def save_match_info(match_info, output_dir="match_data"):
    """Save match info to a JSON file"""
    if not match_info:
        return
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    match_id = match_info['match_id']
    filename = f"match_{match_id}.json"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(match_info, f, indent=2, ensure_ascii=False)
        print(f"Saved match {match_id} to {filepath}")
    except Exception as e:
        print(f"Error saving match {match_id}: {e}")
# Test with the match ID from your example
#match_id = 22747

#1100 earliest known
#My first 13423

def main():
    """Main function to iterate over match IDs and save data"""
    # You can adjust this range based on your needs
    # Start from a reasonable number and go up to current matches
    start_match_id = 1  # Adjust as needed
    end_match_id = 23000    # Adjust as needed
    
    # Or you can provide a specific list of match IDs
    # match_ids = [22747, 22748, 22749]  # Example specific IDs
    
    output_dir = "match_data"
    
    print(f"Starting to process matches from {start_match_id} to {end_match_id}")
    print(f"Output directory: {output_dir}")
    
    successful_matches = 0
    failed_matches = 0
    
    for match_id in range(start_match_id, end_match_id + 1):
        # Check if file already exists
        filepath = os.path.join(output_dir, f"match_{match_id}.json")
        if os.path.exists(filepath):
            print(f"Match {match_id} already processed, skipping...")
            continue
            
        match_info = get_match_info(match_id)
        
        if match_info:
            save_match_info(match_info, output_dir)
            successful_matches += 1
        else:
            failed_matches += 1
            
        # Be respectful to the server - add a small delay
        #time.sleep(1)
        
        # Print progress every 50 matches
        if (match_id - start_match_id + 1) % 50 == 0:
            print(f"Progress: {match_id - start_match_id + 1} matches processed. "
                  f"Successful: {successful_matches}, Failed: {failed_matches}")
    
    print(f"\nCompleted processing matches {start_match_id} to {end_match_id}")
    print(f"Successful: {successful_matches}, Failed: {failed_matches}")
    print(f"Data saved to: {output_dir}/")

if __name__ == "__main__":
    main()