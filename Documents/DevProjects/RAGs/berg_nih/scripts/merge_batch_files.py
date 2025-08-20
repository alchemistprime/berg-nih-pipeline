#!/usr/bin/env python3
"""
Merge Human Batch Files - Combine all processed videos in index order
This script merges the 5 berg_human_batch_*.json files to determine resume point
Preserves ALL original video data fields
"""

import json
import glob
import os
from datetime import datetime
from pathlib import Path

def merge_batch_files(data_dir="data/processed", output_file="data/processed/berg_merged_complete.json"):
    """Merge all human batch files in video_index order"""
    
    # Find all human batch files
    batch_pattern = os.path.join(data_dir, "berg_human_batch_*.json")
    batch_files = glob.glob(batch_pattern)
    
    if not batch_files:
        print(f"❌ No batch files found in {data_dir}")
        return None
    
    print(f"Found {len(batch_files)} batch files:")
    for file in sorted(batch_files):
        print(f"  - {os.path.basename(file)}")
    
    # Collect all videos from all batches
    all_videos = []
    batch_metadata = []
    
    for batch_file in batch_files:
        print(f"\n📖 Reading {os.path.basename(batch_file)}...")
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            # Extract metadata
            if 'batch_metadata' in batch_data:
                metadata = batch_data['batch_metadata']
                metadata['source_file'] = os.path.basename(batch_file)
                batch_metadata.append(metadata)
                print(f"  ✅ Batch metadata: {metadata.get('video_count', 0)} videos, {metadata.get('success_rate', 0)}% success")
            
            # Extract videos - preserve ALL original fields and add index
            if 'videos' in batch_data:
                videos = batch_data['videos']
                for i, video in enumerate(videos):
                    # Add video_index based on current total + position in this batch
                    video['video_index'] = len(all_videos) + i
                    all_videos.append(video)
                print(f"  📹 Found {len(videos)} videos")
            
        except Exception as e:
            print(f"  ❌ Error reading {batch_file}: {e}")
            continue
    
    if not all_videos:
        print("❌ No videos found in any batch files!")
        return None
    
    # Sort videos by index
    print(f"\n🔄 Sorting {len(all_videos)} videos by video_index...")
    all_videos.sort(key=lambda x: x.get('video_index', 0))
    
    # Check for duplicates and gaps
    indices = [v.get('video_index', -1) for v in all_videos]
    unique_indices = set(indices)
    
    print(f"\n📊 Analysis:")
    print(f"  Total videos processed: {len(all_videos)}")
    print(f"  Unique video indices: {len(unique_indices)}")
    print(f"  Lowest index: {min(indices)}")
    print(f"  Highest index: {max(indices)}")
    print(f"  Expected next index: {max(indices) + 1}")
    
    # Check for duplicates
    duplicates = len(all_videos) - len(unique_indices)
    if duplicates > 0:
        print(f"  ⚠️  Duplicate indices found: {duplicates}")
        
        # Remove duplicates (keep first occurrence)
        seen_indices = set()
        unique_videos = []
        for video in all_videos:
            idx = video.get('video_index', -1)
            if idx not in seen_indices:
                unique_videos.append(video)
                seen_indices.add(idx)
        
        print(f"  🔧 After deduplication: {len(unique_videos)} videos")
        all_videos = unique_videos
    
    # Check for gaps
    expected_indices = set(range(min(indices), max(indices) + 1))
    missing_indices = expected_indices - unique_indices
    if missing_indices:
        print(f"  ⚠️  Missing indices: {sorted(missing_indices)}")
    
    # Create merged output
    merged_data = {
        "merge_metadata": {
            "merged_at": datetime.now().isoformat(),
            "source_files": len(batch_files),
            "total_videos": len(all_videos),
            "video_index_range": {
                "min": min(indices),
                "max": max(indices),
                "next_resume_index": max(indices) + 1
            },
            "duplicates_removed": duplicates,
            "missing_indices": sorted(missing_indices) if missing_indices else []
        },
        "batch_sources": batch_metadata,
        "videos": all_videos
    }
    
    # Write merged file
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Merged file created: {output_file}")
    print(f"\n🚀 RESUME COMMAND:")
    print(f"python scripts/vpn_batch_orchestrator.py --total-videos 20 --start-index {max(indices) + 1}")
    
    return merged_data

def main():
    print("🔄 Merging Human Batch Files...")
    print("=" * 50)
    
    # Default paths
    data_dir = "data/processed"
    output_file = "data/processed/berg_merged_complete.json"
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Merge files
    result = merge_batch_files(data_dir, output_file)
    
    if result:
        print("\n" + "=" * 50)
        print("🎉 MERGE COMPLETE!")
        
        resume_index = result['merge_metadata']['video_index_range']['next_resume_index']
        total_processed = result['merge_metadata']['total_videos']
        
        print(f"\n📈 Summary:")
        print(f"  Videos successfully processed: {total_processed}")
        print(f"  Ready to resume from index: {resume_index}")
        print(f"\n🎯 Next command to run:")
        print(f"python scripts/vpn_batch_orchestrator.py --total-videos 20 --start-index {resume_index}")

if __name__ == "__main__":
    main()