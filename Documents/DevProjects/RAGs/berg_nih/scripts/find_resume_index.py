#!/usr/bin/env python3
"""
Find Resume Index - Map processed videos to filtered catalog positions
"""

import json

def find_resume_index():
    """Find the correct resume index by mapping processed videos to filtered catalog"""
    
    # Load complete database
    with open('data/processed/berg_complete_database.json', 'r', encoding='utf-8') as f:
        database = json.load(f)
    
    # Load filtered catalog
    with open('data/processed/berg_filtered_catalog.json', 'r', encoding='utf-8') as f:
        filtered_catalog = json.load(f)
    
    # Extract processed video IDs
    processed_video_ids = set()
    for video in database['videos']:
        processed_video_ids.add(video['video_id'])
    
    print(f"📊 Analysis:")
    print(f"  Processed videos in database: {len(processed_video_ids)}")
    print(f"  Videos in filtered catalog: {len(filtered_catalog['videos'])}")
    
    # Map processed videos to their filtered catalog positions
    processed_positions = []
    
    for index, video in enumerate(filtered_catalog['videos']):
        if video['video_id'] in processed_video_ids:
            processed_positions.append(index)
            print(f"  ✅ Index {index}: {video['title']} ({video['video_id']})")
    
    if processed_positions:
        # Find the highest processed index
        max_processed_index = max(processed_positions)
        resume_index = max_processed_index + 1
        
        print(f"\n🎯 Resume Analysis:")
        print(f"  Highest processed index: {max_processed_index}")
        print(f"  Next resume index: {resume_index}")
        print(f"  Remaining videos: {len(filtered_catalog['videos']) - resume_index}")
        
        # Show next video to process
        if resume_index < len(filtered_catalog['videos']):
            next_video = filtered_catalog['videos'][resume_index]
            print(f"\n📹 Next video to process:")
            print(f"  Index {resume_index}: {next_video['title']}")
            print(f"  Video ID: {next_video['video_id']}")
            print(f"  Duration: {next_video['duration_formatted']}")
        else:
            print(f"\n🎉 ALL VIDEOS PROCESSED!")
        
        # Generate resume command
        remaining = len(filtered_catalog['videos']) - resume_index
        batch_size = min(10, remaining)
        
        if remaining > 0:
            print(f"\n💻 Resume Command:")
            print(f"uv run python scripts/transcript_extractor_human_batch.py --input-file data/processed/berg_filtered_catalog.json --start-index {resume_index} --target-videos {batch_size}")
        
        return resume_index
    else:
        print(f"\n❌ No processed videos found in filtered catalog!")
        return 0

if __name__ == "__main__":
    find_resume_index()