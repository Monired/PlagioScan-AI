"""
PlagioScan AI — Grammar & Mechanics Analysis
Basic heuristics for grammar, capitalization, and punctuation checking.
"""
import re
from typing import Dict, Any
from services.similarity import get_sentences

def analyze_grammar(text: str) -> Dict[str, Any]:
    """
    Checks for common typographical, punctuation, and capitalization errors.
    Returns a score from 0-100.
    """
    if not text.strip():
        return {'grammar_score': 0.0, 'issues': []}
        
    sents = get_sentences(text)
    issues = []
    errors = 0
    
    # 1. Capitalization at start of sentence
    for s in sents:
        if s and s[0].islower():
            errors += 1
            issues.append(f"Lowercase start: '{s[:20]}...'")
            
    # 2. Multiple spaces
    if re.search(r' {3,}', text):
        errors += 2
        issues.append("Multiple consecutive spaces detected.")
        
    # 3. Punctuation spacing (e.g. "word , word")
    if re.search(r'\s+[,.;:!?]', text):
        errors += 1
        issues.append("Space before punctuation detected.")
        
    # 4. Repeated punctuation
    if re.search(r'[!?.]{4,}', text):
        errors += 1
        issues.append("Excessive repeated punctuation.")
        
    # 5. Missing space after punctuation (e.g. "word.Word")
    if re.search(r'[.,;:!?][A-Za-z]', text):
        errors += 2
        issues.append("Missing space after punctuation.")

    base_score = 100.0
    penalty = (errors / max(1, len(sents))) * 20  # scale penalty
    
    final_score = max(0.0, base_score - penalty)
    
    return {
        'grammar_score': round(final_score, 1),
        'issues': list(set(issues))[:5]
    }
