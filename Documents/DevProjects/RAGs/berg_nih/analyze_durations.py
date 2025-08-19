#!/usr/bin/env python3
"""
Quick duration analysis for Dr. Berg video catalog
"""

import json

def analyze_durations(catalog_file):
    """Analyze video durations with detailed breakdown"""
    
    with open(catalog_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    videos = data.get('videos', [])
    
    # Duration buckets (in seconds)
    buckets = {
        '0-1 min': 0,
        '1-2 min': 0, 
        '2-3 min': 0,
        '3-4 min': 0,
        '4-5 min': 0,
        '5-10 min': 0,
        '10-15 min': 0,
        '15-20 min': 0,
        '20+ min': 0
    }
    
    total_under_5min = 0
    
    for video in videos:
        duration = video.get('duration_seconds', 0)
        
        if duration <= 60:
            buckets['0-1 min'] += 1
        elif duration <= 120:
            buckets['1-2 min'] += 1
        elif duration <= 180:
            buckets['2-3 min'] += 1
        elif duration <= 240:
            buckets['3-4 min'] += 1
        elif duration <= 300:
            buckets['4-5 min'] += 1
        elif duration <= 600:
            buckets['5-10 min'] += 1
        elif duration <= 900:
            buckets['10-15 min'] += 1
        elif duration <= 1200:
            buckets['15-20 min'] += 1
        else:
            buckets['20+ min'] += 1
        
        if duration < 300:  # Under 5 minutes
            total_under_5min += 1
    
    print("DR. BERG VIDEO DURATION ANALYSIS")
    print("=" * 50)
    print(f"Total videos analyzed: {len(videos):,}")
    print(f"Videos under 5 minutes: {total_under_5min:,}")
    print()
    
    print("DETAILED BREAKDOWN:")
    print("-" * 30)
    for bucket, count in buckets.items():
        percentage = (count / len(videos)) * 100 if videos else 0
        print(f"{bucket:12}: {count:4,} videos ({percentage:5.1f}%)")
    
    print()
    print("UNDER 5 MINUTE BREAKDOWN:")
    print("-" * 30)
    under_5_total = sum([buckets['0-1 min'], buckets['1-2 min'], buckets['2-3 min'], 
                        buckets['3-4 min'], buckets['4-5 min']])
    
    for bucket in ['0-1 min', '1-2 min', '2-3 min', '3-4 min', '4-5 min']:
        count = buckets[bucket]
        pct_of_under5 = (count / under_5_total) * 100 if under_5_total else 0
        pct_of_total = (count / len(videos)) * 100 if videos else 0
        print(f"{bucket:12}: {count:4,} videos ({pct_of_under5:5.1f}% of <5min, {pct_of_total:4.1f}% of total)")

if __name__ == "__main__":
    analyze_durations('data/processed/berg_complete_catalog.json')