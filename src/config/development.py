import os

class DevelopmentConfig:
    DEBUG = True
    TESTING = False
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    # Feature flags
    ENABLE_BETA_FEATURES = True
