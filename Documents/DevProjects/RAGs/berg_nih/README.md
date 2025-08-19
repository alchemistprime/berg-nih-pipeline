# Berg NIH Natural Medical Application

MVP for a natural medical application that cross-references Dr. Berg's health insights with peer-reviewed medical research.

## Project Structure

```
berg_nih/
├── src/berg_nih/           # Main application code
├── scripts/                # Data extraction and processing scripts
├── data/
│   ├── raw/               # Raw downloads
│   ├── processed/         # Cleaned datasets
│   └── output/            # Generated files for review
├── notebooks/             # Jupyter notebooks for analysis
├── tests/                 # Test files
└── pyproject.toml         # Project configuration
```

## Datasets

### Berg Data
- **File**: `data/processed/berg_exploration_with_transcripts_v2.json`
- **Content**: 49 Dr. Berg videos with full transcripts and extracted claims
- **Total Views**: 43.6M
- **Claims Extracted**: 115

### PMC Research Data
- **File**: `data/processed/pmc_selected_articles_fulltext.json`
- **Content**: 15 peer-reviewed open access articles
- **Total Words**: 192,707
- **Topics**: Vitamin deficiencies, minerals, nutrition

## Key Scripts

- `scripts/berg_explorer.py` - Extract Dr. Berg video data
- `scripts/pmc_title_fetcher.py` - Search PMC for relevant articles
- `scripts/pmc_fulltext_fetcher.py` - Download full text of selected articles

## Usage

1. Set up environment: `uv sync`
2. Configure API keys in `.env`
3. Run data extraction scripts
4. Use processed data for MVP development

## Next Steps

- [ ] Build symptom input interface
- [ ] Create cross-reference engine
- [ ] Develop recommendation system
- [ ] Add natural remedy suggestions with research backing
