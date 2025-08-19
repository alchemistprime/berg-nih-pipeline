#!/usr/bin/env python3
"""
YouTube Video Fetcher for Dr. Berg's Complete Channel
Uses YouTube Data API v3 to get comprehensive video catalog before transcript extraction
"""

import os
import json
import time
import logging
import argparse
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Load environment variables
def load_env_file():
    # Look for .env file in current directory and parent directories
    env_paths = [
        '.env',
        '../.env',
        '../../.env'
    ]
    
    for env_path in env_paths:
        try:
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            value = value.strip('"\'')
                            os.environ[key] = value
                print(f"Loaded environment from: {env_path}")
                return
        except Exception as e:
            continue
    
    print("No .env file found in current or parent directories")

load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeVideoFetcher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key required. Set YOUTUBE_API_KEY environment variable.")
        
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.dr_berg_channel_id = "UC3w193M5tYPJqF0Hi-7U-2g"  # Dr. Berg's channel ID
        self.requests_made = 0
        self.quota_used = 0
        
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make authenticated request to YouTube API"""
        import requests
        
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            self.requests_made += 1
            
            if response.status_code == 403:
                error_data = response.json()
                if 'quotaExceeded' in str(error_data):
                    raise Exception("YouTube API quota exceeded for today")
                elif 'rateLimitExceeded' in str(error_data):
                    logger.warning("Rate limit exceeded, waiting 60 seconds...")
                    time.sleep(60)
                    return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_channel_info(self) -> Dict:
        """Get basic channel information"""
        params = {
            'part': 'snippet,statistics',
            'id': self.dr_berg_channel_id
        }
        
        response = self._make_request('channels', params)
        
        if not response.get('items'):
            raise ValueError(f"Channel not found: {self.dr_berg_channel_id}")
        
        channel = response['items'][0]
        return {
            'channel_id': channel['id'],
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'][:200] + '...',
            'subscriber_count': channel['statistics'].get('subscriberCount', 'Unknown'),
            'video_count': channel['statistics'].get('videoCount', 'Unknown'),
            'view_count': channel['statistics'].get('viewCount', 'Unknown')
        }
    
    def get_uploads_playlist_id(self) -> str:
        """Get the uploads playlist ID for the channel"""
        params = {
            'part': 'contentDetails',
            'id': self.dr_berg_channel_id
        }
        
        response = self._make_request('channels', params)
        self.quota_used += 1
        
        if not response.get('items'):
            raise ValueError(f"Channel not found: {self.dr_berg_channel_id}")
        
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        print(f"Found uploads playlist: {uploads_playlist_id}")
        return uploads_playlist_id

    def get_all_videos(self, max_results: int = None) -> List[Dict]:
        """Get all videos from Dr. Berg's channel using uploads playlist"""
        videos = []
        next_page_token = None
        page_count = 0
        
        logger.info(f"Fetching videos from Dr. Berg's channel...")
        
        # Get the uploads playlist ID
        uploads_playlist_id = self.get_uploads_playlist_id()
        
        while True:
            params = {
                'part': 'snippet',
                'playlistId': uploads_playlist_id,
                'maxResults': 50,  # Max allowed per request
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            try:
                print(f"Fetching page {page_count + 1}...")
                response = self._make_request('playlistItems', params)
                self.quota_used += 1  # playlistItems costs 1 quota unit
                
                items = response.get('items', [])
                print(f"Playlist returned {len(items)} items")
                
                # Get detailed video info for this batch
                video_ids = []
                for item in items:
                    video_id = item['snippet']['resourceId']['videoId']
                    video_ids.append(video_id)
                
                if video_ids:
                    print(f"Getting details for {len(video_ids)} videos...")
                    detailed_videos = self.get_video_details(video_ids)
                    videos.extend(detailed_videos)
                    print(f"Added {len(detailed_videos)} detailed videos")
                
                page_count += 1
                logger.info(f"Fetched page {page_count}, total videos: {len(videos)}")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    print("No more pages available")
                    break
                
                if max_results and len(videos) >= max_results:
                    videos = videos[:max_results]
                    print(f"Reached max_results limit: {max_results}")
                    break
                
                # Rate limiting - be conservative
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching page {page_count + 1}: {e}")
                break
        
        logger.info(f"Total videos fetched: {len(videos)}")
        return videos
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict]:
        """Get detailed information for specific video IDs"""
        if not video_ids:
            return []
        
        params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids[:50])  # Max 50 IDs per request
        }
        
        response = self._make_request('videos', params)
        self.quota_used += 1  # Videos.list costs 1 quota unit
        
        videos = []
        for item in response.get('items', []):
            video = self._parse_video_item(item)
            videos.append(video)
        
        return videos
    
    def _parse_video_item(self, item: Dict) -> Dict:
        """Parse YouTube API video item into our format"""
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})
        
        # Parse duration (PT15M33S -> seconds)
        duration_seconds = self._parse_duration(content_details.get('duration', ''))
        
        # Parse published date
        published_at = snippet.get('publishedAt', '')
        try:
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except:
            published_date = None
        
        return {
            'video_id': item['id'],
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'published_at': published_at,
            'published_date': published_date.isoformat() if published_date else None,
            'duration_seconds': duration_seconds,
            'duration_formatted': self._format_duration(duration_seconds),
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'comment_count': int(statistics.get('commentCount', 0)),
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId', ''),
            'default_language': snippet.get('defaultLanguage', ''),
            'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'url': f"https://www.youtube.com/watch?v={item['id']}",
            'embed_url': f"https://www.youtube.com/embed/{item['id']}",
            # Metadata for transcript extraction
            'transcript_attempted': False,
            'transcript_available': None,
            'api_fetched_at': datetime.utcnow().isoformat()
        }
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse YouTube duration (PT15M33S) to seconds"""
        import re
        
        if not duration_str:
            return 0
        
        # Parse PT15M33S format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0) 
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _format_duration(self, seconds: int) -> str:
        """Format seconds as HH:MM:SS or MM:SS"""
        if seconds == 0:
            return "0:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def filter_videos(self, videos: List[Dict], 
                     min_duration: int = 60,
                     max_duration: int = 7200,
                     exclude_shorts: bool = True) -> List[Dict]:
        """Filter videos based on criteria"""
        filtered = []
        
        for video in videos:
            duration = video['duration_seconds']
            
            # Skip shorts (< 60 seconds) if requested
            if exclude_shorts and duration < 60:
                continue
            
            # Duration filters
            if duration < min_duration or duration > max_duration:
                continue
            
            # Add transcript likelihood score
            title = video['title'].lower()
            description = video['description'].lower()
            
            # Dr. Berg content typically has transcripts
            video['transcript_likely'] = True  # Assume yes for Dr. Berg
            if any(word in title for word in ['live', 'livestream', 'q&a']):
                video['transcript_likely'] = False  # Live content less likely
            
            filtered.append(video)
        
        logger.info(f"Filtered {len(videos)} -> {len(filtered)} videos")
        return filtered
    
    def save_video_catalog(self, videos: List[Dict], filename: str = 'data/processed/berg_complete_catalog.json'):
        """Save complete video catalog"""
        
        # Create enhanced dataset
        channel_info = self.get_channel_info()
        
        catalog = {
            'channel_info': channel_info,
            'fetch_metadata': {
                'fetched_at': datetime.utcnow().isoformat(),
                'total_videos': len(videos),
                'api_requests_made': self.requests_made,
                'quota_units_used': self.quota_used,
                'average_duration': sum(v['duration_seconds'] for v in videos) / len(videos) if videos else 0,
                'date_range': {
                    'earliest': min(v['published_date'] for v in videos if v['published_date']) if videos else None,
                    'latest': max(v['published_date'] for v in videos if v['published_date']) if videos else None
                }
            },
            'videos': videos,
            'summary_stats': {
                'total_views': sum(v['view_count'] for v in videos),
                'total_likes': sum(v['like_count'] for v in videos),
                'total_duration_hours': sum(v['duration_seconds'] for v in videos) / 3600,
                'videos_by_year': self._group_by_year(videos),
                'duration_distribution': self._duration_distribution(videos)
            }
        }
        
        # Ensure directory exists
        dir_name = os.path.dirname(filename)
        if dir_name:  # Only create directory if filename has a directory component
            os.makedirs(dir_name, exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Video catalog saved to {filename}")
        return catalog
    
    def _group_by_year(self, videos: List[Dict]) -> Dict[str, int]:
        """Group videos by publication year"""
        years = {}
        for video in videos:
            if video['published_date']:
                year = video['published_date'][:4]
                years[year] = years.get(year, 0) + 1
        return dict(sorted(years.items()))
    
    def _duration_distribution(self, videos: List[Dict]) -> Dict[str, int]:
        """Analyze duration distribution"""
        distribution = {
            'under_5min': 0,
            '5-15min': 0, 
            '15-30min': 0,
            '30-60min': 0,
            'over_60min': 0
        }
        
        for video in videos:
            duration = video['duration_seconds']
            if duration < 300:
                distribution['under_5min'] += 1
            elif duration < 900:
                distribution['5-15min'] += 1
            elif duration < 1800:
                distribution['15-30min'] += 1
            elif duration < 3600:
                distribution['30-60min'] += 1
            else:
                distribution['over_60min'] += 1
        
        return distribution

def main():
    parser = argparse.ArgumentParser(description='Fetch all Dr. Berg videos using YouTube Data API v3')
    parser.add_argument('--api-key', type=str, help='YouTube Data API key (or set YOUTUBE_API_KEY env var)')
    parser.add_argument('--max-videos', type=int, help='Maximum number of videos to fetch (default: all)')
    parser.add_argument('--output-file', type=str, default='data/processed/berg_complete_catalog.json',
                       help='Output filename for video catalog')
    parser.add_argument('--min-duration', type=int, default=60, help='Minimum video duration in seconds')
    parser.add_argument('--max-duration', type=int, default=7200, help='Maximum video duration in seconds') 
    parser.add_argument('--include-shorts', action='store_true', help='Include YouTube shorts (<60s)')
    
    args = parser.parse_args()
    
    print("Dr. Berg Complete Video Fetcher")
    print("=" * 40)
    
    try:
        fetcher = YouTubeVideoFetcher(api_key=args.api_key)
        
        # Get channel info first
        channel_info = fetcher.get_channel_info()
        print(f"Channel: {channel_info['title']}")
        print(f"Total Videos: {channel_info['video_count']}")
        print(f"Subscribers: {channel_info['subscriber_count']}")
        print()
        
        # Fetch all videos
        print("Fetching all videos... (this may take several minutes)")
        videos = fetcher.get_all_videos(max_results=args.max_videos)
        
        if not videos:
            print("No videos found!")
            return
        
        # Apply filters
        filtered_videos = fetcher.filter_videos(
            videos,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            exclude_shorts=not args.include_shorts
        )
        
        # Save catalog
        catalog = fetcher.save_video_catalog(filtered_videos, args.output_file)
        
        # Print summary
        print(f"\n✓ Video Catalog Creation Complete!")
        print(f"{'='*50}")
        print(f"Total videos fetched: {len(videos)}")
        print(f"Videos after filtering: {len(filtered_videos)}")
        print(f"Date range: {catalog['fetch_metadata']['date_range']['earliest'][:10]} to {catalog['fetch_metadata']['date_range']['latest'][:10]}")
        print(f"Total duration: {catalog['summary_stats']['total_duration_hours']:.1f} hours")
        print(f"API requests made: {fetcher.requests_made}")
        print(f"Quota units used: {fetcher.quota_used}")
        print(f"Catalog saved to: {args.output_file}")
        
        print(f"\nDuration Distribution:")
        for category, count in catalog['summary_stats']['duration_distribution'].items():
            print(f"  {category}: {count} videos")
        
        print(f"\nNext step: Run transcript extraction on this catalog")
        print(f"python scripts/transcript_extractor.py --input-file {args.output_file}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    exit(main())