# Berg NIH Data Pipeline - Lineage Flow Diagram

## Complete Data Processing Pipeline

```mermaid
flowchart TD
    %% Data Sources
    YT[YouTube API<br/>Dr. Berg Channel] 
    PMC[PubMed Central<br/>Medical Research]
    
    %% Main Scripts
    YTF[scripts/youtube_video_fetcher.py<br/>📊 Fetches ALL videos]
    CF[scripts/create_filtered_catalog.py<br/>🔍 Duration filtering]
    TE[scripts/transcript_extractor_human_batch.py<br/>🎤 Extract transcripts]
    MF[scripts/merge_batch_files.py<br/>🔗 Consolidate results]
    PT[scripts/progress_tracker.py<br/>📈 Track progress]
    PMF[scripts/pmc_fulltext_fetcher.py<br/>📚 Medical articles]
    
    %% Core Data Files
    MC[berg_complete_catalog.json<br/>📁 25MB | 5,314 videos<br/>🏆 MASTER CATALOG]
    FC[berg_filtered_catalog.json<br/>📁 11MB | 2,371 videos<br/>⏱️ 2m01s-5m00s duration]
    CD[berg_complete_database.json<br/>📁 591KB | 60 videos<br/>✅ PROCESSED RESULTS]
    PP[berg_processing_progress.json<br/>📁 15KB | Progress tracking<br/>📊 51 videos logged]
    PMD[pmc_selected_articles_fulltext.json<br/>📁 2.5MB | 15 articles<br/>🔬 Medical research]
    
    %% Temporary/Batch Files (deleted)
    BF1[berg_human_batch_1_of_5_*.json]
    BF2[berg_human_batch_2_of_4_*.json]
    BF3[berg_human_batch_3_of_4_*.json]
    BF4[berg_human_batch_*_*.json<br/>6 individual batch files]
    
    %% Data Flow
    YT --> YTF
    YTF --> MC
    MC --> CF
    CF --> FC
    FC --> TE
    TE --> BF1
    TE --> BF2
    TE --> BF3
    TE --> BF4
    BF1 --> MF
    BF2 --> MF
    BF3 --> MF
    BF4 --> MF
    MF --> CD
    TE --> PT
    PT --> PP
    PMC --> PMF
    PMF --> PMD
    
    %% Styling
    classDef masterFile fill:#e1f5fe,stroke:#01579b,stroke-width:3px,color:#000
    classDef processedFile fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef script fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
    classDef tempFile fill:#ffebee,stroke:#c62828,stroke-width:1px,color:#666,stroke-dasharray: 5 5
    classDef external fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    
    class MC masterFile
    class CD,FC,PP,PMD processedFile
    class YTF,CF,TE,MF,PT,PMF script
    class BF1,BF2,BF3,BF4 tempFile
    class YT,PMC external
```

## Pipeline Summary

### 📊 **Data Sources**
- **YouTube API**: Dr. Berg's complete channel
- **PubMed Central**: Peer-reviewed medical research

### 🔄 **Processing Stages**

1. **Video Catalog Creation** (`youtube_video_fetcher.py`)
   - Fetches ALL 5,314 Dr. Berg videos
   - Creates master catalog with metadata
   - **Output**: `berg_complete_catalog.json` (25MB)

2. **Duration Filtering** (`create_filtered_catalog.py`)
   - Filters for optimal transcript extraction (2m01s-5m00s)
   - Reduces to 2,371 target videos
   - **Output**: `berg_filtered_catalog.json` (11MB)

3. **Transcript Extraction** (`transcript_extractor_human_batch.py`)
   - Processes videos in batches of 10
   - Human-like timing to avoid YouTube blocking
   - **Output**: Individual batch files (6 files, ~100KB each)

4. **Results Consolidation** (`merge_batch_files.py`)
   - Combines all batch results into single database
   - **Output**: `berg_complete_database.json` (591KB, 60 videos)

5. **Progress Tracking** (`progress_tracker.py`)
   - Maintains processing state for resume capability
   - **Output**: `berg_processing_progress.json` (15KB)

6. **Medical Research** (`pmc_fulltext_fetcher.py`)
   - Fetches peer-reviewed articles for cross-referencing
   - **Output**: `pmc_selected_articles_fulltext.json` (2.5MB, 15 articles)

### 📁 **Current Data Assets**
- **39MB total processed data**
- **5,314 videos cataloged** (complete metadata)
- **60 videos processed** (with transcripts and claims)
- **2,371 videos ready** for batch processing
- **15 medical articles** for research validation

### 🗑️ **Files Cleaned Up**
- Individual batch files consolidated into database
- Legacy prototype files removed
- Temporary test files deleted
- **1.1MB space recovered**