"""
PlagioScan AI — Multi-Algorithm Similarity Service
Implements: TF-IDF+Cosine, N-Gram, Jaccard, Fuzzy, Sentence-level.
Combines them into a weighted overall similarity score.
"""
import re
import math
from difflib import SequenceMatcher
from collections import Counter
from typing import List, Dict, Tuple


# ─── Text Preprocessing ─────────────────────────────────────────────────────
STOP_WORDS = {
    'a','an','the','and','or','but','in','on','at','to','for','of','with',
    'by','from','as','is','was','are','were','be','been','being','have','has',
    'had','do','does','did','will','would','could','should','may','might',
    'shall','can','this','that','these','those','i','you','he','she','it',
    'we','they','my','your','his','her','its','our','their','what','which',
    'who','whom','when','where','why','how','not','no','nor','so','yet',
    'both','either','neither','each','few','more','most','other','some',
    'such','into','than','then','there','about','above','after','before'
}


def tokenize(text: str, remove_stops: bool = True) -> List[str]:
    """Lowercase, remove punctuation, optionally remove stop words."""
    tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    if remove_stops:
        return [t for t in tokens if t not in STOP_WORDS]
    return tokens


def get_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sents if len(s.strip()) > 20]


def get_ngrams(tokens: List[str], n: int) -> List[Tuple]:
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


# ─── TF-IDF + Cosine ────────────────────────────────────────────────────────
def _tfidf_cosine(text1: str, text2: str) -> float:
    """Cosine similarity using manual TF-IDF (no sklearn dependency required)."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1)
        tfidf = vec.fit_transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(score) * 100, 2)
    except ImportError:
        return _manual_cosine(text1, text2)
    except Exception:
        return _manual_cosine(text1, text2)


def _manual_cosine(text1: str, text2: str) -> float:
    """Fallback manual cosine similarity using TF."""
    t1 = Counter(tokenize(text1))
    t2 = Counter(tokenize(text2))
    if not t1 or not t2:
        return 0.0
    vocab = set(t1) | set(t2)
    v1 = [t1.get(w, 0) for w in vocab]
    v2 = [t2.get(w, 0) for w in vocab]
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return round((dot / (mag1 * mag2)) * 100, 2)


# ─── N-Gram Similarity ──────────────────────────────────────────────────────
def _ngram_similarity(text1: str, text2: str, n: int = 3) -> float:
    """Overlap of n-grams between two texts (character-level trigrams)."""
    if not text1 or not text2:
        return 0.0
    ng1 = set(get_ngrams(list(text1.lower()), n))
    ng2 = set(get_ngrams(list(text2.lower()), n))
    if not ng1 or not ng2:
        return 0.0
    overlap = len(ng1 & ng2)
    return round((2.0 * overlap / (len(ng1) + len(ng2))) * 100, 2)


# ─── Jaccard Similarity ─────────────────────────────────────────────────────
def _jaccard(text1: str, text2: str) -> float:
    """Word-level Jaccard similarity."""
    s1 = set(tokenize(text1))
    s2 = set(tokenize(text2))
    if not s1 or not s2:
        return 0.0
    intersection = s1 & s2
    union = s1 | s2
    return round(len(intersection) / len(union) * 100, 2)


# ─── Fuzzy Matching ─────────────────────────────────────────────────────────
def _fuzzy(text1: str, text2: str) -> float:
    """SequenceMatcher ratio (handles minor edits, paraphrasing)."""
    if not text1 or not text2:
        return 0.0
    # Truncate to 5000 chars for performance
    t1 = text1[:5000]
    t2 = text2[:5000]
    ratio = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
    return round(ratio * 100, 2)


# ─── Sentence-Level Matching ────────────────────────────────────────────────
def sentence_level_matches(text1: str, text2: str,
                            threshold: float = 55.0) -> List[Dict]:
    """
    Compare each sentence of text1 against all sentences of text2.
    Returns list of matching sentence pairs with scores.
    """
    sents1 = get_sentences(text1)
    sents2 = get_sentences(text2)
    matches = []

    for i, s1 in enumerate(sents1):
        best_score = 0.0
        best_match = ''
        for s2 in sents2:
            # Use quick fuzzy for sentence comparison
            score = _fuzzy(s1, s2)
            if score > best_score:
                best_score = score
                best_match = s2
        if best_score >= threshold:
            matches.append({
                'sentence':    s1,
                'match':       best_match,
                'score':       best_score,
                'index':       i,
            })

    return matches


# ─── Combined Score ──────────────────────────────────────────────────────────
WEIGHTS = {
    'tfidf':   0.40,
    'ngram':   0.20,
    'jaccard': 0.15,
    'fuzzy':   0.25,
}


def compute_all_scores(text1: str, text2: str) -> Dict:
    """
    Compute all similarity algorithms and return a dict with individual
    scores plus a weighted combined score.
    """
    if not text1 or not text2:
        return {'tfidf': 0, 'ngram': 0, 'jaccard': 0, 'fuzzy': 0, 'combined': 0}

    scores = {
        'tfidf':   _tfidf_cosine(text1, text2),
        'ngram':   _ngram_similarity(text1, text2),
        'jaccard': _jaccard(text1, text2),
        'fuzzy':   _fuzzy(text1, text2),
    }
    scores['combined'] = round(
        sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 2
    )
    return scores


def compute_similarity(text1: str, text2: str) -> float:
    """Quick combined similarity score (0–100)."""
    return compute_all_scores(text1, text2)['combined']


# ─── Highlight Generator ─────────────────────────────────────────────────────
def generate_highlighted_html(original_text: str,
                               matched_sentences: List[Dict]) -> str:
    """
    Build HTML where matched sentences are wrapped in colored spans.
    Colors:
      score ≥ 80  → red     (critical)
      score ≥ 60  → orange  (high)
      score ≥ 40  → yellow  (moderate)
      score ≥ 25  → green   (low)
    """
    if not original_text:
        return ''

    # Build a map: sentence_text → color class
    highlight_map: Dict[str, str] = {}
    for m in matched_sentences:
        s = m.get('sentence', '').strip()
        sc = m.get('score', 0)
        if sc >= 80:   cls = 'hl-red'
        elif sc >= 60: cls = 'hl-orange'
        elif sc >= 40: cls = 'hl-yellow'
        else:          cls = 'hl-green'
        if s:
            highlight_map[s] = (cls, sc)

    # Escape HTML chars in original text first
    import html as html_mod
    safe_text = html_mod.escape(original_text)

    # Replace matched sentences with highlighted spans
    for sentence, (cls, sc) in sorted(highlight_map.items(),
                                       key=lambda x: -len(x[0])):
        safe_sent = html_mod.escape(sentence)
        tooltip   = f'Similarity: {sc:.1f}%'
        replacement = (f'<mark class="{cls}" data-score="{sc:.1f}" '
                       f'title="{tooltip}">{safe_sent}</mark>')
        safe_text = safe_text.replace(safe_sent, replacement, 1)

    # Convert newlines to HTML breaks
    safe_text = safe_text.replace('\n\n', '</p><p>')
    return f'<p>{safe_text}</p>'
