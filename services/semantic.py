"""
PlagioScan AI — Semantic Similarity Service
Uses sentence-transformers (all-MiniLM-L6-v2) for deep semantic comparison.
Falls back gracefully to TF-IDF cosine if model unavailable.
Model downloads ~90 MB on first use (automatic, cached).
"""
import logging
from typing import List, Tuple

logger = logging.getLogger('plagioscan')

_model = None          # Lazy-loaded singleton
_model_attempted = False


def _load_model():
    """Lazy-load sentence-transformer model once."""
    global _model, _model_attempted
    if _model_attempted:
        return _model
    _model_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        logger.info('[Semantic] Loading all-MiniLM-L6-v2…')
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info('[Semantic] Model ready.')
    except Exception as e:
        logger.warning(f'[Semantic] Model unavailable ({e}). Falling back to TF-IDF.')
        _model = None
    return _model


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two texts (0–100).
    Uses sentence embeddings if model available, else TF-IDF cosine fallback.
    """
    if not text1 or not text2:
        return 0.0

    model = _load_model()
    if model is None:
        return _tfidf_fallback(text1, text2)

    try:
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        embs = model.encode([text1[:4096], text2[:4096]], convert_to_numpy=True)
        score = float(cosine_similarity([embs[0]], [embs[1]])[0][0])
        return round(max(0.0, min(100.0, score * 100)), 2)
    except Exception as e:
        logger.warning(f'[Semantic] Inference error: {e}')
        return _tfidf_fallback(text1, text2)


def semantic_sentence_scores(text: str, reference: str,
                              threshold: float = 30.0) -> List[dict]:
    """
    Return per-sentence semantic similarity scores against a reference.
    Each result: {sentence, score, is_match}
    """
    from services.similarity import get_sentences
    model = _load_model()
    sentences = get_sentences(text)
    if not sentences or not reference:
        return []

    if model is None:
        return _sentence_tfidf_fallback(sentences, reference, threshold)

    try:
        from sklearn.metrics.pairwise import cosine_similarity
        ref_emb  = model.encode([reference[:4096]], convert_to_numpy=True)
        sent_embs = model.encode(sentences[:50], convert_to_numpy=True, batch_size=32)
        results = []
        for sent, emb in zip(sentences[:50], sent_embs):
            score = float(cosine_similarity([emb], ref_emb)[0][0]) * 100
            results.append({
                'sentence': sent[:250],
                'score':    round(score, 1),
                'is_match': score >= threshold,
                'match':    reference[:150] if score >= threshold else '',
            })
        return results
    except Exception as e:
        logger.warning(f'[Semantic] Sentence scoring error: {e}')
        return _sentence_tfidf_fallback(sentences, reference, threshold)


def is_semantic_available() -> bool:
    """Check if sentence-transformers model is loaded."""
    model = _load_model()
    return model is not None


# ── Fallbacks ──────────────────────────────────────────────────────────────
def _tfidf_fallback(text1: str, text2: str) -> float:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec   = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf = vec.fit_transform([text1, text2])
        return round(float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]) * 100, 2)
    except Exception:
        return 0.0


def _sentence_tfidf_fallback(sentences: List[str], reference: str,
                              threshold: float) -> List[dict]:
    results = []
    for sent in sentences[:50]:
        score = _tfidf_fallback(sent, reference[:1000])
        results.append({
            'sentence': sent[:250],
            'score':    score,
            'is_match': score >= threshold,
            'match':    reference[:150] if score >= threshold else '',
        })
    return results
