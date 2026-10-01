"""
PlagioScan AI — Helper Utilities
"""
import os, re, uuid, logging
from datetime import datetime
from flask import request


def generate_unique_filename(original: str) -> str:
    """Generate a unique stored filename preserving extension."""
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else 'txt'
    return f"{uuid.uuid4().hex}.{ext}"


def get_client_ip() -> str:
    """Extract real IP respecting proxies."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def setup_logger(name: str, log_dir: str) -> logging.Logger:
    """Set up a file + console logger."""
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(os.path.join(log_dir, f'{name}.log'), encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger


def truncate_text(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '…'


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def format_datetime(dt: datetime) -> str:
    if dt is None:
        return '—'
    return dt.strftime('%d %b %Y, %H:%M')


def score_color(score: float, invert: bool = False) -> str:
    """Return Bootstrap color class. invert=True for plagiarism (lower=better)."""
    if invert:
        if score < 20:  return 'success'
        if score < 50:  return 'warning'
        return 'danger'
    if score >= 75:     return 'success'
    if score >= 50:     return 'warning'
    return 'danger'


def score_label(score: float, invert: bool = False) -> str:
    if invert:
        if score < 20:  return 'Low'
        if score < 50:  return 'Moderate'
        return 'High'
    if score >= 75:     return 'Excellent'
    if score >= 50:     return 'Good'
    if score >= 25:     return 'Fair'
    return 'Poor'


def slugify(text: str) -> str:
    """Simple slug generator."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[\s_-]+', '-', text)
