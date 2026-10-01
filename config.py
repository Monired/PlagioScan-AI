"""
PlagioScan AI — Configuration
All settings loaded from environment variables via .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # ── Core ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'plagioscan-dev-secret-CHANGE-IN-PROD-2025')
    DEBUG      = False
    TESTING    = False

    # ── Database ──────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'plagioscan.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        'pool_pre_ping': True,
        'pool_recycle':  300,
    }

    # ── File Uploads ──────────────────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, 'uploads')
    REPORTS_FOLDER     = os.path.join(BASE_DIR, 'reports')
    LOGS_FOLDER        = os.path.join(BASE_DIR, 'logs')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024        # 32 MB
    ALLOWED_EXTENSIONS = {'txt','pdf','docx','rtf','odt','png','jpg','jpeg','zip'}

    # ── Security ──────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED              = True
    WTF_CSRF_TIME_LIMIT           = 3600
    SESSION_COOKIE_HTTPONLY       = True
    SESSION_COOKIE_SAMESITE       = 'Lax'
    PERMANENT_SESSION_LIFETIME    = 86400        # 1 day

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_DEFAULT     = '500 per day;100 per hour;20 per minute'

    # ── Email (Flask-Mail) — all optional, gracefully disabled ─────────────
    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@plagioscan.ai')
    MAIL_ENABLED  = bool(os.environ.get('MAIL_USERNAME'))

    # ── Web Search ────────────────────────────────────────────────────────
    WEB_SEARCH_ENABLED  = os.environ.get('WEB_SEARCH_ENABLED', 'true').lower() == 'true'
    WEB_SEARCH_TIMEOUT  = int(os.environ.get('WEB_SEARCH_TIMEOUT', '8'))
    MAX_WEB_RESULTS     = int(os.environ.get('MAX_WEB_RESULTS', '5'))
    MAX_SENTENCES_WEB   = 8

    # ── Academic Search APIs (all free, no key required) ─────────────────
    OPENALEX_EMAIL      = os.environ.get('OPENALEX_EMAIL', 'user@plagioscan.ai')
    ACADEMIC_SEARCH_ENABLED = True
    ACADEMIC_TIMEOUT    = int(os.environ.get('ACADEMIC_TIMEOUT', '8'))
    MAX_ACADEMIC_RESULTS = int(os.environ.get('MAX_ACADEMIC_RESULTS', '5'))

    # ── Sentence Transformers (Semantic AI) ───────────────────────────────
    SEMANTIC_ENABLED    = os.environ.get('SEMANTIC_ENABLED', 'true').lower() == 'true'
    SEMANTIC_MODEL      = os.environ.get('SEMANTIC_MODEL', 'all-MiniLM-L6-v2')

    # ── Analysis ──────────────────────────────────────────────────────────
    MIN_WORDS_FOR_ANALYSIS = 30
    MAX_CONTENT_STORE      = 100_000   # characters stored in DB

    # ── Background Jobs ───────────────────────────────────────────────────
    JOB_TIMEOUT = 300   # seconds before a job is considered stalled


class DevelopmentConfig(Config):
    DEBUG            = True
    SQLALCHEMY_ECHO  = False
    # In dev mode: show password reset link on-screen instead of email
    MAIL_DEV_MODE    = True


class ProductionConfig(Config):
    DEBUG                  = False
    SESSION_COOKIE_SECURE  = True
    REMEMBER_COOKIE_SECURE = True
    MAIL_DEV_MODE          = False


class TestingConfig(Config):
    TESTING              = True
    WTF_CSRF_ENABLED     = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SEMANTIC_ENABLED     = False   # skip heavy model in tests


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
