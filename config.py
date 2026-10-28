import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "campus-lost-and-found-dev-secret-key-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 Megabytes maximum upload size
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "item-images")

    # AI Matching configuration
    MATCH_MIN_SIMILARITY_SCORE = 0.15  # Minimum score (15%) to be considered a potential match
    MATCH_TOP_K = 5  # Top recommendations to return

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'campus_lost_found.db'}"
    )

class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # Disable CSRF for faster headless unit testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
