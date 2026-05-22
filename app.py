import os
import sys
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager, login_required



def create_app():
    app = Flask(__name__)
    
    # Load config
    from config import Config
    app.config.from_object(Config)
    
    # CRITICAL: Tell Flask it's behind a proxy (fixes HTTPS/session issues on Render)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    from models.database import db, User
    db.init_app(app)
    
    # Session configuration for production
    app.config.update(
        SESSION_COOKIE_NAME='autopost_session',
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=True,      # Only send cookies over HTTPS
        SESSION_COOKIE_HTTPONLY=True,    # Prevent JavaScript access
    )
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login', next=request.path))
    
    # Initialize scheduler
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            from services.scheduler import init_scheduler
            init_scheduler(app)
        except Exception as sched_err:
            import logging
            logging.getLogger(__name__).warning(
                f"[startup] Scheduler could not start (non-fatal): {sched_err}"
            )

    # Register blueprints
    from routes.auth import auth_bp
    from routes.posts import posts_bp
    from routes.schedule import schedule_bp
    from routes.settings import settings_bp
    from routes.analytics import analytics_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')
    app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')

    # Template routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login')
    def login():
        return render_template('login.html')
        
    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/create')
    @login_required
    def create():
        return render_template('create.html')

    @app.route('/calendar')
    @login_required
    def calendar():
        return render_template('calendar.html')

    @app.route('/queue')
    def queue():
        return redirect(url_for('faq'))

    @app.route('/faq')
    def faq():
        return render_template('faq.html')

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')

    # Cron Endpoint
    @app.route('/api/cron/publish', methods=['POST'])
    def cron_publish():
        from config import Config
        auth_header = request.headers.get('X-Cron-Auth', '')
        if Config.CRON_SECRET and auth_header != Config.CRON_SECRET:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from services.scheduler import publish_scheduled_posts
            publish_scheduled_posts(app)
            return jsonify({'status': 'ok', 'message': 'Scheduled posts processed.'}), 200
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[cron] Error: {e}")
            return jsonify({'error': str(e)}), 500

    # Create tables ONLY when app context is available
    with app.app_context():
        db.create_all()

    return app


app = create_app()

# Local development only
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*50)
    print("  [OK] AutoPost AI is running!")
    print(f"  >>   Open in browser: http://localhost:{port}")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)