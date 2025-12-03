"""
Configuration Module
Handles application configuration and environment variables.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://localhost/veestributes')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRE = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRE = timedelta(days=30)

    # File Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'}

    # Stripe Payments
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@veestributes.com')

    # Redis/Celery
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    # Security
    BCRYPT_ROUNDS = 12
    RATE_LIMIT_DEFAULT = "200/day;50/hour"
    RATE_LIMIT_STORAGE_URL = REDIS_URL

    # External APIs
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '2b77ae1ea1ab4254983427a54e9402b8')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '711f154392294212946e74241af5714d')
    APPLE_MUSIC_KEY_ID = os.getenv('APPLE_MUSIC_KEY_ID')
    APPLE_MUSIC_PRIVATE_KEY = os.getenv('APPLE_MUSIC_PRIVATE_KEY')

    # Application
    APP_NAME = 'Veestributes'
    VERSION = '1.0.0'
    MAX_RELEASES_PER_USER = int(os.getenv('MAX_RELEASES_PER_USER', 100))
    MAX_TRACKS_PER_RELEASE = int(os.getenv('MAX_TRACKS_PER_RELEASE', 20))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///veestributes_dev.db'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///veestributes_test.db'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Production database URL (Neon PostgreSQL)
    SQLALCHEMY_DATABASE_URI = 'postgresql://neondb_owner:npg_JsS24jXGkpMi@ep-solitary-leaf-aei79o0g.c-2.us-east-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require'
    # Ensure HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    return config.get(config_name, config['default'])
