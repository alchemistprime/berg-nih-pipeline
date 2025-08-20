#!/usr/bin/env python3
"""
Verify Processed Videos Against Filtered Catalog
Cross-reference existing progress with the new filtered catalog
"""

import json
import os
import glob

def verify_progress_against_filtered():
    """Cross-reference processed videos with filtered catalog"""
    
    print("🔍 Verifying Processed Videos Against Filtered Catalog...")
    print("=" * 60)
    
    # Load filtered catalog
    filtered_catalog_file = "data/processed/berg_filtered_catalog.json"
    if not os.path.exists(filtered_catalog_file):
        print(f"❌ Filtered catalog not found: {filtered_catalog_file}")
        return
        
    with open(filtered_catalog_file, 'r', encoding='utf-8') as f:
        filtered_catalog = json.load(f)
    
    filtered_videos = filtered_catalog.get('videos', [])
    print(f"📺 Filtered catalog: {len(filtered_videos):,} videos (indices 0-{len(filtered_videos)-1})")
    
    # Create lookup by video_id
    filtered_lookup = {}
    for i, video in enumerate(filtered_videos):
        video_id = video.get('video_id')
        if video_id:
            filtered_lookup[video_id] = {
                'filtered_index': i,
                'original_index': video.get('original_catalog_index'),
                'title': video.get('title', 'Unknown'),
                'duration': video.get('duration_formatted', 'Unknown')
            }
    
    print(f"🔑 Created lookup for {len(filtered_lookup)} video IDs")
    
    # Load all processed videos from batch files
    batch_files = glob.glob("data/processed/berg_human_batch_*.json")
    if not batch_files:
        print("❌ No batch files found")
        return
        
    processed_videos = []
    for batch_file in sorted(batch_files):
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                
            if 'videos' in batch_data:
                for video in batch_data['videos']:
                    video_id = video.get('video_id')
                    if video_id:
                        processed_videos.append({
                            'video_id': video_id,
                            'title': video.get('title', 'Unknown'),
                            'batch_file': os.path.basename(batch_file)
                        })
        except Exception as e:
            print(f"❌ Error reading {batch_file}: {e}")
    
    print(f"📝 Found {len(processed_videos)} processed videos from batch files")
    
    # Cross-reference processed videos with filtered catalog
    matched_videos = []
    not_in_filtered = []
    
    for processed in processed_videos:
        video_id = processed['video_id']
        if video_id in filtered_lookup:
            filtered_info = filtered_lookup[video_id]
            matched_videos.append({
                'video_id': video_id,
                'filtered_index': filtered_info['filtered_index'],
                'original_index': filtered_info['original_index'],
                'title': filtered_info['title'],
                'duration': filtered_info['duration'],
                'batch_file': processed['batch_file']
            })
        else:
            not_in_filtered.append(processed)
    
    # Sort matched videos by filtered index
    matched_videos.sort(key=lambda x: x['filtered_index'])
    
    print(f"\n📊 Cross-Reference Results:")
    print(f"✅ Processed videos IN filtered catalog: {len(matched_videos)}")
    print(f"❌ Processed videos NOT in filtered catalog: {len(not_in_filtered)}")
    
    if not_in_filtered:
        print(f"\n⚠️  Videos NOT in filtered catalog (outside 2-5 min range):")
        for video in not_in_filtered[:5]:  # Show first 5
            print(f"  - {video['title'][:50]}...")
        if len(not_in_filtered) > 5:
            print(f"  ... and {len(not_in_filtered) - 5} more")
    
    if matched_videos:
        print(f"\n✅ Processed Videos in Filtered Catalog (sorted by index):")
        print(f"{'Index':<8} {'Duration':<8} {'Title':<50} {'Batch File'}")
        print("-" * 85)
        
        for video in matched_videos[:10]:  # Show first 10
            title = video['title'][:45] + "..." if len(video['title']) > 45 else video['title']
            print(f"{video['filtered_index']:<8} {video['duration']:<8} {title:<50} {video['batch_file']}")
        
        if len(matched_videos) > 10:
            print(f"... and {len(matched_videos) - 10} more processed videos")
        
        # Find gaps and determine resume point
        processed_indices = [v['filtered_index'] for v in matched_videos]
        max_processed = max(processed_indices)
        
        # Check for gaps in sequence
        gaps = []
        for i in range(max_processed + 1):
            if i not in processed_indices:
                gaps.append(i)
        
        print(f"\n🎯 Resume Analysis:")
        print(f"  Highest processed index: {max_processed}")
        print(f"  Total gaps in sequence: {len(gaps)}")
        
        if gaps:
            first_gap = min(gaps)
            print(f"  First gap at index: {first_gap}")
            print(f"  📍 RECOMMENDED RESUME INDEX: {first_gap}")
        else:
            next_index = max_processed + 1
            print(f"  No gaps found")
            print(f"  📍 RECOMMENDED RESUME INDEX: {next_index}")
        
        # Show what's at the resume index
        resume_index = min(gaps) if gaps else max_processed + 1
        if resume_index < len(filtered_videos):
            next_video = filtered_videos[resume_index]
            print(f"\n🚀 Next video to process:")
            print(f"  Index: {resume_index}")
            print(f"  Title: {next_video.get('title', 'Unknown')}")
            print(f"  Duration: {next_video.get('duration_formatted', 'Unknown')}")
        
        print(f"\n🎯 RESUME COMMAND:")
        print(f"python scripts/vpn_batch_orchestrator.py --total-videos 20 --start-index {resume_index}")
    
    print("=" * 60)

def main():
    verify_progress_against_filtered()

if __name__ == "__main__":
    main()