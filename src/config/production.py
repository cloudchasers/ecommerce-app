import os

class ProductionConfig:
    DEBUG = False
    TESTING = False
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    BANK_PUBLIC_BASE = os.environ.get('BANK_PUBLIC_BASE', 'https://bank.domain.com')
    MERCHANT_ACCOUNT = os.environ.get('MERCHANT_ACCOUNT', 'sweetcrumb-pastries')
    SESSION_COOKIE_SECURE = True
    ENABLE_BETA_FEATURES = False
