import os

class StagingConfig:
    DEBUG = False
    TESTING = True
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # Feature flags
    ENABLE_BETA_FEATURES = True
