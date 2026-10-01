"""
PlagioScan AI — Auth Routes v2
Added: Forgot Password, Reset Password (email + dev-mode on-screen link)
"""
import secrets
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app)
from flask_login import login_user, logout_user, current_user, login_required

from extensions import db
from models.models import User, ActivityLog, PasswordResetToken
from utils.helpers import get_client_ip

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── Login ──────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('auth/login.html')
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if not user or not user.check_password(password):
            flash('Invalid credentials. Please try again.', 'danger')
            _log(None, 'login_failed', f'attempt: {username}')
            return render_template('auth/login.html')
        if not user.is_active:
            flash('Your account has been disabled. Contact administrator.', 'danger')
            return render_template('auth/login.html')
        login_user(user, remember=request.form.get('remember') == 'on')
        user.last_login = datetime.utcnow()
        db.session.commit()
        _log(user.id, 'login', 'success')
        flash(f'Welcome back, {user.username}! 👋', 'success')
        nxt = request.args.get('next', '')
        return redirect(nxt if nxt.startswith('/') else url_for('dashboard.index'))
    return render_template('auth/login.html')


# ── Register ───────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        errors = []
        if len(username) < 3:  errors.append('Username must be at least 3 characters.')
        if len(username) > 32: errors.append('Username max 32 characters.')
        if not username.replace('_','').replace('-','').isalnum():
            errors.append('Username: only letters, numbers, _ and - allowed.')
        if '@' not in email or '.' not in email:
            errors.append('Please enter a valid email address.')
        if len(password) < 6:  errors.append('Password must be at least 6 characters.')
        if password != confirm: errors.append('Passwords do not match.')
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('auth/register.html',
                                   form_data={'username': username, 'email': email})
        user = User(username=username, email=email)
        user.set_password(password)
        if User.query.count() == 0:
            user.role = 'admin'
            user.email_verified = True
        db.session.add(user)
        db.session.commit()
        _log(user.id, 'register', username)
        login_user(user)
        flash(f'Account created! Welcome to PlagioScan AI, {username}! 🚀', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html', form_data={})


# ── Forgot Password ────────────────────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email).first()
        if user:
            tok = PasswordResetToken.generate(user.id, hours=2)
            db.session.add(tok)
            db.session.commit()
            link = url_for('auth.reset_password', token=tok.token, _external=True)
            dev_mode = getattr(current_app.config, 'MAIL_DEV_MODE',
                               current_app.debug)
            if current_app.config.get('MAIL_ENABLED') and not dev_mode:
                _send_reset_email(user.email, user.username, link)
                flash('Password reset link sent to your email.', 'success')
            else:
                # Dev mode: show link on screen
                reset_link = link
                flash('Dev mode: password reset link shown below. Configure SMTP for email delivery.', 'info')
            _log(user.id, 'forgot_password', email)
        else:
            # Don't reveal whether email exists
            flash('If that email is registered, you will receive a reset link.', 'info')
    return render_template('auth/forgot_password.html', reset_link=reset_link)


# ── Reset Password ─────────────────────────────────────────────────────────────
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    tok = PasswordResetToken.query.filter_by(token=token).first()
    if not tok or not tok.is_valid:
        flash('This password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if len(new_pw) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif new_pw != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            user = User.query.get(tok.user_id)
            user.set_password(new_pw)
            tok.used = True
            db.session.commit()
            _log(user.id, 'password_reset', 'success')
            flash('Password reset successfully! Please login.', 'success')
            return redirect(url_for('auth.login_page'))
    return render_template('auth/reset_password.html', token=token)


# ── Logout ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    _log(current_user.id, 'logout', '')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_page'))


# ── Profile ────────────────────────────────────────────────────────────────────
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_email':
            new_email = request.form.get('new_email', '').strip().lower()
            if '@' not in new_email:
                flash('Invalid email address.', 'danger')
            elif User.query.filter(User.email == new_email, User.id != user.id).first():
                flash('Email already in use by another account.', 'danger')
            else:
                user.email = new_email
                db.session.commit()
                flash('Email updated successfully.', 'success')
        elif action == 'change_password':
            cur = request.form.get('current_password', '')
            new = request.form.get('new_password', '')
            con = request.form.get('confirm_password', '')
            if not user.check_password(cur):
                flash('Current password is incorrect.', 'danger')
            elif len(new) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new != con:
                flash('New passwords do not match.', 'danger')
            else:
                user.set_password(new)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        elif action == 'toggle_theme':
            user.dark_mode = not user.dark_mode
            db.session.commit()
        return redirect(url_for('auth.profile'))
    recent_docs = user.documents.order_by(
        db.text('uploaded_at DESC')
    ).limit(5).all()
    return render_template('dashboard/profile.html', user=user,
                           recent_docs=recent_docs,
                           doc_count=user.doc_count,
                           an_count=user.analysis_count)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _send_reset_email(to_email: str, username: str, link: str):
    try:
        from flask_mail import Mail, Message
        mail = Mail(current_app._get_current_object())
        msg  = Message(
            subject   = 'PlagioScan AI — Password Reset',
            recipients= [to_email],
            html      = f'''<p>Hi {username},</p>
<p>Click the link below to reset your password (valid 2 hours):</p>
<p><a href="{link}">{link}</a></p>
<p>If you did not request this, ignore this email.</p>
<p>— PlagioScan AI Team</p>''',
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email send failed: {e}')


def _log(user_id, action: str, detail: str = ''):
    try:
        log = ActivityLog(user_id=user_id, action=action,
                          detail=detail[:250], ip_address=get_client_ip())
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
