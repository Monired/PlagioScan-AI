"""
PlagioScan AI — File Validators
"""
import os
from werkzeug.utils import secure_filename

ALLOWED = {'txt', 'pdf', 'docx', 'rtf', 'odt', 'png', 'jpg', 'jpeg', 'zip'}
MAX_SIZE = 32 * 1024 * 1024  # 32 MB


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


def safe_filename(filename: str) -> str:
    return secure_filename(filename)


def validate_upload(file) -> tuple[bool, str]:
    """Return (ok, error_message)."""
    if not file or file.filename == '':
        return False, 'No file selected.'
    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'unknown'
        return False, f'File type ".{ext}" is not supported. Allowed: {", ".join(sorted(ALLOWED))}'
    # Check size by reading content length header
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        return False, f'File too large ({size/(1024*1024):.1f} MB). Maximum allowed: 32 MB.'
    if size == 0:
        return False, 'File is empty.'
    return True, ''
