#!/usr/bin/env python3
"""
Test script for PMC fetcher - single search term
"""

from pmc_fetcher import PMCFetcher
import json

def test_single_search():
    print("Testing PMC Fetcher with single search term")
    print("="*50)
    
    # Initialize fetcher
    fetcher = PMCFetcher(email="test@example.com")
    
    # Test with one search term
    test_term = "vitamin D deficiency"
    print(f"Testing search term: {test_term}")
    
    # Search for articles
    pmc_ids = fetcher.search_pmc(test_term, max_results=2)
    print(f"Found PMC IDs: {pmc_ids}")
    
    if pmc_ids:
        # Get full articles
        articles = fetcher.get_article_metadata(pmc_ids)
        print(f"Retrieved {len(articles)} full articles")
        
        # Show sample data
        if articles:
            article = articles[0]
            print(f"\nSample Article:")
            print(f"Title: {article['title']}")
            print(f"Journal: {article['journal']}")
            print(f"Year: {article['year']}")
            print(f"Authors: {', '.join(article['authors'][:3])}...")
            print(f"Word count: {article.get('word_count', 0)}")
            print(f"Sections: {article.get('section_count', 0)}")
            print(f"Abstract: {article['abstract'][:200]}...")
            
            if article.get('full_text_sections'):
                print(f"\nSection titles:")
                for title in article['full_text_sections'].keys():
                    print(f"  - {title}")
            
            # Save test results
            with open('test_pmc_result.json', 'w') as f:
                json.dump(articles, f, indent=2)
            print(f"\nTest results saved to test_pmc_result.json")
    
    else:
        print("No articles found for test search term")

if __name__ == "__main__":
    test_single_search()