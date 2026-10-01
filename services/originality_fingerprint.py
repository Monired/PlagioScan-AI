"""
PlagioScan AI — Originality Fingerprint
Generates a stylistic fingerprint for the author.
"""
import re
import hashlib
from collections import Counter
from typing import Dict, Any

def generate_fingerprint(text: str) -> Dict[str, Any]:
    """
    Analyzes punctuation frequencies, average word lengths, and unique 
    structural choices to create a 'stylistic fingerprint'.
    """
    if not text.strip():
        return {'hash': '', 'metrics': {}}

    # 1. Punctuation usage
    punct = re.findall(r'[.,;:!?()\-"]', text)
    punct_counts = Counter(punct)
    total_punct = len(punct) or 1
    
    punct_freq = {k: round(v / total_punct, 3) for k, v in punct_counts.most_common(5)}
    
    # 2. Word lengths
    words = re.findall(r'\b\w+\b', text)
    lengths = [len(w) for w in words]
    avg_len = sum(lengths) / max(1, len(lengths))
    
    # 3. Create a deterministic string to hash
    fingerprint_str = f"avg_len:{round(avg_len,1)}|"
    for k, v in sorted(punct_freq.items()):
        fingerprint_str += f"{k}:{v}|"
        
    fp_hash = hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()[:12]
    
    return {
        'hash': fp_hash,
        'metrics': {
            'avg_word_length': round(avg_len, 2),
            'punctuation_style': punct_freq
        }
    }
