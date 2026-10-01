"""
PlagioScan AI — Analysis Routes v2
Background jobs, progress polling, results, compare, reports.
"""
import os, io, hashlib, logging
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, send_file, abort, jsonify)
from flask_login import login_required, current_user

from extensions import db
from models.models import Document, Analysis, AnalysisJob, ActivityLog
from services.text_extractor import extract_text
from services.background import submit_analysis_job, get_job_status
from services.report_generator import generate_pdf_report
from utils.validators import validate_upload, safe_filename
from utils.helpers import generate_unique_filename, get_client_ip, word_count

logger = logging.getLogger('plagioscan')
analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')


# ── Upload ─────────────────────────────────────────────────────────────────────
@analysis_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'GET':
        return render_template('dashboard/upload.html')

    file = request.files.get('file')
    ok, err = validate_upload(file)
    if not ok:
        flash(err, 'danger')
        return render_template('dashboard/upload.html')

    # Optional reference file
    ref_content = ''
    ref_file = request.files.get('reference_file')
    if ref_file and ref_file.filename:
        r_ok, _ = validate_upload(ref_file)
        if r_ok:
            ref_stored = generate_unique_filename(ref_file.filename)
            ref_path   = os.path.join(current_app.config['UPLOAD_FOLDER'], ref_stored)
            ref_file.save(ref_path)
            try: ref_content = extract_text(ref_path, ref_file.filename)[:50000]
            except Exception: pass

    orig_name  = file.filename
    stored     = generate_unique_filename(orig_name)
    file_path  = os.path.join(current_app.config['UPLOAD_FOLDER'], stored)
    file.save(file_path)
    file_size  = os.path.getsize(file_path)
    file_type  = orig_name.rsplit('.', 1)[-1].lower() if '.' in orig_name else 'txt'

    try:
        content = extract_text(file_path, orig_name)
    except Exception as e:
        flash(f'Text extraction failed: {e}', 'danger')
        os.remove(file_path)
        return render_template('dashboard/upload.html')

    wc = word_count(content)
    if wc < current_app.config.get('MIN_WORDS_FOR_ANALYSIS', 30):
        flash(f'Document too short ({wc} words). Minimum: 30 words.', 'danger')
        os.remove(file_path)
        return render_template('dashboard/upload.html')

    # Document hash
    doc_hash = hashlib.sha256(content[:50000].encode('utf-8', errors='ignore')).hexdigest()

    doc = Document(
        user_id       = current_user.id,
        filename      = stored,
        original_name = safe_filename(orig_name) or orig_name,
        file_type     = file_type,
        file_size     = file_size,
        word_count    = wc,
        content       = content[:current_app.config.get('MAX_CONTENT_STORE', 100_000)],
        doc_hash      = doc_hash,
        draft_group   = request.form.get('draft_group', '').strip() or None,
        draft_version = int(request.form.get('draft_version', 1) or 1),
    )
    db.session.add(doc)
    db.session.commit()

    # Create job record
    job = AnalysisJob(document_id=doc.id, status='pending', progress=0, stage='Queued')
    db.session.add(job)
    db.session.commit()

    _log(current_user.id, 'upload', f'{orig_name} ({wc} words)')
    flash(f'"{orig_name}" uploaded — analysis started in background!', 'success')
    return redirect(url_for('analysis.progress_page', doc_id=doc.id))


# ── Progress Page ──────────────────────────────────────────────────────────────
@analysis_bp.route('/progress/<int:doc_id>')
@login_required
def progress_page(doc_id: int):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    # Start background job
    submit_analysis_job(current_app._get_current_object(), doc_id, run_web=True)
    return render_template('dashboard/progress.html', doc=doc)


# ── Progress API (polling) ─────────────────────────────────────────────────────
@analysis_bp.route('/progress/<int:doc_id>/status')
@login_required
def progress_status(doc_id: int):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    status = get_job_status(doc_id)
    if status['status'] == 'done':
        an = Analysis.query.filter_by(document_id=doc_id).first()
        status['redirect'] = url_for('analysis.results',
                                     analysis_id=an.id) if an else url_for('dashboard.index')
    return jsonify(status)


# ── Results ────────────────────────────────────────────────────────────────────
@analysis_bp.route('/results/<int:analysis_id>')
@login_required
def results(analysis_id: int):
    analysis = Analysis.query.get_or_404(analysis_id)
    doc = analysis.document
    if doc.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template(
        'dashboard/results.html',
        analysis    = analysis,
        doc         = doc,
        style_d     = analysis.get_json('style_analysis'),
        ai_d        = analysis.get_json('ai_features'),
        web_m       = analysis.get_json('web_matches'),
        academic_m  = analysis.get_json('academic_matches'),
        sim_d       = analysis.get_json('similarity_breakdown'),
        citation_d  = analysis.get_json('citation_data'),
        ai_summary  = analysis.get_json('ai_summary'),
        suggestions = analysis.get_json('improvement_suggestions'),
        sent_scores = analysis.get_json('sentence_scores'),
    )


# ── Preview ────────────────────────────────────────────────────────────────────
@analysis_bp.route('/preview/<int:doc_id>')
@login_required
def preview(doc_id: int):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    return render_template('dashboard/preview.html', doc=doc)


# ── Compare ────────────────────────────────────────────────────────────────────
@analysis_bp.route('/compare/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def compare(doc_id: int):
    from services.similarity import compute_all_scores, sentence_level_matches, generate_highlighted_html
    doc      = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    user_docs = Document.query.filter(
        Document.user_id == current_user.id, Document.id != doc_id
    ).order_by(Document.uploaded_at.desc()).all()
    comparison = None
    ref_doc    = None
    if request.method == 'POST':
        ref_id = request.form.get('ref_doc_id')
        if ref_id:
            ref_doc = Document.query.filter_by(id=int(ref_id), user_id=current_user.id).first()
            if ref_doc and ref_doc.content and doc.content:
                scores       = compute_all_scores(doc.content, ref_doc.content)
                sent_matches = sentence_level_matches(doc.content, ref_doc.content, threshold=35)
                highlighted  = generate_highlighted_html(doc.content, sent_matches)
                comparison   = {'scores': scores, 'sent_matches': sent_matches[:20],
                                'highlighted': highlighted}
    return render_template('dashboard/compare.html', doc=doc, user_docs=user_docs,
                           comparison=comparison, ref_doc=ref_doc)


# ── Delete ─────────────────────────────────────────────────────────────────────
@analysis_bp.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_doc(doc_id: int):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    name = doc.original_name
    try:
        fpath = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.filename)
        if os.path.exists(fpath): os.remove(fpath)
    except Exception: pass
    db.session.delete(doc)
    db.session.commit()
    _log(current_user.id, 'delete_doc', name)
    flash(f'"{name}" deleted.', 'success')
    return redirect(url_for('dashboard.index'))


# ── Re-analyze ─────────────────────────────────────────────────────────────────
@analysis_bp.route('/reanalyze/<int:doc_id>')
@login_required
def reanalyze(doc_id: int):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    # Reset job
    job = AnalysisJob.query.filter_by(document_id=doc_id).first()
    if job:
        job.status   = 'pending'
        job.progress = 0
        job.stage    = 'Queued'
        job.error_msg = None
    else:
        job = AnalysisJob(document_id=doc_id, status='pending')
        db.session.add(job)
    db.session.commit()
    flash(f'Re-analyzing "{doc.original_name}"…', 'info')
    return redirect(url_for('analysis.progress_page', doc_id=doc_id))


# ── PDF Report ─────────────────────────────────────────────────────────────────
@analysis_bp.route('/report/<int:analysis_id>')
@login_required
def download_report(analysis_id: int):
    analysis = Analysis.query.get_or_404(analysis_id)
    doc = analysis.document
    if doc.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    try:
        results_url = url_for('analysis.results', analysis_id=analysis_id, _external=True)
        pdf_bytes = generate_pdf_report(
            analysis_data={
                'plagiarism_score':       analysis.plagiarism_score,
                'originality_score':      analysis.originality_score,
                'writing_quality_score':  analysis.writing_quality_score,
                'research_depth_score':   analysis.research_depth_score,
                'contribution_score':     analysis.contribution_score,
                'readability_score':      analysis.readability_score,
                'vocabulary_score':       analysis.vocabulary_score,
                'academic_score':         analysis.academic_score,
                'citation_score':         analysis.citation_score,
                'semantic_score':         analysis.semantic_score,
                'similarity_breakdown':   analysis.get_json('similarity_breakdown'),
                'style_analysis':         analysis.get_json('style_analysis'),
                'web_matches':            analysis.get_json('web_matches'),
                'citation_data':          analysis.get_json('citation_data'),
                'improvement_suggestions':analysis.get_json('improvement_suggestions'),
                'ai_summary':             analysis.get_json('ai_summary'),
            },
            username     = current_user.username,
            doc_name     = doc.original_name,
            doc_hash     = doc.doc_hash or '',
            overall_score= analysis.overall_score,
            grade        = analysis.grade,
            results_url  = results_url,
        )
        _log(current_user.id, 'download_report', f'analysis={analysis_id}')
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype      = 'application/pdf',
            as_attachment = True,
            download_name = f'PlagioScan_{doc.original_name}_{analysis_id}.pdf',
        )
    except Exception as e:
        logger.exception(f'Report gen failed: {e}')
        flash(f'Report generation failed: {e}', 'danger')
        return redirect(url_for('analysis.results', analysis_id=analysis_id))


def _log(user_id, action: str, detail: str = ''):
    try:
        log = ActivityLog(user_id=user_id, action=action,
                          detail=detail[:250], ip_address=get_client_ip())
        db.session.add(log)
        db.session.commit()
    except Exception: pass
