"""
PlagioScan AI — AI Risk Detection
Uses heuristics to detect AI-generated text (low burstiness, uniform sentence length).
"""
import re
import math
from typing import Dict, Any
from services.similarity import get_sentences

def calculate_ai_risk(text: str) -> Dict[str, Any]:
    """
    Detect potential AI generation using sentence length variance (burstiness)
    and repetitive patterns.
    Returns score 0-100 (100 = Very high AI risk).
    """
    sents = get_sentences(text)
    if not sents or len(sents) < 3:
        return {'ai_risk_score': 0.0, 'burstiness': 0.0, 'flags': []}

    # 1. Burstiness (Sentence Length Variance)
    lengths = [len(s.split()) for s in sents]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # AI tends to have very consistent sentence lengths (low std_dev relative to mean)
    cv = std_dev / mean_len if mean_len > 0 else 0
    burstiness_score = min(100, cv * 100) # Higher = more human-like
    
    # 2. Over-used transitional phrases
    transitions = re.findall(
        r'\b(furthermore|moreover|additionally|in conclusion|to summarize|it is important to note|delve|testament|tapestry)\b', 
        text.lower()
    )
    transition_density = (len(transitions) / max(1, len(lengths))) * 100

    flags = []
    risk = 0.0
    
    if burstiness_score < 30:
        risk += 40
        flags.append("Low sentence variance (highly uniform).")
    elif burstiness_score < 45:
        risk += 20
        
    if transition_density > 15:
        risk += 30
        flags.append("High density of AI-typical transitional phrases.")
        
    if mean_len > 25:
        risk += 10
        
    risk = min(100.0, max(0.0, risk))
    
    return {
        'ai_risk_score': round(risk, 1),
        'burstiness': round(burstiness_score, 1),
        'flags': flags
    }
