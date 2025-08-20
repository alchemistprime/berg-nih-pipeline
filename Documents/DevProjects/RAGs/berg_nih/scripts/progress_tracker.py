#!/usr/bin/env python3
"""
Master Progress Tracking System for Berg Video Processing
Prevents duplicates, tracks exact progress, enables reliable resume
"""

import json
import os
from datetime import datetime
from pathlib import Path

class ProgressTracker:
    def __init__(self, progress_file="data/processed/berg_processing_progress.json", 
                 catalog_file="data/processed/berg_complete_catalog.json",
                 min_duration=121, max_duration=300):
        self.progress_file = progress_file
        self.catalog_file = catalog_file
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.progress_data = self._load_progress()
        self.catalog_data = self._load_catalog()
        self.filtered_catalog = self._filter_catalog_by_duration()
    
    def _load_progress(self):
        """Load existing progress or create new"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "master_progress": {
                    "catalog_file": "berg_complete_catalog.json",
                    "duration_filter": {
                        "min_duration": self.min_duration,
                        "max_duration": self.max_duration
                    },
                    "total_videos_in_catalog": 0,
                    "total_videos_in_target_range": 0,
                    "videos_processed": 0,
                    "last_updated": datetime.now().isoformat(),
                    "last_processed_index": -1
                },
                "processed_videos": {}
            }
    
    def _load_catalog(self):
        """Load video catalog"""
        if not os.path.exists(self.catalog_file):
            print(f"❌ Catalog file not found: {self.catalog_file}")
            return None
            
        with open(self.catalog_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _filter_catalog_by_duration(self):
        """Filter catalog to only videos in target duration range"""
        if not self.catalog_data or 'videos' not in self.catalog_data:
            return []
            
        filtered = []
        for i, video in enumerate(self.catalog_data['videos']):
            duration = video.get('duration_seconds', 0)
            if self.min_duration <= duration <= self.max_duration:
                video_copy = video.copy()
                video_copy['catalog_index'] = i  # Store original catalog index
                filtered.append(video_copy)
                
        return filtered
    
    def scan_existing_batches(self, data_dir="data/processed"):
        """Scan all existing batch files and build progress tracking"""
        print("🔍 Scanning existing batch files...")
        
        import glob
        batch_files = glob.glob(os.path.join(data_dir, "berg_human_batch_*.json"))
        
        if not batch_files:
            print("❌ No batch files found")
            return
        
        total_scanned = 0
        
        for batch_file in sorted(batch_files):
            print(f"📖 Scanning {os.path.basename(batch_file)}...")
            
            try:
                with open(batch_file, 'r', encoding='utf-8') as f:
                    batch_data = json.load(f)
                
                if 'videos' not in batch_data:
                    continue
                    
                for video in batch_data['videos']:
                    video_id = video.get('video_id')
                    if not video_id:
                        continue
                        
                    # Find this video in catalog to get index
                    catalog_index = self._find_video_in_catalog(video_id)
                    
                    if catalog_index is not None:
                        self.progress_data['processed_videos'][video_id] = {
                            "catalog_index": catalog_index,
                            "processed_at": batch_data.get('batch_metadata', {}).get('completed_at', 
                                                          datetime.now().isoformat()),
                            "batch_file": os.path.basename(batch_file),
                            "status": "success",
                            "title": video.get('title', 'Unknown'),
                            "duration": video.get('duration_formatted', 'Unknown')
                        }
                        total_scanned += 1
                        
            except Exception as e:
                print(f"❌ Error scanning {batch_file}: {e}")
        
        # Update master progress
        self.progress_data['master_progress']['videos_processed'] = total_scanned
        self.progress_data['master_progress']['last_updated'] = datetime.now().isoformat()
        
        if self.catalog_data and 'videos' in self.catalog_data:
            self.progress_data['master_progress']['total_videos_in_catalog'] = len(self.catalog_data['videos'])
            self.progress_data['master_progress']['total_videos_in_target_range'] = len(self.filtered_catalog)
        
        # Find next resume index
        processed_indices = [v['catalog_index'] for v in self.progress_data['processed_videos'].values()]
        if processed_indices:
            self.progress_data['master_progress']['last_processed_index'] = max(processed_indices)
        
        self._save_progress()
        
        print(f"✅ Scanned {total_scanned} processed videos")
        return total_scanned
    
    def _find_video_in_catalog(self, video_id):
        """Find video_id in catalog and return its index"""
        if not self.catalog_data or 'videos' not in self.catalog_data:
            return None
            
        for i, video in enumerate(self.catalog_data['videos']):
            if video.get('video_id') == video_id:
                return i
                
        return None
    
    def get_next_resume_index(self):
        """Get the next index to resume processing from"""
        processed_indices = [v['catalog_index'] for v in self.progress_data['processed_videos'].values()]
        
        if not processed_indices:
            return 0
            
        # Find the next unprocessed index
        max_processed = max(processed_indices)
        
        # Check if we have gaps (missing videos in sequence)
        all_processed = set(processed_indices)
        
        # Find first gap or next after max
        for i in range(max_processed + 1):
            if i not in all_processed:
                return i
                
        return max_processed + 1
    
    def is_video_processed(self, video_id):
        """Check if a video has already been processed"""
        return video_id in self.progress_data['processed_videos']
    
    def mark_video_processed(self, video_id, catalog_index, batch_file, additional_data=None):
        """Mark a video as processed"""
        self.progress_data['processed_videos'][video_id] = {
            "catalog_index": catalog_index,
            "processed_at": datetime.now().isoformat(),
            "batch_file": batch_file,
            "status": "success"
        }
        
        if additional_data:
            self.progress_data['processed_videos'][video_id].update(additional_data)
        
        self.progress_data['master_progress']['videos_processed'] = len(self.progress_data['processed_videos'])
        self.progress_data['master_progress']['last_updated'] = datetime.now().isoformat()
        self.progress_data['master_progress']['last_processed_index'] = max(
            [v['catalog_index'] for v in self.progress_data['processed_videos'].values()]
        )
        
        self._save_progress()
    
    def _save_progress(self):
        """Save progress to file"""
        Path(self.progress_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
    
    def get_progress_summary(self):
        """Get a summary of current progress"""
        total_in_catalog = self.progress_data['master_progress']['total_videos_in_catalog']
        target_videos = self.progress_data['master_progress']['total_videos_in_target_range']
        processed = self.progress_data['master_progress']['videos_processed']
        next_index = self.get_next_resume_index()
        
        return {
            'total_videos_in_catalog': total_in_catalog,
            'target_videos_to_process': target_videos,
            'processed_videos': processed,
            'remaining_videos': target_videos - processed,
            'completion_percentage': (processed / target_videos * 100) if target_videos > 0 else 0,
            'next_resume_index': next_index,
            'duration_filter': f"{self.min_duration}-{self.max_duration} seconds"
        }
    
    def print_progress_report(self):
        """Print detailed progress report"""
        summary = self.get_progress_summary()
        
        print("\n" + "="*60)
        print("📊 BERG VIDEO PROCESSING PROGRESS REPORT")
        print("="*60)
        print(f"📺 Total videos in catalog: {summary['total_videos_in_catalog']:,}")
        print(f"🎯 Target videos (2-5 min): {summary['target_videos_to_process']:,}")
        print(f"✅ Videos processed: {summary['processed_videos']:,}")
        print(f"⏳ Videos remaining: {summary['remaining_videos']:,}")
        print(f"📈 Completion: {summary['completion_percentage']:.1f}%")
        print(f"🚀 Next resume index: {summary['next_resume_index']}")
        print(f"⏱️  Duration filter: {summary['duration_filter']}")
        print(f"📅 Last updated: {self.progress_data['master_progress']['last_updated']}")
        
        print(f"\n🎯 RESUME COMMAND:")
        print(f"python scripts/vpn_batch_orchestrator.py --total-videos 20 --start-index {summary['next_resume_index']}")
        print("="*60)

def main():
    print("🎯 Building Master Progress Tracking System...")
    
    tracker = ProgressTracker()
    
    # Scan existing batches to build progress
    total_scanned = tracker.scan_existing_batches()
    
    if total_scanned > 0:
        # Print progress report
        tracker.print_progress_report()
        
        print(f"\n✅ Progress tracking system created!")
        print(f"📁 Progress file: {tracker.progress_file}")
        print(f"🔍 Found and catalogued {total_scanned} processed videos")
        
    else:
        print("❌ No processed videos found to track")

if __name__ == "__main__":
    main()