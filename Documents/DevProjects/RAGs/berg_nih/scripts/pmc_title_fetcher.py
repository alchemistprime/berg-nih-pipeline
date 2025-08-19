#!/usr/bin/env python3
"""
PMC Title Fetcher - Step 1
Fetch article titles and metadata for review before full text extraction
"""

import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PMCTitleFetcher:
    def __init__(self, email: str = "your-email@example.com"):
        """Initialize PMC title fetcher"""
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.rate_limit_delay = 0.34  # ~3 requests per second
        
        # Berg-derived search terms (simplified)
        self.search_terms = [
            "vitamin D deficiency",
            "magnesium deficiency",
            "vitamin A deficiency", 
            "vitamin C deficiency",
            "iron deficiency anemia",
            "thiamine deficiency",
            "zinc deficiency",
            "potassium deficiency",
            "vitamin B12 deficiency",
            "calcium deficiency",
            "vitamin B1 deficiency"
        ]

    def search_pmc_titles_only(self, search_term: str, max_results: int = 10) -> List[str]:
        """Search PMC for article IDs (titles to be fetched separately)"""
        search_url = f"{self.base_url}esearch.fcgi"
        
        # Build search query - simple search without problematic filters
        query = search_term
        
        params = {
            'db': 'pmc',
            'term': query,
            'retmax': max_results,
            'retmode': 'xml',
            'email': self.email,
            'sort': 'relevance',
            'reldate': 1825,  # Last 5 years
            'datetype': 'pdat'
        }
        
        try:
            logger.info(f"Searching PMC for: {search_term}")
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            id_list = root.find('.//IdList')
            
            if id_list is not None:
                pmc_ids = [id_elem.text for id_elem in id_list.findall('Id')]
                logger.info(f"Found {len(pmc_ids)} articles")
                return pmc_ids
            else:
                logger.warning(f"No articles found for: {search_term}")
                return []
                
        except Exception as e:
            logger.error(f"Search request failed: {e}")
            return []

    def get_article_summaries(self, pmc_ids: List[str]) -> List[Dict]:
        """Fetch basic metadata (titles, authors, etc.) without full text"""
        if not pmc_ids:
            return []
            
        # Use esummary for faster metadata-only fetch
        summary_url = f"{self.base_url}esummary.fcgi"
        
        params = {
            'db': 'pmc',
            'id': ','.join(pmc_ids),
            'retmode': 'xml',
            'email': self.email
        }
        
        try:
            logger.info(f"Fetching summaries for {len(pmc_ids)} articles")
            response = requests.get(summary_url, params=params)
            response.raise_for_status()
            
            articles = []
            root = ET.fromstring(response.content)
            
            for doc_sum in root.findall('.//DocSum'):
                article_data = self._parse_summary_xml(doc_sum)
                if article_data:
                    articles.append(article_data)
                    
            logger.info(f"Extracted metadata for {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Summary fetch failed: {e}")
            return []

    def _parse_summary_xml(self, doc_sum) -> Optional[Dict]:
        """Parse article summary XML to extract basic metadata"""
        try:
            # Get PMC ID
            id_elem = doc_sum.find('./Id')
            pmc_id = id_elem.text if id_elem is not None else ""
            
            # Parse items
            title = ""
            authors = []
            journal = ""
            year = ""
            doi = ""
            
            for item in doc_sum.findall('./Item'):
                name = item.get('Name', '')
                
                if name == 'Title':
                    title = item.text or ""
                elif name == 'AuthorList':
                    # Authors are in sub-items
                    author_names = []
                    for author_item in item.findall('./Item'):
                        if author_item.get('Name') == 'Author':
                            author_names.append(author_item.text or "")
                    authors = author_names
                elif name == 'FullJournalName':
                    journal = item.text or ""
                elif name == 'PubDate':
                    pub_date = item.text or ""
                    # Extract year from date string
                    if pub_date:
                        year = pub_date.split()[0] if pub_date.split() else ""
                elif name == 'DOI':
                    doi = item.text or ""
            
            return {
                'pmc_id': pmc_id,
                'title': title,
                'authors': authors,
                'journal': journal,
                'year': year,
                'doi': doi,
                'pmc_url': f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/" if pmc_id else "",
                'selected_for_full_text': False  # User will mark this
            }
            
        except Exception as e:
            logger.error(f"Error parsing summary XML: {e}")
            return None

    def fetch_all_titles(self, articles_per_term: int = 10) -> Dict:
        """Fetch article titles for all search terms"""
        results = {
            'fetch_date': datetime.now().isoformat(),
            'search_terms': self.search_terms,
            'articles_per_term': articles_per_term,
            'search_results': {}
        }
        
        total_articles = 0
        
        for i, search_term in enumerate(self.search_terms, 1):
            logger.info(f"Processing term {i}/{len(self.search_terms)}: {search_term}")
            
            # Search for PMC IDs
            pmc_ids = self.search_pmc_titles_only(search_term, max_results=articles_per_term)
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Get article summaries
            articles = self.get_article_summaries(pmc_ids)
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            results['search_results'][search_term] = {
                'articles_found': len(articles),
                'articles': articles
            }
            
            total_articles += len(articles)
            logger.info(f"Collected {len(articles)} article summaries for: {search_term}")
        
        results['total_articles'] = total_articles
        logger.info(f"Title fetch complete! Total articles: {total_articles}")
        
        return results

    def save_titles_for_review(self, results: Dict, filename: str = 'pmc_titles_for_review.json'):
        """Save title results for user review"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
        
        # Print summary for review
        print(f"\nPMC TITLE FETCH SUMMARY:")
        print(f"="*60)
        print(f"Total articles found: {results['total_articles']}")
        print(f"Search terms processed: {len(results['search_terms'])}")
        print()
        
        for search_term, data in results['search_results'].items():
            count = data['articles_found']
            print(f"{search_term}: {count} articles")
            
            # Show first few titles as preview
            if data['articles'] and count > 0:
                for j, article in enumerate(data['articles'][:3], 1):
                    title = article['title'][:80] + "..." if len(article['title']) > 80 else article['title']
                    print(f"  {j}. {title}")
                if count > 3:
                    print(f"  ... and {count-3} more")
            print()
        
        print(f"Review the articles in {filename}")
        print(f"Mark 'selected_for_full_text': true for articles you want full text for")
        
        return results

def main():
    """Main execution function"""
    print("PMC Title Fetcher - Step 1")
    print("="*50)
    
    # Initialize fetcher
    fetcher = PMCTitleFetcher(email="your-email@example.com")
    
    # Fetch titles for all search terms
    print("Fetching article titles for Berg-related health topics...")
    results = fetcher.fetch_all_titles(articles_per_term=10)
    
    # Save for review
    fetcher.save_titles_for_review(results)
    
    print("\nStep 1 completed! Review the titles and mark which ones you want full text for.")

if __name__ == "__main__":
    main()