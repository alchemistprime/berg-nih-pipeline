#!/usr/bin/env python3
"""
Convert PMC titles JSON to CSV for easier manual review
"""

import json
import csv
from datetime import datetime

def convert_pmc_json_to_csv(json_file: str, csv_file: str):
    """Convert PMC titles JSON to CSV format"""
    
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Prepare CSV data
    csv_rows = []
    
    for search_term, results in data['search_results'].items():
        for article in results['articles']:
            row = {
                'search_term': search_term,
                'pmc_id': article.get('pmc_id', ''),
                'title': article.get('title', ''),
                'authors': '; '.join(article.get('authors', [])),
                'journal': article.get('journal', ''),
                'year': article.get('year', ''),
                'doi': article.get('doi', ''),
                'pmc_url': article.get('pmc_url', ''),
                'selected_for_full_text': article.get('selected_for_full_text', False)
            }
            csv_rows.append(row)
    
    # Write CSV file
    fieldnames = [
        'search_term', 'pmc_id', 'title', 'authors', 'journal', 
        'year', 'doi', 'pmc_url', 'selected_for_full_text'
    ]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"Converted {len(csv_rows)} articles to {csv_file}")
    print(f"Columns: {', '.join(fieldnames)}")
    
    # Show summary by search term
    print(f"\nArticles by search term:")
    for search_term, results in data['search_results'].items():
        count = results['articles_found']
        print(f"  {search_term}: {count} articles")

if __name__ == "__main__":
    convert_pmc_json_to_csv('pmc_titles_for_review.json', 'pmc_titles_for_review.csv')