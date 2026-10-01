"""
PlagioScan AI — Development Runner
"""
import os, sys, subprocess, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PACKAGES = [
    ('flask',              'flask'),
    ('flask-sqlalchemy',   'flask_sqlalchemy'),
    ('flask-login',        'flask_login'),
    ('flask-wtf',          'flask_wtf'),
    ('flask-limiter',      'flask_limiter'),
    ('python-dotenv',      'dotenv'),
    ('scikit-learn',       'sklearn'),
    ('pypdf',              'pypdf'),
    ('python-docx',        'docx'),
    ('reportlab',          'reportlab'),
    ('requests',           'requests'),
    ('beautifulsoup4',     'bs4'),
    ('Pillow',             'PIL'),
    ('werkzeug',           'werkzeug'),
]

def setup():
    print('=' * 62)
    print('  PlagioScan AI  --  Intelligent Plagiarism Detection')
    print('=' * 62)
    print('\n[1/3] Checking dependencies...')
    missing = []
    for pkg, imp in PACKAGES:
        try:
            __import__(imp)
            print(f'      [OK] {pkg}')
        except ImportError:
            missing.append(pkg)
            print(f'      [!!] {pkg} (missing - will install)')

    if missing:
        print(f'\n[2/3] Installing missing packages: {", ".join(missing)}')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)
        print('      All packages installed.')
    else:
        print('[2/3] All dependencies present [OK]')

    print('[3/3] Initializing application...')
    from app import create_app
    app = create_app('development')
    print('      [OK] Database initialized')
    print('      [OK] Default admin: admin / admin123')
    print('\n' + '=' * 62)
    print('  Server: http://127.0.0.1:5000')
    print('  API:    http://127.0.0.1:5000/api/v1/status')
    print('  Press Ctrl+C to stop')
    print('=' * 62 + '\n')
    return app


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = setup()
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)
