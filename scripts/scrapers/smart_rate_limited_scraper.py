#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

"""
Smart rate-limited PractiScore scraper that learns and adapts to rate limits
"""

import requests
import time
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SmartRateLimitedScraper:
    """Intelligent scraper that learns PractiScore's rate limits"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Rate limiting state
        self.successful_requests = 0
        self.blocked_requests = 0
        self.current_delay = 1.0  # Start with 1 second
        self.max_delay = 30.0
        self.min_delay = 0.5
        self.success_streak = 0
        self.block_streak = 0
        
        # Request timing analysis
        self.request_times = []
        self.block_times = []
        
        # User agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
        ]
        
        self.setup_session()
    
    def setup_session(self):
        """Setup session with rotating headers"""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
    
    def analyze_rate_limits(self, test_count: int = 20) -> Dict[str, Any]:
        """Analyze PractiScore's rate limiting behavior"""
        
        print(f"🔍 Analyzing PractiScore rate limits with {test_count} test requests...")
        
        results = {
            'successful': 0,
            'blocked': 0,
            'errors': 0,
            'response_times': [],
            'optimal_delay': 1.0,
            'patterns': []
        }
        
        test_urls = [
            f'https://practiscore.com/results/new/{299990 + i}' 
            for i in range(test_count)
        ]
        
        for i, url in enumerate(test_urls):
            print(f"  Test {i+1}/{test_count}: ", end="")
            
            # Rotate user agent
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            
            start_time = time.time()
            
            try:
                response = self.session.get(url, timeout=10, verify=False)
                response_time = time.time() - start_time
                results['response_times'].append(response_time)
                
                if response.status_code == 200:
                    if 'cloudflare' in response.text.lower() and 'blocked' in response.text.lower():
                        results['blocked'] += 1
                        print(f"BLOCKED (Cloudflare) - {response_time:.2f}s")
                        self.current_delay = min(self.current_delay * 1.5, self.max_delay)
                    else:
                        results['successful'] += 1
                        print(f"SUCCESS - {response_time:.2f}s")
                        self.current_delay = max(self.current_delay * 0.9, self.min_delay)
                        
                elif response.status_code == 403:
                    results['blocked'] += 1
                    print(f"403 FORBIDDEN - {response_time:.2f}s")
                    self.current_delay = min(self.current_delay * 2.0, self.max_delay)
                    
                elif response.status_code == 429:
                    results['blocked'] += 1
                    print(f"429 RATE LIMITED - {response_time:.2f}s")
                    self.current_delay = min(self.current_delay * 3.0, self.max_delay)
                    
                else:
                    results['errors'] += 1
                    print(f"HTTP {response.status_code} - {response_time:.2f}s")
                    
            except requests.RequestException as e:
                results['errors'] += 1
                response_time = time.time() - start_time
                print(f"ERROR: {str(e)[:30]}... - {response_time:.2f}s")
            
            # Adaptive delay based on current success rate
            delay = self.current_delay + random.uniform(0, 1)
            if i < test_count - 1:  # Don't delay after last request
                print(f"    Waiting {delay:.1f}s...")
                time.sleep(delay)
        
        # Calculate optimal delay
        if results['successful'] > 0:
            avg_response_time = sum(results['response_times']) / len(results['response_times'])
            success_rate = results['successful'] / test_count
            
            if success_rate > 0.8:
                results['optimal_delay'] = max(avg_response_time + 1.0, 1.0)
            elif success_rate > 0.5:
                results['optimal_delay'] = max(avg_response_time + 3.0, 3.0)
            elif success_rate > 0.2:
                results['optimal_delay'] = max(avg_response_time + 8.0, 8.0)
            else:
                results['optimal_delay'] = 15.0
        else:
            results['optimal_delay'] = 20.0
        
        return results
    
    def smart_fetch_with_backoff(self, match_id: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Fetch with intelligent exponential backoff"""
        
        for attempt in range(max_retries):
            try:
                # Rotate user agent and add some header variation
                self.session.headers['User-Agent'] = random.choice(self.user_agents)
                
                # Add some randomness to avoid pattern detection
                if random.random() < 0.3:
                    self.session.headers['Accept-Language'] = random.choice([
                        'en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.8,sv;q=0.7'
                    ])
                
                url = f'https://practiscore.com/results/new/{match_id}'
                response = self.session.get(url, timeout=15, verify=False)
                
                if response.status_code == 200:
                    if 'cloudflare' in response.text.lower() and 'blocked' in response.text.lower():
                        self.blocked_requests += 1
                        self.block_streak += 1
                        self.success_streak = 0
                        
                        # Exponential backoff for blocks
                        backoff_delay = min(2 ** attempt * (1 + random.random()), 60)
                        print(f"    Cloudflare block, backing off {backoff_delay:.1f}s")
                        time.sleep(backoff_delay)
                        continue
                    else:
                        self.successful_requests += 1
                        self.success_streak += 1
                        self.block_streak = 0
                        return response
                        
                elif response.status_code in [403, 429]:
                    self.blocked_requests += 1
                    self.block_streak += 1
                    backoff_delay = min(5 ** attempt * (1 + random.random()), 120)
                    print(f"    HTTP {response.status_code}, backing off {backoff_delay:.1f}s")
                    time.sleep(backoff_delay)
                    continue
                    
                else:
                    print(f"    HTTP {response.status_code}")
                    return response
                    
            except requests.RequestException as e:
                backoff_delay = 2 ** attempt
                print(f"    Request error, retrying in {backoff_delay}s: {str(e)[:30]}...")
                time.sleep(backoff_delay)
        
        return None
    
    def calculate_adaptive_delay(self) -> float:
        """Calculate delay based on recent success/failure patterns"""
        
        # Base delay increases with consecutive blocks
        base_delay = 1.0 + (self.block_streak * 2.0)
        
        # Decrease delay with consecutive successes
        if self.success_streak > 3:
            base_delay *= 0.7
        elif self.success_streak > 6:
            base_delay *= 0.5
        
        # Overall success rate adjustment
        total_requests = self.successful_requests + self.blocked_requests
        if total_requests > 10:
            success_rate = self.successful_requests / total_requests
            if success_rate < 0.3:
                base_delay *= 3.0
            elif success_rate < 0.6:
                base_delay *= 1.5
        
        # Add randomization and bounds
        delay = base_delay + random.uniform(0, 2)
        return max(min(delay, self.max_delay), self.min_delay)
    
    def scrape_match_range(self, start_id: int, end_id: int, max_matches: int = 100) -> int:
        """Scrape a range of matches with intelligent rate limiting"""
        
        print(f"🎯 Smart scraping matches {start_id}-{end_id} (max {max_matches})")
        
        successful = 0
        total_checked = 0
        
        for match_id in range(start_id, end_id + 1):
            total_checked += 1
            
            if total_checked % 10 == 0:
                success_rate = (self.successful_requests / 
                              max(self.successful_requests + self.blocked_requests, 1)) * 100
                print(f"  Progress: {total_checked}/{end_id-start_id+1}, "
                      f"Success rate: {success_rate:.1f}%, Found: {successful}")
            
            # Skip if already exists
            filename = f"match_data/{datetime.now().strftime('%Y-%m-%d')}_practiscore_{match_id}.json"
            if os.path.exists(filename):
                continue
            
            print(f"  Fetching {match_id}...", end=" ")
            
            response = self.smart_fetch_with_backoff(str(match_id))
            
            if response and response.status_code == 200:
                # Try to parse match data
                match_data = self.parse_match_response(response.text, str(match_id))
                
                if match_data and match_data.get('combined_results'):
                    successful += 1
                    shooters = len(match_data['combined_results'])
                    title = match_data.get('match_title', 'Unknown')[:30]
                    print(f"✓ {title}... ({shooters} shooters)")
                    
                    # Save the match
                    self.save_match_data(match_data)
                    
                    if successful >= max_matches:
                        print(f"  Reached {max_matches} matches, stopping")
                        break
                else:
                    print("✗ No valid data")
            else:
                print("✗ Failed to fetch")
            
            # Adaptive delay
            delay = self.calculate_adaptive_delay()
            if total_checked % 5 == 0:
                print(f"    Adaptive delay: {delay:.1f}s")
            time.sleep(delay)
        
        return successful
    
    def parse_match_response(self, html_content: str, match_id: str) -> Optional[Dict[str, Any]]:
        """Parse match response - placeholder for actual parsing logic"""
        
        # For now, return None since we can't parse the blocked pages
        # In a real implementation, this would extract match data from HTML
        
        if len(html_content) < 1000:  # Too short, likely an error page
            return None
        
        if 'cloudflare' in html_content.lower():
            return None
        
        # Placeholder - would implement actual parsing here
        return None
    
    def save_match_data(self, match_data: Dict[str, Any]):
        """Save match data"""
        match_date = match_data.get('match_date', '')
        timestamp = match_date.split('T')[0] if 'T' in match_date else datetime.now().strftime('%Y-%m-%d')
        match_id = match_data['match_id']
        filename = f"match_data/{timestamp}_practiscore_{match_id}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)
    
    def print_statistics(self):
        """Print scraping statistics"""
        total = self.successful_requests + self.blocked_requests
        if total > 0:
            success_rate = (self.successful_requests / total) * 100
            print(f"\n📊 Scraping Statistics:")
            print(f"  Total requests: {total}")
            print(f"  Successful: {self.successful_requests} ({success_rate:.1f}%)")
            print(f"  Blocked: {self.blocked_requests} ({100-success_rate:.1f}%)")
            print(f"  Current delay: {self.current_delay:.1f}s")
            print(f"  Success streak: {self.success_streak}")
            print(f"  Block streak: {self.block_streak}")

def main():
    """Main function to test smart rate limiting"""
    
    print("🧠 Smart Rate-Limited PractiScore Scraper")
    print("=" * 50)
    
    scraper = SmartRateLimitedScraper()
    
    # Step 1: Analyze rate limits
    analysis = scraper.analyze_rate_limits(test_count=10)
    
    print(f"\n📊 Rate Limit Analysis Results:")
    print(f"  Successful: {analysis['successful']}")
    print(f"  Blocked: {analysis['blocked']}")
    print(f"  Errors: {analysis['errors']}")
    print(f"  Optimal delay: {analysis['optimal_delay']:.1f}s")
    
    if analysis['successful'] > 0:
        print(f"\n✅ Some requests succeeded! Proceeding with smart scraping...")
        
        # Step 2: Smart scraping with learned parameters
        scraper.current_delay = analysis['optimal_delay']
        
        successful = scraper.scrape_match_range(299980, 299999, max_matches=20)
        
        print(f"\n🏁 Smart scraping complete!")
        print(f"Successfully scraped: {successful} matches")
        
        scraper.print_statistics()
        
    else:
        print(f"\n❌ All requests blocked - PractiScore has strong anti-bot protection")
        print(f"Consider alternative approaches:")
        print(f"  1. Manual data entry for key matches")
        print(f"  2. Browser automation (Selenium)")
        print(f"  3. Requesting API access from PractiScore")
        print(f"  4. Data sharing partnerships")

if __name__ == "__main__":
    main()