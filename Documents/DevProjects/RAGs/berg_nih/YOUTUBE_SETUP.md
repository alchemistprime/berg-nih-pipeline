# YouTube Data API Setup Guide

## Overview
This guide shows how to set up the complete pipeline to fetch ALL of Dr. Berg's videos and extract transcripts.

## Phase 1: Get YouTube Data API v3 Key

### Step 1: Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing one
3. Enable "YouTube Data API v3"
4. Create credentials (API Key)
5. Restrict API key to YouTube Data API v3 (recommended)

### Step 2: Set Environment Variable
Add to your `.env` file:
```bash
YOUTUBE_API_KEY=your_api_key_here
```

## Phase 2: Complete Pipeline Usage

### Option A: Full Automation (Recommended)
```bash
# Step 1: Fetch ALL Dr. Berg videos (uses YouTube Data API v3)
python scripts/youtube_video_fetcher.py \
    --output-file data/processed/berg_complete_catalog.json

# Step 2: Extract transcripts in batches of 50 videos
python scripts/transcript_extractor.py \
    --input-file data/processed/berg_complete_catalog.json \
    --batch-size 50 \
    --save-frequency 10

# Step 3: Continue from where you left off (if interrupted)
python scripts/transcript_extractor.py \
    --input-file data/processed/berg_complete_catalog.json \
    --batch-size 50 \
    --start-index 50  # Resume from video 51
```

### Option B: With Proxy Rotation (For High Volume)
```bash
# Create proxy file
echo "http://proxy1.example.com:8080" > proxies.txt
echo "http://proxy2.example.com:8080" >> proxies.txt

# Extract with proxy rotation
python scripts/transcript_extractor.py \
    --input-file data/processed/berg_complete_catalog.json \
    --batch-size 25 \
    --use-proxies \
    --proxy-file proxies.txt
```

## Expected Results

### Video Catalog (Phase 1)
- **~1000-1500 Dr. Berg videos** (his complete catalog)
- **Rich metadata**: views, duration, publish date, tags
- **Smart filtering**: excludes shorts, includes transcript likelihood scoring
- **API efficient**: ~10-20 requests total

### Transcript Extraction (Phase 2)
- **Batch processing**: Process in chunks of 25-100 videos
- **Resume capability**: Can restart from any point
- **Rate limiting**: Intelligent delays to avoid API blocks
- **Progress tracking**: Saves every N videos processed
- **Error categorization**: Distinguishes temporary vs permanent failures

## Quota Management

### YouTube Data API v3 Quotas
- **Free tier**: 10,000 quota units/day
- **Video catalog**: ~100-200 quota units total
- **Transcript API**: Separate service, different limits

### Estimated Timeline
- **Catalog fetch**: 2-5 minutes
- **Transcript extraction**: 3-8 hours (depending on rate limiting)
- **Total content**: 50-100+ hours of video transcripts

## Troubleshooting

### Common Issues
1. **API Key Error**: Check `.env` file and Google Cloud Console
2. **Quota Exceeded**: Wait 24 hours or use different project
3. **Rate Limited**: Script automatically handles this with backoff
4. **Network Issues**: Use `--start-index` to resume from interruption

### Monitoring Progress
```bash
# Check current progress
tail -f data/processed/berg_exploration_with_transcripts_v3.json.tmp

# View success rates
grep "success rate" transcript_extraction.log
```

## Advanced Options

### Custom Filtering
```bash
# Only videos 5-60 minutes long
python scripts/youtube_video_fetcher.py \
    --min-duration 300 \
    --max-duration 3600

# Include YouTube shorts
python scripts/youtube_video_fetcher.py \
    --include-shorts
```

### Performance Tuning
```bash
# Faster processing (higher risk of rate limits)
python scripts/transcript_extractor.py \
    --batch-size 100 \
    --save-frequency 25

# Conservative processing (slower but more reliable)
python scripts/transcript_extractor.py \
    --batch-size 25 \
    --save-frequency 5
```

## Expected Output Structure

```json
{
  "channel_info": {
    "title": "Dr. Eric Berg DC",
    "video_count": "1,200+",
    "subscriber_count": "10M+"
  },
  "videos": [
    {
      "video_id": "abc123",
      "title": "Vitamin D Deficiency Signs",
      "duration_seconds": 720,
      "view_count": 500000,
      "published_date": "2023-01-15",
      "transcript": {
        "transcript_available": true,
        "full_text": "In this video I want to talk about...",
        "word_count": 1200
      },
      "transcript_claims": [
        {
          "claim_type": "deficiency_symptoms",
          "subject": "vitamin D deficiency",
          "predicate": "causes fatigue and depression"
        }
      ]
    }
  ]
}
```