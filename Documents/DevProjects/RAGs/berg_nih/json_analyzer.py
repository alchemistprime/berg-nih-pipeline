#!/usr/bin/env python3
"""
JSON Data Analyzer for Dr. Berg Video Data
Extracts additional insights and patterns from our exploration data
"""

import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any

class BergDataAnalyzer:
    def __init__(self, data_file: str = 'berg_exploration_with_transcripts_v2.json'):
        self.data_file = data_file
        self.data = self.load_data()
        
    def load_data(self) -> Dict:
        """Load the exploration data"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.data_file} not found")
            return {}
    
    def extract_symptom_keywords(self) -> Dict[str, int]:
        """Extract symptom-related keywords from titles and descriptions"""
        symptom_keywords = [
            'pain', 'fatigue', 'tired', 'cramps', 'headache', 'migraine',
            'nausea', 'bloating', 'constipation', 'diarrhea', 'insomnia',
            'depression', 'anxiety', 'stress', 'inflammation', 'swelling',
            'rash', 'dry', 'itchy', 'burning', 'numbness', 'tingling',
            'weakness', 'dizziness', 'vertigo', 'blurred', 'vision',
            'hair loss', 'thinning', 'brittle', 'cough', 'shortness',
            'breathing', 'heart', 'palpitations', 'tremors', 'shaking',
            'numb', 'pins', 'needles', 'sciatica', 'arthritis',
            'joint', 'muscle', 'bone', 'back', 'neck', 'shoulder'
        ]
        
        symptom_counts = Counter()
        
        for video in self.data.get('videos', []):
            text = f"{video['title']} {video['description']}".lower()
            
            for symptom in symptom_keywords:
                count = text.count(symptom)
                if count > 0:
                    symptom_counts[symptom] += count
        
        return dict(symptom_counts.most_common(20))
    
    def extract_body_systems(self) -> Dict[str, int]:
        """Extract body system references"""
        body_systems = {
            'digestive': ['stomach', 'gut', 'intestine', 'colon', 'liver', 'gallbladder', 'pancreas', 'digestion', 'bile'],
            'nervous': ['brain', 'nerve', 'nervous', 'neurological', 'cognitive', 'memory', 'focus'],
            'cardiovascular': ['heart', 'blood', 'circulation', 'pressure', 'cholesterol', 'arterial'],
            'endocrine': ['thyroid', 'hormone', 'insulin', 'diabetes', 'cortisol', 'adrenal'],
            'immune': ['immune', 'autoimmune', 'inflammation', 'infection', 'allergy'],
            'musculoskeletal': ['bone', 'joint', 'muscle', 'arthritis', 'osteoporosis', 'calcium'],
            'respiratory': ['lung', 'breathing', 'asthma', 'respiratory', 'oxygen'],
            'integumentary': ['skin', 'hair', 'nail', 'rash', 'eczema', 'psoriasis']
        }
        
        system_counts = defaultdict(int)
        
        for video in self.data.get('videos', []):
            text = f"{video['title']} {video['description']}".lower()
            
            for system, keywords in body_systems.items():
                for keyword in keywords:
                    system_counts[system] += text.count(keyword)
        
        return dict(system_counts)
    
    def extract_nutrients_and_supplements(self) -> Dict[str, int]:
        """Extract nutrient and supplement mentions"""
        nutrients = [
            'vitamin d', 'vitamin d3', 'vitamin c', 'vitamin b12', 'vitamin b1', 'vitamin b2', 
            'vitamin b6', 'vitamin b3', 'vitamin a', 'vitamin e', 'vitamin k', 'vitamin k2',
            'thiamine', 'riboflavin', 'niacin', 'folate', 'biotin',
            'magnesium', 'zinc', 'iron', 'calcium', 'potassium', 'selenium',
            'omega 3', 'omega-3', 'fish oil', 'probiotics', 'fiber',
            'coq10', 'collagen', 'turmeric', 'curcumin', 'berberine',
            'betaine', 'hcl', 'digestive enzymes', 'electrolytes'
        ]
        
        nutrient_counts = Counter()
        
        for video in self.data.get('videos', []):
            text = f"{video['title']} {video['description']}".lower()
            
            for nutrient in nutrients:
                count = text.count(nutrient)
                if count > 0:
                    nutrient_counts[nutrient] += count
        
        return dict(nutrient_counts.most_common(20))
    
    def analyze_content_patterns(self) -> Dict[str, Any]:
        """Analyze content patterns and structures"""
        patterns = {
            'question_titles': 0,
            'numbered_lists': 0,
            'warning_words': 0,
            'solution_focused': 0,
            'symptom_focused': 0
        }
        
        warning_words = ['warning', 'danger', 'never', 'avoid', 'stop', 'deadly', 'toxic']
        solution_words = ['best', 'top', 'fix', 'cure', 'heal', 'solution', 'remedy']
        symptom_words = ['signs', 'symptoms', 'warning signs', 'indicators']
        
        for video in self.data.get('videos', []):
            title = video['title'].lower()
            
            # Question titles
            if '?' in title:
                patterns['question_titles'] += 1
            
            # Numbered lists
            if re.search(r'\b\d+\b', title):
                patterns['numbered_lists'] += 1
            
            # Warning content
            if any(word in title for word in warning_words):
                patterns['warning_words'] += 1
            
            # Solution focused
            if any(word in title for word in solution_words):
                patterns['solution_focused'] += 1
            
            # Symptom focused
            if any(word in title for word in symptom_words):
                patterns['symptom_focused'] += 1
        
        return patterns
    
    def extract_dosage_and_recommendations(self) -> List[Dict]:
        """Extract any dosage or specific recommendations from descriptions"""
        dosage_patterns = [
            r'(\d+)\s*(mg|mcg|iu|units?)\s*(daily|per day|twice daily)',
            r'take\s*(\d+)\s*(mg|mcg|iu|units?)',
            r'(\d+)\s*to\s*(\d+)\s*(mg|mcg|iu|units?)',
            r'(\d+)\s*(mg|mcg|iu|units?)\s*of\s*([a-zA-Z\s]+)',
        ]
        
        recommendations = []
        
        for video in self.data.get('videos', []):
            text = f"{video['title']} {video['description']}"
            
            for pattern in dosage_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    recommendations.append({
                        'video_id': video['video_id'],
                        'title': video['title'],
                        'dosage_info': match,
                        'pattern': pattern
                    })
        
        return recommendations
    
    def analyze_engagement_vs_content(self) -> Dict[str, Any]:
        """Analyze relationship between content type and engagement"""
        content_engagement = {
            'deficiency_videos': [],
            'symptom_videos': [],
            'solution_videos': [],
            'warning_videos': []
        }
        
        for video in self.data.get('videos', []):
            title = video['title'].lower()
            stats = video.get('statistics', {})
            engagement = stats.get('engagement_rate', 0)
            views = stats.get('view_count', 0)
            
            video_data = {
                'title': video['title'],
                'views': views,
                'engagement': engagement
            }
            
            if 'deficiency' in title or 'deficient' in title:
                content_engagement['deficiency_videos'].append(video_data)
            elif any(word in title for word in ['signs', 'symptoms', 'warning']):
                content_engagement['symptom_videos'].append(video_data)
            elif any(word in title for word in ['best', 'top', 'fix', 'cure']):
                content_engagement['solution_videos'].append(video_data)
            elif any(word in title for word in ['never', 'danger', 'warning', 'avoid']):
                content_engagement['warning_videos'].append(video_data)
        
        # Calculate averages
        analysis = {}
        for category, videos in content_engagement.items():
            if videos:
                avg_engagement = sum(v['engagement'] for v in videos) / len(videos)
                avg_views = sum(v['views'] for v in videos) / len(videos)
                analysis[category] = {
                    'count': len(videos),
                    'avg_engagement': round(avg_engagement, 2),
                    'avg_views': int(avg_views),
                    'top_performer': max(videos, key=lambda x: x['views'])
                }
        
        return analysis
    
    def generate_comprehensive_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive analysis of all patterns"""
        print("Analyzing Dr. Berg video data patterns...")
        
        analysis = {
            'dataset_overview': {
                'total_videos': len(self.data.get('videos', [])),
                'total_views': self.data.get('summary_stats', {}).get('total_views', 0),
                'avg_engagement': self.data.get('summary_stats', {}).get('avg_engagement_rate', 0)
            },
            'symptom_keywords': self.extract_symptom_keywords(),
            'body_systems': self.extract_body_systems(),
            'nutrients_supplements': self.extract_nutrients_and_supplements(),
            'content_patterns': self.analyze_content_patterns(),
            'dosage_recommendations': self.extract_dosage_and_recommendations(),
            'engagement_analysis': self.analyze_engagement_vs_content()
        }
        
        return analysis
    
    def save_analysis(self, analysis: Dict, filename: str = 'berg_content_analysis.json'):
        """Save analysis to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"Analysis saved to {filename}")

def main():
    """Main execution"""
    print("Dr. Berg Content Analysis Tool")
    print("=" * 40)
    
    analyzer = BergDataAnalyzer()
    
    if not analyzer.data:
        print("No data to analyze. Run berg_explorer.py first.")
        return
    
    # Generate comprehensive analysis
    analysis = analyzer.generate_comprehensive_analysis()
    
    # Save analysis
    analyzer.save_analysis(analysis)
    
    # Print key insights
    print(f"\nKEY INSIGHTS:")
    print(f"-" * 20)
    print(f"Total videos analyzed: {analysis['dataset_overview']['total_videos']}")
    print(f"Total views: {analysis['dataset_overview']['total_views']:,}")
    
    print(f"\nTop Symptoms Mentioned:")
    for symptom, count in list(analysis['symptom_keywords'].items())[:5]:
        print(f"  {symptom}: {count} mentions")
    
    print(f"\nTop Body Systems:")
    for system, count in sorted(analysis['body_systems'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {system}: {count} mentions")
    
    print(f"\nTop Nutrients/Supplements:")
    for nutrient, count in list(analysis['nutrients_supplements'].items())[:5]:
        print(f"  {nutrient}: {count} mentions")
    
    print(f"\nContent Pattern Analysis:")
    patterns = analysis['content_patterns']
    print(f"  Question titles: {patterns['question_titles']}")
    print(f"  Numbered lists: {patterns['numbered_lists']}")
    print(f"  Solution-focused: {patterns['solution_focused']}")
    print(f"  Symptom-focused: {patterns['symptom_focused']}")

if __name__ == "__main__":
    main()