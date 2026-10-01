"""
PlagioScan AI — Dashboard Routes v2
Adds: history endpoint, analytics data for charts
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from extensions import db
from models.models import Document, Analysis

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    docs_with_analysis = (
        db.session.query(Document, Analysis)
        .outerjoin(Analysis, Document.id == Analysis.document_id)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    total_docs = len(docs_with_analysis)
    analyzed   = sum(1 for _, a in docs_with_analysis if a and a.status == 'done')
    plag_list  = [a.plagiarism_score  for _, a in docs_with_analysis if a and a.status=='done']
    orig_list  = [a.originality_score for _, a in docs_with_analysis if a and a.status=='done']
    avg_plag   = round(sum(plag_list) / len(plag_list), 1) if plag_list else 0
    avg_orig   = round(sum(orig_list) / len(orig_list), 1) if orig_list else 0

    # Chart data — last 7 analyses
    chart_labels, chart_plag, chart_orig = [], [], []
    for doc, an in reversed(docs_with_analysis[-7:]):
        if an and an.status == 'done':
            chart_labels.append(doc.original_name[:16])
            chart_plag.append(round(an.plagiarism_score, 1))
            chart_orig.append(round(an.originality_score, 1))

    return render_template(
        'dashboard/index.html',
        docs_with_analysis = docs_with_analysis,
        total_docs  = total_docs,
        analyzed    = analyzed,
        avg_plag    = avg_plag,
        avg_orig    = avg_orig,
        chart_labels= chart_labels,
        chart_plag  = chart_plag,
        chart_orig  = chart_orig,
    )


@dashboard_bp.route('/history')
@login_required
def history():
    """Full analysis history for the current user."""
    rows = (
        db.session.query(Document, Analysis)
        .outerjoin(Analysis, Document.id == Analysis.document_id)
        .filter(Document.user_id == current_user.id,
                Analysis.status  == 'done')
        .order_by(Analysis.analyzed_at.desc())
        .all()
    )
    return render_template('dashboard/history.html', rows=rows)
