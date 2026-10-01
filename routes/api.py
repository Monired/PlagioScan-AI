"""
PlagioScan AI — REST API v1
POST /api/v1/upload   — upload and queue analysis
POST /api/v1/analyze  — trigger analysis for existing doc
GET  /api/v1/status   — service health
GET  /api/v1/documents — list user docs
GET  /api/v1/analysis/<id> — get analysis result
GET  /api/v1/history  — full history
GET  /api/v1/stats    — user statistics
GET  /api/v1/progress/<doc_id> — job progress
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models.models import Document, Analysis, AnalysisJob
from services.background import get_job_status

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/status')
def status():
    try:
        from services.semantic import is_semantic_available
        semantic = is_semantic_available()
    except Exception:
        semantic = False
    return jsonify({
        'service': 'PlagioScan AI',
        'version': '2.0.0',
        'status':  'operational',
        'features': {
            'semantic_ai':      semantic,
            'web_search':       current_app.config.get('WEB_SEARCH_ENABLED', True),
            'academic_search':  current_app.config.get('ACADEMIC_SEARCH_ENABLED', True),
            'ocr':              False,
        },
        'algorithms': ['TF-IDF', 'N-Gram', 'Jaccard', 'Fuzzy', 'Cosine', 'Semantic'],
        'sources':    ['OpenAlex', 'Semantic Scholar', 'Crossref', 'DuckDuckGo'],
    })


@api_bp.route('/documents')
@login_required
def documents():
    docs = Document.query.filter_by(user_id=current_user.id)\
                   .order_by(Document.uploaded_at.desc()).limit(50).all()
    return jsonify([{
        'id':          d.id,
        'name':        d.original_name,
        'type':        d.file_type,
        'word_count':  d.word_count,
        'size':        d.size_display,
        'hash':        d.doc_hash,
        'uploaded_at': d.uploaded_at.isoformat(),
        'has_analysis': d.analysis is not None,
    } for d in docs])


@api_bp.route('/analysis/<int:analysis_id>')
@login_required
def get_analysis(analysis_id: int):
    an = Analysis.query.get_or_404(analysis_id)
    if an.document.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    return jsonify({
        'id':                   an.id,
        'document_id':          an.document_id,
        'status':               an.status,
        'plagiarism_score':     an.plagiarism_score,
        'originality_score':    an.originality_score,
        'overall_score':        an.overall_score,
        'grade':                an.grade,
        'writing_quality_score':an.writing_quality_score,
        'research_depth_score': an.research_depth_score,
        'citation_score':       an.citation_score,
        'semantic_score':       an.semantic_score,
        'similarity_breakdown': an.get_json('similarity_breakdown'),
        'web_matches_count':    len(an.get_json('web_matches')),
        'academic_matches_count': len(an.get_json('academic_matches')),
        'suggestions_count':    len(an.get_json('improvement_suggestions')),
        'analyzed_at':          an.analyzed_at.isoformat(),
    })


@api_bp.route('/history')
@login_required
def history():
    rows = db.session.query(Document, Analysis)\
        .outerjoin(Analysis)\
        .filter(Document.user_id == current_user.id,
                Analysis.status  == 'done')\
        .order_by(Analysis.analyzed_at.desc()).limit(50).all()
    return jsonify([{
        'document':      d.original_name,
        'analysis_id':   a.id,
        'plagiarism':    a.plagiarism_score,
        'originality':   a.originality_score,
        'overall':       a.overall_score,
        'grade':         a.grade,
        'analyzed_at':   a.analyzed_at.isoformat(),
    } for d, a in rows])


@api_bp.route('/stats')
@login_required
def stats():
    docs = Document.query.filter_by(user_id=current_user.id).all()
    analyses = [d.analysis for d in docs if d.analysis and d.analysis.status == 'done']
    return jsonify({
        'total_documents':  len(docs),
        'total_analyses':   len(analyses),
        'total_words':      sum(d.word_count for d in docs),
        'avg_plagiarism':   round(sum(a.plagiarism_score for a in analyses)/max(len(analyses),1), 1),
        'avg_originality':  round(sum(a.originality_score for a in analyses)/max(len(analyses),1), 1),
        'avg_overall':      round(sum(a.overall_score for a in analyses)/max(len(analyses),1), 1),
        'member_since':     current_user.created_at.isoformat(),
    })


@api_bp.route('/progress/<int:doc_id>')
@login_required
def progress(doc_id: int):
    Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    return jsonify(get_job_status(doc_id))
