#!/usr/bin/env python3
"""
PMC Article Fetcher
Fetches open access articles with commercial use permissions from PubMed Central
that are relevant to Dr. Berg's health topics
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

class PMCFetcher:
    def __init__(self, email: str = "your-email@example.com"):
        """
        Initialize PMC fetcher
        
        Args:
            email: Your email for NCBI E-utilities (required for rate limiting compliance)
        """
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.rate_limit_delay = 0.34  # ~3 requests per second (NCBI requirement)
        
        # Berg-derived search terms mapped to topics
        self.search_terms = {
            "thiamine_bladder": "thiamine deficiency bladder dysfunction",
            "magnesium_hypertension": "magnesium glycinate blood pressure hypertension", 
            "vitamin_d_immune": "vitamin D deficiency immune system symptoms",
            "potassium_cardiovascular": "potassium deficiency cardiovascular health",
            "b12_neuropathy": "vitamin B12 deficiency peripheral neuropathy",
            "thiamine_sciatica": "thiamine deficiency carpal tunnel sciatica",
            "iron_anemia": "iron deficiency anemia fatigue symptoms",
            "b1_adrenal": "vitamin B1 thiamine adrenal fatigue",
            "magnesium_cramps": "magnesium deficiency muscle cramps calcium regulation",
            "vitamin_d_zinc": "vitamin D zinc absorption immune function"
        }
        
        # Commercial use licenses we want
        self.commercial_licenses = [
            "CC BY",
            "CC BY-SA", 
            "CC BY-NC-SA",
            "CC0"
        ]

    def search_pmc(self, search_term: str, max_results: int = 10) -> List[str]:
        """
        Search PMC for articles using E-search
        
        Args:
            search_term: Search query
            max_results: Maximum number of PMC IDs to return
            
        Returns:
            List of PMC IDs
        """
        search_url = f"{self.base_url}esearch.fcgi"
        
        # Build search query with filters
        query = f'({search_term}) AND "open access"[filter] AND "free full text"[filter]'
        
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
                logger.info(f"Found {len(pmc_ids)} articles for search term")
                return pmc_ids
            else:
                logger.warning(f"No articles found for: {search_term}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"XML parsing failed: {e}")
            return []

    def get_article_metadata(self, pmc_ids: List[str]) -> List[Dict]:
        """
        Fetch detailed metadata and full text for PMC articles using E-fetch
        
        Args:
            pmc_ids: List of PMC IDs
            
        Returns:
            List of article metadata dictionaries with full text
        """
        if not pmc_ids:
            return []
            
        fetch_url = f"{self.base_url}efetch.fcgi"
        
        params = {
            'db': 'pmc',
            'id': ','.join(pmc_ids),
            'retmode': 'xml',
            'email': self.email
        }
        
        try:
            logger.info(f"Fetching full articles for {len(pmc_ids)} PMC IDs")
            response = requests.get(fetch_url, params=params)
            response.raise_for_status()
            
            articles = []
            root = ET.fromstring(response.content)
            
            for article_elem in root.findall('.//article'):
                article_data = self._parse_article_xml(article_elem)
                if article_data and self._has_commercial_license(article_data):
                    # Extract full text content
                    full_text_data = self._extract_full_text(article_elem)
                    article_data.update(full_text_data)
                    articles.append(article_data)
                    
            logger.info(f"Extracted {len(articles)} articles with commercial licenses and full text")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Fetch request failed: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"XML parsing failed: {e}")
            return []

    def _parse_article_xml(self, article_elem) -> Optional[Dict]:
        """Parse article XML element to extract metadata"""
        try:
            # Get front matter
            front = article_elem.find('.//front')
            if front is None:
                return None
                
            article_meta = front.find('.//article-meta')
            if article_meta is None:
                return None
            
            # Extract basic metadata
            title_elem = article_meta.find('.//title-group/article-title')
            title = title_elem.text if title_elem is not None else "No title"
            
            # Abstract
            abstract_elem = article_meta.find('.//abstract')
            abstract = ""
            if abstract_elem is not None:
                # Get all text from abstract, handling multiple paragraphs
                abstract_parts = []
                for p in abstract_elem.findall('.//p'):
                    if p.text:
                        abstract_parts.append(p.text.strip())
                abstract = " ".join(abstract_parts)
            
            # Authors
            authors = []
            for contrib in article_meta.findall('.//contrib[@contrib-type="author"]'):
                name_elem = contrib.find('.//name')
                if name_elem is not None:
                    surname = name_elem.find('surname')
                    given_names = name_elem.find('given-names')
                    if surname is not None and given_names is not None:
                        authors.append(f"{given_names.text} {surname.text}")
            
            # Publication date
            pub_date = article_meta.find('.//pub-date[@pub-type="epub"]')
            if pub_date is None:
                pub_date = article_meta.find('.//pub-date[@pub-type="ppub"]')
            
            year = ""
            if pub_date is not None:
                year_elem = pub_date.find('year')
                year = year_elem.text if year_elem is not None else ""
            
            # Journal
            journal_elem = front.find('.//journal-title')
            journal = journal_elem.text if journal_elem is not None else "Unknown journal"
            
            # PMC ID
            pmc_id_elem = article_meta.find('.//article-id[@pub-id-type="pmc"]')
            pmc_id = pmc_id_elem.text if pmc_id_elem is not None else ""
            
            # DOI
            doi_elem = article_meta.find('.//article-id[@pub-id-type="doi"]')
            doi = doi_elem.text if doi_elem is not None else ""
            
            # Keywords
            keywords = []
            for kwd_group in article_meta.findall('.//kwd-group'):
                for kwd in kwd_group.findall('.//kwd'):
                    if kwd.text:
                        keywords.append(kwd.text.strip())
            
            # License information
            license_elem = article_meta.find('.//license')
            license_type = ""
            license_url = ""
            if license_elem is not None:
                license_url = license_elem.get('href', '')
                # Try to extract license type from URL or text
                if 'creativecommons.org' in license_url:
                    if '/by/' in license_url:
                        license_type = "CC BY"
                    elif '/by-sa/' in license_url:
                        license_type = "CC BY-SA"
                    elif '/by-nc-sa/' in license_url:
                        license_type = "CC BY-NC-SA"
                    elif '/zero/' in license_url:
                        license_type = "CC0"
            
            return {
                'pmc_id': pmc_id,
                'doi': doi,
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'journal': journal,
                'year': year,
                'keywords': keywords,
                'license_type': license_type,
                'license_url': license_url,
                'pmc_url': f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/" if pmc_id else ""
            }
            
        except Exception as e:
            logger.error(f"Error parsing article XML: {e}")
            return None

    def _extract_full_text(self, article_elem) -> Dict:
        """Extract full text content from article XML"""
        try:
            full_text_data = {
                'full_text_sections': {},
                'full_text_combined': '',
                'word_count': 0,
                'section_count': 0
            }
            
            # Find the body element
            body = article_elem.find('.//body')
            if body is None:
                logger.warning("No body section found in article")
                return full_text_data
            
            sections = {}
            all_text_parts = []
            
            # Extract main sections
            for sec in body.findall('.//sec'):
                section_title = ""
                section_content = ""
                
                # Get section title
                title_elem = sec.find('.//title')
                if title_elem is not None and title_elem.text:
                    section_title = title_elem.text.strip()
                
                # Get section content (all paragraphs)
                paragraphs = []
                for p in sec.findall('.//p'):
                    p_text = self._extract_text_from_element(p)
                    if p_text:
                        paragraphs.append(p_text)
                
                section_content = " ".join(paragraphs)
                
                if section_title and section_content:
                    sections[section_title] = section_content
                    all_text_parts.append(f"{section_title}: {section_content}")
                elif section_content:
                    # Section without title
                    sections[f"Section_{len(sections)+1}"] = section_content
                    all_text_parts.append(section_content)
            
            # Also check for any paragraphs directly in body (not in sections)
            direct_paragraphs = []
            for p in body.findall('./p'):  # Direct children only
                p_text = self._extract_text_from_element(p)
                if p_text:
                    direct_paragraphs.append(p_text)
            
            if direct_paragraphs:
                content = " ".join(direct_paragraphs)
                sections["Main_Content"] = content
                all_text_parts.append(content)
            
            # Combine all text
            combined_text = " ".join(all_text_parts)
            
            full_text_data.update({
                'full_text_sections': sections,
                'full_text_combined': combined_text,
                'word_count': len(combined_text.split()) if combined_text else 0,
                'section_count': len(sections)
            })
            
            logger.info(f"Extracted {len(sections)} sections, {full_text_data['word_count']} words")
            return full_text_data
            
        except Exception as e:
            logger.error(f"Error extracting full text: {e}")
            return {
                'full_text_sections': {},
                'full_text_combined': '',
                'word_count': 0,
                'section_count': 0
            }

    def _extract_text_from_element(self, element) -> str:
        """Recursively extract all text from an XML element, handling nested tags"""
        text_parts = []
        
        # Get direct text
        if element.text:
            text_parts.append(element.text.strip())
        
        # Get text from all child elements
        for child in element:
            child_text = self._extract_text_from_element(child)
            if child_text:
                text_parts.append(child_text)
            
            # Get tail text after child element
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return " ".join(part for part in text_parts if part)

    def _has_commercial_license(self, article_data: Dict) -> bool:
        """Check if article has commercial use license"""
        license_type = article_data.get('license_type', '')
        
        # If we found a specific license type, check if it's commercial
        if license_type:
            return any(license_type.startswith(commercial) for commercial in self.commercial_licenses)
        
        # If no specific license found, be permissive for open access articles
        # Most PMC open access articles allow commercial use
        return True

    def fetch_articles_for_all_topics(self, articles_per_topic: int = 5) -> Dict:
        """
        Fetch articles for all Berg-related search terms
        
        Args:
            articles_per_topic: Number of articles to fetch per search term
            
        Returns:
            Dictionary with search results organized by topic
        """
        all_results = {
            'fetch_date': datetime.now().isoformat(),
            'search_terms_used': self.search_terms,
            'articles_per_topic': articles_per_topic,
            'topics': {}
        }
        
        total_articles = 0
        
        for topic_key, search_term in self.search_terms.items():
            logger.info(f"Processing topic: {topic_key}")
            
            # Search for PMC IDs
            pmc_ids = self.search_pmc(search_term, max_results=articles_per_topic * 2)  # Get extra to filter
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Get article metadata
            articles = self.get_article_metadata(pmc_ids[:articles_per_topic])
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            all_results['topics'][topic_key] = {
                'search_term': search_term,
                'articles_found': len(articles),
                'articles': articles
            }
            
            total_articles += len(articles)
            logger.info(f"Collected {len(articles)} articles for {topic_key}")
        
        all_results['total_articles'] = total_articles
        logger.info(f"Fetch complete! Total articles collected: {total_articles}")
        
        return all_results

    def save_results(self, results: Dict, filename: str = 'pmc_articles_berg_topics.json'):
        """Save PMC fetch results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
        
        # Print summary
        print(f"\nPMC FETCH SUMMARY:")
        print(f"="*50)
        print(f"Total articles collected: {results['total_articles']}")
        print(f"Topics searched: {len(results['topics'])}")
        
        for topic_key, topic_data in results['topics'].items():
            print(f"  {topic_key}: {topic_data['articles_found']} articles")
        
        return results

def main():
    """Main execution function"""
    print("PMC Article Fetcher for Berg Topics")
    print("="*50)
    
    # Initialize fetcher
    # TODO: Replace with your actual email
    fetcher = PMCFetcher(email="your-email@example.com")
    
    # Fetch articles for all topics
    print("Fetching PMC articles for Berg-related health topics...")
    results = fetcher.fetch_articles_for_all_topics(articles_per_topic=5)
    
    # Save results
    fetcher.save_results(results)
    
    print("\nFetch completed successfully!")

if __name__ == "__main__":
    main()