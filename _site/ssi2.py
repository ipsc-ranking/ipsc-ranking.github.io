import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from dateutil import parser
import json
import os
from typing import Optional, Dict, Any, List

LEVELS = {'Level II', 'Level III', 'Level IV', 'Level V'}

DIVISIONS = {
    'Open', 'Standard', 'Production', 'Revolver', 'Classic',
    'Pistol Caliber Carbine', 'Production Optics'
}

# Async-safe counters
class AsyncCounter:
    def __init__(self):
        self._value = 0
        self._lock = asyncio.Lock()
    
    async def increment(self):
        async with self._lock:
            self._value += 1
            return self._value
    
    @property
    def value(self):
        return self._value

# Global counters
successful_counter = AsyncCounter()
failed_counter = AsyncCounter()
skipped_counter = AsyncCounter()

def parse_date_string(date_text: str) -> Optional[str]:
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

def parse_combined_results(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse the combined results from the HTML"""
    results = []
    
    # Find the results table
    table = soup.find('table', id='sortTable')
    if not table:
        return results
    
    # Find all result rows (skip header)
    tbody = table.find('tbody')
    if not tbody:
        return results
        
    rows = tbody.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 11:  # Ensure we have all expected columns
            # Parse category abbreviation
            category = cells[6].get_text(strip=True)
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

def check_existing_match_data(match_id: int, output_dir: str = "match_data") -> Optional[Dict[str, Any]]:
    """Check if match data already exists and return its info"""
    filepath = os.path.join(output_dir, f"match_{match_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Error reading existing match {match_id}: {e}")
    return None

def is_match_eligible(match_info: Optional[Dict[str, Any]]) -> bool:
    """Check if match is Level II or above and has eligible divisions"""
    if not match_info:
        return True  # If we don't have info, we should check
    
    match_level = match_info.get('match_level')
    if match_level not in LEVELS:
        return False
    
    # Check if any of the match divisions are in our DIVISIONS set
    match_divisions = {div['name'] for div in match_info.get('divisions', [])}
    has_eligible_division = bool(match_divisions.intersection(DIVISIONS))
    
    return has_eligible_division

async def get_match_info(session: aiohttp.ClientSession, match_id: int) -> Optional[Dict[str, Any]]:
    """Get match info including combined results if it's Level II or above and has eligible divisions"""
    url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/selection/'
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            text = await response.text()
    except Exception as e:
        print(f"Error fetching match {match_id}: {e}")
        return None
        
    soup = BeautifulSoup(text, 'html.parser')
    
    match_info = {
        'match_id': match_id,
        'divisions': [],
        'match_url': None,
        'match_title': None,
        'match_level': None,
        'match_date': None
    }
    
    # Find the first ssi-table that contains the divisions and return URL
    first_table = soup.find('div', class_='ssi-table')
    if not first_table:
        print(f"No table found for match {match_id}")
        return None
        
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
            # Skip the "Combined" link for divisions list
            if 'combined' not in link.get('href', ''):
                name = link.text.strip()
                match_info['divisions'].append({
                    'url': link.get('href'),
                    'name': name
                })
    
    # Fetch match level and date from the match URL
    if match_info['match_url']:
        try:
            async with session.get('https://shootnscoreit.com' + match_info['match_url'], 
                                 timeout=aiohttp.ClientTimeout(total=30)) as match_response:
                match_response.raise_for_status()
                match_text = await match_response.text()
                match_soup = BeautifulSoup(match_text, 'html.parser')
                
                # Look for match level in the page text
                level_match = re.search(r'Level\s+(I{1,3}|IV|V)', match_text, re.IGNORECASE)
                if level_match:
                    match_info['match_level'] = level_match.group(0)

                # Extract match date from the ssi-card-title
                date_title = match_soup.find('div', class_='ssi-card-title title-2')
                if date_title:
                    date_text = date_title.get_text(strip=True)
                    match_info['match_date'] = parse_date_string(date_text)
                    
        except Exception as e:
            print(f"Error fetching match details for {match_id}: {e}")
    
    # Check if match is eligible (Level II+ AND has divisions we care about)
    if is_match_eligible(match_info):
        match_divisions = {div['name'] for div in match_info.get('divisions', [])}
        eligible_divisions = match_divisions.intersection(DIVISIONS)
        
        print(f"Fetching combined results for {match_info['match_level']} match {match_id}")
        print(f"  Eligible divisions: {', '.join(eligible_divisions)}")
        
        combined_url = f'https://shootnscoreit.com/ipsc/results/match/{match_id}/combined/'
        
        try:
            async with session.get(combined_url, timeout=aiohttp.ClientTimeout(total=30)) as result_response:
                result_response.raise_for_status()
                result_text = await result_response.text()
                result_soup = BeautifulSoup(result_text, 'html.parser')
                combined_results = parse_combined_results(result_soup)
                match_info['combined_results'] = combined_results
                print(f"  Found {len(combined_results)} combined results for match {match_id}")
                
        except Exception as e:
            print(f"Error fetching combined results for match {match_id}: {e}")
            match_info['combined_results'] = []
    else:
        match_divisions = {div['name'] for div in match_info.get('divisions', [])}
        ineligible_divisions = match_divisions - DIVISIONS
        
        if match_info.get('match_level') not in LEVELS:
            print(f"Skipping match {match_id} - Level: {match_info.get('match_level', 'Unknown')}")
        else:
            print(f"Skipping match {match_id} - No eligible divisions")
            if ineligible_divisions:
                print(f"  Found divisions: {', '.join(ineligible_divisions)}")
    
    return match_info

async def save_match_info(match_info: Dict[str, Any], output_dir: str = "match_data"):
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

async def process_single_match(session: aiohttp.ClientSession, match_id: int, output_dir: str = "match_data") -> str:
    """Process a single match - this will be run in parallel"""
    global successful_counter, failed_counter, skipped_counter
    
    # Check if file already exists
    existing_data = check_existing_match_data(match_id, output_dir)
    
    if existing_data:
        # If we have existing data, check if it's eligible and complete
        if is_match_eligible(existing_data):
            if 'combined_results' in existing_data:
                print(f"Match {match_id} already processed with combined results, skipping...")
                await skipped_counter.increment()
                return 'skipped'
            else:
                print(f"Match {match_id} exists but missing combined results, reprocessing...")
        else:
            print(f"Match {match_id} already processed (not eligible), skipping...")
            await skipped_counter.increment()
            return 'skipped'
    
    try:
        match_info = await get_match_info(session, match_id)
        
        if match_info:
            await save_match_info(match_info, output_dir)
            if is_match_eligible(match_info):
                await successful_counter.increment()
                return 'success'
            else:
                await skipped_counter.increment()
                return 'skipped'
        else:
            await failed_counter.increment()
            return 'failed'
    except Exception as e:
        print(f"Error processing match {match_id}: {e}")
        await failed_counter.increment()
        return 'failed'

async def process_matches_batch(session: aiohttp.ClientSession, match_ids: List[int], output_dir: str) -> List[str]:
    """Process a batch of matches concurrently"""
    tasks = [process_single_match(session, match_id, output_dir) for match_id in match_ids]
    return await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    """Main function to iterate over match IDs and save data using async processing"""
    # You can adjust this range based on your needs
    start_match_id = 1
    end_match_id = 24700
    
    output_dir = "match_data"
    concurrent_limit = 50  # Number of concurrent requests
    batch_size = 100      # Process in batches for progress reporting
    
    print(f"Starting to process matches from {start_match_id} to {end_match_id}")
    print(f"Using {concurrent_limit} concurrent connections")
    print(f"Batch size: {batch_size}")
    print(f"Output directory: {output_dir}")
    print(f"Looking for divisions: {', '.join(sorted(DIVISIONS))}")
    print(f"Looking for levels: {', '.join(sorted(LEVELS))}")
    
    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Configure aiohttp session with connection limits
    connector = aiohttp.TCPConnector(
        limit=concurrent_limit,
        limit_per_host=concurrent_limit,
        ttl_dns_cache=300,
        use_dns_cache=True
    )
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        total_matches = end_match_id - start_match_id + 1
        processed_matches = 0
        
        # Process matches in batches
        for batch_start in range(start_match_id, end_match_id + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_match_id)
            match_ids = list(range(batch_start, batch_end + 1))
            
            print(f"\nProcessing batch: matches {batch_start} to {batch_end}")
            
            # Process the batch
            results = await process_matches_batch(session, match_ids, output_dir)
            processed_matches += len(match_ids)
            
            # Report progress
            print(f"Progress: {processed_matches}/{total_matches} matches processed")
            print(f"Successful: {successful_counter.value}, "
                  f"Skipped: {skipped_counter.value}, "
                  f"Failed: {failed_counter.value}")
    
    print(f"\nCompleted processing matches {start_match_id} to {end_match_id}")
    print(f"Successful (Level II+ with eligible divisions): {successful_counter.value}")
    print(f"Skipped: {skipped_counter.value}")
    print(f"Failed: {failed_counter.value}")
    print(f"Data saved to: {output_dir}/")

if __name__ == "__main__":
    asyncio.run(main())