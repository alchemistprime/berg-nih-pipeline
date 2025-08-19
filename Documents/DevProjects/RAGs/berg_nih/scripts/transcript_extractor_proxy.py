#!/usr/bin/env python3
"""
Transcript Extractor with Proxy Support - Parallel Processing Version
Runs alongside the main extractor for comparison testing
"""

# Copy the entire enhanced transcript extractor but with different defaults
import os
import json
import time
import logging
import random
import re
from typing import Dict, List, Optional
from functools import wraps
from itertools import cycle

# Load environment variables
def load_env_file():
    env_paths = ['.env', '../.env', '../../.env']
    for env_path in env_paths:
        try:
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            value = value.strip('"\'')
                            os.environ[key] = value
                return
        except Exception as e:
            continue

load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptExtractorProxy:
    def __init__(self, use_proxies: bool = True, proxy_list: List[str] = None):
        # API method detection
        self.api_method = None
        self.api_instance = None
        
        self.setup_transcript_api()
        
        # Rate limiting configuration (more aggressive for proxy mode)
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 1.0  # Faster with proxies
        self.max_delay = 5.0   # Faster max delay
        self.backoff_factor = 2.0
        self.max_retries = 3
        self.ip_blocked = False
        
        # Proxy configuration (enabled by default)
        self.use_proxies = use_proxies
        self.proxy_list = proxy_list or []
        self.proxy_cycle = cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.failed_proxies = set()
        
    def setup_transcript_api(self):
        """Setup YouTube transcript API with method detection"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.transcript_api = YouTubeTranscriptApi
            self._detect_api_method()
            logger.info(f"YouTube Transcript API loaded successfully using method: {self.api_method}")
        except ImportError:
            logger.error("youtube-transcript-api not found. Install with: pip install youtube-transcript-api")
            self.transcript_api = None
    
    def _detect_api_method(self):
        """Detect which API method to use"""
        from youtube_transcript_api import YouTubeTranscriptApi
        
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            self.api_method = 'get_transcript'
            self.api_instance = YouTubeTranscriptApi
            logger.info("Using get_transcript (static method)")
        elif hasattr(YouTubeTranscriptApi, 'fetch'):
            self.api_method = 'fetch'
            self.api_instance = YouTubeTranscriptApi()
            logger.info("Using fetch (instance method)")
        else:
            available_methods = [m for m in dir(YouTubeTranscriptApi) if not m.startswith('_')]
            raise ImportError(f"Neither 'fetch' nor 'get_transcript' method found. Available: {available_methods}")
    
    def _validate_video_id(self, video_id: str) -> bool:
        """Validate YouTube video ID format"""
        pattern = r'^[a-zA-Z0-9_-]{11}$'
        return bool(re.match(pattern, video_id))
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next working proxy from rotation"""
        if not self.use_proxies or not self.proxy_cycle:
            return None
        
        attempts = 0
        while attempts < len(self.proxy_list):
            proxy = next(self.proxy_cycle)
            if proxy not in self.failed_proxies:
                return proxy
            attempts += 1
        
        # All proxies failed, reset and try again
        logger.warning("All proxies failed, resetting failed proxy list")
        self.failed_proxies.clear()
        return next(self.proxy_cycle) if self.proxy_cycle else None
    
    def _setup_proxy_session(self):
        """Setup requests session with proxy for youtube-transcript-api"""
        if not self.use_proxies or not self.current_proxy:
            return
        
        try:
            import requests
            
            # Parse proxy URL
            if '@' in self.current_proxy:
                # Format: http://user:pass@host:port
                protocol, rest = self.current_proxy.split('://', 1)
                auth_host = rest
                if '@' in auth_host:
                    auth, host_port = auth_host.split('@', 1)
                    username, password = auth.split(':', 1)
                else:
                    host_port = auth_host
                    username = password = None
            else:
                # Format: http://host:port
                protocol, host_port = self.current_proxy.split('://', 1)
                username = password = None
            
            # Create proxy dict for requests
            proxy_dict = {
                'http': self.current_proxy,
                'https': self.current_proxy
            }
            
            # Monkey patch the youtube_transcript_api to use our proxy
            import youtube_transcript_api._api
            original_get = requests.get
            
            def proxied_get(*args, **kwargs):
                kwargs['proxies'] = proxy_dict
                kwargs['timeout'] = 10
                return original_get(*args, **kwargs)
            
            # Replace requests.get temporarily
            requests.get = proxied_get
            youtube_transcript_api._api.requests.get = proxied_get
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to setup proxy session: {e}")
            return False

    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """Extract transcript with proxy support"""
        if not self.transcript_api:
            return None
        
        if not self._validate_video_id(video_id):
            logger.error(f"Invalid video ID format: {video_id}")
            return {
                'video_id': video_id,
                'transcript_available': False,
                'error': 'Invalid video ID format'
            }
        
        for attempt in range(self.max_retries):
            try:
                # Get next proxy if using proxies
                if self.use_proxies and (attempt > 0 or not self.current_proxy):
                    self.current_proxy = self._get_next_proxy()
                    if self.current_proxy:
                        logger.info(f"Using proxy: {self.current_proxy}")
                        self._setup_proxy_session()
                
                # Simple rate limiting
                time.sleep(self.min_delay + random.uniform(0.1, 0.3))
                
                # Fetch transcript
                if self.api_method == 'fetch':
                    transcript_list = self.api_instance.fetch(video_id, languages=['en'])
                    full_text = ' '.join([item.text for item in transcript_list])
                elif self.api_method == 'get_transcript':
                    transcript_list = self.api_instance.get_transcript(video_id, languages=['en'])
                    full_text = ' '.join([item['text'] for item in transcript_list])
                else:
                    raise Exception(f"Unknown API method: {self.api_method}")
                
                # Clean transcript
                full_text = self.clean_transcript(full_text)
                
                return {
                    'video_id': video_id,
                    'transcript_available': True,
                    'full_text': full_text,
                    'word_count': len(full_text.split()),
                    'transcript_segments': len(transcript_list),
                    'proxy_used': self.current_proxy if self.use_proxies else None
                }
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if any(phrase in error_msg for phrase in [
                    'ipblocked', 'ip blocked', 'blocking requests',
                    'connection', 'timeout', 'proxy'
                ]):
                    if self.use_proxies and self.current_proxy:
                        logger.warning(f"Proxy issue: {e}, switching...")
                        self.failed_proxies.add(self.current_proxy)
                        self.current_proxy = None
                        continue
                    else:
                        logger.error(f"Connection issue: {e}")
                        break
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {
            'video_id': video_id,
            'transcript_available': False,
            'error': str(e) if 'e' in locals() else 'Failed after retries'
        }
    
    def clean_transcript(self, text: str) -> str:
        """Clean up transcript text"""
        text = re.sub(r'\[Music\]', '', text)
        text = re.sub(r'\[Applause\]', '', text)
        text = re.sub(r'\[Laughter\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

def main():
    """Main execution for proxy comparison"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dr. Berg Transcript Extractor - PROXY VERSION')
    parser.add_argument('--proxy-file', type=str, required=True, help='File containing proxy list (one per line)')
    parser.add_argument('--input-file', type=str, help='Input exploration data file')
    parser.add_argument('--output-file', type=str, help='Output filename')
    parser.add_argument('--test-count', type=int, default=10, help='Number of videos to test (default: 10)')
    parser.add_argument('--start-index', type=int, default=100, help='Start from video N to avoid conflicts')
    
    args = parser.parse_args()
    
    print("Dr. Berg Transcript Extractor - PROXY COMPARISON")
    print("=" * 50)
    
    # Load proxy list
    try:
        with open(args.proxy_file, 'r') as f:
            proxy_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"Loaded {len(proxy_list)} proxies from {args.proxy_file}")
    except FileNotFoundError:
        print(f"ERROR: Proxy file {args.proxy_file} not found")
        return 1
    
    if not proxy_list:
        print("ERROR: No valid proxies found in file")
        return 1
    
    # Initialize extractor
    extractor = TranscriptExtractorProxy(use_proxies=True, proxy_list=proxy_list)
    
    if not extractor.transcript_api:
        print("ERROR: YouTube Transcript API not available")
        return 1
    
    # Load video data
    try:
        with open(args.input_file or 'data/processed/berg_complete_catalog.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        print(f"ERROR: Input file not found: {e}")
        return 1
    
    # Filter videos (same criteria as main script)
    videos = data.get('videos', [])
    filtered_videos = []
    for video in videos:
        duration = video.get('duration_seconds', 0)
        if 121 <= duration <= 300:  # 2-5 minutes
            filtered_videos.append(video)
    
    print(f"Found {len(filtered_videos)} videos in 2-5 minute range")
    
    # Test subset starting from offset to avoid conflicts
    test_videos = filtered_videos[args.start_index:args.start_index + args.test_count]
    print(f"Testing {len(test_videos)} videos starting from index {args.start_index}")
    print(f"Using proxies: {len(proxy_list)} available")
    print()
    
    # Process videos
    results = []
    success_count = 0
    start_time = time.time()
    
    for i, video in enumerate(test_videos):
        video_id = video['video_id']
        title = video['title'][:50]
        
        print(f"PROXY TEST {i+1}/{len(test_videos)}: {title}...")
        
        result = extractor.get_transcript(video_id)
        
        if result and result['transcript_available']:
            success_count += 1
            proxy_info = f" (via {result.get('proxy_used', 'direct')})" if extractor.use_proxies else ""
            print(f"  ✓ Success: {result['word_count']} words{proxy_info}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No result'
            print(f"  ✗ Failed: {error}")
        
        results.append({**video, 'transcript_result': result})
    
    # Summary
    elapsed = time.time() - start_time
    success_rate = (success_count / len(test_videos)) * 100
    
    print(f"\nPROXY COMPARISON RESULTS:")
    print(f"=" * 40)
    print(f"Videos tested: {len(test_videos)}")
    print(f"Successful: {success_count}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Rate: {len(test_videos)/elapsed*60:.1f} videos/hour")
    print(f"Failed proxies: {len(extractor.failed_proxies)}")
    
    # Save results
    output_file = args.output_file or f'proxy_test_results_{int(time.time())}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_metadata': {
                'test_count': len(test_videos),
                'success_count': success_count,
                'success_rate': success_rate,
                'elapsed_seconds': elapsed,
                'proxies_used': len(proxy_list),
                'failed_proxies': list(extractor.failed_proxies)
            },
            'results': results
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    exit(main())