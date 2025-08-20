#!/usr/bin/env python3
"""
Human-Like Batch Transcript Extractor for Dr. Berg Videos
Implements human-like processing patterns with configurable wait times and proxy rotation
Supports parallel processing with multiple simultaneous batch operations
"""

import os
import json
import time
import logging
import random
import re
import threading
import subprocess
import sys
from typing import Dict, List, Optional, Tuple
from functools import wraps
from itertools import cycle
from datetime import datetime, timedelta

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class HumanLikeBatchExtractor:
    def __init__(self, use_proxies: bool = True, proxy_list: List[str] = None):
        # API method detection
        self.api_method = None
        self.api_instance = None
        
        self.setup_transcript_api()
        
        # Human-like timing configuration
        self.min_video_delay = 8.0   # 8-20 seconds between videos
        self.max_video_delay = 20.0
        self.batch_wait_times = [20, 22, 30, 23, 22]  # Minutes between batches
        self.current_batch = 0
        
        # Rate limiting (conservative for human-like behavior)
        self.request_count = 0
        self.last_request_time = 0
        self.max_retries = 3
        self.ip_blocked = False
        
        # Proxy configuration
        self.use_proxies = use_proxies
        self.proxy_list = proxy_list or []
        self.proxy_cycle = cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.failed_proxies = set()
        
        # Batch tracking
        self.batch_stats = {
            'batches_completed': 0,
            'total_videos_processed': 0,
            'total_successes': 0,
            'start_time': None,
            'proxy_rotations': 0
        }
    
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
        self.batch_stats['proxy_rotations'] += 1
        return next(self.proxy_cycle) if self.proxy_cycle else None
    
    def _setup_proxy_session(self):
        """Setup proxy session with current proxy"""
        if not self.use_proxies or not self.current_proxy:
            return
        
        try:
            import requests
            
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
                kwargs['timeout'] = 15
                return original_get(*args, **kwargs)
            
            # Replace requests.get temporarily
            requests.get = proxied_get
            youtube_transcript_api._api.requests.get = proxied_get
            
            logger.info(f"Proxy session configured: {self.current_proxy}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to setup proxy session: {e}")
            if self.current_proxy:
                self.failed_proxies.add(self.current_proxy)
            return False
    
    def _human_like_delay(self):
        """Implement human-like delays between video requests"""
        # Random delay between videos (8-20 seconds)
        base_delay = random.uniform(self.min_video_delay, self.max_video_delay)
        
        # Add occasional longer pauses (simulate human breaks)
        if random.random() < 0.1:  # 10% chance of longer pause
            base_delay += random.uniform(30, 90)  # 30-90 second break
            logger.info(f"Taking a human-like break: {base_delay:.1f}s")
        
        # Add small jitter
        jitter = random.uniform(-1.0, 1.0)
        total_delay = max(base_delay + jitter, 5.0)  # Minimum 5 seconds
        
        logger.debug(f"Human-like delay: {total_delay:.1f}s")
        time.sleep(total_delay)
    
    def _rotate_proxy(self):
        """Rotate to next proxy"""
        if not self.use_proxies:
            return
        
        old_proxy = self.current_proxy
        self.current_proxy = self._get_next_proxy()
        
        if self.current_proxy != old_proxy:
            logger.info(f"Rotated proxy: {old_proxy} -> {self.current_proxy}")
            self._setup_proxy_session()
            self.batch_stats['proxy_rotations'] += 1
    
    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """Extract transcript with human-like behavior"""
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
                # Apply human-like delay before each request
                if attempt == 0:
                    self._human_like_delay()
                else:
                    # Longer delays on retries
                    retry_delay = random.uniform(15, 45)
                    logger.info(f"Retry delay: {retry_delay:.1f}s")
                    time.sleep(retry_delay)
                
                # Fetch transcript using detected API method
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
                
                self.request_count += 1
                self.last_request_time = time.time()
                
                return {
                    'video_id': video_id,
                    'transcript_available': True,
                    'full_text': full_text,
                    'word_count': len(full_text.split()),
                    'transcript_segments': len(transcript_list),
                    'proxy_used': self.current_proxy if self.use_proxies else None,
                    'attempt': attempt + 1
                }
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle IP blocking
                if any(phrase in error_msg for phrase in [
                    'ipblocked', 'ip blocked', 'blocking requests',
                    'requestblocked', 'request blocked'
                ]):
                    logger.error(f"IP BLOCKED detected (attempt {attempt + 1})")
                    if self.use_proxies:
                        logger.info("Rotating proxy due to IP block...")
                        if self.current_proxy:
                            self.failed_proxies.add(self.current_proxy)
                        self._rotate_proxy()
                        continue
                    else:
                        # Without proxies, wait longer
                        block_delay = random.uniform(300, 600)  # 5-10 minutes
                        logger.error(f"No proxies available. Waiting {block_delay/60:.1f} minutes...")
                        time.sleep(block_delay)
                        continue
                
                # Handle other errors
                elif any(phrase in error_msg for phrase in [
                    'timeout', 'connection', 'temporary', '503', '502'
                ]):
                    logger.warning(f"Temporary error (attempt {attempt + 1}): {e}")
                    if self.use_proxies and random.random() < 0.5:  # 50% chance to rotate proxy
                        self._rotate_proxy()
                    continue
                
                else:
                    # Permanent error, don't retry
                    logger.warning(f"Permanent error for {video_id}: {e}")
                    break
        
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
    
    def process_batch(self, videos: List[Dict], batch_number: int, output_file: str) -> Dict:
        """Process a single batch of videos with human-like behavior"""
        logger.info(f"Starting batch {batch_number} with {len(videos)} videos")
        
        if not self.batch_stats['start_time']:
            self.batch_stats['start_time'] = time.time()
        
        # Rotate proxy at start of each batch
        if self.use_proxies:
            self._rotate_proxy()
        
        results = []
        success_count = 0
        
        for i, video in enumerate(videos):
            video_id = video['video_id']
            title = video['title'][:50]
            
            logger.info(f"Batch {batch_number} - Video {i+1}/{len(videos)}: {title}...")
            
            # Get transcript
            transcript_result = self.get_transcript(video_id)
            
            # Combine with video data
            enhanced_video = {
                **video,
                'transcript_attempted': True,
                'transcript_result': transcript_result,
                'batch_number': batch_number,
                'processed_at': datetime.now().isoformat()
            }
            
            results.append(enhanced_video)
            
            if transcript_result and transcript_result['transcript_available']:
                success_count += 1
                proxy_info = f" (via proxy)" if self.use_proxies else ""
                logger.info(f"  ✓ Success: {transcript_result['word_count']} words{proxy_info}")
            else:
                error = transcript_result.get('error', 'Unknown error') if transcript_result else 'No result'
                logger.warning(f"  ✗ Failed: {error}")
        
        # Update batch stats
        self.batch_stats['batches_completed'] += 1
        self.batch_stats['total_videos_processed'] += len(videos)
        self.batch_stats['total_successes'] += success_count
        
        # Save batch results
        batch_data = {
            'batch_metadata': {
                'batch_number': batch_number,
                'video_count': len(videos),
                'success_count': success_count,
                'success_rate': (success_count / len(videos)) * 100,
                'proxy_rotations': self.batch_stats['proxy_rotations'],
                'completed_at': datetime.now().isoformat()
            },
            'videos': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Batch {batch_number} completed: {success_count}/{len(videos)} successful")
        logger.info(f"Batch results saved to: {output_file}")
        
        return batch_data
    
    def wait_between_batches(self, batch_number: int, total_batches: int):
        """Implement human-like wait between batches"""
        if batch_number >= total_batches:
            return
        
        # Get wait time for this batch (cycling through predefined times)
        wait_minutes = self.batch_wait_times[batch_number % len(self.batch_wait_times)]
        
        # Add some randomness (+/- 2 minutes)
        jitter = random.uniform(-2, 2)
        actual_wait = max(wait_minutes + jitter, 5)  # Minimum 5 minutes
        
        logger.info(f"Human-like break between batches: {actual_wait:.1f} minutes")
        
        # Show countdown every 5 minutes
        remaining = actual_wait * 60
        while remaining > 0:
            if remaining > 300:  # More than 5 minutes
                logger.info(f"Break time remaining: {remaining/60:.1f} minutes")
                time.sleep(300)  # Sleep 5 minutes
                remaining -= 300
            else:
                time.sleep(remaining)
                remaining = 0
        
        logger.info("Break completed, resuming processing...")

def process_human_like_batches(
    input_file: str,
    target_videos: int = 50,
    videos_per_batch: int = 10,
    use_proxies: bool = True,
    proxy_file: str = None,
    min_duration: int = 121,
    max_duration: int = 300,
    start_index: int = 0
) -> List[str]:
    """Process videos in human-like batches"""
    
    logger.info("Dr. Berg Human-Like Batch Transcript Extractor")
    logger.info("=" * 50)
    
    # Load proxy list
    proxy_list = []
    if use_proxies and proxy_file:
        try:
            with open(proxy_file, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"Loaded {len(proxy_list)} proxies from {proxy_file}")
        except FileNotFoundError:
            logger.warning(f"Proxy file {proxy_file} not found. Continuing without proxies.")
            use_proxies = False
    
    # Initialize extractor
    extractor = HumanLikeBatchExtractor(use_proxies=use_proxies, proxy_list=proxy_list)
    
    if not extractor.transcript_api:
        logger.error("YouTube Transcript API not available")
        return []
    
    # Load and filter videos
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        return []
    
    videos = data.get('videos', [])
    
    # Apply duration filtering
    filtered_videos = []
    for video in videos:
        duration = video.get('duration_seconds', 0)
        if min_duration <= duration <= max_duration:
            filtered_videos.append(video)
    
    logger.info(f"Found {len(filtered_videos)} videos in duration range {min_duration//60}:{min_duration%60:02d} to {max_duration//60}:{max_duration%60:02d}")
    
    # Select target videos starting from start_index
    target_videos_list = filtered_videos[start_index:start_index + target_videos]
    logger.info(f"Processing {len(target_videos_list)} videos starting from index {start_index}")
    
    # Split into batches
    batches = []
    for i in range(0, len(target_videos_list), videos_per_batch):
        batch = target_videos_list[i:i + videos_per_batch]
        batches.append(batch)
    
    logger.info(f"Split into {len(batches)} batches of ~{videos_per_batch} videos each")
    logger.info(f"Batch wait times: {extractor.batch_wait_times} minutes")
    logger.info("")
    
    # Process each batch
    batch_files = []
    for batch_num, batch_videos in enumerate(batches):
        batch_number = batch_num + 1
        
        # Generate batch output filename
        timestamp = int(time.time())
        batch_filename = f"data/processed/berg_human_batch_{batch_number}_of_{len(batches)}_{timestamp}.json"
        
        logger.info(f"Starting batch {batch_number}/{len(batches)} ({len(batch_videos)} videos)")
        
        # Process batch
        batch_result = extractor.process_batch(batch_videos, batch_number, batch_filename)
        batch_files.append(batch_filename)
        
        # Wait between batches (except after last batch)
        if batch_number < len(batches):
            extractor.wait_between_batches(batch_number - 1, len(batches))
    
    # Final summary
    total_time = time.time() - extractor.batch_stats['start_time']
    logger.info("")
    logger.info("HUMAN-LIKE BATCH PROCESSING COMPLETED")
    logger.info("=" * 40)
    logger.info(f"Total batches: {extractor.batch_stats['batches_completed']}")
    logger.info(f"Total videos processed: {extractor.batch_stats['total_videos_processed']}")
    logger.info(f"Total successes: {extractor.batch_stats['total_successes']}")
    logger.info(f"Overall success rate: {(extractor.batch_stats['total_successes'] / extractor.batch_stats['total_videos_processed']) * 100:.1f}%")
    logger.info(f"Total time: {total_time/3600:.1f} hours")
    logger.info(f"Proxy rotations: {extractor.batch_stats['proxy_rotations']}")
    logger.info(f"Batch files created: {len(batch_files)}")
    
    return batch_files

def create_parallel_script(script_id: str, target_videos: int, start_index: int, videos_per_batch: int = 10) -> str:
    """Create a parallel script instance for simultaneous execution"""
    script_content = f'''#!/usr/bin/env python3
"""
Parallel Script {script_id} - Human-Like Batch Processing
Auto-generated script for parallel execution
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from transcript_extractor_human_batch import process_human_like_batches

if __name__ == "__main__":
    print(f"Starting Parallel Script {script_id}")
    print("=" * 40)
    
    batch_files = process_human_like_batches(
        input_file="data/processed/berg_complete_catalog.json",
        target_videos={target_videos},
        videos_per_batch={videos_per_batch},
        use_proxies=True,
        proxy_file="test_proxies.txt",
        min_duration=121,
        max_duration=300,
        start_index={start_index}
    )
    
    print(f"\\nParallel Script {script_id} completed!")
    print(f"Created {{len(batch_files)}} batch files")
    for file in batch_files:
        print(f"  - {{file}}")
'''
    
    script_filename = f"scripts/parallel_batch_{script_id}.py"
    with open(script_filename, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_filename, 0o755)
    
    return script_filename

def show_processing_status():
    """Show current processing status and next start index"""
    database_file = "data/processed/berg_complete_database.json"
    filtered_catalog_file = "data/processed/berg_filtered_catalog.json"
    
    try:
        # Load current database
        if os.path.exists(database_file):
            with open(database_file, 'r', encoding='utf-8') as f:
                database = json.load(f)
            processed_count = len(database.get('videos', []))
        else:
            processed_count = 0
        
        # Load filtered catalog to get total
        if os.path.exists(filtered_catalog_file):
            with open(filtered_catalog_file, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            total_videos = len(catalog.get('videos', []))
        else:
            total_videos = 0
        
        # Calculate progress
        progress_pct = (processed_count / total_videos * 100) if total_videos > 0 else 0
        next_index = processed_count  # Sequential processing
        
        # Display status
        print("\n" + "="*60)
        print("📊 PROCESSING STATUS")
        print("="*60)
        print(f"📁 Database: {processed_count} videos processed")
        print(f"📁 Filtered catalog: {total_videos} total videos")
        print(f"📈 Progress: {progress_pct:.1f}% complete")
        print(f"🚀 Next start index: {next_index}")
        print("="*60)
        
        if next_index < total_videos:
            print(f"\n🎯 NEXT RUN COMMAND:")
            print(f"python scripts/transcript_extractor_human_batch.py --start-index {next_index}")
        else:
            print(f"\n✅ ALL VIDEOS PROCESSED!")
        
        print()
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def append_to_database(batch_results, start_index, end_index):
    """Append batch results to berg_complete_database.json"""
    database_file = "data/processed/berg_complete_database.json"
    
    try:
        # Load existing database or create new one
        if os.path.exists(database_file):
            with open(database_file, 'r', encoding='utf-8') as f:
                database = json.load(f)
        else:
            database = {
                "database_metadata": {
                    "created_at": datetime.now().isoformat(),
                    "description": "Complete database of all processed Dr. Berg videos with full metadata",
                    "total_videos": 0,
                    "data_sources": []
                },
                "processing_summary": {
                    "videos_processed": 0,
                    "batch_files_processed": 0,
                    "earliest_batch": None,
                    "latest_batch": datetime.now().isoformat()
                },
                "videos": []
            }
        
        # Add new videos to database
        existing_videos = database.get('videos', [])
        existing_videos.extend(batch_results)
        database['videos'] = existing_videos
        
        # Update metadata
        database['database_metadata']['total_videos'] = len(existing_videos)
        database['database_metadata']['last_updated'] = datetime.now().isoformat()
        database['processing_summary']['videos_processed'] = len(existing_videos)
        database['processing_summary']['latest_batch'] = datetime.now().isoformat()
        
        # Save updated database
        with open(database_file, 'w', encoding='utf-8') as f:
            json.dump(database, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Appended {len(batch_results)} videos to database")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error appending to database: {e}")
        return False

def main():
    """Main execution for human-like batch processing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dr. Berg Human-Like Batch Transcript Extractor')
    parser.add_argument('--input-file', type=str, default='data/processed/berg_filtered_catalog.json', help='Input video catalog file (default: filtered catalog)')
    parser.add_argument('--target-videos', type=int, default=10, help='Total number of videos to process (default: 10)')
    parser.add_argument('--videos-per-batch', type=int, default=10, help='Videos per batch (default: 10)')
    parser.add_argument('--use-proxies', action='store_true', default=True, help='Enable proxy rotation (default: True)')
    parser.add_argument('--proxy-file', type=str, default='test_proxies.txt', help='Proxy list file (default: test_proxies.txt)')
    parser.add_argument('--min-duration', type=int, default=121, help='Minimum video duration in seconds (default: 121)')
    parser.add_argument('--max-duration', type=int, default=300, help='Maximum video duration in seconds (default: 300)')
    parser.add_argument('--start-index', type=int, default=0, help='Start from video index N (default: 0)')
    parser.add_argument('--create-parallel', type=int, help='Create N parallel script instances for simultaneous execution')
    parser.add_argument('--status', action='store_true', help='Show current processing status and next start index')
    
    args = parser.parse_args()
    
    # Handle status check
    if args.status:
        show_processing_status()
        return
    
    if args.create_parallel:
        print(f"Creating {args.create_parallel} parallel script instances...")
        print("=" * 50)
        
        scripts_created = []
        videos_per_script = args.target_videos // args.create_parallel
        
        for i in range(args.create_parallel):
            script_id = f"{i+1:02d}"
            script_start_index = args.start_index + (i * videos_per_script)
            script_target = videos_per_script
            
            # Last script gets any remaining videos
            if i == args.create_parallel - 1:
                script_target = args.target_videos - (i * videos_per_script)
            
            script_file = create_parallel_script(script_id, script_target, script_start_index, args.videos_per_batch)
            scripts_created.append(script_file)
            
            print(f"Created {script_file}:")
            print(f"  - Videos: {script_target}")
            print(f"  - Start index: {script_start_index}")
            print(f"  - Videos per batch: {args.videos_per_batch}")
        
        print(f"\nTo run all scripts in parallel:")
        print("=" * 30)
        for script in scripts_created:
            print(f"python {script} &")
        print("wait  # Wait for all to complete")
        
        print(f"\nOr run them in separate terminals:")
        print("=" * 30)
        for script in scripts_created:
            print(f"python {script}")
        
        return
    
    # Single script execution
    batch_files = process_human_like_batches(
        input_file=args.input_file,
        target_videos=args.target_videos,
        videos_per_batch=args.videos_per_batch,
        use_proxies=args.use_proxies,
        proxy_file=args.proxy_file,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        start_index=args.start_index
    )
    
    # Extract processed videos from batch files and append to database
    all_processed_videos = []
    for batch_file in batch_files:
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            if 'videos' in batch_data:
                all_processed_videos.extend(batch_data['videos'])
        except Exception as e:
            logger.error(f"Error reading batch file {batch_file}: {e}")
    
    if all_processed_videos:
        # Append to database
        end_index = args.start_index + len(all_processed_videos) - 1
        success = append_to_database(all_processed_videos, args.start_index, end_index)
        
        if success:
            # Show batch completion summary
            print(f"\n" + "="*60)
            print("✅ BATCH COMPLETE!")
            print("="*60)
            print(f"📊 This batch: Index {args.start_index}-{end_index} ({len(all_processed_videos)} videos)")
            
            # Show total progress
            try:
                database_file = "data/processed/berg_complete_database.json"
                with open(database_file, 'r', encoding='utf-8') as f:
                    database = json.load(f)
                total_processed = len(database.get('videos', []))
                
                # Get total videos in filtered catalog for percentage
                try:
                    with open("data/processed/berg_filtered_catalog.json", 'r', encoding='utf-8') as f:
                        catalog = json.load(f)
                    total_videos = len(catalog.get('videos', []))
                    progress_pct = (total_processed / total_videos * 100) if total_videos > 0 else 0
                    print(f"📈 Total processed: {total_processed} videos ({progress_pct:.1f}%)")
                except:
                    print(f"📈 Total processed: {total_processed} videos")
                
                next_index = args.start_index + len(all_processed_videos)
                print(f"🚀 Next run: --start-index {next_index}")
                
            except Exception as e:
                logger.error(f"Error showing progress: {e}")
            
            print("="*60)
        else:
            print(f"\n❌ Error appending results to database")
    else:
        print(f"\n⚠️ No videos were processed successfully")
    
    print(f"\n✓ Human-like batch processing completed!")
    print(f"✓ Created {len(batch_files)} batch files")

if __name__ == "__main__":
    main()