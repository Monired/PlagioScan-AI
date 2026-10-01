"""
PlagioScan AI — Full Pipeline Test
Tests the entire background analysis pipeline synchronously.
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.similarity import tokenize, get_sentences, compute_all_scores
from services.ai_risk import calculate_ai_risk
from services.originality_fingerprint import generate_fingerprint
from services.grammar_analysis import analyze_grammar
from services.style_analysis import analyze_style
from services.contribution import analyze_contribution
from services.research_depth import analyze_research_depth

@pytest.fixture
def sample_text():
    return (
        "Artificial intelligence is rapidly transforming the modern world. "
        "Furthermore, many researchers argue that this technology will \"change everything\" we know about computing [1]. "
        "However, we must be careful with how we deploy these systems. They are being built by engineers who have tested them extensively. "
        "It is important to note that safety should be the primary concern. "
        "In conclusion, we propose a new framework for AI alignment that addresses these issues."
    )

def test_similarity_computation():
    doc_text = "The quick brown fox jumps over the lazy dog."
    ref_text = "A fast brown fox jumps over a sleeping dog."
    scores = compute_all_scores(doc_text, ref_text)
    
    assert 'tfidf' in scores
    assert 'ngram' in scores
    assert 'combined' in scores
    assert scores['combined'] > 10.0

def test_ai_risk(sample_text):
    risk_data = calculate_ai_risk(sample_text)
    assert 'ai_risk_score' in risk_data
    assert 'burstiness' in risk_data
    # Contains "Furthermore", "It is important to note", "In conclusion"
    assert risk_data['ai_risk_score'] > 20.0

def test_originality_fingerprint(sample_text):
    fp = generate_fingerprint(sample_text)
    assert 'hash' in fp
    assert len(fp['hash']) == 12
    assert 'avg_word_length' in fp['metrics']

def test_grammar_analysis():
    bad_text = "this is a Bad sentence .with multiple   spaces.and Missing spaces after punctuation."
    grammar_data = analyze_grammar(bad_text)
    assert grammar_data['grammar_score'] < 100.0
    assert len(grammar_data['issues']) > 0

def test_style_analysis(sample_text):
    style = analyze_style(sample_text)
    assert 'passive_voice_pct' in style
    assert 'tone' in style
    
def test_contribution_analysis(sample_text):
    contrib = analyze_contribution(sample_text)
    assert 'contribution_score' in contrib
    assert contrib['insight_density'] > 0

def test_research_depth(sample_text):
    depth = analyze_research_depth(sample_text)
    assert 'research_depth_score' in depth
    assert depth['research_depth_score'] > 0
