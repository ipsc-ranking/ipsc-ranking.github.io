#!/usr/bin/env python3
"""
High-performance async script to fetch ALL matches from ipscresults.org using concurrent requests.
This should be significantly faster than the sequential version.
"""

import os
import json
import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor

class AsyncIPSCResultsClient:
    """Async client for fetching data from IPSCResults.org OData API"""
    
    def __init__(self, max_concurrent=10):
        self.base_url = 'https://ipscresults.org/odata'
        self.max_concurrent = max_concurrent
        self.session = None
        self.semaphore = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=self.max_concurrent)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_match_list(self) -> List[Dict[str, Any]]:
        """Fetch the complete match list from IPSCResults.org"""
        url = f"{self.base_url}/StatsMatchList?$format=json&$count=true"
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('value', [])
        except Exception as e:
            print(f"Error fetching match list: {e}")
            return []
    
    async def get_match_detail(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific match"""
        url = f"{self.base_url}/StatsMatchDetail({match_id})?$format=json&$count=true"
        
        async with self.semaphore:  # Limit concurrent requests
            try:
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                print(f"Error fetching match detail {match_id}: {e}")
                return None
    
    async def get_match_divisions(self, match_id: str) -> List[Dict[str, Any]]:
        """Fetch available divisions for a match"""
        url = f"{self.base_url}/StatsMatchDetail/Stats.DivisionList(id={match_id})?$format=json&$count=true"
        
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('value', [])
            except Exception as e:
                print(f"Error fetching divisions for match {match_id}: {e}")
                return []
    
    async def get_match_results(self, match_id: str, division_code: int) -> List[Dict[str, Any]]:
        """Fetch results for a specific match and division"""
        url = f"{self.base_url}/StatsMatchDetail/Stats.MatchResult(id={match_id},div={division_code})?$format=json&$count=true"
        
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('value', [])
            except Exception as e:
                print(f"Error fetching results for match {match_id}, division {division_code}: {e}")
                return []
    
    def get_handgun_division_codes(self, divisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find all handgun division codes from divisions list"""
        # IPSC handgun divisions (including PCC which uses handgun calibers)
        handgun_divisions = [
            'production optics', 'production', 'classic', 'standard', 
            'open', 'revolver', 'limited', 'carry optics', 'pcc',
            'pistol caliber carbine'
        ]
        
        # Non-handgun discipline indicators to exclude
        non_handgun_indicators = [
            'shotgun', 'rifle', 'sg', 'rf', 'precision',
            '3-gun', 'multigun', 'long range'
        ]
        
        found_divisions = []
        for division in divisions:
            division_name = division.get('Division', '').lower().strip()
            
            # First check if it contains non-handgun indicators - if so, exclude it
            if any(non_hg in division_name for non_hg in non_handgun_indicators):
                continue
                
            # Then check if it matches handgun divisions
            # Use exact match or word boundary matching to avoid false positives
            is_handgun = False
            for hg_div in handgun_divisions:
                # Check for exact match
                if division_name == hg_div:
                    is_handgun = True
                    break
                # Check for word boundary matches (e.g., "Open Division" matches "open")
                import re
                if re.search(r'\\b' + re.escape(hg_div) + r'\\b', division_name):
                    is_handgun = True
                    break
            
            if is_handgun:
                found_divisions.append({
                    'code': division.get('DivisionCode'),
                    'name': division.get('Division'),
                    'division_data': division
                })
        
        return found_divisions

class AsyncIPSCResultsMatchFetcher:
    """Async utility class for fetching individual IPSCResults matches"""
    
    def __init__(self, client: AsyncIPSCResultsClient):
        self.client = client
    
    def _normalize_region(self, region_code: str) -> str:
        """Normalize region codes to standard format"""
        region_mapping = {
            'SWE': 'SWE',
            'DEN': 'DEN', 
            'NOR': 'NOR',
            'FIN': 'FIN',
            'GER': 'GER',
            'DEU': 'GER',  # Alternative German code
            # Add more mappings as needed
        }
        return region_mapping.get(region_code, region_code)
    
    async def fetch_match(self, match_info: Dict[str, Any], match_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Fetch a single IPSCResults match with all handgun divisions
        
        Args:
            match_info: Match information from the match list
            match_list: Complete match list for level lookup
            
        Returns:
            Combined match data dictionary or None if not found/error
        """
        match_id = match_info['ID']
        
        try:
            # Get match detail and divisions concurrently
            match_detail_task = self.client.get_match_detail(match_id)
            divisions_task = self.client.get_match_divisions(match_id)
            
            match_detail, divisions = await asyncio.gather(
                match_detail_task, divisions_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(match_detail, Exception) or not match_detail:
                return None
            if isinstance(divisions, Exception):
                divisions = []
            
            # Get handgun divisions
            handgun_divisions = self.client.get_handgun_division_codes(divisions)
            if not handgun_divisions:
                return None
            
            # Fetch results for all handgun divisions concurrently
            results_tasks = []
            for division_info in handgun_divisions:
                division_code = division_info['code']
                task = self.client.get_match_results(match_id, division_code)
                results_tasks.append((division_info, task))
            
            # Wait for all results
            division_results = []
            for division_info, task in results_tasks:
                try:
                    results = await task
                    if results:
                        division_results.append((division_info, results))
                except Exception:
                    continue
            
            if not division_results:
                return None
            
            # Build combined match data with all divisions
            all_divisions = {}
            combined_results = []
            
            for division_info, results in division_results:
                div_name = division_info['name']
                
                # Process shooters for this division
                division_shooters = []
                for i, result in enumerate(results):
                    # Parse competitor name
                    full_name = result.get('CompetitorName', '').strip()
                    name_parts = full_name.split() if full_name else ['Unknown', 'Shooter']
                    
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    else:
                        first_name = name_parts[0] if name_parts else 'Unknown'
                        last_name = 'Shooter'
                    
                    shooter = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'alias': '',
                        'region': self._normalize_region(result.get('Region', match_info.get('RegionName', 'Unknown'))),
                        'division': div_name,
                        'category': result.get('Category', []) if result.get('Category') else [],
                        'classification': result.get('Recognition', ''),
                        'club': '',  # Not available in IPSCResults.org
                        'match_percentage': float(result.get('MatchPercent', 0)),
                        'placement': int(result.get('Rank', i + 1)),
                        'match_points': float(result.get('Points', 0)),
                        'competitor_number': result.get('CompetitorNumber', ''),
                    }
                    division_shooters.append(shooter)
                    combined_results.append(shooter)
                
                # Store division results
                all_divisions[div_name] = {
                    'division_name': div_name,
                    'division_code': division_info['code'],
                    'shooters': division_shooters,
                    'shooter_count': len(division_shooters)
                }
            
            # Build complete match data
            match_data = {
                'match_id': match_id,
                'match_title': match_info['Name'],
                'match_date': f"{match_info['Date']}T10:00:00" if match_info.get('Date') else datetime.now().isoformat(),
                'match_level': int(match_info.get('Level', 2)),  # Normalize to integer
                'club_name': match_detail.get('Location', match_info.get('RegionName', 'Unknown')),
                'region': match_info.get('RegionName', 'Unknown'),
                'source': 'ipscresults',
                'divisions': all_divisions,
                'combined_results': combined_results,  # All shooters from all divisions
                'total_shooters': len(combined_results),
                'division_count': len(all_divisions),
                'api_data': {
                    'match_info': match_info,
                    'match_detail': match_detail,
                    'divisions_fetched': list(all_divisions.keys())
                }
            }
            
            return match_data
            
        except Exception as e:
            print(f"Error fetching IPSCResults match {match_id}: {e}")
            return None
    
    def save_match_data(self, match_data: Dict[str, Any]) -> str:
        """Save IPSCResults match data to JSON file"""
        match_date = match_data.get('match_date', '')
        timestamp = self._extract_date_for_filename(match_date)
        match_id = str(match_data['match_id'])[:8]  # Use first 8 chars of UUID
        filename = f"match_data/{timestamp}_ipscresults_{match_id}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            return filename
        except IOError as e:
            print(f"Error saving IPSCResults match data to {filename}: {e}")
            raise
    
    def _extract_date_for_filename(self, match_date: str) -> str:
        """Extract date from match_date for filename prefix (YYYY-MM-DD format)"""
        try:
            if 'T' in match_date:
                return match_date.split('T')[0]
            elif '-' in match_date and len(match_date) >= 10:
                return match_date[:10]
        except:
            pass
        
        return datetime.now().strftime('%Y-%m-%d')

def load_existing_match_ids() -> Set[str]:
    """Load existing IPSCResults match IDs to avoid duplicates"""
    existing_ids = set()
    
    if not os.path.exists('./match_data/'):
        return existing_ids
    
    for filename in os.listdir('./match_data/'):
        if '_ipscresults_' in filename and filename.endswith('.json'):
            try:
                with open(f'./match_data/{filename}', 'r') as f:
                    data = json.load(f)
                    
                # Extract match ID from the data
                match_id = data.get('match_id')
                if match_id:
                    existing_ids.add(match_id)
                    
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}")
                continue
    
    return existing_ids

async def process_matches_batch(client: AsyncIPSCResultsClient, 
                               matches_batch: List[Dict[str, Any]], 
                               match_list: List[Dict[str, Any]],
                               batch_num: int, 
                               total_batches: int) -> tuple:
    """Process a batch of matches concurrently"""
    
    fetcher = AsyncIPSCResultsMatchFetcher(client)
    
    # Process all matches in this batch concurrently
    tasks = []
    for match_info in matches_batch:
        task = fetcher.fetch_match(match_info, match_list)
        tasks.append((match_info, task))
    
    # Wait for all tasks in batch to complete
    batch_results = []
    for match_info, task in tasks:
        try:
            match_data = await task
            if match_data:
                batch_results.append((match_info, match_data))
        except Exception as e:
            print(f"Error processing {match_info.get('Name', 'Unknown')}: {e}")
    
    # Save results (using thread pool to avoid blocking)
    def save_match(args):
        match_info, match_data = args
        try:
            filename = fetcher.save_match_data(match_data)
            return (True, match_info, match_data, filename)
        except Exception as e:
            return (False, match_info, None, str(e))
    
    # Use thread pool for file I/O
    with ThreadPoolExecutor(max_workers=5) as executor:
        save_results = list(executor.map(save_match, batch_results))
    
    # Count results
    saved = sum(1 for success, _, _, _ in save_results if success)
    errors = sum(1 for success, _, _, _ in save_results if not success)
    total_divisions = sum(
        len(match_data.get('divisions', {})) 
        for success, _, match_data, _ in save_results 
        if success and match_data
    )
    
    print(f"\\n📊 Batch {batch_num}/{total_batches} complete:")
    print(f"   Processed: {len(matches_batch)} matches")
    print(f"   Saved: {saved}")
    print(f"   Errors: {errors}")
    print(f"   Divisions: {total_divisions}")
    
    return saved, errors, total_divisions

async def fetch_all_matches_async():
    """Async function to fetch ALL matches from ipscresults.org"""
    print("🚀 Async IPSCResults.org COMPLETE Database Fetcher")
    print("=" * 60)
    print("Using concurrent requests for maximum speed!")
    print("=" * 60)
    
    # Load existing match IDs
    existing_ids = load_existing_match_ids()
    print(f"📊 Found {len(existing_ids)} existing IPSCResults matches")
    
    # Ensure directories exist
    os.makedirs('./match_data/', exist_ok=True)
    
    async with AsyncIPSCResultsClient(max_concurrent=15) as client:
        # Get complete match list
        print("📡 Fetching complete match list from ipscresults.org...")
        matches = await client.get_match_list()
        
        if not matches:
            print("❌ Failed to fetch match list")
            return 0
        
        print(f"✅ Retrieved {len(matches)} total matches from API")
        
        # Analyze the dataset
        dates = [m.get('Date', '') for m in matches if m.get('Date')]
        dates = [d for d in dates if d]
        if dates:
            dates.sort()
            print(f"📅 Date range: {dates[0]} to {dates[-1]}")
        
        # Level distribution
        levels = {}
        for m in matches:
            level = m.get('Level', 'Unknown')
            levels[level] = levels.get(level, 0) + 1
        print(f"🎯 Level distribution: {dict(sorted(levels.items()))}")
        
        # Filter out already processed matches
        new_matches = [m for m in matches if m['ID'] not in existing_ids]
        print(f"📥 New matches to process: {len(new_matches)}")
        
        if not new_matches:
            print("✅ All matches already processed!")
            return 0
        
        # Process matches in batches for better progress tracking
        batch_size = 20  # Process 20 matches concurrently
        batches = [new_matches[i:i + batch_size] for i in range(0, len(new_matches), batch_size)]
        
        print(f"🔄 Processing {len(new_matches)} matches in {len(batches)} batches of {batch_size}")
        print("=" * 60)
        
        total_saved = 0
        total_errors = 0
        total_divisions = 0
        start_time = time.time()
        
        for i, batch in enumerate(batches, 1):
            batch_start = time.time()
            
            saved, errors, divisions = await process_matches_batch(
                client, batch, matches, i, len(batches)
            )
            
            total_saved += saved
            total_errors += errors  
            total_divisions += divisions
            
            batch_time = time.time() - batch_start
            elapsed = time.time() - start_time
            avg_time_per_batch = elapsed / i
            remaining_batches = len(batches) - i
            eta_seconds = remaining_batches * avg_time_per_batch
            eta_minutes = eta_seconds / 60
            
            print(f"   Batch time: {batch_time:.1f}s | ETA: {eta_minutes:.1f} minutes")
        
        total_time = time.time() - start_time
        
        print(f"\\n🎯 Complete Async Fetch Summary:")
        print(f"   Total matches in database: {len(matches)}")
        print(f"   Previously processed: {len(existing_ids)}")
        print(f"   New matches processed: {len(new_matches)}")
        print(f"   Successfully saved: {total_saved}")
        print(f"   Errors: {total_errors}")
        print(f"   Total divisions processed: {total_divisions}")
        print(f"   Total time: {total_time/60:.1f} minutes")
        print(f"   Speed: {len(new_matches)/(total_time/60):.1f} matches/minute")
        
        return total_saved

def main():
    """Main function"""
    start_time = datetime.now()
    
    try:
        # Run the async fetch
        new_matches = asyncio.run(fetch_all_matches_async())
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if new_matches > 0:
            print(f"\\n✅ Successfully fetched {new_matches} new match files!")
            print(f"⏱️  Total time: {duration}")
            print(f"\\n🔧 Next steps:")
            print("   1. Run ranking generation: python process_matches.py")
            print("   2. Update website: python update_rankings.py")
            print("\\n📈 This will SIGNIFICANTLY improve ranking accuracy!")
            print("   - Much larger dataset")
            print("   - Historical data back to 2004")  
            print("   - More accurate skill ratings")
        else:
            print(f"\\n📍 No new matches to process")
            print("   All ipscresults.org matches are already in the database")
        
        return 0
        
    except Exception as e:
        print(f"\\n❌ Error during async fetch: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())