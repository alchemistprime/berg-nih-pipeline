#!/usr/bin/env python3
"""
Enhance Progress Database - Complete metadata consolidation
Combines all processed videos from batch files into comprehensive database
"""

import json
import glob
import os
from datetime import datetime
from pathlib import Path

def enhance_progress_database(
    data_dir="data/processed",
    progress_file="data/processed/berg_processing_progress.json",
    output_file="data/processed/berg_complete_database.json"
):
    """Create complete database with all metadata from processed videos"""
    
    print("🔄 Creating Complete Video Database...")
    print("=" * 60)
    
    # Find all batch files
    batch_files = glob.glob(os.path.join(data_dir, "berg_human_batch_*.json"))
    if not batch_files:
        print("❌ No batch files found")
        return False
    
    print(f"📁 Found {len(batch_files)} batch files:")
    for file in sorted(batch_files):
        print(f"  - {os.path.basename(file)}")
    
    # Collect all videos with complete metadata
    complete_videos = []
    batch_metadata = []
    
    for batch_file in sorted(batch_files):
        print(f"\n📖 Processing {os.path.basename(batch_file)}...")
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            # Store batch metadata
            if 'batch_metadata' in batch_data:
                metadata = batch_data['batch_metadata'].copy()
                metadata['source_file'] = os.path.basename(batch_file)
                batch_metadata.append(metadata)
                
                video_count = metadata.get('video_count', 0)
                success_rate = metadata.get('success_rate', 0)
                completed_at = metadata.get('completed_at', 'Unknown')
                print(f"  ✅ Batch: {video_count} videos, {success_rate}% success, completed {completed_at}")
            
            # Extract all videos with complete metadata
            if 'videos' in batch_data:
                videos = batch_data['videos']
                for video in videos:
                    if video.get('video_id'):
                        # Add processing metadata
                        enhanced_video = video.copy()
                        enhanced_video['processing_metadata'] = {
                            'batch_file': os.path.basename(batch_file),
                            'processed_at': batch_data.get('batch_metadata', {}).get('completed_at', datetime.now().isoformat()),
                            'processing_status': 'success'
                        }
                        complete_videos.append(enhanced_video)
                        
                print(f"  📹 Extracted {len(videos)} videos with complete metadata")
                
        except Exception as e:
            print(f"  ❌ Error processing {batch_file}: {e}")
            continue
    
    if not complete_videos:
        print("❌ No videos found in batch files!")
        return False
    
    # Sort videos by title for consistent ordering
    complete_videos.sort(key=lambda x: x.get('title', '').lower())
    
    # Create comprehensive database
    database = {
        "database_metadata": {
            "created_at": datetime.now().isoformat(),
            "description": "Complete database of all processed Dr. Berg videos with full metadata",
            "total_videos": len(complete_videos),
            "source_batch_files": len(batch_files),
            "data_sources": [os.path.basename(f) for f in sorted(batch_files)]
        },
        "processing_summary": {
            "videos_processed": len(complete_videos),
            "batch_files_processed": len(batch_files),
            "earliest_batch": min([b.get('completed_at', '') for b in batch_metadata]) if batch_metadata else 'Unknown',
            "latest_batch": max([b.get('completed_at', '') for b in batch_metadata]) if batch_metadata else 'Unknown'
        },
        "batch_metadata": batch_metadata,
        "videos": complete_videos
    }
    
    # Show database statistics
    print(f"\n📊 Database Statistics:")
    print(f"  Total videos: {len(complete_videos)}")
    print(f"  Source batch files: {len(batch_files)}")
    
    # Show video metadata fields available
    if complete_videos:
        sample_video = complete_videos[0]
        fields = list(sample_video.keys())
        print(f"  Metadata fields per video: {len(fields)}")
        print(f"  Available fields: {', '.join(fields[:10])}{'...' if len(fields) > 10 else ''}")
    
    # Show duration distribution
    durations = [v.get('duration_seconds', 0) for v in complete_videos if v.get('duration_seconds')]
    if durations:
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        print(f"  Duration range: {min_duration//60}:{min_duration%60:02d} to {max_duration//60}:{max_duration%60:02d}")
        print(f"  Average duration: {avg_duration//60:.0f}:{avg_duration%60:02.0f}")
    
    # Show view count stats
    view_counts = [v.get('view_count', 0) for v in complete_videos if v.get('view_count')]
    if view_counts:
        total_views = sum(view_counts)
        avg_views = total_views / len(view_counts)
        print(f"  Total views: {total_views:,}")
        print(f"  Average views per video: {avg_views:,.0f}")
    
    # Save complete database
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(database, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Complete database saved: {output_file}")
    
    # Show sample video
    print(f"\n📋 Sample video record:")
    if complete_videos:
        sample = complete_videos[0]
        print(f"  Title: {sample.get('title', 'Unknown')}")
        print(f"  Duration: {sample.get('duration_formatted', 'Unknown')}")
        print(f"  Views: {sample.get('view_count', 0):,}")
        print(f"  Published: {sample.get('published_date', 'Unknown')}")
        print(f"  Video ID: {sample.get('video_id', 'Unknown')}")
        print(f"  Transcript length: {len(sample.get('transcript', ''))} characters")
        print(f"  Processed in: {sample.get('processing_metadata', {}).get('batch_file', 'Unknown')}")
    
    return True

def main():
    print("🎯 Creating Complete Dr. Berg Video Database...")
    
    success = enhance_progress_database()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ COMPLETE DATABASE CREATED!")
        print("=" * 60)
        print("📁 File: data/processed/berg_complete_database.json")
        print("📊 Contains: All processed videos with complete metadata")
        print("🔍 Includes: titles, descriptions, transcripts, view counts, etc.")
        print("📈 Ready for: Analysis, search, reporting")
    else:
        print("\n❌ Failed to create complete database")

if __name__ == "__main__":
    main()