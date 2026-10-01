"""
PlagioScan AI — Unit Tests: Similarity Algorithms
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestTokenize:
    def test_basic(self):
        from services.similarity import tokenize
        tokens = tokenize("The quick brown fox jumps over the lazy dog")
        assert isinstance(tokens, list)
        assert 'quick' in tokens
        assert 'the' not in tokens  # stop word removed

    def test_empty(self):
        from services.similarity import tokenize
        assert tokenize("") == []


class TestTFIDFCosine:
    def test_identical(self):
        from services.similarity import _tfidf_cosine
        score = _tfidf_cosine("hello world test document", "hello world test document")
        assert score >= 95.0

    def test_empty(self):
        from services.similarity import _tfidf_cosine
        assert _tfidf_cosine("", "hello") == 0.0

    def test_different(self):
        from services.similarity import _tfidf_cosine
        score = _tfidf_cosine("apple orange banana fruit",
                               "car truck road vehicle engine")
        assert score < 20.0


class TestJaccard:
    def test_identical(self):
        from services.similarity import _jaccard
        assert _jaccard("hello world", "hello world") == 100.0

    def test_disjoint(self):
        from services.similarity import _jaccard
        assert _jaccard("alpha beta gamma", "delta epsilon zeta") == 0.0

    def test_partial(self):
        from services.similarity import _jaccard
        score = _jaccard("hello world foo", "hello world bar")
        assert 0 < score < 100


class TestNGram:
    def test_identical(self):
        from services.similarity import _ngram_similarity
        score = _ngram_similarity("hello world foo bar", "hello world foo bar")
        assert score >= 95.0

    def test_empty(self):
        from services.similarity import _ngram_similarity
        assert _ngram_similarity("", "hello") == 0.0


class TestComputeAllScores:
    def test_returns_dict(self):
        from services.similarity import compute_all_scores
        result = compute_all_scores(
            "The quick brown fox jumps over the lazy dog",
            "The quick brown fox jumps over the lazy dog"
        )
        assert isinstance(result, dict)
        assert 'tfidf' in result
        assert 'combined' in result

    def test_scores_in_range(self):
        from services.similarity import compute_all_scores
        result = compute_all_scores("foo bar baz", "hello world test")
        for key, val in result.items():
            assert 0.0 <= val <= 100.0, f"{key}={val} out of range"
