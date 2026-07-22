import os

class ProductionConfig:
    DEBUG = False
    TESTING = False
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # Strict production settings
    SESSION_COOKIE_SECURE = True
    ENABLE_BETA_FEATURES = False
