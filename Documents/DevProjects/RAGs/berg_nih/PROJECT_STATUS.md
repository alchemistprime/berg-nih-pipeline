# Dr. Berg Video Processing Pipeline - Project Status

**Date**: August 18, 2025  
**Status**: YouTube IP blocked during transcript extraction  

## 🎯 **Project Objective**
Process ALL Dr. Berg YouTube videos (5,647 total) to extract transcripts and medical claims for research analysis.

## ✅ **Completed Successfully**

### **Phase 1: Video Catalog (COMPLETE)**
- **Script**: `scripts/youtube_video_fetcher.py`
- **Output**: `data/processed/berg_complete_catalog.json`
- **Results**: 
  - 5,647 total videos fetched
  - 5,314 videos after filtering  
  - Date range: 2008-2019 to 2025 (17 years)
  - Total duration: 921.3 hours
  - API quota used: 227 units (very efficient)

### **Video Duration Analysis**
- **Under 5min**: 2,768 videos (52.1%)
- **5-15min**: 1,903 videos (35.8%) 
- **15-30min**: 170 videos (3.2%)
- **30-60min**: 116 videos (2.2%)
- **Over 60min**: 357 videos (6.7%)

**Target Range Selected**: 2-5 minutes (2,371 videos) for optimal transcript success rate

## ⚡ **Current Processing Status**

### **Phase 2: Transcript Extraction (IN PROGRESS)**
- **Script**: `scripts/transcript_extractor.py` (enhanced with IP blocking protection)
- **Target**: Videos 121-300 seconds (2m01s to 5m00s)
- **Total Target Videos**: 2,371 videos
- **Batch Size**: 25 videos per batch
- **Progress**: ~12 videos successfully processed before IP block

### **YouTube IP Blocking Situation**
- **Status**: In "YouTube jail" - aggressive IP blocking
- **Detection**: After ~12 successful extractions
- **Current Behavior**: Script cooling off in 5→8→11→14→17 minute cycles
- **Attempts**: Second round of escalating delays
- **Root Cause**: Too many requests triggered YouTube's anti-scraping protection

## 🛠️ **Enhanced Scripts Created**

### **1. Video Fetcher** (`youtube_video_fetcher.py`)
- ✅ Uses YouTube Data API v3 efficiently
- ✅ Fetches complete channel via uploads playlist
- ✅ Rich metadata extraction (views, duration, publish dates)
- ✅ Smart filtering and duration analysis
- ✅ Handles 5,000+ videos reliably

### **2. Enhanced Transcript Extractor** (`transcript_extractor.py`)
**Key Features**:
- ✅ Adaptive API method detection (fetch vs get_transcript)
- ✅ Intelligent rate limiting with exponential backoff
- ✅ IP blocking detection and extended cooling off (5-17 minutes)
- ✅ Batch processing with resume capability
- ✅ Duration filtering (--min-duration, --max-duration)
- ✅ Auto-filename generation
- ✅ Progress saving every N videos
- ✅ Comprehensive error categorization
- ✅ Proxy rotation support (attempted)

### **3. Proxy Version** (`transcript_extractor_proxy.py`)
- ⚠️ Created but proxy integration challenging with youtube-transcript-api
- ⚠️ YouTube blocking is IP-range based, not individual IP

## 📊 **Key Data Files**

### **Main Catalog**
- **File**: `data/processed/berg_complete_catalog.json`
- **Content**: Complete Dr. Berg video metadata
- **Videos**: 5,314 filtered videos
- **Size**: Comprehensive metadata for all videos

### **Progress File** 
- **File**: `data/processed/berg_transcripts_2m01s_to_5m00s_batch25.json`
- **Content**: Partial results from transcript extraction
- **Status**: ~12 videos processed before IP block

## 🔧 **Technical Configuration**

### **API Setup**
- **YouTube Data API Key**: Configured in `.env` file
- **Quota Usage**: Very efficient (227 units for 5,647 videos)
- **Rate Limiting**: Conservative (3-15 second delays)

### **Environment**
- **Platform**: Windows via WSL
- **Python**: Virtual environment with youtube-transcript-api
- **Network**: Oxylabs residential proxies purchased but integration complex

### **Current Command**
```bash
uv run python scripts\transcript_extractor.py ^
    --input-file data\processed\berg_complete_catalog.json ^
    --min-duration 121 ^
    --max-duration 300 ^
    --batch-size 25 ^
    --auto-filename
```

## 🚨 **Current Challenge: YouTube IP Blocking**

### **Problem**
- YouTube detected scraping pattern after ~12 videos
- Implemented aggressive IP blocking
- Escalating cooling off periods not breaking through
- Proxy integration with youtube-transcript-api library is complex

### **Script Response**
- ✅ Detecting IP blocks correctly
- ✅ Implementing 5-17 minute cooling off periods
- ✅ Escalating delays appropriately  
- ✅ Saving progress (won't lose completed work)
- ⚠️ Currently in second round of cooling off cycle

## 💡 **Next Steps & Options**

### **Option A: Wait Strategy**
- Let current script continue cooling off
- YouTube blocks typically resolve in 1-24 hours
- Enhanced error handling will eventually succeed
- **Timeline**: 12-24 hours for 2,371 videos

### **Option B: Different Network/Time**
- Switch to mobile hotspot (different IP range)
- Process during off-peak hours (less detection)
- Use different physical location
- **Timeline**: 4-8 hours with fresh IP

### **Option C: Professional Proxy Service**
- Implement deeper proxy integration
- Use residential proxy service (Oxylabs purchased)
- Requires custom youtube-transcript-api modifications
- **Timeline**: 2-4 hours development + 2-4 hours processing

### **Option D: Alternative Transcript Sources**
- Explore YouTube official API transcript endpoints
- Use browser automation (Selenium) with proxies
- Direct HTML parsing approaches
- **Timeline**: 4-8 hours development + processing

## 🎯 **Success Metrics Achieved**

### **Video Catalog Success**
- ✅ 100% success rate (5,647/5,647 videos)
- ✅ Comprehensive 17-year dataset
- ✅ Rich metadata for analysis
- ✅ Duration-based filtering working

### **Transcript Extraction Partial Success**
- ✅ 12 successful extractions before blocking
- ✅ Error handling working perfectly
- ✅ Progress saving functional
- ✅ Batch processing operational

## 📁 **File Structure**
```
berg_nih/
├── data/processed/
│   ├── berg_complete_catalog.json (5,314 videos)
│   └── berg_transcripts_2m01s_to_5m00s_batch25.json (partial)
├── scripts/
│   ├── youtube_video_fetcher.py (complete)
│   ├── transcript_extractor.py (enhanced)
│   └── transcript_extractor_proxy.py (experimental)
├── .env (YouTube API key configured)
├── test_proxies.txt (Oxylabs residential proxy)
└── PROJECT_STATUS.md (this file)
```

## 🚀 **Resume Instructions**

### **To Continue Current Approach**
Script is already running with enhanced IP blocking protection. Will eventually succeed.

### **To Restart with Fresh IP**
```bash
# From different network/location:
cd C:\Users\sean\Documents\DevProjects\RAGs\berg_nih
uv run python scripts\transcript_extractor.py ^
    --input-file data\processed\berg_complete_catalog.json ^
    --min-duration 121 ^
    --max-duration 300 ^
    --batch-size 10 ^
    --start-index 12 ^
    --save-frequency 5 ^
    --auto-filename
```

### **To Use Different Duration Range**
```bash
# Try shorter videos (higher success rate):
uv run python scripts\transcript_extractor.py ^
    --min-duration 60 ^
    --max-duration 120 ^
    --batch-size 10
```

## 🏆 **Project Value**

### **Current Dataset Value**
- **5,314 videos** with complete metadata
- **921.3 hours** of health content catalogued
- **17 years** of Dr. Berg's evolution tracked
- **Comprehensive search index** ready

### **Target Dataset Value** (when complete)
- **2,371 video transcripts** (2-5 minute optimal range)
- **~150-200 hours** of transcript text
- **~7,000-15,000 medical claims** extracted
- **Searchable knowledge base** of health information

## 📞 **Contact Information**
- **API Service**: Oxylabs residential proxies active
- **Environment**: Windows/WSL with Python virtual environment
- **Status**: Pipeline fully functional, temporarily blocked by YouTube