import os
from dotenv import load_dotenv

load_dotenv()

def _fix_db_url(url: str | None) -> str | None:
    """Supabase gives a 'postgres://' URI but SQLAlchemy needs 'postgresql://'.
    This one-line fix prevents a 'could not translate host' error on Vercel."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    SQLALCHEMY_DATABASE_URI = _fix_db_url(os.environ.get('DATABASE_URL')) or 'sqlite:///linkedin_ai.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API Keys
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    POLLINATIONS_API_URL = "https://image.pollinations.ai/prompt"
    
    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID')
    LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET')
    LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI') or 'http://localhost:5000/api/auth/callback'
    
    # Cron secret — Supabase Edge Function sends this to authenticate itself
    CRON_SECRET = os.environ.get('CRON_SECRET')
    
    # Session / Remember me
    REMEMBER_COOKIE_DURATION = 86400 * 30  # 30 days
