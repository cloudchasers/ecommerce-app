import os

class DevelopmentConfig:
    DEBUG = True
    TESTING = False
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    BANK_PUBLIC_URL = os.environ.get('BANK_PUBLIC_URL', 'http://127.0.0.1:5001')
    MERCHANT_ACCOUNT = os.environ.get('MERCHANT_ACCOUNT', 'cloudchasers')
    ENABLE_BETA_FEATURES = True
