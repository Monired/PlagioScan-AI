"""
PlagioScan AI — Flask Application Factory v2
Uses extensions.py to avoid circular imports.
"""
import os, logging
from flask import Flask, render_template

from config    import config_map
from extensions import db, login_manager, csrf, limiter
from utils.helpers import setup_logger, score_color, score_label, format_datetime


def create_app(env: str = 'default') -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    cfg = config_map.get(env, config_map['default'])
    app.config.from_object(cfg)

    # Ensure required directories exist
    for key in ('UPLOAD_FOLDER', 'REPORTS_FOLDER', 'LOGS_FOLDER'):
        os.makedirs(app.config[key], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'tests'), exist_ok=True)

    # Extensions
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view         = 'auth.login_page'
    login_manager.login_message      = 'Please login to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from models.models import User
        return User.query.get(int(user_id))

    # Logging
    setup_logger('plagioscan', app.config['LOGS_FOLDER'])

    # Blueprints
    from routes.auth      import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.analysis  import analysis_bp
    from routes.admin     import admin_bp
    from routes.api       import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Root
    @app.route('/')
    def index():
        return render_template('index.html')

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):    return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):    return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e): return render_template('errors/500.html'), 500

    # Jinja globals & filters
    app.jinja_env.globals.update(score_color=score_color, score_label=score_label)
    app.jinja_env.filters['fmt_dt']    = format_datetime
    app.jinja_env.filters['score_col'] = score_color
    app.jinja_env.filters['score_lbl'] = score_label

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    from models.models import User
    with app.app_context():
        if User.query.count() == 0:
            admin = User(username='admin', email='admin@plagioscan.ai', role='admin', email_verified=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('[PlagioScan] Default admin: admin / admin123')
