"""
PlagioScan AI — Core Plagiarism Orchestrator
Combines all services into a single analysis pipeline.
"""
import time
import logging
from typing import Dict, Any

from services.similarity import (
    compute_all_scores,
    sentence_level_matches,
    generate_highlighted_html,
)
from services.analysis_engine import run_full_analysis
from services.web_search import search_web_matches

logger = logging.getLogger('plagioscan')


def _generate_suggestions(ai: Dict, plag_score: float,
                           web_matches: list) -> list:
    """Generate actionable improvement suggestions."""
    sugg = []

    # Plagiarism suggestions
    if plag_score >= 50:
        sugg.append('⚠️ High similarity detected — paraphrase flagged sections in your own words.')
        sugg.append('Add proper citations for all referenced information.')
    elif plag_score >= 20:
        sugg.append('Some similarity found — review highlighted sections and add citations where needed.')

    # Writing quality
    passive = ai.get('passive_voice_pct', 0)
    if passive >= 40:
        sugg.append(f'Reduce passive voice usage (currently {passive:.0f}%) — use active voice for clarity.')
    elif passive >= 25:
        sugg.append(f'Consider reducing passive voice ({passive:.0f}%) for a stronger academic tone.')

    # Vocabulary
    vocab = ai.get('vocabulary_richness', 0)
    if vocab < 40:
        sugg.append('Vocabulary diversity is low — avoid repeating the same words; use synonyms.')
    elif vocab < 60:
        sugg.append('Consider diversifying your vocabulary to strengthen the writing.')

    # Readability
    read = ai.get('readability_score', 0)
    if read < 30:
        sugg.append('Text is very complex — simplify sentence structures for better readability.')
    elif read > 80:
        sugg.append('Text may be too simple for academic writing — use more precise academic language.')

    # Citations
    cit = ai.get('citations', {})
    if cit.get('count', 0) == 0:
        sugg.append('No citations detected — academic writing requires proper source referencing.')
    elif cit.get('score', 0) < 40:
        sugg.append('Citation quality is low — include more diverse and authoritative references.')

    # Academic vocabulary
    acad = ai.get('academic_vocab_score', 0)
    if acad < 30:
        sugg.append('Use more academic vocabulary to improve the scholarly tone of your writing.')

    # Contribution
    contrib = ai.get('contribution', {})
    if contrib.get('contribution_score', 0) < 30:
        sugg.append('Add more original analysis, opinions, and conclusions to increase contribution score.')

    # Repeated phrases
    rep = ai.get('repeated_phrases', [])
    if rep:
        phrases = [r['phrase'] for r in rep[:3]]
        sugg.append(f'Repeated phrases detected: "{", ".join(phrases)}" — vary your expression.')

    # AI indicator
    ai_ind = ai.get('ai_indicator', {})
    if ai_ind.get('probability', 0) >= 55:
        sugg.append('⚡ AI-assisted writing patterns detected — ensure content reflects your original voice.')

    # Duplicate paragraphs
    dups = ai.get('duplicate_paras', [])
    if dups:
        sugg.append(f'{len(dups)} duplicate/near-duplicate paragraph(s) found — remove repetition.')

    # Structure
    struct = ai.get('structure', {})
    if not struct.get('has_intro'):
        sugg.append('Add a clear Introduction section to improve document structure.')
    if not struct.get('has_conclusion'):
        sugg.append('Add a Conclusion section summarizing your findings and contributions.')
    if not struct.get('has_references'):
        sugg.append('Add a References/Bibliography section at the end of the document.')

    # Web matches
    if web_matches and len(web_matches) >= 3:
        sugg.append(f'{len(web_matches)} matching web sources found — review and cite them properly.')

    return sugg[:12]   # Max 12 suggestions


def run_plagiarism_analysis(text: str,
                             reference_text: str = '',
                             run_web_search: bool = True,
                             web_timeout: int = 8,
                             max_web_results: int = 5) -> Dict[str, Any]:
    """
    Full plagiarism analysis pipeline.

    Steps:
    1. Run AI feature analysis
    2. Compute similarity vs reference doc (if provided)
    3. Run web search plagiarism detection
    4. Generate highlighted HTML
    5. Compute final scores
    6. Generate improvement suggestions

    Returns a comprehensive result dict.
    """
    start_time = time.time()

    words = text.split()
    if len(words) < 30:
        return {'error': 'Document too short. Please upload at least 30 words.', 'status': 'error'}

    # ── Step 1: AI Analysis ──────────────────────────────────────────────────
    logger.info('Running AI analysis...')
    ai_features = run_full_analysis(text)

    # ── Step 2: Local Similarity ─────────────────────────────────────────────
    local_similarity = {}
    local_sentence_matches = []
    if reference_text and len(reference_text.split()) >= 20:
        logger.info('Computing local document similarity...')
        local_similarity = compute_all_scores(text, reference_text)
        local_sentence_matches = sentence_level_matches(text, reference_text, threshold=45.0)

    # ── Step 3: Web Search ───────────────────────────────────────────────────
    web_matches = []
    if run_web_search:
        logger.info('Running web plagiarism search...')
        try:
            web_matches = search_web_matches(
                text,
                max_sentences=max_web_results,
                max_results=max_web_results,
                timeout=web_timeout,
            )
        except Exception as e:
            logger.warning(f'Web search failed: {e}')
            web_matches = []

    # ── Step 4: Compute Overall Plagiarism Score ─────────────────────────────
    # Use web matches as the primary plagiarism signal; local as secondary
    web_plag  = max((m['similarity'] for m in web_matches), default=0.0)
    local_plag = local_similarity.get('combined', 0.0)

    if web_matches:
        # Average of top 3 web matches weighted more heavily
        top3 = sorted(web_matches, key=lambda m: -m['similarity'])[:3]
        web_plag_avg = sum(m['similarity'] for m in top3) / len(top3)
        overall_plag = max(web_plag_avg, local_plag)
    else:
        overall_plag = local_plag

    # ── Step 5: Generate Highlighted HTML ────────────────────────────────────
    all_sentence_matches = local_sentence_matches.copy()
    # Add web-matched sentences
    for wm in web_matches:
        if wm.get('matched_sentence') and wm.get('similarity', 0) >= 25:
            all_sentence_matches.append({
                'sentence': wm['matched_sentence'],
                'match':    wm.get('snippet', ''),
                'score':    wm['similarity'],
            })

    highlighted_html = generate_highlighted_html(text, all_sentence_matches)

    # ── Step 6: Compile Similarity Breakdown ────────────────────────────────
    if local_similarity:
        sim_breakdown = local_similarity
    elif web_matches:
        best = max(web_matches, key=lambda m: m['similarity'])
        sim_breakdown = {
            'tfidf':    best.get('tfidf', 0),
            'fuzzy':    best.get('fuzzy', 0),
            'combined': overall_plag,
            'ngram':    0, 'jaccard': 0,
        }
    else:
        sim_breakdown = {'tfidf': 0, 'ngram': 0, 'jaccard': 0, 'fuzzy': 0, 'combined': 0}

    # ── Step 7: Final Scores ──────────────────────────────────────────────────
    originality  = round(max(0.0, 100.0 - overall_plag), 1)
    contrib_d    = ai_features.get('contribution', {})
    citations_d  = ai_features.get('citations', {})
    struct_d     = ai_features.get('structure', {})

    writing_quality  = round(ai_features.get('writing_quality', 0.0), 1)
    research_depth   = round(ai_features.get('research_depth', 0.0), 1)
    contribution     = round(contrib_d.get('contribution_score', 0.0), 1)
    readability      = round(ai_features.get('readability_score', 0.0), 1)
    vocab_score      = round(ai_features.get('vocabulary_score', 0.0), 1)
    academic_score   = round((
        writing_quality  * 0.25 +
        research_depth   * 0.25 +
        originality      * 0.20 +
        contribution     * 0.15 +
        citations_d.get('score', 0) * 0.15
    ), 1)
    grammar_score    = round(ai_features.get('grammar_score', 0.0), 1)
    citation_score   = round(citations_d.get('score', 0.0), 1)

    # ── Step 8: Suggestions ───────────────────────────────────────────────────
    suggestions = _generate_suggestions(ai_features, overall_plag, web_matches)

    # ── Step 9: Per-sentence scores ───────────────────────────────────────────
    sentence_scores = [
        {
            'sentence': m.get('sentence', '')[:150],
            'score':    m.get('score', 0),
            'match':    m.get('match', '')[:150],
        }
        for m in sorted(all_sentence_matches, key=lambda x: -x.get('score', 0))[:20]
    ]

    processing_time = round(time.time() - start_time, 2)
    logger.info(f'Analysis complete in {processing_time}s | Plagiarism: {overall_plag:.1f}%')

    return {
        'status': 'done',
        'processing_time': processing_time,

        # Core scores
        'plagiarism_score':      round(overall_plag, 1),
        'originality_score':     originality,
        'writing_quality_score': writing_quality,
        'research_depth_score':  research_depth,
        'contribution_score':    contribution,
        'readability_score':     readability,
        'vocabulary_score':      vocab_score,
        'academic_score':        academic_score,
        'grammar_score':         grammar_score,
        'citation_score':        citation_score,

        # Detailed data (JSON-serializable)
        'similarity_breakdown':    sim_breakdown,
        'style_analysis':          {
            'avg_sentence_length':  ai_features.get('structure', {}).get('avg_para_length', 0),
            'vocabulary_richness':  ai_features.get('vocabulary_richness', 0),
            'reading_ease':         ai_features.get('readability_ease', 0),
            'fk_grade':             ai_features.get('fk_grade_level', 0),
            'passive_voice_pct':    ai_features.get('passive_voice_pct', 0),
            'tone':                 ai_features.get('tone', {}),
            'word_count':           len(words),
            'sentence_count':       ai_features.get('structure', {}).get('sentence_count', 0),
            'paragraph_count':      ai_features.get('structure', {}).get('paragraph_count', 0),
        },
        'ai_features':             ai_features,
        'web_matches':             web_matches,
        'local_matches':           local_sentence_matches,
        'highlighted_html':        highlighted_html,
        'improvement_suggestions': suggestions,
        'sentence_scores':         sentence_scores,
    }
