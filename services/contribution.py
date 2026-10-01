"""
PlagioScan AI — Intellectual Contribution
Analyzes the original value added beyond citations.
"""
import re
from typing import Dict, Any

def analyze_contribution(text: str) -> Dict[str, Any]:
    """
    Measures intellectual contribution by evaluating the ratio of original 
    analytical phrases to cited/quoted text.
    """
    if not text.strip():
        return {'contribution_score': 0.0, 'insight_density': 0.0}
        
    # Find quotes
    quotes = re.findall(r'"([^"]*)"', text)
    quote_words = sum(len(q.split()) for q in quotes)
    
    total_words = len(re.findall(r'\b\w+\b', text))
    if total_words == 0:
        return {'contribution_score': 0.0, 'insight_density': 0.0}
        
    # Find analytical markers
    markers = re.findall(
        r'\b(argue|propose|suggest|conclude|demonstrate|show|illustrate|'
        r'indicate|prove|analyze|evaluate|interpret|therefore|however|'
        r'conversely|in contrast|our results|this study|we found)\b',
        text.lower()
    )
    
    insight_density = (len(markers) / total_words) * 100
    
    # Base score
    score = min(100.0, insight_density * 15)
    
    # Penalize if the text is entirely quotes
    quote_ratio = quote_words / total_words
    if quote_ratio > 0.4:
        score -= (quote_ratio - 0.4) * 100
        
    return {
        'contribution_score': round(max(0.0, score), 1),
        'insight_density': round(insight_density, 2)
    }
