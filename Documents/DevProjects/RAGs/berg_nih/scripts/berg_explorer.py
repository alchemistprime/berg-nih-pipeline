#!/usr/bin/env python3
"""
Micro ETL Pipeline for Dr. Berg Video Data Exploration
Extracts top 100 most viewed health videos for analysis
"""

import os
import json
import re
import requests
import random
import time
import html
import isodate
from datetime import datetime
from typing import List, Dict, Optional
import logging
from googleapiclient.discovery import build
from transcript_extractor import TranscriptExtractor

# Load environment variables from .env file manually
def load_env_file():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value
    except FileNotFoundError:
        pass

load_env_file()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BergVideoExplorer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.channel_id = "UC3w193M5tYPJqF0Hi-7U-2g"  # Dr. Berg's main channel (13.7M subs)
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
        # Health-related keywords for filtering
        self.health_keywords = [
            'symptoms', 'deficiency', 'vitamin', 'mineral', 'health', 'pain',
            'digestive', 'liver', 'kidney', 'thyroid', 'diabetes', 'keto',
            'intermittent fasting', 'nutrition', 'supplement', 'acid reflux',
            'insulin', 'weight loss', 'fatigue', 'inflammation', 'gut health'
        ]
        
        # Exclude non-health content
        self.exclude_keywords = [
            'announcement', 'live stream', 'Q&A general', 'product review',
            'channel update', 'behind the scenes'
        ]
    
    def extract_video_metadata(self, max_videos: int = 100) -> List[Dict]:
        """Extract metadata for top health videos from Dr. Berg's channel"""
        logger.info(f"Extracting top {max_videos} health videos from Dr. Berg's channel")
        
        all_videos = []
        next_page_token = None
        
        # Fetch a larger pool of videos to randomize from (e.g., ~150)
        while len(all_videos) < (max_videos * 3) and len(all_videos) < 500:
            # Intelligent delay to mimic human behavior
            if random.random() < 0.2:  # 20% chance of a longer pause
                long_delay = random.uniform(5, 10)
                logger.info(f"Taking a longer pause: {long_delay:.2f} seconds...")
                time.sleep(long_delay)
            else:
                short_delay = random.uniform(1, 3)
                time.sleep(short_delay)

            try:
                search_request = self.youtube.search().list(
                    part='snippet',
                    channelId=self.channel_id,
                    order='relevance',  # Change from viewCount to relevance
                    maxResults=50,  # Fetch a full page of results
                    #q='health symptoms vitamin deficiency',  # Add search query
                    q='fatique, high blood pressure, hormones, dizziness, anxiety', #Add search query
                    pageToken=next_page_token
                )
                response = search_request.execute()
                logger.info(f"API returned {len(response.get('items', []))} items")
                
                for item in response.get('items', []):
                    video_data = self._process_video_item(item)
                    if video_data:
                        logger.info(f"Found video: {video_data['title']}")
                        if self._is_health_related(video_data):
                            all_videos.append(video_data)
                            logger.info(f"Added health video: {video_data['title']}")
                        else:
                            logger.info(f"Filtered out non-health video: {video_data['title']}")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
                break
        
        # Randomly select top videos from the larger pool
        selected_videos = random.sample(all_videos, min(max_videos, len(all_videos)))
        
        logger.info(f"Extracted {len(selected_videos)} health-related videos")
        return selected_videos
    
    def _process_video_item(self, item: Dict) -> Dict:
        """Process individual video item from API response"""
        snippet = item.get('snippet', {})
        
        return {
            'video_id': item['id']['videoId'],
            'title': html.unescape(snippet.get('title', '')),
            'description': html.unescape(snippet.get('description', '')),
            'published_at': snippet.get('publishedAt', ''),
            'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'channel_title': snippet.get('channelTitle', ''),
        }
    
    def _is_health_related(self, video_data: Dict) -> bool:
        """Check if video is health-related based on title and description"""
        text = f"{video_data['title']} {video_data['description']}".lower()
        
        # Check for exclude keywords first
        for exclude_word in self.exclude_keywords:
            if exclude_word in text:
                return False
        
        # Check for health keywords
        for health_word in self.health_keywords:
            if health_word in text:
                return True
        
        return False
    
    def get_video_statistics(self, video_ids: List[str]) -> Dict:
        """Get detailed statistics for videos"""
        logger.info(f"Getting statistics for {len(video_ids)} videos")
        
        stats = {}
        
        # Process in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            url = f"{self.base_url}/videos"
            params = {
                'key': self.api_key,
                'id': ','.join(batch_ids),
                'part': 'statistics,contentDetails'
            }
            
            try:
                # Add a small random delay to appear more human
                time.sleep(random.uniform(0.5, 1.5))

                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('items', []):
                    video_id = item['id']
                    statistics = item.get('statistics', {})
                    content_details = item.get('contentDetails', {})
                    
                    stats[video_id] = {
                        'view_count': int(statistics.get('viewCount', 0)),
                        'like_count': int(statistics.get('likeCount', 0)),
                        'comment_count': int(statistics.get('commentCount', 0)),
                        'duration': content_details.get('duration', ''),
                        'engagement_rate': self._calculate_engagement_rate(statistics)
                    }
                    
            except requests.RequestException as e:
                logger.error(f"Statistics request failed: {e}")
        
        return stats
    
    def _calculate_engagement_rate(self, statistics: Dict) -> float:
        """Calculate engagement rate (likes + comments) / views"""
        views = int(statistics.get('viewCount', 0))
        likes = int(statistics.get('likeCount', 0))
        comments = int(statistics.get('commentCount', 0))
        
        if views == 0:
            return 0.0
        
        return round((likes + comments) / views * 100, 3)
    
    def get_video_durations(self, video_ids: List[str]) -> Dict[str, int]:
        """Fetches video durations in seconds from the YouTube API."""
        durations = {}
        # The API allows fetching 50 videos at a time
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            try:
                request = self.youtube.videos().list(
                    part="contentDetails",
                    id=",".join(batch_ids)
                )
                response = request.execute()
                for item in response.get("items", []):
                    video_id = item["id"]
                    duration_iso = item["contentDetails"]["duration"]
                    # Convert ISO 8601 duration to seconds
                    duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
                    durations[video_id] = int(duration_seconds)
            except Exception as e:
                print(f"ERROR: Could not fetch durations for batch {i//50 + 1}: {e}")
        return durations
    
    def extract_basic_claims(self, video_data: Dict) -> List[Dict]:
        """Extract basic health claims from video title and description"""
        text = f"{video_data['title']} {video_data['description']}"
        
        # Simple regex patterns for common Dr. Berg claim structures
        patterns = [
            r'(?:cause|causes) of ([^,\\.]+)',
            r'(?:signs|symptoms) of ([^,\\.]+)',
            r'(?:best|top) (\\d+) (?:foods|supplements|vitamins) for ([^,\\.]+)',
            r'([^,\\.]+) deficiency',
            r'how to (?:fix|cure|treat) ([^,\\.]+)',
            r'([^,\\.]+) for ([^,\\.]+)',
        ]
        
        claims = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    claims.append({
                        'pattern_type': pattern,
                        'extracted_terms': list(match),
                        'confidence': 'low'  # Title/description only
                    })
                else:
                    claims.append({
                        'pattern_type': pattern,
                        'extracted_terms': [match],
                        'confidence': 'low'
                    })
        
        return claims
    
    def prepare_exploration_data(self, videos: List[Dict], stats: Dict):
        """Prepare exploration data without saving to file"""
        
        # Combine video data with statistics
        enriched_videos = []
        for video in videos:
            video_id = video['video_id']
            enriched_video = {
                **video,
                'statistics': stats.get(video_id, {}),
                'basic_claims': self.extract_basic_claims(video)
            }
            enriched_videos.append(enriched_video)
        
        # Sort by view count
        enriched_videos.sort(key=lambda x: x['statistics'].get('view_count', 0), reverse=True)
        
        exploration_data = {
            'extraction_date': datetime.now().isoformat(),
            'total_videos': len(enriched_videos),
            'channel_id': self.channel_id,
            'videos': enriched_videos,
            'summary_stats': self._generate_summary_stats(enriched_videos)
        }
        
        return exploration_data

    def save_exploration_data(self, videos: List[Dict], stats: Dict, filename: str = 'berg_exploration_data_v2.json'):
        """Save exploration data to JSON file"""
        exploration_data = self.prepare_exploration_data(videos, stats)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(exploration_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exploration data saved to {filename}")
        return exploration_data
    
    def _generate_summary_stats(self, videos: List[Dict]) -> Dict:
        """Generate summary statistics for the video dataset"""
        if not videos:
            return {}
        
        view_counts = [v['statistics'].get('view_count', 0) for v in videos]
        engagement_rates = [v['statistics'].get('engagement_rate', 0) for v in videos]
        
        # Extract common topics from titles
        all_titles = ' '.join([v['title'] for v in videos]).lower()
        topic_counts = {}
        for keyword in self.health_keywords:
            count = all_titles.count(keyword)
            if count > 0:
                topic_counts[keyword] = count
        
        return {
            'total_views': sum(view_counts),
            'avg_views': round(sum(view_counts) / len(view_counts), 0),
            'max_views': max(view_counts),
            'min_views': min(view_counts),
            'avg_engagement_rate': round(sum(engagement_rates) / len(engagement_rates), 3),
            'top_topics': dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _generate_mock_data(self) -> Dict:
        """Generate mock data for testing without API key"""
        return {
            'extraction_date': datetime.now().isoformat(),
            'total_videos': 3,
            'channel_id': self.channel_id,
            'videos': [
                {
                    'video_id': 'mock_001',
                    'title': 'The #1 Cause of Stomach Pain (and how to fix it)',
                    'description': 'Dr. Berg explains how stomach acid deficiency causes pain and recommends betaine HCl...',
                    'published_at': '2024-01-15T10:30:00Z',
                    'thumbnail_url': 'https://example.com/thumb1.jpg',
                    'channel_title': 'Dr. Eric Berg DC',
                    'statistics': {'view_count': 850000, 'like_count': 25000, 'comment_count': 3200, 'engagement_rate': 3.32},
                    'basic_claims': [
                        {'pattern_type': 'cause', 'extracted_terms': ['stomach pain'], 'confidence': 'low'},
                        {'pattern_type': 'deficiency', 'extracted_terms': ['stomach acid'], 'confidence': 'low'}
                    ]
                },
                {
                    'video_id': 'mock_002', 
                    'title': 'Vitamin D Deficiency: 10 Signs You Need More',
                    'description': 'Common symptoms of vitamin D deficiency include fatigue, depression, bone pain...',
                    'published_at': '2024-01-10T14:20:00Z',
                    'thumbnail_url': 'https://example.com/thumb2.jpg',
                    'channel_title': 'Dr. Eric Berg DC',
                    'statistics': {'view_count': 1200000, 'like_count': 35000, 'comment_count': 4800, 'engagement_rate': 3.32},
                    'basic_claims': [
                        {'pattern_type': 'signs', 'extracted_terms': ['vitamin D deficiency'], 'confidence': 'low'},
                        {'pattern_type': 'symptoms', 'extracted_terms': ['fatigue', 'depression'], 'confidence': 'low'}
                    ]
                },
                {
                    'video_id': 'mock_003',
                    'title': 'Best Foods for Liver Detox',
                    'description': 'Top foods that support liver function including cruciferous vegetables...',
                    'published_at': '2024-01-05T09:15:00Z',
                    'thumbnail_url': 'https://example.com/thumb3.jpg',
                    'channel_title': 'Dr. Eric Berg DC',
                    'statistics': {'view_count': 675000, 'like_count': 18500, 'comment_count': 2100, 'engagement_rate': 3.05},
                    'basic_claims': [
                        {'pattern_type': 'best_foods', 'extracted_terms': ['liver detox'], 'confidence': 'low'}
                    ]
                }
            ],
            'summary_stats': {
                'total_views': 2725000,
                'avg_views': 908333,
                'max_views': 1200000,
                'min_views': 675000,
                'avg_engagement_rate': 3.23,
                'top_topics': {
                    'deficiency': 2,
                    'vitamin': 1,
                    'liver': 1,
                    'pain': 1,
                    'symptoms': 1
                }
            }
        }

def main():
    """Main execution function"""
    print("Dr. Berg Video Data Explorer")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("WARNING: No YouTube API key found in environment variables")
        print("Set YOUTUBE_API_KEY environment variable to use live data")
        print("Proceeding with mock data for demonstration...")
        
        # Generate mock data for demonstration
        mock_explorer = BergVideoExplorer()
        mock_data = mock_explorer._generate_mock_data()
        
        # Note: No need to save intermediate file since we pass data directly to transcript extractor
        
        print(f"Generated mock dataset with {len(mock_data['videos'])} videos")
        
        # Print summary
        print("\nEXPLORATION SUMMARY:")
        print("-" * 30)
        summary = mock_data['summary_stats']
        print(f"Total videos analyzed: {mock_data['total_videos']}")
        print(f"Total views: {summary.get('total_views', 0):,}")
        print(f"Average views per video: {summary.get('avg_views', 0):,}")
        print(f"Average engagement rate: {summary.get('avg_engagement_rate', 0)}%")
        
        print("\nTop Health Topics:")
        for topic, count in list(summary.get('top_topics', {}).items())[:5]:
            print(f"  {topic}: {count} mentions")

        # Run transcript extraction for mock data
        print("\nRunning transcript extraction on mock data...")
        extractor = TranscriptExtractor()
        enhanced_mock = extractor.process_video_transcripts(
            exploration_data=mock_data,
            output_filename='berg_exploration_with_transcripts_v2.json'
        )
        
        return enhanced_mock
    
    # Initialize explorer
    explorer = BergVideoExplorer(api_key)
    
    # Extract video metadata
    print("Extracting video metadata...")
    videos = explorer.extract_video_metadata(max_videos=30)
    
    if not videos:
        print("No videos found. Check API key and channel access.")
        return None
    
    # Get video statistics
    print("Getting video statistics...")
    video_ids = [v['video_id'] for v in videos]
    stats = explorer.get_video_statistics(video_ids)
    
    # Prepare exploration data (no intermediate file saving needed)
    print("Preparing exploration data...")
    exploration_data = explorer.prepare_exploration_data(videos, stats)
    
    # Print summary
    print("\nEXPLORATION SUMMARY:")
    print("-" * 30)
    summary = exploration_data['summary_stats']
    print(f"Total videos analyzed: {exploration_data['total_videos']}")
    print(f"Total views: {summary.get('total_views', 0):,}")
    print(f"Average views per video: {summary.get('avg_views', 0):,}")
    print(f"Average engagement rate: {summary.get('avg_engagement_rate', 0)}%")
    
    print("\nTop Health Topics:")
    for topic, count in list(summary.get('top_topics', {}).items())[:5]:
        print(f"  {topic}: {count} mentions")

    # Run transcript extraction for live data
    print("\nRunning transcript extraction on live data...")
    extractor = TranscriptExtractor()
    enhanced_data = extractor.process_video_transcripts(
        exploration_data=exploration_data,
        output_filename='berg_exploration_with_transcripts_v2.json'
    )
    
    return enhanced_data

if __name__ == "__main__":
    data = main()
    if data:
        print("\nScript finished successfully!")
