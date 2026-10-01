"""
PlagioScan AI — Research Depth
Analyzes depth of research through citation density and complexity.
"""
import re
from typing import Dict, Any

def analyze_research_depth(text: str) -> Dict[str, Any]:
    """
    Calculates a score for research depth based on vocabulary complexity,
    citation mentions, and factual density.
    """
    if not text.strip():
        return {'research_depth_score': 0.0}
        
    words = re.findall(r'\b\w+\b', text)
    if not words:
        return {'research_depth_score': 0.0}
        
    # Find citations e.g. [1], (Author, Year)
    citations = re.findall(r'(\[\d+\]|\([A-Za-z]+,\s*\d{4}\))', text)
    citation_density = len(citations) / (len(words) / 100) # per 100 words
    
    # Vocabulary complexity (words > 8 chars)
    complex_words = sum(1 for w in words if len(w) > 8)
    complexity_ratio = complex_words / len(words)
    
    # Calculate score
    score = (citation_density * 20) + (complexity_ratio * 200)
    
    return {
        'research_depth_score': round(min(100.0, max(0.0, score)), 1)
    }
