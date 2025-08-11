#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.aiohttp python3Packages.beautifulsoup4 python3Packages.asyncio

"""
Parallel PractiScore scraper using asyncio for concurrent requests
"""

import asyncio
import aiohttp
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class AsyncCounter:
    """Thread-safe async counter"""
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

class ParallelPractiScoreScraper:
    """Parallel PractiScore scraper using asyncio"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        
        # IPSC Handgun divisions
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        # Async counters
        self.checked_counter = AsyncCounter()
        self.valid_counter = AsyncCounter()
        self.ipsc_counter = AsyncCounter()
        self.saved_counter = AsyncCounter()
        self.redirect_counter = AsyncCounter()
        self.error_counter = AsyncCounter()
        
        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def is_valid_match(self, session: aiohttp.ClientSession, match_id: str) -> tuple[bool, str, str]:
        """Check if match exists and get title"""
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                
                if response.status != 200:
                    return False, f"HTTP {response.status}", ""
                
                content = await response.text()
                
                if len(content) < 2000:
                    return False, "Too short", ""
                
                if 'Scores Search' in content:
                    return False, "Redirected to search", ""
                
                # Extract title
                soup = BeautifulSoup(content, 'html.parser')
                title_meta = soup.find('meta', {'property': 'og:title'})
                
                if title_meta and title_meta.get('content'):
                    title = title_meta['content'].strip()
                    if title and title != "Scores Search":
                        return True, title, content
                
                return False, "No valid title", ""
                
        except asyncio.TimeoutError:
            return False, "Timeout", ""
        except Exception as e:
            return False, f"Error: {str(e)[:30]}", ""
    
    def extract_match_data(self, html_content: str, match_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Extract match data from HTML"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for shooters
            shooters = []
            
            # Method 1: JavaScript data
            js_shooters = self._extract_js_shooters(html_content)
            if js_shooters:
                shooters.extend(js_shooters)
            
            # Method 2: HTML tables
            if not shooters:
                table_shooters = self._extract_table_shooters(soup)
                if table_shooters:
                    shooters.extend(table_shooters)
            
            if not shooters:
                return None
            
            # Filter for IPSC handgun shooters
            handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
            
            if not handgun_shooters:
                return None
            
            return {
                'match_id': int(match_id),
                'match_title': title,
                'match_date': datetime.now().strftime('%Y-%m-%dT10:00:00'),
                'match_level': 'Level II',
                'club_name': 'Unknown',
                'combined_results': handgun_shooters,
                'production_optics_results': [s for s in handgun_shooters 
                                             if 'production optics' in s.get('division', '').lower()],
                'source': 'practiscore'
            }
            
        except Exception as e:
            print(f"    Parse error for {match_id}: {str(e)[:30]}...")
            return None
    
    def _extract_js_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from JavaScript"""
        
        shooters = []
        
        patterns = [
            r'var\s+shooters\s*=\s*(\[.*?\]);',
            r'shooters\s*:\s*(\[.*?\])',
            r'match_shooters\s*:\s*(\[.*?\])',
            r'results\s*:\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    
                    data = json.loads(json_str)
                    
                    for shooter in data:
                        if isinstance(shooter, dict) and not shooter.get('sh_del', False):
                            formatted = self._format_shooter(shooter)
                            if formatted:
                                shooters.append(formatted)
                                
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return shooters
    
    def _extract_table_shooters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shooters from HTML tables"""
        
        shooters = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                shooter = self._parse_table_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_table_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse table row to shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name
        name = None
        for text in cell_texts:
            if (re.match(r'^[A-Za-zÅÄÖåäö\s\-\.\']{3,50}$', text) and 
                ' ' in text and 
                len(text.split()) <= 4):
                name = text
                break
        
        if not name:
            return None
        
        name_parts = name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Find percentage
        percentage = 0.0
        for text in cell_texts:
            if '%' in text:
                try:
                    percentage = float(text.replace('%', '').replace(',', '.'))
                    break
                except ValueError:
                    continue
            elif re.match(r'^\d+[\.,]?\d*$', text):
                try:
                    num = float(text.replace(',', '.'))
                    if 0 <= num <= 150:
                        percentage = num
                        break
                except ValueError:
                    continue
        
        # Find division
        division = 'Production Optics'
        for text in cell_texts:
            text_lower = text.lower()
            for div in self.handgun_divisions:
                if div in text_lower:
                    division = text
                    break
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': 'UNK',
            'division': division,
            'match_percentage': percentage,
            'placement': 999
        }
    
    def _format_shooter(self, raw_shooter: Dict) -> Optional[Dict[str, Any]]:
        """Format raw shooter data"""
        
        first_name = raw_shooter.get('sh_fn', raw_shooter.get('first_name', ''))
        last_name = raw_shooter.get('sh_ln', raw_shooter.get('last_name', ''))
        
        if not first_name and not last_name:
            return None
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': raw_shooter.get('alias', ''),
            'region': raw_shooter.get('region', 'UNK'),
            'division': raw_shooter.get('sh_dvp', raw_shooter.get('division', 'Production Optics')),
            'match_percentage': float(raw_shooter.get('percentage', raw_shooter.get('match_percentage', 0.0))),
            'placement': raw_shooter.get('placement', 999)
        }
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if shooter is in handgun division"""
        
        division = shooter.get('division', '').lower()
        
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', '3-gun', 'multigun', 'precision'}
        if any(excl in division for excl in excluded):
            return False
        
        return True
    
    async def save_match_data(self, match_data: Dict[str, Any]):
        """Save match data async"""
        
        match_date = match_data.get('match_date', '')
        timestamp = match_date.split('T')[0] if 'T' in match_date else datetime.now().strftime('%Y-%m-%d')
        match_id = match_data['match_id']
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            await self.saved_counter.increment()
        except IOError as e:
            print(f"Save error for {match_id}: {e}")
    
    async def scrape_match(self, session: aiohttp.ClientSession, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match async"""
        
        await self.checked_counter.increment()
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            return None
        
        # Check if match is valid
        is_valid, info, content = await self.is_valid_match(session, match_id)
        
        if not is_valid:
            if info.startswith('HTTP') or info.startswith('Error'):
                await self.error_counter.increment()
            else:
                await self.redirect_counter.increment()
            return None
        
        await self.valid_counter.increment()
        title = info
        
        # Extract match data
        match_data = self.extract_match_data(content, match_id, title)
        
        if match_data:
            await self.ipsc_counter.increment()
            await self.save_match_data(match_data)
            
            shooters = len(match_data.get('combined_results', []))
            print(f"✅ {match_id}: {title[:40]}... ({shooters} shooters)")
            
            return match_data
        
        return None
    
    async def scrape_range_batch(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """Scrape a batch of matches concurrently"""
        
        # Create session with connection limits
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def scrape_with_semaphore(match_id: str):
                async with semaphore:
                    return await self.scrape_match(session, match_id)
            
            # Create tasks for all matches
            tasks = [scrape_with_semaphore(match_id) for match_id in match_ids]
            
            # Run tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            valid_results = []
            for result in results:
                if isinstance(result, dict):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    await self.error_counter.increment()
            
            return valid_results
    
    async def scrape_range(self, start_id: int, end_id: int, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Scrape a range of match IDs in batches"""
        
        print(f"🚀 Parallel scraping matches {start_id}-{end_id} (concurrent: {self.max_concurrent})")
        
        all_results = []
        match_ids = [str(i) for i in range(start_id, end_id + 1)]
        
        # Process in batches
        for i in range(0, len(match_ids), batch_size):
            batch = match_ids[i:i + batch_size]
            batch_start = start_id + i
            batch_end = min(start_id + i + batch_size - 1, end_id)
            
            print(f"  📦 Processing batch {batch_start}-{batch_end} ({len(batch)} matches)...")
            
            batch_results = await self.scrape_range_batch(batch)
            all_results.extend(batch_results)
            
            # Progress update
            print(f"  📊 Batch complete: {len(batch_results)} IPSC matches found")
            self.print_progress()
            
            # Rate limiting between batches
            if i + batch_size < len(match_ids):
                print("  ⏸️  Pausing 5s between batches...")
                await asyncio.sleep(5)
        
        return all_results
    
    def print_progress(self):
        """Print current progress"""
        print(f"    Progress: {self.checked_counter.value} checked, {self.valid_counter.value} valid, "
              f"{self.ipsc_counter.value} IPSC, {self.saved_counter.value} saved")

async def main():
    """Main async function"""
    
    print("🌐 Parallel PractiScore Scraper")
    print("=" * 50)
    
    scraper = ParallelPractiScoreScraper(max_concurrent=15)  # Moderate concurrency
    
    # Test proven ranges in parallel
    ranges_to_test = [
        (99500, 100500),   # Around 100000 (proven)
        (249500, 250500),  # Around 250000 (proven)
        (199500, 200500),  # Around 200000 (proven)
        (149500, 150500),  # Around 150000
    ]
    
    all_results = []
    
    for start, end in ranges_to_test:
        print(f"\n--- Parallel scraping range {start}-{end} ---")
        
        start_time = time.time()
        
        results = await scraper.scrape_range(start, end, batch_size=200)
        
        elapsed = time.time() - start_time
        
        print(f"Range {start}-{end} complete: {len(results)} IPSC matches in {elapsed:.1f}s")
        all_results.extend(results)
        
        if len(results) > 0:
            print(f"✅ Found matches - rate: {len(results)/elapsed:.1f} matches/sec")
        
        # Pause between ranges
        if len(all_results) < 100:  # Continue if we haven't found enough
            print("Pausing 10s before next range...")
            await asyncio.sleep(10)
        else:
            print(f"Found {len(all_results)} total matches - stopping")
            break
    
    print(f"\n🏁 Parallel scraping complete!")
    print(f"📊 Final Statistics:")
    print(f"  Total checked: {scraper.checked_counter.value}")
    print(f"  Valid matches: {scraper.valid_counter.value}")
    print(f"  IPSC matches: {scraper.ipsc_counter.value}")
    print(f"  Saved matches: {scraper.saved_counter.value}")
    print(f"  Redirects: {scraper.redirect_counter.value}")
    print(f"  Errors: {scraper.error_counter.value}")
    
    if len(all_results) > 0:
        print(f"\n📋 Next steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Check new files in match_data/ directory")
        print(f"3. Expand to more ranges if needed")

if __name__ == "__main__":
    asyncio.run(main())