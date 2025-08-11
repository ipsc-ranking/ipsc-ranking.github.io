#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.aiohttp python3Packages.beautifulsoup4 python3Packages.asyncio

"""
Targeted parallel PractiScore scraper - focuses on most productive ranges
"""

import asyncio
import aiohttp
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup

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

class TargetedPractiScoreScraper:
    """Fast targeted scraper for high-yield PractiScore ranges"""
    
    def __init__(self, max_concurrent: int = 30):
        self.max_concurrent = max_concurrent
        
        self.handgun_divisions = {
            'production', 'production optics', 'carry optics', 'po',
            'classic', 'standard', 'open', 'revolver', 'limited',
            'optics', 'light', 'ccp', 'limited-10', 'standard manual'
        }
        
        # Counters
        self.checked_counter = AsyncCounter()
        self.valid_counter = AsyncCounter()
        self.ipsc_counter = AsyncCounter()
        self.saved_counter = AsyncCounter()
        self.existing_counter = AsyncCounter()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
        }
    
    async def quick_check_and_scrape(self, session: aiohttp.ClientSession, match_id: str) -> Optional[Dict[str, Any]]:
        """Quick check and scrape in one operation"""
        
        await self.checked_counter.increment()
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            await self.existing_counter.increment()
            return None
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            async with session.get(url, headers=self.headers, timeout=8) as response:
                
                if response.status != 200:
                    return None
                
                content = await response.text()
                
                if len(content) < 2000 or 'Scores Search' in content:
                    return None
                
                await self.valid_counter.increment()
                
                # Quick title extraction
                title_match = re.search(r'<meta property="og:title" content="([^"]*)"', content)
                if not title_match:
                    return None
                
                title = title_match.group(1).strip()
                if not title or title == "Scores Search":
                    return None
                
                # Quick shooter extraction
                shooters = self._fast_extract_shooters(content)
                
                if not shooters:
                    return None
                
                # Quick IPSC check
                if not self._quick_ipsc_check(shooters, title):
                    return None
                
                await self.ipsc_counter.increment()
                
                # Filter handgun shooters
                handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
                
                if not handgun_shooters:
                    return None
                
                # Create and save match data
                match_data = {
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
                
                await self._save_match_data(match_data)
                await self.saved_counter.increment()
                
                print(f"✅ {match_id}: {title[:35]}... ({len(handgun_shooters)} shooters)")
                return match_data
                
        except Exception:
            return None
    
    def _fast_extract_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Fast shooter extraction focusing on most common patterns"""
        
        shooters = []
        
        # Try JavaScript first (fastest)
        js_match = re.search(r'(?:var\s+shooters|shooters\s*:)\s*=?\s*(\[.*?\]);', html_content, re.DOTALL)
        if js_match:
            try:
                json_str = js_match.group(1)
                json_str = re.sub(r',\s*[}\]]', lambda m: m.group(0)[1:], json_str)  # Clean trailing commas
                data = json.loads(json_str)
                
                for shooter in data:
                    if isinstance(shooter, dict):
                        formatted = self._format_shooter(shooter)
                        if formatted:
                            shooters.append(formatted)
                
                if shooters:
                    return shooters
            except:
                pass
        
        # Fallback to table parsing (slower but reliable)
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 5:
                continue
            
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:
                    continue
                
                shooter = self._parse_shooter_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_shooter_row(self, cells) -> Optional[Dict[str, Any]]:
        """Fast shooter row parsing"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find name (must have space and reasonable length)
        name = None
        for text in cell_texts:
            if (3 <= len(text) <= 50 and ' ' in text and 
                re.match(r'^[A-Za-zÅÄÖåäöÆØæø\s\-\.\']+$', text) and
                len(text.split()) <= 4):
                name = text
                break
        
        if not name:
            return None
        
        name_parts = name.split()
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Find percentage (quick scan)
        percentage = 0.0
        for text in cell_texts:
            if '%' in text:
                try:
                    percentage = float(text.replace('%', ''))
                    break
                except:
                    continue
            elif re.match(r'^\d+\.\d+$', text):
                try:
                    num = float(text)
                    if 50 <= num <= 120:
                        percentage = num
                        break
                except:
                    continue
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': 'UNK',
            'division': 'Production Optics',
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
    
    def _quick_ipsc_check(self, shooters: List[Dict], title: str) -> bool:
        """Quick IPSC match check"""
        
        if not shooters:
            return False
        
        # Title check
        title_lower = title.lower()
        if any(word in title_lower for word in ['uspsa', 'ipsc', 'production', 'open', 'classic']):
            return True
        
        # Division check (first few shooters)
        handgun_count = 0
        for shooter in shooters[:min(5, len(shooters))]:
            division = shooter.get('division', '').lower()
            if any(div in division for div in self.handgun_divisions):
                handgun_count += 1
        
        return handgun_count >= 1
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if handgun shooter"""
        
        division = shooter.get('division', '').lower()
        
        if any(div in division for div in self.handgun_divisions):
            return True
        
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine'}
        return not any(ex in division for ex in excluded)
    
    async def _save_match_data(self, match_data: Dict[str, Any]):
        """Save match data"""
        
        timestamp = datetime.now().strftime('%Y-%m-%d')
        match_id = match_data['match_id']
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    async def scrape_range_fast(self, start_id: int, end_id: int) -> List[Dict[str, Any]]:
        """Fast parallel range scraping"""
        
        print(f"🚀 Fast scraping {start_id}-{end_id} ({end_id-start_id+1} matches)")
        
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def scrape_with_limit(match_id: str):
                async with semaphore:
                    return await self.quick_check_and_scrape(session, match_id)
            
            # Create all tasks
            match_ids = [str(i) for i in range(start_id, end_id + 1)]
            tasks = [scrape_with_limit(match_id) for match_id in match_ids]
            
            # Run all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid results
            valid_results = [r for r in results if isinstance(r, dict)]
            
            return valid_results
    
    def print_stats(self):
        """Print statistics"""
        print(f"    📊 {self.checked_counter.value} checked, {self.valid_counter.value} valid, "
              f"{self.ipsc_counter.value} IPSC, {self.saved_counter.value} saved, {self.existing_counter.value} existing")

async def main():
    """Main targeted scraping"""
    
    print("🎯 Targeted Fast PractiScore Scraper")
    print("=" * 50)
    
    scraper = TargetedPractiScoreScraper(max_concurrent=35)
    
    # Target most productive ranges based on what we know works
    priority_ranges = [
        # High-yield ranges (known to have many matches)  
        (99800, 100200),   # Dense around 100000
        (249800, 250200),  # Dense around 250000
        (199800, 200200),  # Dense around 200000
        
        # Expansion ranges (likely to have matches)
        (98000, 99800),    # Before 100k
        (100200, 102000),  # After 100k
        (248000, 249800),  # Before 250k
        (250200, 252000),  # After 250k
        (198000, 199800),  # Before 200k
        (200200, 202000),  # After 200k
        
        # Discovery ranges (fill gaps)
        (149800, 150200),  # Around 150k
        (295000, 300000),  # Latest matches
        (90000, 98000),    # Pre-100k
        (102000, 110000),  # Post-100k
        (240000, 248000),  # Pre-250k
        (252000, 260000),  # Post-250k
    ]
    
    all_results = []
    total_start = time.time()
    
    for i, (start, end) in enumerate(priority_ranges, 1):
        print(f"\n🎯 Priority Range {i}/{len(priority_ranges)}: {start}-{end}")
        
        range_start = time.time()
        results = await scraper.scrape_range_fast(start, end)
        range_time = time.time() - range_start
        
        all_results.extend(results)
        rate = (end - start + 1) / range_time if range_time > 0 else 0
        
        print(f"  ⚡ Range complete: {len(results)} IPSC matches in {range_time:.1f}s ({rate:.0f} req/s)")
        scraper.print_stats()
        
        # Brief pause if we found matches (server courtesy)
        if len(results) > 0:
            await asyncio.sleep(2)
        
        # Stop if we've found many matches (process and continue later)
        total_found = len(all_results)
        if total_found >= 200:
            print(f"\n🛑 Found {total_found} matches - pausing for processing")
            break
    
    total_time = time.time() - total_start
    
    print(f"\n🏁 Fast scraping complete!")
    print(f"📊 Session Statistics:")
    print(f"  Total checked: {scraper.checked_counter.value}")
    print(f"  Valid matches: {scraper.valid_counter.value}")
    print(f"  IPSC matches: {scraper.ipsc_counter.value}")
    print(f"  Saved matches: {scraper.saved_counter.value}")
    print(f"  Already existed: {scraper.existing_counter.value}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average rate: {scraper.checked_counter.value/total_time:.0f} checks/s")
    
    new_matches = len(all_results)
    if new_matches > 0:
        print(f"\n✅ Success! Found {new_matches} new IPSC matches")
        print(f"📋 Next steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Re-run scraper to continue with remaining ranges")
    else:
        print(f"\n📝 No new matches in this session - all ranges already covered")

if __name__ == "__main__":
    asyncio.run(main())