#!/usr/bin/env python3
"""
PMC Full-Text Fetcher - Step 2
Fetch complete articles for user-selected PMC articles
"""

import csv
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

class PMCFullTextFetcher:
    def __init__(self, email: str = "your-email@example.com"):
        """Initialize PMC full-text fetcher"""
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.rate_limit_delay = 0.34  # ~3 requests per second

    def load_selected_articles(self, csv_file: str) -> List[Dict]:
        """Load selected articles from CSV file"""
        selected_articles = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # For culled file, treat all articles as selected
                    # Also check if explicitly marked as selected
                    selected = row.get('selected_for_full_text', '').lower()
                    if 'culled' in csv_file.lower() or selected in ['true', '1', 'yes', 'y']:
                        selected_articles.append({
                            'search_term': row['search_term'],
                            'pmc_id': row['pmc_id'],
                            'title': row['title'],
                            'authors': row['authors'],
                            'journal': row['journal'],
                            'year': row['year'],
                            'doi': row['doi'],
                            'pmc_url': row['pmc_url']
                        })
            
            logger.info(f"Found {len(selected_articles)} selected articles")
            return selected_articles
            
        except FileNotFoundError:
            logger.error(f"CSV file {csv_file} not found")
            return []
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []

    def fetch_full_article(self, pmc_id: str) -> Optional[Dict]:
        """Fetch complete article content from PMC"""
        fetch_url = f"{self.base_url}efetch.fcgi"
        
        params = {
            'db': 'pmc',
            'id': pmc_id,
            'retmode': 'xml',
            'email': self.email
        }
        
        try:
            logger.info(f"Fetching full article PMC{pmc_id}")
            response = requests.get(fetch_url, params=params)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            article_elem = root.find('.//article')
            
            if article_elem is not None:
                return self._parse_full_article_xml(article_elem, pmc_id)
            else:
                logger.warning(f"No article content found for PMC{pmc_id}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Fetch request failed for PMC{pmc_id}: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"XML parsing failed for PMC{pmc_id}: {e}")
            return None

    def _parse_full_article_xml(self, article_elem, pmc_id: str) -> Dict:
        """Parse complete article XML to extract all content"""
        article_data = {
            'pmc_id': pmc_id,
            'metadata': {},
            'full_text_sections': {},
            'full_text_combined': '',
            'abstract': '',
            'keywords': [],
            'references_count': 0,
            'figures_count': 0,
            'tables_count': 0,
            'word_count': 0
        }
        
        try:
            # Extract metadata from front matter
            front = article_elem.find('.//front')
            if front is not None:
                metadata = self._extract_metadata(front)
                article_data['metadata'] = metadata
                article_data['abstract'] = metadata.get('abstract', '')
                article_data['keywords'] = metadata.get('keywords', [])
            
            # Extract main body content
            body = article_elem.find('.//body')
            if body is not None:
                sections, combined_text = self._extract_body_sections(body)
                article_data['full_text_sections'] = sections
                article_data['full_text_combined'] = combined_text
                article_data['word_count'] = len(combined_text.split()) if combined_text else 0
            
            # Count references, figures, tables
            article_data['references_count'] = len(article_elem.findall('.//ref'))
            article_data['figures_count'] = len(article_elem.findall('.//fig'))
            article_data['tables_count'] = len(article_elem.findall('.//table-wrap'))
            
            logger.info(f"Extracted article PMC{pmc_id}: {article_data['word_count']} words, {len(article_data['full_text_sections'])} sections")
            return article_data
            
        except Exception as e:
            logger.error(f"Error parsing article XML for PMC{pmc_id}: {e}")
            return article_data

    def _extract_metadata(self, front_elem) -> Dict:
        """Extract metadata from front matter"""
        metadata = {}
        
        article_meta = front_elem.find('.//article-meta')
        if article_meta is None:
            return metadata
        
        # Title
        title_elem = article_meta.find('.//title-group/article-title')
        if title_elem is not None:
            metadata['title'] = self._extract_text_from_element(title_elem)
        
        # Abstract
        abstract_elem = article_meta.find('.//abstract')
        if abstract_elem is not None:
            abstract_parts = []
            for p in abstract_elem.findall('.//p'):
                p_text = self._extract_text_from_element(p)
                if p_text:
                    abstract_parts.append(p_text)
            metadata['abstract'] = " ".join(abstract_parts)
        
        # Keywords
        keywords = []
        for kwd_group in article_meta.findall('.//kwd-group'):
            for kwd in kwd_group.findall('.//kwd'):
                if kwd.text:
                    keywords.append(kwd.text.strip())
        metadata['keywords'] = keywords
        
        # Authors
        authors = []
        for contrib in article_meta.findall('.//contrib[@contrib-type="author"]'):
            name_elem = contrib.find('.//name')
            if name_elem is not None:
                surname = name_elem.find('surname')
                given_names = name_elem.find('given-names')
                if surname is not None and given_names is not None:
                    authors.append(f"{given_names.text} {surname.text}")
        metadata['authors'] = authors
        
        # Journal info
        journal_elem = front_elem.find('.//journal-title')
        if journal_elem is not None:
            metadata['journal'] = journal_elem.text
        
        return metadata

    def _extract_body_sections(self, body_elem) -> tuple:
        """Extract all body sections with their content"""
        sections = {}
        all_text_parts = []
        
        # Extract main sections
        for sec in body_elem.findall('.//sec'):
            section_title = "Unknown Section"
            section_content = ""
            
            # Get section title
            title_elem = sec.find('.//title')
            if title_elem is not None:
                section_title = self._extract_text_from_element(title_elem)
            
            # Get all paragraphs in this section
            paragraphs = []
            for p in sec.findall('.//p'):
                p_text = self._extract_text_from_element(p)
                if p_text:
                    paragraphs.append(p_text)
            
            section_content = " ".join(paragraphs)
            
            if section_content:
                sections[section_title] = section_content
                all_text_parts.append(f"{section_title}: {section_content}")
        
        # Also get any direct paragraphs in body (not in sections)
        direct_paragraphs = []
        for p in body_elem.findall('./p'):  # Direct children only
            p_text = self._extract_text_from_element(p)
            if p_text:
                direct_paragraphs.append(p_text)
        
        if direct_paragraphs:
            content = " ".join(direct_paragraphs)
            sections["Main Content"] = content
            all_text_parts.append(content)
        
        combined_text = " ".join(all_text_parts)
        return sections, combined_text

    def _extract_text_from_element(self, element) -> str:
        """Recursively extract all text from XML element"""
        text_parts = []
        
        if element.text:
            text_parts.append(element.text.strip())
        
        for child in element:
            child_text = self._extract_text_from_element(child)
            if child_text:
                text_parts.append(child_text)
            
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return " ".join(part for part in text_parts if part)

    def fetch_selected_articles(self, csv_file: str) -> Dict:
        """Fetch full text for all selected articles"""
        # Load selected articles
        selected_articles = self.load_selected_articles(csv_file)
        
        if not selected_articles:
            logger.error("No selected articles found")
            return {}
        
        results = {
            'fetch_date': datetime.now().isoformat(),
            'selected_articles_count': len(selected_articles),
            'successfully_fetched': 0,
            'articles': {}
        }
        
        logger.info(f"Fetching full text for {len(selected_articles)} selected articles")
        
        for i, article in enumerate(selected_articles, 1):
            pmc_id = article['pmc_id']
            search_term = article['search_term']
            title = article['title']
            
            logger.info(f"Processing {i}/{len(selected_articles)}: PMC{pmc_id}")
            logger.info(f"Title: {title[:60]}...")
            
            # Fetch full article
            full_article = self.fetch_full_article(pmc_id)
            
            if full_article:
                # Combine metadata with full text
                combined_article = {
                    **article,  # Original metadata
                    **full_article,  # Full text content
                    'berg_search_term': search_term,
                    'fetch_status': 'success'
                }
                
                results['articles'][pmc_id] = combined_article
                results['successfully_fetched'] += 1
                
                logger.info(f"✓ Success: {full_article['word_count']} words, {len(full_article['full_text_sections'])} sections")
            else:
                # Keep article info even if full text failed
                failed_article = {
                    **article,
                    'berg_search_term': search_term,
                    'fetch_status': 'failed',
                    'full_text_sections': {},
                    'full_text_combined': '',
                    'word_count': 0
                }
                results['articles'][pmc_id] = failed_article
                logger.warning(f"✗ Failed to fetch full text")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
        
        logger.info(f"Fetch complete! {results['successfully_fetched']}/{len(selected_articles)} articles retrieved")
        return results

    def save_results(self, results: Dict, filename: str = 'pmc_selected_articles_fulltext.json'):
        """Save full-text results"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
        
        # Print summary
        print(f"\nPMC FULL-TEXT FETCH SUMMARY:")
        print(f"="*60)
        print(f"Selected articles: {results['selected_articles_count']}")
        print(f"Successfully fetched: {results['successfully_fetched']}")
        print(f"Success rate: {results['successfully_fetched']/results['selected_articles_count']*100:.1f}%")
        
        total_words = sum(article.get('word_count', 0) for article in results['articles'].values())
        print(f"Total words extracted: {total_words:,}")
        
        # Show articles by Berg topic
        by_topic = {}
        for article in results['articles'].values():
            topic = article.get('berg_search_term', 'unknown')
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(article)
        
        print(f"\nArticles by Berg topic:")
        for topic, articles in by_topic.items():
            successful = sum(1 for a in articles if a.get('fetch_status') == 'success')
            print(f"  {topic}: {successful}/{len(articles)} articles")
        
        return results

def main():
    """Main execution function"""
    print("PMC Full-Text Fetcher - Step 2")
    print("="*50)
    
    # Initialize fetcher
    fetcher = PMCFullTextFetcher(email="your-email@example.com")
    
    # Use the updated CSV file name
    csv_file = 'pmc_titles_for_review_culled.csv'
    try:
        with open(csv_file, 'r') as f:
            pass
        print(f"Using culled CSV file: {csv_file}")
    except FileNotFoundError:
        print(f"ERROR: {csv_file} not found")
        print("Please ensure the culled CSV file with your 15 selected articles exists")
        return
    
    # Fetch full text for selected articles
    print("Fetching full text for your 15 selected articles...")
    results = fetcher.fetch_selected_articles(csv_file)
    
    if results:
        # Save results
        fetcher.save_results(results)
        print("\nStep 2 completed! Full-text articles ready for Berg cross-referencing.")
    else:
        print("No articles to fetch. Check your CSV file selections.")

if __name__ == "__main__":
    main()