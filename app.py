import os
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager, login_required
from config import Config
from models.database import db, User

# Detect if we're running inside Vercel (serverless — APScheduler won't work there)
IS_VERCEL = os.environ.get('VERCEL') == '1'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    
    # Session configuration for stability during OAuth redirects
    app.config.update(
        SESSION_COOKIE_NAME='autopost_session',
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False, # Set to True in production with HTTPS
        SESSION_COOKIE_HTTPONLY=True,
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
    
    # Initialize scheduler locally only — on Vercel this is handled by Supabase Edge Functions
    if not IS_VERCEL:
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            try:
                from services.scheduler import init_scheduler
                init_scheduler(app)
            except Exception as sched_err:
                import logging
                logging.getLogger(__name__).warning(
                    f"[startup] Scheduler could not start (non-fatal): {sched_err}"
                )
    else:
        import logging
        logging.getLogger(__name__).info("[startup] Running on Vercel — APScheduler disabled. Using Supabase Edge Functions for scheduling.")

    # Register blueprints (to be imported from routes)
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
        # Review hub removed — redirect to FAQ
        return redirect(url_for('faq'))

    @app.route('/faq')
    def faq():
        return render_template('faq.html')

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')

    # ----------------------------------------------------------------
    # Cron Endpoint — called by Supabase Edge Function every N minutes
    # Protected by a shared CRON_SECRET so no one else can trigger it.
    # ----------------------------------------------------------------
    @app.route('/api/cron/publish', methods=['POST'])
    def cron_publish():
        # Verify the secret header sent by Supabase
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

    # Create tables
    with app.app_context():
        db.create_all()

    return app


# ----------------------------------------------------------------
# Module-level app object — required by Vercel's WSGI entry point.
# Vercel looks for `app` at the top level of the file specified in
# vercel.json's `src` field.
# ----------------------------------------------------------------
app = create_app()

if __name__ == '__main__':
    import sys
    # Fix Windows console encoding so the startup banner prints without crashing
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        app = create_app()
    except Exception as startup_err:
        print(f"\n[FATAL] Application failed to start: {startup_err}")
        print("Check your .env file and make sure all required packages are installed.\n")
        sys.exit(1)

    port = int(os.environ.get('PORT', 5000))

    # Print a clear startup banner so the link is always visible in the terminal
    print("\n" + "="*50)
    print("  [OK] AutoPost AI is running!")
    print(f"  >>   Open in browser: http://localhost:{port}")
    print("="*50 + "\n")

    # host='0.0.0.0' makes the server reachable on any platform / network interface.
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)
