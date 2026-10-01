"""
PlagioScan AI — Auth Decorators & Utilities
"""
from functools import wraps
from flask import redirect, url_for, flash, request, abort
from flask_login import current_user


def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login_page', next=request.url))
        if not current_user.is_active:
            flash('Your account has been disabled. Contact admin.', 'danger')
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restrict access to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login first.', 'warning')
            return redirect(url_for('auth.login_page'))
        if not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def active_required(f):
    """Ensure account is active."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated and not current_user.is_active:
            flash('Account disabled.', 'danger')
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated
