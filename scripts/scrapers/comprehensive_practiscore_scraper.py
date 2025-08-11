#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.aiohttp python3Packages.beautifulsoup4 python3Packages.asyncio

"""
Comprehensive parallel PractiScore scraper - systematically covers all ranges
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

class ComprehensivePractiScoreScraper:
    """Comprehensive parallel scraper covering all PractiScore ranges"""
    
    def __init__(self, max_concurrent: int = 20):
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
        self.existing_counter = AsyncCounter()
        
        # Headers with user agent rotation
        self.user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        
        self.base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with rotating user agent"""
        import random
        headers = self.base_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers
    
    async def check_match_exists(self, session: aiohttp.ClientSession, match_id: str) -> Tuple[bool, str, str]:
        """Check if match exists and get basic info"""
        
        url = f'https://practiscore.com/results/new/{match_id}'
        
        try:
            async with session.get(url, headers=self.get_headers(), timeout=10) as response:
                
                if response.status != 200:
                    return False, f"HTTP {response.status}", ""
                
                content = await response.text()
                
                if len(content) < 2000:
                    return False, "Content too short", ""
                
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
    
    def extract_shooters_from_content(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from HTML content"""
        
        shooters = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: JavaScript data
        js_shooters = self._extract_js_shooters(html_content)
        if js_shooters:
            shooters.extend(js_shooters)
        
        # Method 2: HTML tables
        if not shooters:
            table_shooters = self._extract_table_shooters(soup)
            if table_shooters:
                shooters.extend(table_shooters)
        
        return shooters
    
    def _extract_js_shooters(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract shooters from JavaScript"""
        
        shooters = []
        
        # JavaScript patterns for PractiScore
        patterns = [
            r'var\s+shooters\s*=\s*(\[.*?\]);',
            r'shooters\s*:\s*(\[.*?\])',
            r'match_shooters\s*:\s*(\[.*?\])',
            r'results\s*:\s*(\[.*?\])',
            r'matchData\s*=\s*\{[^}]*shooters\s*:\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JSON
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
            if len(rows) < 5:  # Skip small tables
                continue
            
            # Parse shooter rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:  # Need enough columns
                    continue
                
                shooter = self._parse_shooter_row(cells)
                if shooter:
                    shooters.append(shooter)
        
        return shooters
    
    def _parse_shooter_row(self, cells) -> Optional[Dict[str, Any]]:
        """Parse table row to extract shooter data"""
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Find placement
        placement = 999
        for i, text in enumerate(cell_texts[:3]):
            if text.isdigit() and 1 <= int(text) <= 500:
                placement = int(text)
                break
        
        # Find name
        name = None
        first_name = ""
        last_name = ""
        
        for text in cell_texts:
            if (re.match(r'^[A-Za-zÅÄÖåäöÆØæø\s\-\.\']{3,50}$', text) and 
                ' ' in text and 
                len(text.split()) <= 4 and
                not any(div in text.lower() for div in self.handgun_divisions)):
                name = text
                name_parts = name.split()
                first_name = name_parts[0] if name_parts else ''
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                break
        
        if not first_name and not last_name:
            return None
        
        # Find percentage
        percentage = 0.0
        for text in cell_texts:
            if '%' in text:
                try:
                    percentage = float(text.replace('%', '').replace(',', '.'))
                    break
                except ValueError:
                    continue
            elif re.match(r'^\d+[\.,]\d+$', text):
                try:
                    num = float(text.replace(',', '.'))
                    if 50 <= num <= 120:
                        percentage = num
                        break
                except ValueError:
                    continue
        
        # Find division
        division = 'Production Optics'  # Default
        for text in cell_texts:
            text_lower = text.lower()
            for div in self.handgun_divisions:
                if div in text_lower:
                    division = text
                    break
        
        # Find region
        region = 'UNK'
        for text in cell_texts:
            if re.match(r'^[A-Z]{2,3}$', text) and text not in ['DNS', 'DNF', 'DQ']:
                region = text
                break
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'alias': '',
            'region': region,
            'division': division,
            'match_percentage': percentage,
            'placement': placement
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
    
    def _is_ipsc_handgun_match(self, shooters: List[Dict], title: str) -> bool:
        """Check if this is an IPSC handgun match"""
        
        if not shooters:
            return False
        
        # Check title for IPSC/USPSA indicators
        title_lower = title.lower()
        if any(indicator in title_lower for indicator in ['uspsa', 'ipsc', 'production', 'open', 'classic']):
            return True
        
        # Check shooter divisions
        handgun_count = 0
        for shooter in shooters[:10]:
            division = shooter.get('division', '').lower()
            if any(hg_div in division for hg_div in self.handgun_divisions):
                handgun_count += 1
        
        return handgun_count >= max(1, len(shooters[:10]) * 0.3)
    
    def _is_handgun_shooter(self, shooter: Dict) -> bool:
        """Check if shooter is in handgun division"""
        
        division = shooter.get('division', '').lower()
        
        if any(hg_div in division for hg_div in self.handgun_divisions):
            return True
        
        excluded = {'rifle', 'shotgun', 'pcc', 'carbine', 'precision', '3-gun', 'multigun'}
        if any(excl in division for excl in excluded):
            return False
        
        return True
    
    async def scrape_match(self, session: aiohttp.ClientSession, match_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single match"""
        
        await self.checked_counter.increment()
        
        # Check if already exists
        filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
        if os.path.exists(filename):
            await self.existing_counter.increment()
            return None
        
        # Check if match exists
        exists, info, content = await self.check_match_exists(session, match_id)
        
        if not exists:
            if info.startswith('HTTP') or info.startswith('Error'):
                await self.error_counter.increment()
            else:
                await self.redirect_counter.increment()
            return None
        
        await self.valid_counter.increment()
        title = info
        
        # Extract shooters
        shooters = self.extract_shooters_from_content(content)
        
        if not shooters:
            return None
        
        # Check if IPSC handgun match
        if not self._is_ipsc_handgun_match(shooters, title):
            return None
        
        await self.ipsc_counter.increment()
        
        # Filter handgun shooters
        handgun_shooters = [s for s in shooters if self._is_handgun_shooter(s)]
        
        if not handgun_shooters:
            return None
        
        # Create match data
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
        
        # Save match data
        await self.save_match_data(match_data)
        await self.saved_counter.increment()
        
        print(f"✅ {match_id}: {title[:40]}... ({len(handgun_shooters)} shooters)")
        return match_data
    
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
        except IOError as e:
            print(f"Save error for {match_id}: {e}")
    
    async def scrape_range_batch(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """Scrape a batch of matches concurrently"""
        
        # Create session with connection limits
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def scrape_with_semaphore(match_id: str):
                async with semaphore:
                    # Add small random delay to avoid overwhelming server
                    await asyncio.sleep(0.1 + (hash(match_id) % 100) / 1000)
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
    
    async def scrape_comprehensive_range(self, start_id: int, end_id: int, batch_size: int = 500) -> List[Dict[str, Any]]:
        """Comprehensively scrape a range without missing matches"""
        
        print(f"🚀 Comprehensive scraping {start_id}-{end_id} (concurrent: {self.max_concurrent})")
        
        all_results = []
        match_ids = [str(i) for i in range(start_id, end_id + 1)]
        total_batches = len(match_ids) // batch_size + (1 if len(match_ids) % batch_size else 0)
        
        # Process in batches
        for batch_num, i in enumerate(range(0, len(match_ids), batch_size), 1):
            batch = match_ids[i:i + batch_size]
            batch_start = start_id + i
            batch_end = min(start_id + i + batch_size - 1, end_id)
            
            print(f"  📦 Batch {batch_num}/{total_batches}: {batch_start}-{batch_end} ({len(batch)} matches)")
            
            batch_start_time = time.time()
            batch_results = await self.scrape_range_batch(batch)
            batch_time = time.time() - batch_start_time
            
            all_results.extend(batch_results)
            
            # Progress update
            rate = len(batch) / batch_time if batch_time > 0 else 0
            print(f"    ⚡ Batch complete: {len(batch_results)} IPSC matches found in {batch_time:.1f}s ({rate:.1f} req/s)")
            self.print_progress()
            
            # Rate limiting between batches
            if batch_num < total_batches:
                print("    ⏸️  Pausing 3s between batches...")
                await asyncio.sleep(3)
        
        return all_results
    
    def print_progress(self):
        """Print current progress"""
        print(f"      📊 Total: {self.checked_counter.value} checked, {self.valid_counter.value} valid, "
              f"{self.ipsc_counter.value} IPSC, {self.saved_counter.value} saved")
        print(f"      📊 Skipped: {self.existing_counter.value} existing, {self.redirect_counter.value} redirects, "
              f"{self.error_counter.value} errors")

async def main():
    """Main comprehensive scraping function"""
    
    print("🌐 Comprehensive Parallel PractiScore Scraper")
    print("=" * 60)
    
    scraper = ComprehensivePractiScoreScraper(max_concurrent=25)
    
    # Comprehensive range strategy - cover all potential ranges systematically
    ranges_to_scrape = [
        # First priority: Proven working ranges and immediate surroundings
        (99000, 101000),    # Around proven 100000
        (249000, 251000),   # Around proven 250000
        (199000, 201000),   # Around proven 200000
        
        # Second priority: Expand around working ranges
        (95000, 99000),     # Before 100000 range
        (101000, 105000),   # After 100000 range
        (245000, 249000),   # Before 250000 range
        (251000, 255000),   # After 250000 range
        (195000, 199000),   # Before 200000 range
        (201000, 205000),   # After 200000 range
        
        # Third priority: Check other potential dense ranges
        (149000, 151000),   # Around 150000
        (299000, 301000),   # Latest possible matches
        (50000, 52000),     # Older matches
        (149000, 151000),   # Mid-range
        
        # Fourth priority: Fill gaps systematically
        (1000, 10000),      # Very old matches
        (20000, 30000),     # Old matches
        (40000, 50000),     # Older matches
        (80000, 95000),     # Pre-100k range
        (105000, 120000),   # Post-100k range
        (120000, 140000),   # Mid-old range
        (160000, 180000),   # Mid-new range
        (180000, 195000),   # Pre-200k range
        (205000, 230000),   # Post-200k range
        (230000, 245000),   # Pre-250k range
        (255000, 280000),   # Post-250k range
        (280000, 299000),   # Recent range
    ]
    
    all_results = []
    total_start_time = time.time()
    
    for range_num, (start, end) in enumerate(ranges_to_scrape, 1):
        print(f"\n🎯 RANGE {range_num}/{len(ranges_to_scrape)}: {start}-{end}")
        print("-" * 50)
        
        range_start_time = time.time()
        
        results = await scraper.scrape_comprehensive_range(start, end)
        
        range_time = time.time() - range_start_time
        all_results.extend(results)
        
        print(f"Range {start}-{end} complete: {len(results)} IPSC matches in {range_time:.1f}s")
        
        if len(results) > 0:
            print(f"✅ Productive range! Found {len(results)} matches")
            # If we found matches, this range is productive
        else:
            print(f"⭕ Empty range - no IPSC matches found")
        
        # Show cumulative progress
        total_time = time.time() - total_start_time
        total_found = len(all_results)
        print(f"🏆 CUMULATIVE: {total_found} matches in {total_time:.1f}s "
              f"({total_found/total_time*60:.1f} matches/min)")
        
        # Stop if we've found a lot of matches (can continue later)
        if total_found >= 500:
            print(f"\n🛑 Found {total_found} matches - pausing for processing")
            print("Run again to continue with remaining ranges")
            break
        
        # Brief pause between ranges
        if range_num < len(ranges_to_scrape):
            print("⏸️  Pausing 5s before next range...")
            await asyncio.sleep(5)
    
    total_time = time.time() - total_start_time
    
    print(f"\n🏁 Comprehensive scraping session complete!")
    print(f"📊 Final Statistics:")
    print(f"  Total checked: {scraper.checked_counter.value}")
    print(f"  Valid matches: {scraper.valid_counter.value}")
    print(f"  IPSC matches: {scraper.ipsc_counter.value}")
    print(f"  Saved matches: {scraper.saved_counter.value}")
    print(f"  Already existed: {scraper.existing_counter.value}")
    print(f"  Redirects: {scraper.redirect_counter.value}")
    print(f"  Errors: {scraper.error_counter.value}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Rate: {scraper.checked_counter.value/total_time:.1f} checks/s")
    
    if len(all_results) > 0:
        print(f"\n✅ Success! Found {len(all_results)} new IPSC matches")
        print(f"📋 Next steps:")
        print(f"1. Run 'python process_matches.py' to update rankings")
        print(f"2. Re-run this scraper to continue with remaining ranges")
        print(f"3. Check match_data/ directory for new files")
    else:
        print(f"\n📝 No new matches found in this session")
        print(f"All tested ranges either had no matches or were already scraped")

if __name__ == "__main__":
    asyncio.run(main())