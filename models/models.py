"""
PlagioScan AI — Database Models (v2)
SQLAlchemy ORM: User, Document, Analysis, AnalysisJob,
                PasswordResetToken, ActivityLog
"""
from datetime import datetime, timedelta
import json, secrets
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# ─────────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(16),  default='user', nullable=False)
    is_active     = db.Column(db.Boolean, default=True,  nullable=False)
    email_verified= db.Column(db.Boolean, default=False, nullable=False)
    dark_mode     = db.Column(db.Boolean, default=True,  nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    documents     = db.relationship('Document',  backref='owner', lazy='dynamic',
                                    cascade='all, delete-orphan')
    reset_tokens  = db.relationship('PasswordResetToken', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def doc_count(self) -> int:
        return self.documents.count()

    @property
    def analysis_count(self) -> int:
        return sum(1 for d in self.documents if d.analysis is not None)

    @property
    def total_words_analysed(self) -> int:
        return sum(d.word_count for d in self.documents)

    def __repr__(self):
        return f'<User {self.username}>'


# ─────────────────────────────────────────────────────────────────────────────
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token      = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate(user_id: int, hours: int = 2) -> 'PasswordResetToken':
        tok = PasswordResetToken(
            user_id    = user_id,
            token      = secrets.token_urlsafe(48),
            expires_at = datetime.utcnow() + timedelta(hours=hours),
        )
        return tok

    @property
    def is_valid(self) -> bool:
        return (not self.used) and (datetime.utcnow() < self.expires_at)


# ─────────────────────────────────────────────────────────────────────────────
class Document(db.Model):
    __tablename__ = 'documents'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename      = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=False)
    file_type     = db.Column(db.String(16),  nullable=False)
    file_size     = db.Column(db.Integer, default=0)
    word_count    = db.Column(db.Integer, default=0)
    content       = db.Column(db.Text, nullable=True)
    doc_hash      = db.Column(db.String(64), nullable=True, index=True)   # SHA-256
    draft_group   = db.Column(db.String(128), nullable=True)
    draft_version = db.Column(db.Integer, default=1)
    uploaded_at   = db.Column(db.DateTime, default=datetime.utcnow)

    analysis = db.relationship('Analysis',    backref='document',
                               uselist=False, cascade='all, delete-orphan')
    job      = db.relationship('AnalysisJob', backref='document',
                               uselist=False, cascade='all, delete-orphan')

    @property
    def size_display(self) -> str:
        b = self.file_size
        if b < 1024:      return f'{b} B'
        if b < 1_048_576: return f'{b/1024:.1f} KB'
        return f'{b/1_048_576:.1f} MB'

    def __repr__(self):
        return f'<Document {self.original_name}>'


# ─────────────────────────────────────────────────────────────────────────────
class AnalysisJob(db.Model):
    """Tracks the state of a background analysis task."""
    __tablename__ = 'analysis_jobs'

    id          = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'),
                            nullable=False, unique=True, index=True)
    status      = db.Column(db.String(20), default='pending')   # pending/running/done/error
    progress    = db.Column(db.Integer,  default=0)             # 0-100
    stage       = db.Column(db.String(64), default='Queued')    # human label
    error_msg   = db.Column(db.String(512), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def update(self, progress: int, stage: str, status: str = 'running'):
        self.progress  = progress
        self.stage     = stage
        self.status    = status
        self.updated_at = datetime.utcnow()


# ─────────────────────────────────────────────────────────────────────────────
class Analysis(db.Model):
    __tablename__ = 'analyses'

    id          = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'),
                            nullable=False, unique=True, index=True)

    status          = db.Column(db.String(20), default='pending')
    processing_time = db.Column(db.Float, default=0.0)

    # Core scores (0-100)
    plagiarism_score       = db.Column(db.Float, default=0.0)
    originality_score      = db.Column(db.Float, default=100.0)
    writing_quality_score  = db.Column(db.Float, default=0.0)
    research_depth_score   = db.Column(db.Float, default=0.0)
    contribution_score     = db.Column(db.Float, default=0.0)
    readability_score      = db.Column(db.Float, default=0.0)
    vocabulary_score       = db.Column(db.Float, default=0.0)
    academic_score         = db.Column(db.Float, default=0.0)
    grammar_score          = db.Column(db.Float, default=0.0)
    citation_score         = db.Column(db.Float, default=0.0)
    semantic_score         = db.Column(db.Float, default=0.0)   # NEW

    # JSON blobs
    similarity_breakdown    = db.Column(db.Text, default='{}')
    style_analysis          = db.Column(db.Text, default='{}')
    ai_features             = db.Column(db.Text, default='{}')
    citation_data           = db.Column(db.Text, default='{}')  # NEW
    academic_matches        = db.Column(db.Text, default='[]')  # NEW
    web_matches             = db.Column(db.Text, default='[]')
    local_matches           = db.Column(db.Text, default='[]')
    highlighted_html        = db.Column(db.Text, default='')
    improvement_suggestions = db.Column(db.Text, default='[]')
    sentence_scores         = db.Column(db.Text, default='[]')
    ai_summary              = db.Column(db.Text, default='{}')  # NEW

    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_json(self, col: str):
        val = getattr(self, col, None)
        default = [] if col in ('web_matches','local_matches',
                                'improvement_suggestions','sentence_scores',
                                'academic_matches') else {}
        try:
            return json.loads(val) if val else default
        except Exception:
            return default

    def set_json(self, col: str, data) -> None:
        setattr(self, col, json.dumps(data, default=str))

    @property
    def overall_score(self) -> float:
        return round((
            self.originality_score       * 0.28 +
            self.writing_quality_score   * 0.18 +
            self.research_depth_score    * 0.15 +
            self.contribution_score      * 0.14 +
            self.readability_score       * 0.10 +
            self.vocabulary_score        * 0.08 +
            self.citation_score          * 0.07
        ), 1)

    @property
    def grade(self) -> str:
        s = self.overall_score
        if s >= 85: return 'A'
        if s >= 70: return 'B'
        if s >= 55: return 'C'
        if s >= 40: return 'D'
        return 'F'

    def __repr__(self):
        return f'<Analysis doc={self.document_id} plag={self.plagiarism_score:.1f}%>'


# ─────────────────────────────────────────────────────────────────────────────
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(64),  nullable=False)
    detail     = db.Column(db.String(256), nullable=True)
    ip_address = db.Column(db.String(48),  nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Log {self.action} user={self.user_id}>'
