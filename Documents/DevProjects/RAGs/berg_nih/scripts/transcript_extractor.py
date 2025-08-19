#!/usr/bin/env python3
"""
Transcript Extractor for Dr. Berg Videos
Adds transcript extraction capability to our exploration pipeline
"""

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
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    value = value.strip('"\'')
                    os.environ[key] = value
    except FileNotFoundError:
        pass

load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptExtractor:
    def __init__(self, use_proxies: bool = False, proxy_list: List[str] = None):
        # API method detection (initialize before setup)
        self.api_method = None
        self.api_instance = None
        
        # Setup API and detect method
        self.setup_transcript_api()
        
        # Rate limiting configuration (enhanced for IP blocking)
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 3.0  # Increased from 1.0
        self.max_delay = 15.0  # Increased from 8.0
        self.backoff_factor = 2.5  # Increased from 2.0
        self.max_retries = 5  # Increased from 3
        self.ip_blocked = False  # Track if we're currently IP blocked
        
        # Proxy configuration
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
            
            # Detect available methods
            self._detect_api_method()
            
            logger.info(f"YouTube Transcript API loaded successfully using method: {self.api_method}")
        except ImportError:
            logger.error("youtube-transcript-api not found. Install with: pip install youtube-transcript-api")
            self.transcript_api = None
    
    def _detect_api_method(self):
        """Detect which API method to use and how to parse results"""
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Check available methods in order of preference
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
        
        # All proxies failed, reset failed list and try again
        logger.warning("All proxies failed, resetting failed proxy list")
        self.failed_proxies.clear()
        return next(self.proxy_cycle) if self.proxy_cycle else None
    
    def _setup_proxy_session(self, proxy: str = None):
        """Setup requests session with proxy if needed"""
        if not proxy or not self.use_proxies:
            return None
        
        try:
            import requests
            session = requests.Session()
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
            # Test proxy with a quick request
            session.get('https://httpbin.org/ip', timeout=5)
            self.current_proxy = proxy
            return session
        except Exception as e:
            logger.warning(f"Proxy {proxy} failed: {e}")
            self.failed_proxies.add(proxy)
            return None
    
    def _rate_limited_request(self, func, *args, **kwargs):
        """Execute function with rate limiting and retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Handle proxy rotation if enabled
                if self.use_proxies and (attempt > 0 or not self.current_proxy):
                    proxy = self._get_next_proxy()
                    if proxy:
                        session = self._setup_proxy_session(proxy)
                        if not session and attempt == 0:
                            # Try without proxy on first attempt if proxy setup fails
                            pass
                
                # Implement intelligent rate limiting
                self._wait_for_rate_limit()
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Update request tracking
                self.request_count += 1
                self.last_request_time = time.time()
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Categorize errors for retry logic
                if any(phrase in error_msg for phrase in [
                    'ipblocked', 'ip blocked', 'blocking requests from your ip',
                    'requestblocked', 'request blocked'
                ]):
                    # IP blocked - need longer cooling off period
                    self.ip_blocked = True
                    delay = 300 + (attempt * 180)  # 5-14 minutes escalating
                    logger.error(f"IP BLOCKED by YouTube (attempt {attempt + 1}/{self.max_retries}). Cooling off for {delay/60:.1f} minutes...")
                    logger.error(f"Consider using --use-proxies option or waiting longer between batches")
                    time.sleep(delay)
                    continue
                    
                elif any(phrase in error_msg for phrase in [
                    'rate limit', 'too many requests', '429', 'quota exceeded'
                ]):
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}). Waiting {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                
                elif any(phrase in error_msg for phrase in [
                    'timeout', 'connection', 'temporary', '503', '502', 'proxy'
                ]):
                    # Try different proxy or increase delay
                    if self.use_proxies and self.current_proxy:
                        self.failed_proxies.add(self.current_proxy)
                        self.current_proxy = None
                    
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(f"Temporary error (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                
                else:
                    # Permanent error, don't retry
                    raise e
        
        raise Exception(f"Failed after {self.max_retries} attempts")
    
    def _wait_for_rate_limit(self):
        """Implement intelligent rate limiting with adaptive delays"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # If recently IP blocked, use very conservative delays
        if self.ip_blocked:
            base_delay = self.max_delay * 2  # Very conservative
        else:
            # Calculate adaptive delay based on request frequency
            if self.request_count > 0:
                time_window = max((current_time - self.last_request_time) / 60, 1)
                requests_per_minute = self.request_count / time_window
                
                # Much more conservative limits
                if requests_per_minute > 10:  # Reduced from 30
                    base_delay = self.max_delay
                elif requests_per_minute > 5:  # Reduced from 15
                    base_delay = self.min_delay * 3
                elif requests_per_minute > 3:  # Reduced from 10
                    base_delay = self.min_delay * 2
                else:
                    base_delay = self.min_delay
            else:
                base_delay = self.min_delay
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.2, 0.5)  # Increased jitter
        total_delay = base_delay + jitter
        
        if time_since_last < total_delay:
            sleep_time = total_delay - time_since_last
            time.sleep(sleep_time)
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        base_delay = self.min_delay * (self.backoff_factor ** attempt)
        max_delay = min(base_delay, 30.0)  # Cap at 30 seconds
        jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
        return max_delay * jitter
    
    def _fetch_transcript_adaptive(self, video_id: str) -> List[Dict]:
        """Adaptively fetch transcript using detected API method"""
        if self.api_method == 'fetch':
            return self.api_instance.fetch(video_id, languages=['en'])
        elif self.api_method == 'get_transcript':
            return self.api_instance.get_transcript(video_id, languages=['en'])
        else:
            raise Exception(f"Unknown API method: {self.api_method}")
    
    def _extract_text_adaptive(self, transcript_list: List) -> str:
        """Extract text from transcript list, handling different return types"""
        if not transcript_list:
            return ''
        
        first_item = transcript_list[0]
        
        # Handle object with .text attribute (fetch method)
        if hasattr(first_item, 'text'):
            return ' '.join([item.text for item in transcript_list])
        
        # Handle dict with 'text' key (get_transcript method)
        elif isinstance(first_item, dict) and 'text' in first_item:
            return ' '.join([item['text'] for item in transcript_list])
        
        else:
            raise Exception(f"Unknown transcript format: {type(first_item)}")
    
    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """Extract transcript for a single video with robust error handling"""
        if not self.transcript_api:
            return None
        
        # Validate video ID
        if not self._validate_video_id(video_id):
            logger.error(f"Invalid video ID format: {video_id}")
            return {
                'video_id': video_id,
                'transcript_available': False,
                'full_text': '',
                'word_count': 0,
                'transcript_segments': 0,
                'error': 'Invalid video ID format'
            }
        
        try:
            # Use rate-limited request with adaptive API method
            transcript_list = self._rate_limited_request(
                self._fetch_transcript_adaptive, video_id
            )
            
            # Extract text adaptively based on return type
            full_text = self._extract_text_adaptive(transcript_list)
            
            # Clean up transcript artifacts
            full_text = self.clean_transcript(full_text)
            
            return {
                'video_id': video_id,
                'transcript_available': True,
                'full_text': full_text,
                'word_count': len(full_text.split()),
                'transcript_segments': len(transcript_list),
                'api_method_used': self.api_method,
                'proxy_used': self.current_proxy if self.use_proxies else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Could not get transcript for {video_id}: {error_msg}")
            
            # Categorize error for better handling
            error_type = 'unknown'
            if 'not available' in error_msg.lower() or 'disabled' in error_msg.lower():
                error_type = 'transcript_disabled'
            elif 'not found' in error_msg.lower() or '404' in error_msg:
                error_type = 'video_not_found'
            elif 'rate limit' in error_msg.lower() or '429' in error_msg:
                error_type = 'rate_limited'
            elif 'invalid' in error_msg.lower():
                error_type = 'invalid_format'
            
            return {
                'video_id': video_id,
                'transcript_available': False,
                'full_text': '',
                'word_count': 0,
                'transcript_segments': 0,
                'error': error_msg,
                'error_type': error_type
            }
    
    def clean_transcript(self, text: str) -> str:
        """Clean up transcript text"""
        import re
        
        # Remove common artifacts
        text = re.sub(r'\[Music\]', '', text)
        text = re.sub(r'\[Applause\]', '', text)
        text = re.sub(r'\[Laughter\]', '', text)
        
        # Fix common transcription errors
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces
        text = text.strip()
        
        return text
    
    def extract_medical_claims(self, transcript_text: str) -> List[Dict]:
        """Extract medical claims from transcript using improved patterns"""
        import re
        
        claims = []
        
        # Enhanced patterns for Dr. Berg's speaking style
        patterns = [
            # Direct recommendations
            (r'if you have (.{5,40}),?\s*(?:you should|try|take|do)\s*(.{5,60})', 'recommendation'),
            
            # Deficiency patterns
            (r'(.{5,40})\s*deficiency\s*(?:causes?|leads? to|results? in)\s*(.{5,60})', 'deficiency_cause'),
            (r'(?:signs?|symptoms?)\s*of\s*(.{5,40})\s*deficiency[:\s]*(.{5,100})', 'deficiency_symptoms'),
            
            # Causation patterns
            (r'(.{5,40})\s*(?:is caused by|comes from|results from)\s*(.{5,60})', 'causation'),
            
            # Best/top recommendations
            (r'(?:best|top)\s*(?:thing|way|food|supplement|vitamin)\s*for\s*(.{5,40})\s*is\s*(.{5,60})', 'best_for'),
            
            # Body signals
            (r'(?:when|if)\s*your body\s*(.{5,60}),?\s*(?:it means|that means)\s*(.{5,60})', 'body_signal'),
            
            # Problem-solution
            (r'(?:the problem with|issue with)\s*(.{5,40})\s*is\s*(.{5,60})', 'problem_identified')
        ]
        
        for pattern, claim_type in patterns:
            matches = re.findall(pattern, transcript_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    claims.append({
                        'claim_type': claim_type,
                        'subject': match[0].strip(),
                        'predicate': match[1].strip(),
                        'confidence': 'medium',  # From transcript vs title/description
                        'pattern_used': pattern
                    })
        
        return claims
    
    def process_video_transcripts(self, exploration_data=None, exploration_data_file: str = None, output_filename: str = 'data/processed/berg_exploration_with_transcripts_v3.json', batch_size: int = None, start_index: int = 0, save_frequency: int = 10, min_duration: int = None, max_duration: int = None) -> Dict:
        """Process transcripts for all videos in exploration data"""
        
        # Support both in-memory data and file-based input for backward compatibility
        if exploration_data is not None:
            data = exploration_data
        elif exploration_data_file is not None:
            # Load existing exploration data from file
            try:
                with open(exploration_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                logger.error(f"Exploration data file {exploration_data_file} not found")
                return {}
        else:
            logger.error("Must provide either exploration_data or exploration_data_file")
            return {}
        
        videos = data.get('videos', [])
        original_video_count = len(videos)
        
        # Apply duration filtering if specified
        if min_duration is not None or max_duration is not None:
            filtered_videos = []
            for video in videos:
                duration = video.get('duration_seconds', 0)
                
                # Check minimum duration
                if min_duration is not None and duration < min_duration:
                    continue
                    
                # Check maximum duration  
                if max_duration is not None and duration > max_duration:
                    continue
                    
                filtered_videos.append(video)
            
            videos = filtered_videos
            logger.info(f"Duration filtering: {original_video_count} -> {len(videos)} videos")
            if min_duration and max_duration:
                logger.info(f"Filter range: {min_duration//60}:{min_duration%60:02d} to {max_duration//60}:{max_duration%60:02d}")
            elif min_duration:
                logger.info(f"Minimum duration: {min_duration//60}:{min_duration%60:02d}")
            elif max_duration:
                logger.info(f"Maximum duration: {max_duration//60}:{max_duration%60:02d}")
        
        total_videos = len(videos)
        
        # Apply start index and batch size
        if start_index > 0:
            videos = videos[start_index:]
            logger.info(f"Resuming from video {start_index + 1}/{total_videos}")
        
        if batch_size:
            videos = videos[:batch_size]
            logger.info(f"Processing batch of {len(videos)} videos (from index {start_index})")
        else:
            logger.info(f"Processing {len(videos)} videos...")
        
        # Process each video
        transcript_data = []
        success_count = 0
        failed_videos = []
        
        for i, video in enumerate(videos):
            video_id = video['video_id']
            title = video['title']
            
            current_index = start_index + i + 1
            logger.info(f"Processing {current_index}/{total_videos} ({i+1}/{len(videos)} in batch): {title[:50]}...")
            
            # Get transcript
            transcript_result = self.get_transcript(video_id)
            
            if transcript_result and transcript_result['transcript_available']:
                # Extract claims from transcript
                claims = self.extract_medical_claims(transcript_result['full_text'])
                
                # Combine with existing video data
                enhanced_video = {
                    **video,
                    'transcript': transcript_result,
                    'transcript_claims': claims,
                    'total_claims': len(video.get('basic_claims', [])) + len(claims)
                }
                
                transcript_data.append(enhanced_video)
                success_count += 1
                
                logger.info(f"✓ Extracted {len(claims)} claims from transcript ({transcript_result['word_count']} words)")
            else:
                # Keep video data without transcript
                enhanced_video = {
                    **video,
                    'transcript': transcript_result or {'transcript_available': False},
                    'transcript_claims': [],
                    'total_claims': len(video.get('basic_claims', []))
                }
                transcript_data.append(enhanced_video)
                logger.warning(f"✗ No transcript available")
            
            # Rate limiting handled by _rate_limited_request
            
            # Progress update and incremental save
            if (i + 1) % save_frequency == 0:
                logger.info(f"Progress: {i+1}/{len(videos)} processed, {success_count} transcripts extracted")
                # Save progress periodically
            elif (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(videos)} processed, {success_count} transcripts extracted")
        
        # Create enhanced dataset
        enhanced_data = {
            **data,
            'videos': transcript_data,
            'transcript_stats': {
                'total_videos': len(videos),
                'transcripts_extracted': success_count,
                'transcript_success_rate': round(success_count / len(videos) * 100, 1),
                'total_transcript_claims': sum(len(v.get('transcript_claims', [])) for v in transcript_data),
                'avg_claims_per_video': round(sum(v.get('total_claims', 0) for v in transcript_data) / len(transcript_data), 1)
            }
        }
        
        # Save enhanced data
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Enhanced data saved to {output_filename}")
        
        # Print summary
        print(f"\nTRANSCRIPT EXTRACTION SUMMARY:")
        print(f"{'='*40}")
        print(f"Videos processed: {len(videos)}")
        print(f"Transcripts extracted: {success_count}")
        print(f"Success rate: {enhanced_data['transcript_stats']['transcript_success_rate']}%")
        print(f"Total claims extracted: {enhanced_data['transcript_stats']['total_transcript_claims']}")
        print(f"Average claims per video: {enhanced_data['transcript_stats']['avg_claims_per_video']}")
        
        return enhanced_data

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dr. Berg Transcript Extractor')
    parser.add_argument('--use-proxies', action='store_true', help='Enable proxy rotation for high-volume extraction')
    parser.add_argument('--proxy-file', type=str, help='File containing proxy list (one per line)')
    parser.add_argument('--input-file', type=str, help='Input exploration data file')
    parser.add_argument('--output-file', type=str, help='Output filename (default: data/processed/berg_exploration_with_transcripts_v3.json)')
    parser.add_argument('--batch-size', type=int, help='Process videos in batches of N (default: process all)')
    parser.add_argument('--start-index', type=int, default=0, help='Start processing from video index N (0-based)')
    parser.add_argument('--save-frequency', type=int, default=10, help='Save progress every N videos (default: 10)')
    parser.add_argument('--min-duration', type=int, help='Minimum video duration in seconds (e.g., 120 for 2 minutes)')
    parser.add_argument('--max-duration', type=int, help='Maximum video duration in seconds (e.g., 300 for 5 minutes)')
    parser.add_argument('--auto-filename', action='store_true', help='Auto-generate output filename based on duration filter')
    
    args = parser.parse_args()
    
    # Auto-generate output filename based on duration filter
    if args.auto_filename or (args.min_duration or args.max_duration):
        if not args.output_file:
            filename_parts = ['berg_transcripts']
            
            if args.min_duration and args.max_duration:
                min_min = args.min_duration // 60
                min_sec = args.min_duration % 60
                max_min = args.max_duration // 60
                max_sec = args.max_duration % 60
                filename_parts.append(f"{min_min}m{min_sec:02d}s_to_{max_min}m{max_sec:02d}s")
            elif args.min_duration:
                min_min = args.min_duration // 60
                min_sec = args.min_duration % 60
                filename_parts.append(f"min_{min_min}m{min_sec:02d}s")
            elif args.max_duration:
                max_min = args.max_duration // 60
                max_sec = args.max_duration % 60
                filename_parts.append(f"max_{max_min}m{max_sec:02d}s")
            
            if args.batch_size:
                filename_parts.append(f"batch{args.batch_size}")
                
            args.output_file = f"data/processed/{'_'.join(filename_parts)}.json"
            print(f"Auto-generated output filename: {args.output_file}")
    
    print("Dr. Berg Transcript Extractor v2.0")
    print("=" * 40)
    
    # Load proxy list if specified
    proxy_list = []
    if args.use_proxies and args.proxy_file:
        try:
            with open(args.proxy_file, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(proxy_list)} proxies from {args.proxy_file}")
        except FileNotFoundError:
            print(f"WARNING: Proxy file {args.proxy_file} not found. Continuing without proxies.")
            args.use_proxies = False
    
    # Initialize extractor with proxy configuration
    extractor = TranscriptExtractor(
        use_proxies=args.use_proxies,
        proxy_list=proxy_list
    )
    
    if not extractor.transcript_api:
        print("ERROR: YouTube Transcript API not available")
        print("Install with: pip install youtube-transcript-api")
        return
    
    print(f"Configuration:")
    print(f"  API Method: {extractor.api_method}")
    print(f"  Proxy Rotation: {'Enabled' if args.use_proxies else 'Disabled'}")
    if args.use_proxies:
        print(f"  Proxy Count: {len(proxy_list)}")
    print()
    
    # Process transcripts with batch support and duration filtering
    result = extractor.process_video_transcripts(
        exploration_data_file=args.input_file,
        output_filename=args.output_file,
        batch_size=args.batch_size,
        start_index=args.start_index,
        save_frequency=args.save_frequency,
        min_duration=args.min_duration,
        max_duration=args.max_duration
    )
    
    if result:
        print(f"\n✓ Transcript extraction completed successfully!")
        print(f"✓ Enhanced data saved to: {args.output_file or 'data/processed/berg_exploration_with_transcripts_v3.json'}")
        
        # Print final statistics
        stats = result.get('transcript_stats', {})
        if stats:
            print(f"\nFinal Statistics:")
            print(f"  Total requests made: {extractor.request_count}")
            print(f"  Success rate: {stats.get('transcript_success_rate', 0)}%")
            print(f"  Total claims extracted: {stats.get('total_transcript_claims', 0)}")
            if args.use_proxies:
                print(f"  Failed proxies: {len(extractor.failed_proxies)}")

if __name__ == "__main__":
    main()