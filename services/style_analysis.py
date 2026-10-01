"""
PlagioScan AI — Style Analysis
Extracts tone and passive voice analysis.
"""
import re
from typing import Dict, Any
from services.similarity import get_sentences

_PASSIVE_PATTERN = re.compile(
    r'\b(is|are|was|were|be|been|being|am)\s+'
    r'(being\s+)?'
    r'(\w+ed|written|done|seen|known|shown|given|taken|made|found|'
    r'used|said|told|shown|helped|created|developed|implemented|designed|'
    r'built|tested|analyzed|evaluated|studied|examined|discussed|presented)\b',
    re.IGNORECASE
)

def analyze_style(text: str) -> Dict[str, Any]:
    """Analyze passive voice and overall writing tone."""
    if not text.strip():
        return {'passive_voice_pct': 0.0, 'tone': 'Neutral'}
        
    sents = get_sentences(text)
    if not sents:
        return {'passive_voice_pct': 0.0, 'tone': 'Neutral'}
        
    passive_count = sum(1 for s in sents if _PASSIVE_PATTERN.search(s))
    passive_pct = round(passive_count / len(sents) * 100, 1)
    
    # Tone heuristics
    formal_words = len(re.findall(r'\b(furthermore|therefore|thus|hence|moreover|consequently|analyze|determine|demonstrate)\b', text.lower()))
    informal_words = len(re.findall(r'\b(like|stuff|things|really|very|good|bad|maybe|probably)\b', text.lower()))
    
    tone = 'Neutral'
    if formal_words > informal_words * 2:
        tone = 'Academic/Formal'
    elif informal_words > formal_words:
        tone = 'Informal/Casual'
        
    return {
        'passive_voice_pct': passive_pct,
        'tone': tone
    }
