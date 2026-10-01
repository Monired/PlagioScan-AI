"""
PlagioScan AI — Admin Routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from sqlalchemy import func
from models.models import db, User, Document, Analysis, ActivityLog
from utils.decorators import admin_required
from utils.helpers import get_client_ip

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_required
def index():
    users   = User.query.order_by(User.created_at.desc()).all()
    doc_cnt = db.session.query(func.count(Document.id)).scalar() or 0
    an_cnt  = db.session.query(func.count(Analysis.id)).scalar() or 0

    avg_plag = db.session.query(func.avg(Analysis.plagiarism_score)).scalar() or 0
    avg_orig = db.session.query(func.avg(Analysis.originality_score)).scalar() or 0
    avg_wq   = db.session.query(func.avg(Analysis.writing_quality_score)).scalar() or 0
    avg_rd   = db.session.query(func.avg(Analysis.research_depth_score)).scalar() or 0

    doc_counts = {
        row[0]: row[1]
        for row in db.session.query(Document.user_id,
                                     func.count(Document.id))
                              .group_by(Document.user_id).all()
    }

    recent = (
        db.session.query(Analysis, Document, User)
        .join(Document, Analysis.document_id == Document.id)
        .join(User, Document.user_id == User.id)
        .order_by(Analysis.analyzed_at.desc())
        .limit(20).all()
    )

    logs = ActivityLog.query.order_by(
        ActivityLog.created_at.desc()
    ).limit(50).all()

    return render_template(
        'admin/index.html',
        users=users,
        doc_count=doc_cnt,
        analysis_count=an_cnt,
        avg_plag=round(avg_plag or 0, 1),
        avg_orig=round(avg_orig or 0, 1),
        avg_wq=round(avg_wq or 0, 1),
        avg_rd=round(avg_rd or 0, 1),
        doc_counts=doc_counts,
        recent=recent,
        logs=logs,
    )


@admin_bp.route('/delete_user/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid: int):
    user = User.query.get_or_404(uid)
    if user.is_admin:
        flash('Cannot delete admin accounts.', 'danger')
        return redirect(url_for('admin.index'))
    name = user.username
    db.session.delete(user)
    db.session.commit()
    _log(current_user.id, 'admin_delete_user', f'Deleted user: {name}')
    flash(f'User "{name}" and all their data deleted.', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/toggle_user/<int:uid>', methods=['POST'])
@admin_required
def toggle_user(uid: int):
    user = User.query.get_or_404(uid)
    if user.is_admin:
        flash('Cannot disable admin accounts.', 'danger')
        return redirect(url_for('admin.index'))
    user.is_active = not user.is_active
    db.session.commit()
    state = 'enabled' if user.is_active else 'disabled'
    _log(current_user.id, 'admin_toggle_user', f'{state}: {user.username}')
    flash(f'User "{user.username}" {state}.', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/view_analysis/<int:analysis_id>')
@admin_required
def view_analysis(analysis_id: int):
    from routes.analysis import results as analysis_results
    return redirect(url_for('analysis.results', analysis_id=analysis_id))


def _log(user_id, action: str, detail: str = ''):
    try:
        log = ActivityLog(user_id=user_id, action=action,
                          detail=detail[:250], ip_address=get_client_ip())
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
