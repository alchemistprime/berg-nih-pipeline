#!/usr/bin/env python3
"""
Create Filtered Berg Catalog - Only 2-5 minute videos
This creates a clean, sequential catalog for processing
"""

import json
import os
from datetime import datetime
from pathlib import Path

def create_filtered_catalog(
    input_catalog="data/processed/berg_complete_catalog.json",
    output_catalog="data/processed/berg_filtered_catalog.json",
    min_duration=121,  # Just over 2 minutes
    max_duration=300   # Exactly 5 minutes
):
    """Create filtered catalog with only videos in target duration range"""
    
    print("🔍 Creating Filtered Berg Catalog...")
    print(f"Duration range: {min_duration}-{max_duration} seconds ({min_duration//60}m{min_duration%60:02d}s - {max_duration//60}m{max_duration%60:02d}s)")
    
    # Load original catalog
    if not os.path.exists(input_catalog):
        print(f"❌ Input catalog not found: {input_catalog}")
        return False
        
    with open(input_catalog, 'r', encoding='utf-8') as f:
        original_catalog = json.load(f)
    
    if 'videos' not in original_catalog:
        print("❌ No videos found in catalog")
        return False
    
    original_videos = original_catalog['videos']
    print(f"📺 Original catalog: {len(original_videos):,} videos")
    
    # Filter videos by duration
    filtered_videos = []
    for i, video in enumerate(original_videos):
        duration = video.get('duration_seconds', 0)
        if min_duration <= duration <= max_duration:
            # Add original catalog index for reference
            video_copy = video.copy()
            video_copy['original_catalog_index'] = i
            filtered_videos.append(video_copy)
    
    print(f"✅ Filtered catalog: {len(filtered_videos):,} videos")
    print(f"📊 Reduction: {((len(original_videos) - len(filtered_videos)) / len(original_videos) * 100):.1f}% fewer videos")
    
    # Create filtered catalog structure
    filtered_catalog = {
        "channel_info": original_catalog.get("channel_info", {}),
        "filter_metadata": {
            "created_at": datetime.now().isoformat(),
            "source_catalog": "berg_complete_catalog.json",
            "duration_filter": {
                "min_duration": min_duration,
                "max_duration": max_duration,
                "min_formatted": f"{min_duration//60}m{min_duration%60:02d}s",
                "max_formatted": f"{max_duration//60}m{max_duration%60:02d}s"
            },
            "original_video_count": len(original_videos),
            "filtered_video_count": len(filtered_videos),
            "reduction_percentage": round((len(original_videos) - len(filtered_videos)) / len(original_videos) * 100, 1)
        },
        "videos": filtered_videos
    }
    
    # Save filtered catalog
    Path(output_catalog).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_catalog, 'w', encoding='utf-8') as f:
        json.dump(filtered_catalog, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Filtered catalog saved: {output_catalog}")
    
    # Show some sample videos
    print(f"\n📋 Sample videos in filtered catalog:")
    for i in range(min(5, len(filtered_videos))):
        video = filtered_videos[i]
        duration = video.get('duration_formatted', 'Unknown')
        title = video.get('title', 'Unknown')[:60]
        original_idx = video.get('original_catalog_index', 'Unknown')
        print(f"  [{i:3d}] {duration} - {title}... (orig: {original_idx})")
    
    if len(filtered_videos) > 5:
        print(f"  ... and {len(filtered_videos) - 5:,} more videos")
    
    print(f"\n🎯 Processing Summary:")
    print(f"  Target videos to process: {len(filtered_videos):,}")
    print(f"  Sequential indices: 0 to {len(filtered_videos) - 1}")
    print(f"  Clean resume logic: processed count = next index")
    
    return True

def main():
    print("🎯 Creating Filtered Berg Catalog (2-5 minutes only)...")
    print("=" * 60)
    
    success = create_filtered_catalog()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ FILTERED CATALOG CREATED!")
        print("=" * 60)
        print("📁 File: data/processed/berg_filtered_catalog.json")
        print("🎯 Use this catalog for all future processing")
        print("🔄 Clean sequential indexing: 0, 1, 2, 3...")
        print("📈 Simple progress tracking")
    else:
        print("\n❌ Failed to create filtered catalog")

if __name__ == "__main__":
    main()