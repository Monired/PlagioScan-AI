"""
PlagioScan AI — Draft Compare
Compares two documents to find additions, deletions, and modifications.
"""
from difflib import SequenceMatcher
from typing import Dict, Any
from services.similarity import tokenize

def compare_drafts(old_text: str, new_text: str) -> Dict[str, Any]:
    """
    Compares two drafts and returns a similarity score and change metrics.
    """
    if not old_text and not new_text:
        return {'similarity': 100.0, 'changes': 'None'}
        
    old_tokens = tokenize(old_text, remove_stops=False)
    new_tokens = tokenize(new_text, remove_stops=False)
    
    sm = SequenceMatcher(None, old_tokens, new_tokens)
    ratio = sm.ratio()
    
    # Rough estimate of additions/deletions based on token length diff
    added = max(0, len(new_tokens) - len(old_tokens))
    deleted = max(0, len(old_tokens) - len(new_tokens))
    
    return {
        'similarity': round(ratio * 100, 1),
        'tokens_added': added,
        'tokens_deleted': deleted
    }
