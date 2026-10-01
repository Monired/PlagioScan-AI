"""
PlagioScan AI — Background Job Runner
Threading-based background analysis — no Celery/Redis needed.
Jobs tracked in AnalysisJob DB table; UI polls /analysis/progress/<doc_id>.
"""
import threading
import logging
import time

logger = logging.getLogger('plagioscan')

# Active thread registry {doc_id: threading.Thread}
_active_jobs: dict = {}
_lock = threading.Lock()


def submit_analysis_job(app, doc_id: int, run_web: bool = True) -> None:
    """Submit an analysis to run in background thread."""
    with _lock:
        if doc_id in _active_jobs and _active_jobs[doc_id].is_alive():
            logger.info(f'[BG] Job for doc={doc_id} already running.')
            return

        t = threading.Thread(
            target  = _run_job,
            args    = (app, doc_id, run_web),
            daemon  = True,
            name    = f'analysis-{doc_id}',
        )
        _active_jobs[doc_id] = t
        t.start()
        logger.info(f'[BG] Started analysis thread for doc={doc_id}')


def _run_job(app, doc_id: int, run_web: bool) -> None:
    with app.app_context():
        from extensions import db
        from models.models import Document, Analysis, AnalysisJob
        
        # New analysis modules
        from services.ai_risk import calculate_ai_risk
        from services.originality_fingerprint import generate_fingerprint
        from services.style_analysis import analyze_style
        from services.grammar_analysis import analyze_grammar
        from services.contribution import analyze_contribution
        from services.research_depth import analyze_research_depth
        from services.citation_checker import check_citations, get_missing_citations_warning
        from services.analysis_engine import flesch_reading_ease, flesch_kincaid_grade, vocabulary_score

        job = AnalysisJob.query.filter_by(document_id=doc_id).first()
        doc = Document.query.get(doc_id)

        if not job or not doc:
            return

        def _step(pct: int, stage: str):
            job.update(pct, stage)
            try: db.session.commit()
            except Exception: db.session.rollback()

        try:
            start_time = time.time()
            _step(5,  'Extracting text…')

            if not doc.content:
                from services.text_extractor import extract_text
                import os
                from flask import current_app
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.filename)
                doc.content = extract_text(path, doc.original_name)[:100_000]
                db.session.commit()
                
            text = doc.content

            _step(20, 'Searching internet sources…')
            web_matches = []
            if run_web:
                try:
                    from services.web_search import search_web_matches
                    web_matches = search_web_matches(text, timeout=12, max_results=5)
                except Exception as e:
                    logger.warning(f'[BG] Web search error: {e}')

            _step(35, 'Searching academic databases…')
            academic_matches = []
            try:
                from services.academic_search import multi_source_academic_search
                academic_matches = multi_source_academic_search(text[:3000], max_per_source=3)
            except Exception as e:
                logger.warning(f'[BG] Academic search error: {e}')

            _step(50, 'Running similarity algorithms…')
            # Combine text from all sources to compare against the document
            all_web_text = ' '.join([m.get('matched_sentence','') + ' ' + m.get('snippet','') for m in web_matches])
            all_acad_text = ' '.join([m.get('abstract','') for m in academic_matches])
            all_ref = (all_web_text + ' ' + all_acad_text).strip()
            
            from services.similarity import compute_all_scores, sentence_level_matches, generate_highlighted_html
            sim_scores = compute_all_scores(text, all_ref) if all_ref else {
                'tfidf': 0.0, 'ngram': 0.0, 'jaccard': 0.0, 'fuzzy': 0.0, 'combined': 0.0
            }

            _step(65, 'Computing semantic similarity…')
            try:
                from services.semantic import semantic_similarity
                semantic = semantic_similarity(text[:4096], all_ref[:4096]) if all_ref else 0.0
            except Exception:
                semantic = 0.0

            _step(75, 'Analyzing writing quality & AI Risk…')
            
            # Execute new dedicated modules
            style_data = analyze_style(text)
            grammar_data = analyze_grammar(text)
            contrib_data = analyze_contribution(text)
            research_data = analyze_research_depth(text)
            ai_risk_data = calculate_ai_risk(text)
            fingerprint = generate_fingerprint(text)
            
            vocab_sc = vocabulary_score(text)
            read_ease = flesch_reading_ease(text)
            fk_grade = flesch_kincaid_grade(text)
            readability_sc = max(0, min(100, (read_ease * 0.5 + max(0, 100 - fk_grade * 5) * 0.5)))
            
            writing_qual = round((
                grammar_data['grammar_score'] * 0.3 + 
                vocab_sc * 0.3 + 
                readability_sc * 0.2 + 
                max(0, 100 - style_data['passive_voice_pct']) * 0.2
            ), 1)

            _step(85, 'Checking citations…')
            citation_data = check_citations(text)
            missing_cites = get_missing_citations_warning(text)
            if missing_cites:
                citation_data['missing_citation_warnings'] = missing_cites

            _step(90, 'Generating highlighted report…')
            sent_scores = sentence_level_matches(text, all_ref, threshold=25) if all_ref else []
            highlighted = generate_highlighted_html(text, sent_scores) if all_ref else text

            _step(95, 'Saving results…')
            
            # Compute total plagiarism score correctly based on web similarity and algorithmic scores
            web_sims = [m.get('similarity', 0) for m in web_matches]
            acad_sims = [m.get('similarity', 0) for m in academic_matches]
            max_source = max((web_sims + acad_sims) or [0])
            combined_sc = sim_scores.get('combined', 0)
            
            plag_score  = round(max(max_source, combined_sc), 1)
            orig_score  = round(max(0, 100 - plag_score), 1)
            
            processing_time = round(time.time() - start_time, 2)

            old = Analysis.query.filter_by(document_id=doc_id).first()
            if old:
                db.session.delete(old)
                db.session.commit()

            analysis = Analysis(
                document_id            = doc_id,
                status                 = 'done',
                processing_time        = processing_time,

                plagiarism_score       = plag_score,
                originality_score      = orig_score,
                writing_quality_score  = writing_qual,
                research_depth_score   = research_data['research_depth_score'],
                contribution_score     = contrib_data['contribution_score'],
                readability_score      = readability_sc,
                vocabulary_score       = vocab_sc,
                academic_score         = (research_data['research_depth_score'] + citation_data.get('citation_score', 0)) / 2,
                grammar_score          = grammar_data['grammar_score'],
                citation_score         = citation_data.get('citation_score', 0),
                semantic_score         = semantic,

                highlighted_html       = highlighted,
            )
            
            ai_features = {
                'ai_risk': ai_risk_data,
                'fingerprint': fingerprint,
                'writing_quality_score': writing_qual,
                'readability_score': readability_sc,
                'grammar_issues': grammar_data.get('issues', []),
                'contribution_insight_density': contrib_data.get('insight_density', 0.0)
            }
            
            analysis.set_json('similarity_breakdown', sim_scores)
            analysis.set_json('style_analysis', style_data)
            analysis.set_json('ai_features', ai_features)
            analysis.set_json('citation_data', citation_data)
            analysis.set_json('web_matches', web_matches)
            analysis.set_json('academic_matches', academic_matches)
            analysis.set_json('sentence_scores', sent_scores[:30])
            
            # Aggregate warnings and strengths
            strengths = []
            if orig_score > 85: strengths.append("Highly original content.")
            if writing_qual > 80: strengths.append("Excellent writing quality.")
            if vocab_sc > 70: strengths.append("Strong and varied vocabulary.")
            
            weaknesses = []
            if plag_score > 30: weaknesses.append("High similarity to external sources.")
            if grammar_data['grammar_score'] < 60: weaknesses.append("Multiple grammar or typographical errors detected.")
            if ai_risk_data['ai_risk_score'] > 60: weaknesses.append("Detected text structure often associated with AI generation.")
            if citation_data.get('warnings'): weaknesses.extend(citation_data['warnings'][:2])
            
            analysis.set_json('ai_summary', {
                'strengths': strengths,
                'weaknesses': weaknesses,
                'suggestions': ai_risk_data.get('flags', []) + grammar_data.get('issues', [])
            })

            db.session.add(analysis)
            job.update(100, 'Complete', 'done')
            db.session.commit()
            logger.info(f'[BG] Analysis done for doc={doc_id}. Plag={plag_score}%')

        except Exception as e:
            logger.exception(f'[BG] Analysis failed for doc={doc_id}: {e}')
            try:
                job.status    = 'error'
                job.error_msg = str(e)[:500]
                db.session.commit()
                old = Analysis.query.filter_by(document_id=doc_id).first()
                if not old:
                    db.session.add(Analysis(document_id=doc_id, status='error'))
                    db.session.commit()
            except Exception:
                db.session.rollback()
        finally:
            with _lock:
                _active_jobs.pop(doc_id, None)

def get_job_status(doc_id: int) -> dict:
    from models.models import AnalysisJob
    job = AnalysisJob.query.filter_by(document_id=doc_id).first()
    if not job:
        return {'status': 'not_found', 'progress': 0, 'stage': 'Not started'}
    return {
        'status':   job.status,
        'progress': job.progress,
        'stage':    job.stage,
        'error':    job.error_msg,
    }
