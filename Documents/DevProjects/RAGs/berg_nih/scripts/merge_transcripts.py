#!/usr/bin/env python3
"""
Merge berg_exploration_with_transcripts.json into berg_exploration_with_transcripts_v2.json
Avoiding duplicates based on video_id
"""

import json
from datetime import datetime
from typing import Dict, List

def load_json_file(filename: str) -> Dict:
    """Load and return JSON data from file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {filename} not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return {}

def merge_transcript_files():
    """Merge transcript files avoiding duplicates"""
    
    # Load both files
    print("Loading berg_exploration_with_transcripts_v2.json...")
    v2_data = load_json_file('berg_exploration_with_transcripts_v2.json')
    
    print("Loading berg_exploration_with_transcripts.json...")
    v1_data = load_json_file('berg_exploration_with_transcripts.json')
    
    if not v2_data or not v1_data:
        print("Error: Could not load one or both files")
        return
    
    # Get existing video IDs from v2
    existing_video_ids = {video['video_id'] for video in v2_data.get('videos', [])}
    print(f"Found {len(existing_video_ids)} videos in v2 file")
    
    # Find unique videos from v1 that aren't in v2
    v1_videos = v1_data.get('videos', [])
    unique_videos = []
    
    for video in v1_videos:
        video_id = video['video_id']
        if video_id not in existing_video_ids:
            unique_videos.append(video)
            print(f"Adding unique video: {video['title'][:60]}...")
    
    print(f"Found {len(unique_videos)} unique videos to add from v1 file")
    
    if not unique_videos:
        print("No unique videos to merge. Files already contain the same videos.")
        return
    
    # Merge the data
    merged_videos = v2_data['videos'] + unique_videos
    total_videos = len(merged_videos)
    
    # Update metadata
    merged_data = {
        'extraction_date': datetime.now().isoformat(),
        'total_videos': total_videos,
        'channel_id': v2_data['channel_id'],
        'videos': merged_videos
    }
    
    # Recalculate summary stats
    print("Recalculating summary statistics...")
    
    # Transcript stats
    transcripts_extracted = sum(1 for v in merged_videos if v.get('transcript', {}).get('transcript_available', False))
    total_transcript_claims = sum(len(v.get('transcript_claims', [])) for v in merged_videos)
    total_basic_claims = sum(len(v.get('basic_claims', [])) for v in merged_videos)
    total_claims = sum(v.get('total_claims', 0) for v in merged_videos)
    
    merged_data['transcript_stats'] = {
        'total_videos': total_videos,
        'transcripts_extracted': transcripts_extracted,
        'transcript_success_rate': round(transcripts_extracted / total_videos * 100, 1) if total_videos > 0 else 0,
        'total_transcript_claims': total_transcript_claims,
        'total_basic_claims': total_basic_claims,
        'total_claims': total_claims,
        'avg_claims_per_video': round(total_claims / total_videos, 1) if total_videos > 0 else 0
    }
    
    # Video stats (views, engagement, etc.)
    view_counts = [v.get('statistics', {}).get('view_count', 0) for v in merged_videos]
    engagement_rates = [v.get('statistics', {}).get('engagement_rate', 0) for v in merged_videos]
    
    merged_data['summary_stats'] = {
        'total_views': sum(view_counts),
        'avg_views': round(sum(view_counts) / len(view_counts), 0) if view_counts else 0,
        'max_views': max(view_counts) if view_counts else 0,
        'min_views': min(view_counts) if view_counts else 0,
        'avg_engagement_rate': round(sum(engagement_rates) / len(engagement_rates), 3) if engagement_rates else 0
    }
    
    # Save merged file
    output_filename = 'berg_exploration_with_transcripts_v2_merged.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nMERGE COMPLETE!")
    print(f"="*50)
    print(f"Output file: {output_filename}")
    print(f"Total videos: {total_videos}")
    print(f"Videos from v2: {len(v2_data['videos'])}")
    print(f"Unique videos added from v1: {len(unique_videos)}")
    print(f"Transcripts available: {transcripts_extracted}")
    print(f"Success rate: {merged_data['transcript_stats']['transcript_success_rate']}%")
    print(f"Total claims: {total_claims}")
    print(f"Total views: {merged_data['summary_stats']['total_views']:,}")
    
    return merged_data

if __name__ == "__main__":
    print("Berg Transcript File Merger")
    print("="*40)
    merge_transcript_files()