import os

class ProductionConfig:
    DEBUG = False
    TESTING = False
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    BANK_PUBLIC_URL = os.environ.get('BANK_PUBLIC_URL', 'https://bank.domain.com')
    MERCHANT_ACCOUNT = os.environ.get('MERCHANT_ACCOUNT', 'cloudchasers')
    SESSION_COOKIE_SECURE = True
    ENABLE_BETA_FEATURES = False
