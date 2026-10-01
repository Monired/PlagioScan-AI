# 🛡 PlagioScan AI
## Intelligent Plagiarism Detection & Originality Analysis Platform

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

PlagioScan AI is a professional, enterprise-grade academic integrity platform combining multi-algorithm plagiarism detection, live web comparison, and 20+ AI writing analysis features.

---

## 🚀 Quick Start

```bash
cd plagioscan_ai
python run.py
```

Server: **http://127.0.0.1:5000**  
Default Admin: `admin` / `admin123`

---

## ✨ Features

### 🔬 Detection Engine (5 Algorithms)
- **TF-IDF + Cosine Similarity** (40% weight) — scikit-learn powered
- **N-Gram Similarity** (20% weight) — character trigrams
- **Jaccard Similarity** (15% weight) — word set overlap
- **Fuzzy String Matching** (25% weight) — SequenceMatcher
- **Weighted Combined Score** — single confidence score

### 🌐 Internet Plagiarism Detection
- DuckDuckGo search — no API key required
- Live page download + clean text extraction
- Sentence-level matching against web content
- Source URL, title, confidence score

### 🤖 AI Analysis Features (20+)
| Feature | Description |
|---------|-------------|
| Originality Score | Overall original content percentage |
| Writing Quality | Grammar + vocabulary + readability composite |
| Research Depth | Citation analysis + academic vocabulary |
| Contribution Score | Original analysis and opinion signals |
| Readability | Flesch-Kincaid Reading Ease + Grade Level |
| Vocabulary Richness | Type-Token Ratio |
| Passive Voice % | Regex-based sentence-level detection |
| Grammar Quality | Heuristic punctuation/capitalization checker |
| Writing Tone | Formal/Informal/Mixed classifier |
| Academic Score | Composite academic quality score |
| AI Content Indicator | Experimental AI-written content heuristic |
| Citation Checker | APA, IEEE, DOI, URL pattern detection |
| Keyword Density | Top 15 keyword frequencies |
| Repeated Phrases | Repeated n-gram detection |
| Duplicate Paragraphs | Near-duplicate paragraph finder |
| Document Structure | Intro/Conclusion/References detection |
| Sentence Complexity | Average length, variation |
| Vocabulary Score | Richness + average word length |
| Highlighted Matches | Color-coded severity highlighting |
| Improvement Suggestions | 12 actionable recommendations |

### 📊 Visualizations
- Radar chart (7-axis score visualization)
- Progress bars (per algorithm)
- Score cards with animated counters
- Highlighted text (red/orange/yellow/green by severity)
- Side-by-side synchronized comparison

### 📄 File Support
- PDF (text-based + scanned via OCR*)
- DOCX / DOC
- TXT, RTF, ODT
- PNG, JPG, JPEG (OCR*)
- ZIP archives (batch processing)

*OCR requires: `pip install pytesseract Pillow` + Tesseract binary

### 🏗 Architecture

```
plagioscan_ai/
├── app.py               # Flask app factory
├── config.py            # Environment-based configs
├── run.py               # Development runner
├── models/models.py     # SQLAlchemy ORM models
├── routes/              # Flask Blueprints
│   ├── auth.py          # Login, Register, Profile
│   ├── dashboard.py     # User dashboard
│   ├── analysis.py      # Upload, Analyze, Results
│   ├── admin.py         # Admin panel
│   └── api.py           # REST API v1
├── services/            # Business logic
│   ├── text_extractor.py
│   ├── similarity.py    # All algorithms
│   ├── analysis_engine.py # AI features
│   ├── plagiarism.py    # Orchestrator
│   ├── web_search.py    # Internet detection
│   └── report_generator.py # PDF reports
├── utils/               # Helpers
│   ├── decorators.py
│   ├── validators.py
│   └── helpers.py
├── static/css/style.css # Premium dark theme
├── static/js/main.js    # Interactive JS
└── templates/           # Jinja2 HTML templates
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```bash
SECRET_KEY=your-secret-key-here
WEB_SEARCH_ENABLED=true
WEB_SEARCH_TIMEOUT=8
MAX_WEB_RESULTS=5
# DATABASE_URL=postgresql://user:pass@host/db  # optional, SQLite by default
```

---

## 🔒 Security Features
- CSRF protection (Flask-WTF)
- Rate limiting (Flask-Limiter)
- Werkzeug password hashing
- Secure filename sanitization
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (Jinja2 auto-escaping)
- SECRET_KEY in environment variables
- Session security flags

---

## 🚢 Deployment

### Render / Railway
```bash
# Set environment variables in dashboard, then:
# Build: pip install -r requirements.txt
# Start: gunicorn "app:create_app('production')" --workers=2 --bind=0.0.0.0:$PORT
```

### Docker
```bash
cp .env.example .env
docker-compose up -d
```

### PythonAnywhere
```bash
pip install -r requirements.txt
# WSGI: from app import create_app; application = create_app('production')
```

---

## 🔌 REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | Service health check |
| `/api/v1/documents` | GET | List user documents |
| `/api/v1/analysis/<id>` | GET | Get analysis results |
| `/api/v1/stats` | GET | User statistics |

---

## 📦 Dependencies

Core: `flask`, `flask-sqlalchemy`, `flask-login`, `flask-wtf`, `flask-limiter`  
ML/NLP: `scikit-learn`  
Documents: `pypdf`, `python-docx`, `Pillow`  
Web Search: `requests`, `beautifulsoup4`  
Reports: `reportlab`  
Config: `python-dotenv`  
Deploy: `gunicorn`

---

## 📝 License

MIT License — Free for academic and personal use.

---

*Built with ❤️ for academic integrity — PlagioScan AI v1.0.0*
